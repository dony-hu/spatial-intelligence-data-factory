"""
Factory Agents - Five specialized agent roles for the factory demonstration system
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import random

from tools.factory_framework import (
    FactoryRole, ProcessStep, WorkOrderStatus, ProductionLineStatus,
    FactoryState, ProductRequirement, ProcessSpec, ProductionLine,
    WorkOrder, Worker, TaskExecution, QualityCheckResult,
    generate_id, ProductType
)


class FactoryAgent(ABC):
    """Base class for all factory agents"""

    def __init__(self, agent_id: str, role: FactoryRole, name: str):
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.decisions_made: List[Dict[str, Any]] = []
        self.created_at = datetime.now()

    @abstractmethod
    def execute(self, factory_state: FactoryState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent's responsibility"""
        pass

    def log_decision(self, action: str, details: Dict[str, Any]) -> None:
        """Log a decision made by this agent"""
        self.decisions_made.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        })


class FactoryDirector(FactoryAgent):
    """
    厂长 - Factory Director
    Responsible for overall factory management, requirement evaluation, and production planning
    """

    def __init__(self):
        super().__init__(
            agent_id=generate_id('dir'),
            role=FactoryRole.DIRECTOR,
            name='Factory Director (厂长)'
        )

    def evaluate_requirement(self, requirement: ProductRequirement) -> Tuple[bool, Dict[str, Any]]:
        """Evaluate if a product requirement is feasible"""
        feasibility = {
            'feasible': True,
            'estimated_lines_needed': 1,
            'estimated_workers_needed': 3,
            'estimated_duration_minutes': 120,
            'risk_level': 'low',
            'confidence': 0.95,
            'concerns': []
        }

        # Assess based on input data size
        input_size = len(requirement.input_data)
        if input_size > 1000:
            feasibility['estimated_lines_needed'] = max(1, input_size // 500)
            feasibility['estimated_workers_needed'] = feasibility['estimated_lines_needed'] * 3
            feasibility['risk_level'] = 'medium' if input_size > 5000 else 'low'

        # Check SLA
        max_duration = requirement.sla_metrics.get('max_duration', 240)
        if feasibility['estimated_duration_minutes'] > max_duration:
            feasibility['concerns'].append(f"Estimated duration exceeds SLA: {feasibility['estimated_duration_minutes']} > {max_duration}")
            feasibility['risk_level'] = 'high'

        quality_threshold = requirement.sla_metrics.get('quality_threshold', 0.9)
        if quality_threshold > 0.98:
            feasibility['concerns'].append("Very high quality requirement may need additional QA resources")

        return feasibility['feasible'], feasibility

    def create_production_plan(
        self,
        requirement: ProductRequirement,
        process_spec: ProcessSpec
    ) -> Dict[str, Any]:
        """Create a production plan for approved requirements"""
        plan = {
            'plan_id': generate_id('plan'),
            'requirement_id': requirement.requirement_id,
            'process_spec_id': process_spec.process_id,
            'production_lines_needed': max(1, len(requirement.input_data) // 100),
            'workers_per_line': process_spec.required_workers,
            'expected_start': datetime.now(),
            'expected_completion': datetime.now() + timedelta(minutes=process_spec.estimated_duration),
            'resource_allocation': {
                'workers': process_spec.required_workers * max(1, len(requirement.input_data) // 100),
                'processing_capacity': len(requirement.input_data),
                'quality_checkpoints': 3
            },
            'approval_status': 'approved',
            'created_by': self.agent_id
        }

        self.log_decision('create_production_plan', plan)
        return plan

    def get_factory_status(self, factory_state: FactoryState) -> Dict[str, Any]:
        """Aggregate factory status for management view"""
        factory_state.update_metrics()

        return {
            'status_timestamp': datetime.now().isoformat(),
            'overall_status': factory_state.status,
            'production_lines': len(factory_state.production_lines),
            'active_tasks': len(factory_state.get_active_work_orders()),
            'pending_tasks': len(factory_state.get_pending_work_orders()),
            'metrics': factory_state.metrics.to_dict(),
            'recommendations': self._generate_recommendations(factory_state)
        }

    def _generate_recommendations(self, factory_state: FactoryState) -> List[str]:
        """Generate operational recommendations"""
        recommendations = []

        # Check utilization
        avg_util = sum(
            line.utilization_rate for line in factory_state.production_lines.values()
        ) / len(factory_state.production_lines) if factory_state.production_lines else 0

        if avg_util < 0.3:
            recommendations.append("Low production line utilization. Consider consolidating lines or reducing workers.")
        elif avg_util > 0.9:
            recommendations.append("High utilization. Consider adding more workers or production lines.")

        # Check quality
        if factory_state.metrics.quality_rate < 0.9:
            recommendations.append("Quality rate below threshold. Recommend additional QA checkpoints.")

        # Check cost efficiency
        for line in factory_state.production_lines.values():
            if line.average_cost_per_item > 0.1:
                recommendations.append(f"Line {line.line_name} has high cost per item. Review process optimization.")

        return recommendations

    def execute(self, factory_state: FactoryState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method"""
        action = context.get('action', 'status')

        if action == 'evaluate_requirement':
            requirement = context['requirement']
            feasible, details = self.evaluate_requirement(requirement)
            return {
                'agent': self.name,
                'action': action,
                'feasible': feasible,
                'details': details
            }

        elif action == 'create_plan':
            requirement = context['requirement']
            process_spec = context['process_spec']
            plan = self.create_production_plan(requirement, process_spec)
            return {
                'agent': self.name,
                'action': action,
                'plan': plan
            }

        elif action == 'status':
            status = self.get_factory_status(factory_state)
            return {
                'agent': self.name,
                'action': action,
                'factory_status': status
            }

        return {'agent': self.name, 'error': 'Unknown action'}


class ProcessExpert(FactoryAgent):
    """
    工艺专家 - Process Expert
    Responsible for designing and optimizing process specifications
    """

    def __init__(self):
        super().__init__(
            agent_id=generate_id('exp'),
            role=FactoryRole.PROCESS_EXPERT,
            name='Process Expert (工艺专家)'
        )

    def design_process(self, requirement: ProductRequirement) -> ProcessSpec:
        """Design a process specification for a requirement"""
        # Map product types to process steps
        steps_map = {
            ProductType.ADDRESS_CLEANING: [
                ProcessStep.PARSING,
                ProcessStep.STANDARDIZATION,
                ProcessStep.VALIDATION
            ],
            ProductType.ENTITY_FUSION: [
                ProcessStep.PARSING,
                ProcessStep.FUSION,
                ProcessStep.VALIDATION
            ],
            ProductType.RELATIONSHIP_EXTRACTION: [
                ProcessStep.PARSING,
                ProcessStep.EXTRACTION,
                ProcessStep.VALIDATION
            ],
            ProductType.DATA_VALIDATION: [
                ProcessStep.VALIDATION,
                ProcessStep.QUALITY_CHECK
            ],
            ProductType.CUSTOM: [
                ProcessStep.PARSING,
                ProcessStep.VALIDATION
            ]
        }

        steps = steps_map.get(requirement.product_type, steps_map[ProductType.CUSTOM])

        process_spec = ProcessSpec(
            process_id=generate_id('proc'),
            process_name=f"Process for {requirement.product_name}",
            steps=steps,
            estimated_duration=len(requirement.input_data) * 0.5,  # 0.5 min per item
            required_workers=3,
            quality_rules={
                'accuracy_threshold': requirement.sla_metrics.get('quality_threshold', 0.95),
                'error_tolerance': 0.05,
                'qa_checkpoints': 3
            },
            resource_requirements={
                'memory_mb': 512,
                'cpu_cores': 2,
                'storage_gb': 1
            }
        )

        self.log_decision('design_process', {
            'requirement_id': requirement.requirement_id,
            'process_id': process_spec.process_id,
            'steps': [s.value for s in steps]
        })

        return process_spec

    def optimize_process(self, process_spec: ProcessSpec, execution_history: List[TaskExecution]) -> ProcessSpec:
        """Optimize a process based on execution history"""
        if not execution_history:
            return process_spec

        # Calculate average metrics
        avg_duration = sum(e.duration_minutes for e in execution_history) / len(execution_history)
        avg_quality = sum(e.quality_score for e in execution_history) / len(execution_history)

        # Adjust estimated duration based on actual
        new_duration = avg_duration * 1.1  # Add 10% buffer

        # Log optimization
        self.log_decision('optimize_process', {
            'process_id': process_spec.process_id,
            'old_duration': process_spec.estimated_duration,
            'new_duration': new_duration,
            'avg_quality': avg_quality
        })

        process_spec.estimated_duration = new_duration
        return process_spec

    def execute(self, factory_state: FactoryState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method"""
        action = context.get('action', 'design')

        if action == 'design':
            requirement = context['requirement']
            process_spec = self.design_process(requirement)
            return {
                'agent': self.name,
                'action': action,
                'process_spec': process_spec
            }

        elif action == 'optimize':
            process_spec = context['process_spec']
            execution_history = context.get('execution_history', [])
            optimized = self.optimize_process(process_spec, execution_history)
            return {
                'agent': self.name,
                'action': action,
                'optimized_spec': optimized
            }

        return {'agent': self.name, 'error': 'Unknown action'}


class ProductionLineLeader(FactoryAgent):
    """
    生产线组长 - Production Line Leader
    Responsible for line creation, worker allocation, and task management
    """

    def __init__(self):
        super().__init__(
            agent_id=generate_id('lead'),
            role=FactoryRole.PRODUCTION_LEADER,
            name='Production Line Leader (组长)'
        )

    def create_production_line(
        self,
        line_name: str,
        process_spec: ProcessSpec,
        worker_count: int
    ) -> ProductionLine:
        """Create a new production line with allocated workers"""
        from tools.factory_framework import Worker as WorkerModel

        line = ProductionLine(
            line_id=generate_id('line'),
            line_name=line_name,
            process_spec=process_spec,
            max_capacity=100
        )

        # Allocate workers
        for i in range(worker_count):
            worker = WorkerModel(
                worker_id=generate_id('worker'),
                name=f"Worker_{i+1}",
                assigned_line_id=line.line_id
            )
            line.workers.append(worker)

        self.log_decision('create_production_line', {
            'line_id': line.line_id,
            'worker_count': worker_count,
            'process_spec_id': process_spec.process_id
        })

        return line

    def assign_task(
        self,
        work_order: WorkOrder,
        production_line: ProductionLine
    ) -> Dict[str, Any]:
        """Assign a work order to a production line"""
        assignment = {
            'work_order_id': work_order.work_order_id,
            'line_id': production_line.line_id,
            'assigned_at': datetime.now().isoformat(),
            'status': 'assigned'
        }

        work_order.assigned_line_id = production_line.line_id
        production_line.active_tasks += 1

        self.log_decision('assign_task', assignment)
        return assignment

    def monitor_progress(self, production_line: ProductionLine) -> Dict[str, Any]:
        """Monitor production line progress"""
        return {
            'line_id': production_line.line_id,
            'line_name': production_line.line_name,
            'active_tasks': production_line.active_tasks,
            'completed_tasks': production_line.completed_tasks,
            'failed_tasks': production_line.failed_tasks,
            'worker_count': len(production_line.workers),
            'utilization': production_line.utilization_rate,
            'avg_quality': production_line.average_quality_score,
            'total_tokens': production_line.total_tokens_consumed,
            'cost_per_item': production_line.average_cost_per_item
        }

    def execute(self, factory_state: FactoryState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method"""
        action = context.get('action', 'create')

        if action == 'create':
            process_spec = context['process_spec']
            worker_count = context.get('worker_count', 3)
            line_name = context.get('line_name', f"Line_{process_spec.process_name}")
            line = self.create_production_line(line_name, process_spec, worker_count)
            return {
                'agent': self.name,
                'action': action,
                'production_line': line
            }

        elif action == 'assign':
            work_order = context['work_order']
            production_line = context['production_line']
            assignment = self.assign_task(work_order, production_line)
            return {
                'agent': self.name,
                'action': action,
                'assignment': assignment
            }

        elif action == 'monitor':
            production_line = context['production_line']
            progress = self.monitor_progress(production_line)
            return {
                'agent': self.name,
                'action': action,
                'progress': progress
            }

        return {'agent': self.name, 'error': 'Unknown action'}


class Worker(FactoryAgent):
    """
    工人 - Worker Agent
    Responsible for executing data processing tasks
    """

    def __init__(self, worker_id: str = None):
        agent_id = worker_id or generate_id('worker')
        super().__init__(
            agent_id=agent_id,
            role=FactoryRole.WORKER,
            name=f'Worker ({agent_id[:8]}...)'
        )
        self.current_task = None
        self.total_tokens_consumed = 0.0
        self.tasks_completed = 0

    def execute_task(
        self,
        work_order: WorkOrder,
        input_data: Dict[str, Any],
        process_step: ProcessStep
    ) -> TaskExecution:
        """Execute a processing task"""
        execution_id = generate_id('exec')
        start_time = datetime.now()

        # Simulate task execution with realistic metrics
        # Token consumption based on data complexity
        data_str = str(input_data)
        tokens_consumed = len(data_str) / 100.0  # Rough estimate
        duration = random.uniform(0.5, 2.0)  # 30 seconds to 2 minutes

        # Simulate output
        output_data = {
            'processed': True,
            'execution_id': execution_id,
            'process_step': process_step.value,
            'input_items': 1
        }

        if process_step == ProcessStep.PARSING:
            output_data['parsed_fields'] = len(input_data)
        elif process_step == ProcessStep.STANDARDIZATION:
            output_data['standardized'] = True
        elif process_step == ProcessStep.VALIDATION:
            output_data['valid'] = True
        elif process_step == ProcessStep.FUSION:
            output_data['fused_entities'] = 1

        # Quality score with some variance
        quality_score = random.uniform(0.85, 1.0)

        execution = TaskExecution(
            execution_id=execution_id,
            work_order_id=work_order.work_order_id,
            worker_id=self.agent_id,
            process_step=process_step,
            input_data=input_data,
            output_data=output_data,
            status=WorkOrderStatus.COMPLETED,
            token_consumed=tokens_consumed,
            duration_minutes=duration,
            quality_score=quality_score,
            started_at=start_time,
            completed_at=start_time + timedelta(minutes=duration)
        )

        self.total_tokens_consumed += tokens_consumed
        self.tasks_completed += 1

        self.log_decision('execute_task', {
            'execution_id': execution_id,
            'tokens_consumed': tokens_consumed,
            'quality_score': quality_score
        })

        return execution

    def execute(self, factory_state: FactoryState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method"""
        action = context.get('action', 'execute_task')

        if action == 'execute_task':
            work_order = context['work_order']
            input_data = context['input_data']
            process_step = context.get('process_step', ProcessStep.PARSING)

            execution = self.execute_task(work_order, input_data, process_step)
            return {
                'agent': self.name,
                'action': action,
                'execution': execution
            }

        return {'agent': self.name, 'error': 'Unknown action'}


class QualityInspector(FactoryAgent):
    """
    质检员 - Quality Inspector
    Responsible for quality verification and inspection
    """

    def __init__(self):
        super().__init__(
            agent_id=generate_id('qa'),
            role=FactoryRole.QUALITY_INSPECTOR,
            name='Quality Inspector (质检员)'
        )

    def inspect_execution(
        self,
        execution: TaskExecution,
        quality_threshold: float = 0.9
    ) -> QualityCheckResult:
        """Inspect a task execution"""
        check_id = generate_id('check')

        # Validation rules
        issues = []
        if execution.quality_score < quality_threshold:
            issues.append(f"Quality score {execution.quality_score} below threshold {quality_threshold}")

        if not execution.output_data.get('processed'):
            issues.append("Task did not complete processing")

        passed = len(issues) == 0 and execution.quality_score >= quality_threshold

        recommendations = ""
        if not passed:
            if execution.quality_score < 0.7:
                recommendations = "Recommend rework with additional QA review"
            elif execution.quality_score < quality_threshold:
                recommendations = "Recommend worker training on quality standards"

        check_result = QualityCheckResult(
            check_id=check_id,
            work_order_id=execution.work_order_id,
            execution_id=execution.execution_id,
            inspector_id=self.agent_id,
            quality_score=execution.quality_score,
            passed=passed,
            issues=issues,
            recommendations=recommendations
        )

        self.log_decision('inspect_execution', {
            'execution_id': execution.execution_id,
            'passed': passed,
            'quality_score': execution.quality_score
        })

        return check_result

    def generate_quality_report(self, factory_state: FactoryState) -> Dict[str, Any]:
        """Generate overall quality report"""
        factory_state.update_metrics()

        passed_checks = sum(1 for check in factory_state.quality_checks if check.passed)
        total_checks = len(factory_state.quality_checks)

        report = {
            'report_id': generate_id('report'),
            'generated_at': datetime.now().isoformat(),
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'pass_rate': passed_checks / total_checks if total_checks > 0 else 0,
            'avg_quality_score': factory_state.metrics.overall_quality_rate,
            'common_issues': self._analyze_issues(factory_state),
            'recommendations': self._generate_recommendations(factory_state)
        }

        return report

    def _analyze_issues(self, factory_state: FactoryState) -> List[str]:
        """Analyze common quality issues"""
        issue_counts = {}
        for check in factory_state.quality_checks:
            for issue in check.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Return top 5 issues
        return sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def _generate_recommendations(self, factory_state: FactoryState) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []

        if factory_state.metrics.quality_rate < 0.9:
            recommendations.append("Implement additional QA checkpoints for failing tasks")

        failed_executions = sum(
            1 for exec in factory_state.task_executions
            if exec.status == WorkOrderStatus.FAILED
        )
        if failed_executions > factory_state.metrics.total_tasks_completed * 0.1:
            recommendations.append("High failure rate detected. Review process design and worker training")

        return recommendations

    def execute(self, factory_state: FactoryState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method"""
        action = context.get('action', 'inspect')

        if action == 'inspect':
            execution = context['execution']
            quality_threshold = context.get('quality_threshold', 0.9)
            check_result = self.inspect_execution(execution, quality_threshold)
            return {
                'agent': self.name,
                'action': action,
                'check_result': check_result
            }

        elif action == 'report':
            report = self.generate_quality_report(factory_state)
            return {
                'agent': self.name,
                'action': action,
                'report': report
            }

        return {'agent': self.name, 'error': 'Unknown action'}
