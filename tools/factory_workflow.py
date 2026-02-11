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
    ProductionLineStatus, generate_id, ProcessStep
)
from tools.factory_agents import (
    FactoryDirector, ProcessExpert, ProductionLineLeader,
    Worker, QualityInspector
)
from database.factory_db import FactoryDB


class FactoryWorkflow:
    """Orchestrates factory operations and workflows"""

    def __init__(self, factory_name: str = "Data Factory", db_path: str = "database/factory.db"):
        self.factory_state = FactoryState(factory_name)
        self.db = FactoryDB(db_path)

        # Initialize agents
        self.director = FactoryDirector()
        self.expert = ProcessExpert()
        self.leader = ProductionLineLeader()
        self.inspector = QualityInspector()
        self.workers: Dict[str, Worker] = {}

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
        """Create and optionally execute a complete production workflow"""
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

        # Stage 1: Director evaluates requirement
        director_eval = self.director.execute(self.factory_state, {
            'action': 'evaluate_requirement',
            'requirement': requirement
        })
        workflow['stages']['director_evaluation'] = director_eval

        if not director_eval.get('feasible'):
            workflow['status'] = 'rejected'
            workflow['timestamps']['completed_at'] = datetime.now().isoformat()
            return workflow

        # Stage 2: Expert designs process
        expert_design = self.expert.execute(self.factory_state, {
            'action': 'design',
            'requirement': requirement
        })
        process_spec = expert_design['process_spec']
        workflow['stages']['expert_design'] = {
            'process_id': process_spec.process_id,
            'steps': [s.value for s in process_spec.steps],
            'estimated_duration': process_spec.estimated_duration
        }
        self.factory_state.add_process_spec(process_spec)
        self.db.save_process_spec(process_spec)

        # Stage 3: Director creates production plan
        plan = self.director.execute(self.factory_state, {
            'action': 'create_plan',
            'requirement': requirement,
            'process_spec': process_spec
        })['plan']
        workflow['stages']['production_plan'] = plan

        # Stage 4: Leader creates production lines
        lines_needed = plan['production_lines_needed']
        workers_per_line = plan['workers_per_line']
        production_lines = []

        for i in range(lines_needed):
            line_creation = self.leader.execute(self.factory_state, {
                'action': 'create',
                'process_spec': process_spec,
                'worker_count': workers_per_line,
                'line_name': f"{requirement.product_name}_Line_{i+1}"
            })
            line = line_creation['production_line']
            production_lines.append(line)
            self.factory_state.add_production_line(line)
            self.db.save_production_line(line)

            # Register workers with workflow
            for worker in line.workers:
                worker_agent = Worker(worker.worker_id)
                self.workers[worker.worker_id] = worker_agent

        workflow['stages']['production_lines_created'] = {
            'count': lines_needed,
            'line_ids': [line.line_id for line in production_lines]
        }

        # Stage 5: Create work orders
        work_orders = []
        for i, input_item in enumerate(requirement.input_data):
            order = WorkOrder(
                work_order_id=generate_id('wo'),
                requirement_id=requirement.requirement_id,
                product_name=requirement.product_name,
                process_spec=process_spec,
                assigned_line_id=production_lines[i % lines_needed].line_id,
                status=WorkOrderStatus.PENDING,
                priority=requirement.priority,
                expected_completion=datetime.now() + timedelta(minutes=process_spec.estimated_duration)
            )
            work_orders.append(order)
            self.factory_state.add_work_order(order)
            self.db.save_work_order(order)

        workflow['stages']['work_orders_created'] = {
            'count': len(work_orders),
            'order_ids': [wo.work_order_id for wo in work_orders]
        }

        # Stage 6: Execute tasks if auto_execute is True
        if auto_execute:
            execution_results = []
            for order_idx, order in enumerate(work_orders):
                # Get assigned line
                line = self.factory_state.get_production_line(order.assigned_line_id)
                if not line or not line.workers:
                    continue

                # Get a worker
                worker = self.workers.get(line.workers[0].worker_id)
                if not worker:
                    continue

                # Execute each step
                for step in process_spec.steps:
                    execution = worker.execute(self.factory_state, {
                        'action': 'execute_task',
                        'work_order': order,
                        'input_data': requirement.input_data[order_idx],
                        'process_step': step
                    })['execution']

                    self.factory_state.record_task_execution(execution)
                    self.db.save_task_execution(execution)

                    # Quality check
                    quality_threshold = requirement.sla_metrics.get('quality_threshold', 0.9)
                    check = self.inspector.execute(self.factory_state, {
                        'action': 'inspect',
                        'execution': execution,
                        'quality_threshold': quality_threshold
                    })['check_result']

                    self.factory_state.record_quality_check(check)
                    self.db.save_quality_check(check)

                    execution_results.append({
                        'execution_id': execution.execution_id,
                        'quality_passed': check.passed,
                        'tokens_consumed': execution.token_consumed
                    })

                # Mark order as completed
                order.status = WorkOrderStatus.COMPLETED
                order.completed_at = datetime.now()
                self.db.save_work_order(order)

            workflow['stages']['task_executions'] = {
                'count': len(execution_results),
                'quality_passed': sum(1 for r in execution_results if r['quality_passed']),
                'total_tokens': sum(r['tokens_consumed'] for r in execution_results)
            }

        workflow['status'] = 'completed' if auto_execute else 'created'
        workflow['timestamps']['completed_at'] = datetime.now().isoformat()

        return workflow

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
