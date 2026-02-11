"""
Factory Workflow - Orchestration layer for factory operations
Manages the complete workflow from product requirement to delivery
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

from tools.factory_framework import (
    FactoryState, ProductRequirement, ProcessSpec, ProductionLine,
    WorkOrder, TaskExecution, QualityCheckResult, WorkOrderStatus,
    ProductionLineStatus, generate_id, ProcessStep, ProductType, GraphNode, GraphRelationship
)
from tools.factory_agents import (
    FactoryDirector, ProcessExpert, ProductionLineLeader,
    Worker, QualityInspector
)
from database.factory_db import FactoryDB


class FactoryWorkflow:
    """Orchestrates factory operations and workflows"""

    # 两条固定产线ID
    ADDRESS_CLEANING_LINE_ID = "line_address_cleaning"
    ADDRESS_TO_GRAPH_LINE_ID = "line_address_to_graph"

    def __init__(self, factory_name: str = "Data Factory", db_path: str = "database/factory.db", init_production_lines: bool = True):
        self.factory_state = FactoryState(factory_name)
        self.db = FactoryDB(db_path)
        self.production_lines_initialized = False

        # Initialize agents
        self.director = FactoryDirector()
        self.expert = ProcessExpert()
        self.leader = ProductionLineLeader()
        self.inspector = QualityInspector()
        self.workers: Dict[str, Worker] = {}

        # Initialize fixed production lines if needed
        if init_production_lines:
            self._initialize_production_lines()

    def _initialize_production_lines(self) -> None:
        """Initialize the two fixed production lines for the address-to-graph pipeline"""
        if self.production_lines_initialized:
            return

        # Line 1: Address Cleaning
        process_spec_1 = ProcessSpec(
            process_id=generate_id('proc'),
            process_name='地址清洗工艺',
            steps=[ProcessStep.PARSING, ProcessStep.STANDARDIZATION, ProcessStep.VALIDATION],
            estimated_duration=1.0,
            required_workers=2,
            quality_rules={'min_quality_score': 0.85},
            resource_requirements={'cpu': 'standard', 'memory': '512MB'}
        )
        self.factory_state.add_process_spec(process_spec_1)
        self.db.save_process_spec(process_spec_1)

        line_1 = self.leader.execute(self.factory_state, {
            'action': 'create',
            'process_spec': process_spec_1,
            'worker_count': 2,
            'line_name': '地址清洗产线'
        })['production_line']

        # 强制设置产线ID为固定值
        line_1.line_id = self.ADDRESS_CLEANING_LINE_ID

        self.factory_state.add_production_line(line_1)
        self.db.save_production_line(line_1)

        for worker in line_1.workers:
            worker_agent = Worker(worker.worker_id)
            self.workers[worker.worker_id] = worker_agent

        # Line 2: Address to Graph
        process_spec_2 = ProcessSpec(
            process_id=generate_id('proc'),
            process_name='地址转图谱工艺',
            steps=[ProcessStep.EXTRACTION, ProcessStep.FUSION, ProcessStep.VALIDATION],
            estimated_duration=1.0,
            required_workers=2,
            quality_rules={'min_quality_score': 0.85},
            resource_requirements={'cpu': 'standard', 'memory': '512MB'}
        )
        self.factory_state.add_process_spec(process_spec_2)
        self.db.save_process_spec(process_spec_2)

        line_2 = self.leader.execute(self.factory_state, {
            'action': 'create',
            'process_spec': process_spec_2,
            'worker_count': 2,
            'line_name': '地址-图谱产线'
        })['production_line']

        # 强制设置产线ID为固定值
        line_2.line_id = self.ADDRESS_TO_GRAPH_LINE_ID

        self.factory_state.add_production_line(line_2)
        self.db.save_production_line(line_2)

        for worker in line_2.workers:
            worker_agent = Worker(worker.worker_id)
            self.workers[worker.worker_id] = worker_agent

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
            execution_results = {'cleaning': [], 'graph': []}

            for order_idx, (cleaning_order, graph_order) in enumerate(zip(cleaning_orders, graph_orders)):
                input_item = requirement.input_data[order_idx]

                # Execute cleaning pipeline
                cleaned_address = self._execute_cleaning_pipeline(
                    cleaning_order, cleaning_spec, input_item, requirement
                )
                execution_results['cleaning'].append({
                    'order_id': cleaning_order.work_order_id,
                    'input': input_item.get('raw', ''),
                    'output': cleaned_address
                })

                # Execute graph generation pipeline
                graph_nodes, graph_relationships = self._execute_graph_pipeline(
                    graph_order, graph_spec, cleaned_address, requirement, input_item.get('id', '')
                )
                execution_results['graph'].append({
                    'order_id': graph_order.work_order_id,
                    'nodes_generated': len(graph_nodes),
                    'relationships_generated': len(graph_relationships)
                })

            workflow['stages']['task_executions'] = {
                'cleaning_completed': len(execution_results['cleaning']),
                'graph_completed': len(execution_results['graph']),
                'graph_nodes_total': sum(r['nodes_generated'] for r in execution_results['graph']),
                'graph_relationships_total': sum(r['relationships_generated'] for r in execution_results['graph'])
            }

        workflow['status'] = 'completed' if auto_execute else 'created'
        workflow['timestamps']['completed_at'] = datetime.now().isoformat()

        return workflow

    def _execute_cleaning_pipeline(
        self,
        order: WorkOrder,
        spec: ProcessSpec,
        input_item: Dict[str, Any],
        requirement: ProductRequirement
    ) -> str:
        """Execute address cleaning pipeline and return standardized address"""
        line = self.factory_state.get_production_line(order.assigned_line_id)
        if not line or not line.workers:
            return ""

        worker = self.workers.get(line.workers[0].worker_id)
        if not worker:
            return ""

        cleaned_address = ""
        quality_threshold = requirement.sla_metrics.get('quality_threshold', 0.9)

        for step in spec.steps:
            execution = worker.execute(self.factory_state, {
                'action': 'execute_task',
                'work_order': order,
                'input_data': input_item,
                'process_step': step
            })['execution']

            self.factory_state.record_task_execution(execution)
            self.db.save_task_execution(execution)

            if step == ProcessStep.STANDARDIZATION:
                cleaned_address = execution.output_data.get('standardized_address', '')

            # Quality check
            check = self.inspector.execute(self.factory_state, {
                'action': 'inspect',
                'execution': execution,
                'quality_threshold': quality_threshold
            })['check_result']

            self.factory_state.record_quality_check(check)
            self.db.save_quality_check(check)

        order.status = WorkOrderStatus.COMPLETED
        order.completed_at = datetime.now()
        self.db.save_work_order(order)

        return cleaned_address

    def _execute_graph_pipeline(
        self,
        order: WorkOrder,
        spec: ProcessSpec,
        standardized_address: str,
        requirement: ProductRequirement,
        source_address_id: str
    ) -> tuple:
        """Execute address-to-graph pipeline and return generated nodes and relationships"""
        line = self.factory_state.get_production_line(order.assigned_line_id)
        if not line or not line.workers:
            return [], []

        worker = self.workers.get(line.workers[0].worker_id)
        if not worker:
            return [], []

        graph_nodes = []
        graph_relationships = []
        quality_threshold = requirement.sla_metrics.get('quality_threshold', 0.9)

        for step in spec.steps:
            execution = worker.execute(self.factory_state, {
                'action': 'execute_task',
                'work_order': order,
                'input_data': {'standardized_address': standardized_address},
                'process_step': step
            })['execution']

            self.factory_state.record_task_execution(execution)
            self.db.save_task_execution(execution)

            if step == ProcessStep.EXTRACTION or step == ProcessStep.FUSION:
                output = execution.output_data
                # Extract graph nodes from output
                for node_data in output.get('nodes', []):
                    node = GraphNode(
                        node_id=generate_id('node'),
                        node_type=node_data.get('type', 'location'),
                        name=node_data.get('name', ''),
                        properties=node_data.get('properties', {}),
                        source_address=source_address_id
                    )
                    graph_nodes.append(node)
                    self.factory_state.add_graph_node(node)
                    self.db.save_graph_node(node)

                # Extract graph relationships from output
                for rel_data in output.get('relationships', []):
                    relationship = GraphRelationship(
                        relationship_id=generate_id('rel'),
                        source_node_id=rel_data.get('source', ''),
                        target_node_id=rel_data.get('target', ''),
                        relationship_type=rel_data.get('type', 'related'),
                        properties=rel_data.get('properties', {}),
                        source_address=source_address_id
                    )
                    graph_relationships.append(relationship)
                    self.factory_state.add_graph_relationship(relationship)
                    self.db.save_graph_relationship(relationship)

            # Quality check
            check = self.inspector.execute(self.factory_state, {
                'action': 'inspect',
                'execution': execution,
                'quality_threshold': quality_threshold
            })['check_result']

            self.factory_state.record_quality_check(check)
            self.db.save_quality_check(check)

        order.status = WorkOrderStatus.COMPLETED
        order.completed_at = datetime.now()
        self.db.save_work_order(order)

        return graph_nodes, graph_relationships

    def get_factory_status(self) -> Dict[str, Any]:
        """Get current factory operational status"""
        status = self.director.execute(self.factory_state, {
            'action': 'status'
        })
        return status

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
        line = self.factory_state.get_production_line(line_id)
        if not line:
            return {'error': 'Production line not found'}

        progress = self.leader.execute(self.factory_state, {
            'action': 'monitor',
            'production_line': line
        })
        return progress['progress']

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
