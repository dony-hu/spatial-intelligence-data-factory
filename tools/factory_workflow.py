"""
Factory Workflow - Orchestration layer for factory operations
Manages the complete workflow from product requirement to delivery
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

from tools.factory_framework import (
    FactoryState, ProductRequirement, ProcessSpec, ProductionLine,
    WorkOrder, WorkOrderStatus, ProductionLineStatus, generate_id
)
from tools.factory_agents import (
    FactoryDirector, ProcessExpert, ProductionLineLeader,
    Worker, QualityInspector
)
from tools.factory_roles import (
    DirectorService,
    ProcessExpertService,
    ProductionLineLeaderService,
    WorkerExecutionService,
)
from database.factory_db import FactoryDB


class FactoryWorkflow:
    """Orchestrates factory operations and workflows"""

    # 两条固定产线ID
    ADDRESS_CLEANING_LINE_ID = "line_address_cleaning"
    ADDRESS_TO_GRAPH_LINE_ID = "line_address_to_graph"
    REQUIRED_APPROVAL_GATES = (
        "kpi_frozen",
        "compliance_approved",
        "release_window_confirmed",
    )

    def __init__(self, factory_name: str = "Data Factory", db_path: str = "database/factory.db", init_production_lines: bool = True):
        self.factory_state = FactoryState(factory_name)
        self.db = FactoryDB(db_path)
        self.production_lines_initialized = False
        self.graph_node_ids: set = set()
        self.graph_relationship_ids: set = set()
        self.approval_status: Dict[str, bool] = {
            gate: False for gate in self.REQUIRED_APPROVAL_GATES
        }
        self.approval_records: List[Dict[str, Any]] = []

        # Initialize agents
        self.director = FactoryDirector()
        self.expert = ProcessExpert()
        self.leader = ProductionLineLeader()
        self.inspector = QualityInspector()
        self.workers: Dict[str, Worker] = {}
        self.director_service = DirectorService(self.factory_state, self.director)
        self.process_expert_service = ProcessExpertService(self.expert)
        self.line_leader_service = ProductionLineLeaderService(
            factory_state=self.factory_state,
            db=self.db,
            leader=self.leader,
            workers=self.workers,
        )
        self.worker_execution_service = WorkerExecutionService(
            factory_state=self.factory_state,
            db=self.db,
            workers=self.workers,
            inspector=self.inspector,
            graph_node_ids=self.graph_node_ids,
            graph_relationship_ids=self.graph_relationship_ids,
        )

        # Initialize fixed production lines if needed
        if init_production_lines:
            self._initialize_production_lines()

    def approve_gate(self, gate_name: str, approver: str, note: str = "") -> Dict[str, Any]:
        """Record manual approval for a required governance gate."""
        if gate_name not in self.approval_status:
            return {
                "status": "rejected",
                "error": f"Unknown approval gate: {gate_name}",
                "allowed_gates": list(self.REQUIRED_APPROVAL_GATES),
            }

        self.approval_status[gate_name] = True
        record = {
            "gate": gate_name,
            "approved": True,
            "approver": approver,
            "note": note,
            "approved_at": datetime.now().isoformat(),
        }
        self.approval_records.append(record)
        return {"status": "approved", "record": record}

    def approve_all_required_gates(self, approver: str, note: str = "demo auto approval") -> List[Dict[str, Any]]:
        """Convenience helper for demos/tests to satisfy required gates."""
        return [
            self.approve_gate(gate, approver=approver, note=note)
            for gate in self.REQUIRED_APPROVAL_GATES
        ]

    def get_missing_approvals(self) -> List[str]:
        """Return list of required gates still pending approval."""
        return [gate for gate, approved in self.approval_status.items() if not approved]

    def _initialize_production_lines(self) -> None:
        """Initialize the two fixed production lines for the address-to-graph pipeline"""
        if self.production_lines_initialized:
            return

        process_spec_1 = self.process_expert_service.create_cleaning_spec()
        self.factory_state.add_process_spec(process_spec_1)
        self.db.save_process_spec(process_spec_1)

        self.line_leader_service.create_line(
            process_spec=process_spec_1,
            line_name='地址清洗产线',
            line_id=self.ADDRESS_CLEANING_LINE_ID,
            worker_count=2,
        )

        process_spec_2 = self.process_expert_service.create_graph_spec()
        self.factory_state.add_process_spec(process_spec_2)
        self.db.save_process_spec(process_spec_2)

        self.line_leader_service.create_line(
            process_spec=process_spec_2,
            line_name='地址-图谱产线',
            line_id=self.ADDRESS_TO_GRAPH_LINE_ID,
            worker_count=2,
        )

        self.production_lines_initialized = True

    def submit_product_requirement(self, requirement: ProductRequirement) -> Dict[str, Any]:
        """Submit a new product requirement to the factory"""
        # Save to database
        self.db.save_product_requirement(requirement)

        # Register with factory state
        self.factory_state.add_product_requirement(requirement)

        return {
            'requirement_id': requirement.requirement_id,
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat(),
            'product_name': requirement.product_name
        }

    def create_production_workflow(
        self,
        requirement: ProductRequirement,
        auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        Create and optionally execute a complete production workflow with two pipelines:
        Pipeline 1: Address Cleaning (原始地址 -> 标准化地址)
        Pipeline 2: Address-to-Graph (标准化地址 -> 图谱节点和关系)
        """
        workflow_id = generate_id('wf')
        workflow_start = datetime.now()

        workflow = {
            'workflow_id': workflow_id,
            'requirement_id': requirement.requirement_id,
            'stages': {},
            'timestamps': {
                'started_at': workflow_start.isoformat()
            }
        }

        # Get the two fixed production lines
        cleaning_line = self.factory_state.get_production_line(self.ADDRESS_CLEANING_LINE_ID)
        graph_line = self.factory_state.get_production_line(self.ADDRESS_TO_GRAPH_LINE_ID)

        if not cleaning_line or not graph_line:
            workflow['status'] = 'rejected'
            workflow['error'] = 'Production lines not initialized'
            return workflow

        # Get process specs for both lines
        cleaning_specs = list(self.factory_state.process_specs.values())
        if len(cleaning_specs) < 2:
            workflow['status'] = 'rejected'
            workflow['error'] = 'Process specifications not found'
            return workflow

        cleaning_spec = cleaning_specs[0]
        graph_spec = cleaning_specs[1]

        workflow['stages']['pipeline_setup'] = {
            'cleaning_line': cleaning_line.line_name,
            'graph_line': graph_line.line_name
        }

        # Stage 1: Create work orders for address cleaning pipeline
        cleaning_orders = []
        graph_orders = []

        for i, input_item in enumerate(requirement.input_data):
            # Order for cleaning line
            cleaning_order = WorkOrder(
                work_order_id=generate_id('wo'),
                requirement_id=requirement.requirement_id,
                product_name=f"{requirement.product_name}_Cleaning",
                process_spec=cleaning_spec,
                assigned_line_id=cleaning_line.line_id,
                status=WorkOrderStatus.PENDING,
                priority=requirement.priority,
                expected_completion=datetime.now() + timedelta(minutes=cleaning_spec.estimated_duration)
            )
            cleaning_orders.append(cleaning_order)
            self.factory_state.add_work_order(cleaning_order)
            self.db.save_work_order(cleaning_order)

            # Order for graph line (depends on cleaning order)
            graph_order = WorkOrder(
                work_order_id=generate_id('wo'),
                requirement_id=requirement.requirement_id,
                product_name=f"{requirement.product_name}_ToGraph",
                process_spec=graph_spec,
                assigned_line_id=graph_line.line_id,
                status=WorkOrderStatus.PENDING,
                priority=requirement.priority,
                depends_on_work_order_id=cleaning_order.work_order_id,
                expected_completion=datetime.now() + timedelta(minutes=cleaning_spec.estimated_duration + graph_spec.estimated_duration)
            )
            graph_orders.append(graph_order)
            self.factory_state.add_work_order(graph_order)
            self.db.save_work_order(graph_order)

        workflow['stages']['work_orders_created'] = {
            'cleaning_orders': len(cleaning_orders),
            'graph_orders': len(graph_orders),
            'total_orders': len(cleaning_orders) + len(graph_orders)
        }

        # Stage 2: Execute if auto_execute is True
        if auto_execute:
            missing_approvals = self.get_missing_approvals()
            workflow['stages']['approval_gates'] = {
                'required': list(self.REQUIRED_APPROVAL_GATES),
                'approved': [gate for gate, ok in self.approval_status.items() if ok],
                'missing': missing_approvals,
                'records': list(self.approval_records),
            }
            if missing_approvals:
                workflow['status'] = 'pending_approval'
                workflow['timestamps']['blocked_at'] = datetime.now().isoformat()
                workflow['error'] = f"Missing required approvals: {', '.join(missing_approvals)}"
                return workflow

            execution_results = {'cleaning': [], 'graph': [], 'failed_cases': []}

            for order_idx, (cleaning_order, graph_order) in enumerate(zip(cleaning_orders, graph_orders)):
                input_item = requirement.input_data[order_idx]

                # Execute cleaning pipeline
                source_id = str(
                    input_item.get('id')
                    or input_item.get('source')
                    or input_item.get('raw')
                    or input_item.get('address', '')
                )
                cleaning_output = self._execute_cleaning_pipeline(
                    cleaning_order, cleaning_spec, input_item, requirement
                )
                execution_results['cleaning'].append({
                    'order_id': cleaning_order.work_order_id,
                    'source_id': source_id,
                    'input': input_item.get('raw') or input_item.get('address', ''),
                    'input_item': dict(input_item),
                    'output': cleaning_output
                })

                if not cleaning_output.get('standardized_address'):
                    execution_results['failed_cases'].append({
                        'source_id': source_id,
                        'stage': 'cleaning',
                        'reason': 'CLEANING_INVALID_OUTPUT',
                    })
                    continue

                # Execute graph generation pipeline
                graph_nodes, graph_relationships, graph_gate, graph_metrics = self._execute_graph_pipeline(
                    graph_order,
                    graph_spec,
                    cleaning_output,
                    requirement,
                    str(input_item.get('id') or input_item.get('source') or input_item.get('raw') or input_item.get('address', '')),
                )
                execution_results['graph'].append({
                    'order_id': graph_order.work_order_id,
                    'source_id': str(input_item.get('id') or input_item.get('source') or input_item.get('raw') or input_item.get('address', '')),
                    'nodes_generated': len(graph_nodes),
                    'relationships_generated': len(graph_relationships),
                    'nodes_merged': graph_metrics.get('nodes_merged', 0),
                    'relationships_merged': graph_metrics.get('relationships_merged', 0),
                    'nodes': graph_metrics.get('nodes', []),
                    'relationships': graph_metrics.get('relationships', []),
                    'gate_pass': graph_gate['pass'],
                })
                if not graph_gate['pass']:
                    source_id = input_item.get('id') or input_item.get('source') or input_item.get('raw') or input_item.get('address', '')
                    execution_results['failed_cases'].append({
                        'source_id': source_id,
                        'stage': 'graph',
                        'reason': graph_gate['reason'],
                    })

            workflow['stages']['task_executions'] = {
                'cleaning_completed': len(execution_results['cleaning']),
                'graph_completed': len(execution_results['graph']),
                'graph_nodes_total': sum(r['nodes_generated'] for r in execution_results['graph']),
                'graph_relationships_total': sum(r['relationships_generated'] for r in execution_results['graph']),
                'graph_nodes_generated_total': sum(r['nodes_generated'] for r in execution_results['graph']),
                'graph_relationships_generated_total': sum(r['relationships_generated'] for r in execution_results['graph']),
                'graph_nodes_merged_total': sum(r['nodes_merged'] for r in execution_results['graph']),
                'graph_relationships_merged_total': sum(r['relationships_merged'] for r in execution_results['graph']),
                'cleaning_case_details': execution_results['cleaning'],
                'graph_case_details': [
                    {
                        'source_id': r.get('source_id', ''),
                        'nodes_generated': r.get('nodes_generated', 0),
                        'relationships_generated': r.get('relationships_generated', 0),
                        'nodes_merged': r.get('nodes_merged', 0),
                        'relationships_merged': r.get('relationships_merged', 0),
                        'nodes': r.get('nodes', []),
                        'relationships': r.get('relationships', []),
                    }
                    for r in execution_results['graph']
                ],
                'failed_cases': execution_results['failed_cases'],
            }
            if execution_results['failed_cases']:
                workflow['status'] = 'failed'
                workflow['error'] = 'One or more cases failed output gates'
                workflow['timestamps']['completed_at'] = datetime.now().isoformat()
                return workflow

        workflow['status'] = 'completed' if auto_execute else 'created'
        workflow['timestamps']['completed_at'] = datetime.now().isoformat()

        return workflow

    def _execute_cleaning_pipeline(
        self,
        order: WorkOrder,
        spec: ProcessSpec,
        input_item: Dict[str, Any],
        requirement: ProductRequirement
    ) -> Dict[str, Any]:
        """Execute address cleaning pipeline and return structured cleaning output."""
        return self.worker_execution_service.execute_cleaning_pipeline(
            order=order,
            spec=spec,
            input_item=input_item,
            requirement=requirement,
        )

    def _execute_graph_pipeline(
        self,
        order: WorkOrder,
        spec: ProcessSpec,
        cleaning_output: Dict[str, Any],
        requirement: ProductRequirement,
        source_address_id: str
    ) -> tuple:
        """Execute address-to-graph pipeline and return generated nodes and relationships"""
        return self.worker_execution_service.execute_graph_pipeline(
            order=order,
            spec=spec,
            cleaning_output=cleaning_output,
            requirement=requirement,
            source_address_id=source_address_id,
        )

    def _mark_line_task_started(self, line: ProductionLine) -> None:
        """Mark line as running for a work order execution."""
        self.worker_execution_service._mark_line_task_started(line)

    def _mark_line_task_completed(self, line: ProductionLine, tokens: float, quality_score: float) -> None:
        """Persist line-level metrics after a work order completes."""
        self.worker_execution_service._mark_line_task_completed(line, tokens, quality_score)

    def _mark_line_task_failed(self, line: ProductionLine, tokens: float, quality_score: float) -> None:
        """Persist line-level metrics when a work order fails output gates."""
        self.worker_execution_service._mark_line_task_failed(line, tokens, quality_score)

    def get_factory_status(self) -> Dict[str, Any]:
        """Get current factory operational status"""
        return self.director_service.get_factory_status()

    def list_active_work_orders(self) -> List[Dict[str, Any]]:
        """List all active work orders"""
        active_orders = self.factory_state.get_active_work_orders()
        return [order.to_dict() for order in active_orders]

    def list_pending_work_orders(self) -> List[Dict[str, Any]]:
        """List all pending work orders"""
        pending_orders = self.factory_state.get_pending_work_orders()
        return [order.to_dict() for order in pending_orders]

    def get_worker_cost_summary(self) -> Dict[str, Any]:
        """Get worker cost summary by production line"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'lines': {},
            'total_tokens': 0.0,
            'average_cost_per_item': 0.0
        }

        for line_id, line in self.factory_state.production_lines.items():
            if line.completed_tasks == 0:
                avg_cost = 0.0
            else:
                avg_cost = line.total_tokens_consumed / line.completed_tasks

            summary['lines'][line_id] = {
                'line_name': line.line_name,
                'total_tokens': line.total_tokens_consumed,
                'completed_tasks': line.completed_tasks,
                'average_cost_per_item': avg_cost,
                'worker_count': len(line.workers),
                'utilization': line.utilization_rate
            }

            summary['total_tokens'] += line.total_tokens_consumed

        if self.factory_state.metrics.total_tasks_completed > 0:
            summary['average_cost_per_item'] = (
                summary['total_tokens'] / self.factory_state.metrics.total_tasks_completed
            )

        return summary

    def get_quality_report(self) -> Dict[str, Any]:
        """Get quality inspection report"""
        report = self.inspector.execute(self.factory_state, {
            'action': 'report'
        })
        return report['report']

    def get_production_line_status(self, line_id: str) -> Dict[str, Any]:
        """Get status of a specific production line"""
        return self.line_leader_service.get_line_status(line_id)

    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of all active workflows"""
        self.factory_state.update_metrics()

        return {
            'timestamp': datetime.now().isoformat(),
            'factory_name': self.factory_state.factory_name,
            'factory_status': self.factory_state.status,
            'production_lines': {
                'total': len(self.factory_state.production_lines),
                'running': sum(
                    1 for line in self.factory_state.production_lines.values()
                    if line.status == ProductionLineStatus.RUNNING
                ),
                'idle': sum(
                    1 for line in self.factory_state.production_lines.values()
                    if line.status == ProductionLineStatus.IDLE
                )
            },
            'work_orders': {
                'total': len(self.factory_state.work_orders),
                'pending': len(self.factory_state.get_pending_work_orders()),
                'in_progress': len(self.factory_state.get_active_work_orders()),
                'completed': sum(
                    1 for wo in self.factory_state.work_orders.values()
                    if wo.status == WorkOrderStatus.COMPLETED
                )
            },
            'metrics': self.factory_state.metrics.to_dict(),
            'cost_summary': self.get_worker_cost_summary()
        }

    def export_state_to_json(self) -> str:
        """Export factory state as JSON"""
        return self.factory_state.to_json()

    def get_database_statistics(self) -> Dict[str, Any]:
        """Get statistics from database"""
        return self.db.get_statistics()
