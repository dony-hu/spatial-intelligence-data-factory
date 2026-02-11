"""
Factory Framework - Core data models for the factory demonstration system
Represents a manufacturing factory metaphor for data processing workflows
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid
import json


class FactoryRole(Enum):
    """Factory operational roles"""
    DIRECTOR = "director"          # 厂长 - Overall management
    PROCESS_EXPERT = "expert"      # 工艺专家 - Process design
    PRODUCTION_LEADER = "leader"   # 生产线组长 - Line coordination
    WORKER = "worker"              # 工人 - Task execution
    QUALITY_INSPECTOR = "inspector" # 质检员 - Quality control


class ProductType(Enum):
    """Data product types"""
    ADDRESS_CLEANING = "address_cleaning"          # 地址清洗
    ENTITY_FUSION = "entity_fusion"                # 实体融合
    RELATIONSHIP_EXTRACTION = "relationship_extraction"  # 关系抽取
    DATA_VALIDATION = "data_validation"            # 数据验证
    CUSTOM = "custom"                              # 自定义产品


class ProcessStep(Enum):
    """Standard processing steps"""
    PARSING = "parsing"             # 解析
    STANDARDIZATION = "standardization"  # 标准化
    VALIDATION = "validation"       # 验证
    FUSION = "fusion"               # 融合
    EXTRACTION = "extraction"       # 抽取
    QUALITY_CHECK = "quality_check"  # 质检


class WorkOrderStatus(Enum):
    """Work order lifecycle states"""
    PENDING = "pending"             # 等待中
    IN_PROGRESS = "in_progress"    # 进行中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"               # 失败
    CANCELLED = "cancelled"         # 取消


class ProductionLineStatus(Enum):
    """Production line operational states"""
    IDLE = "idle"                   # 空闲
    RUNNING = "running"             # 运行中
    PAUSED = "paused"               # 暂停
    MAINTENANCE = "maintenance"     # 维护中


@dataclass
class ProcessSpec:
    """Work process specification"""
    process_id: str
    process_name: str
    steps: List[ProcessStep]
    estimated_duration: float  # in minutes
    required_workers: int
    quality_rules: Dict[str, Any]
    resource_requirements: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'process_id': self.process_id,
            'process_name': self.process_name,
            'steps': [step.value for step in self.steps],
            'estimated_duration': self.estimated_duration,
            'required_workers': self.required_workers,
            'quality_rules': self.quality_rules,
            'resource_requirements': self.resource_requirements,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class ProductRequirement:
    """Customer product requirement"""
    requirement_id: str
    product_name: str
    product_type: ProductType
    input_format: str
    output_format: str
    input_data: List[Dict[str, Any]]
    sla_metrics: Dict[str, Any]  # e.g., {"max_duration": 120, "quality_threshold": 0.95}
    priority: int = 5  # 1=highest, 10=lowest
    submitted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'requirement_id': self.requirement_id,
            'product_name': self.product_name,
            'product_type': self.product_type.value,
            'input_format': self.input_format,
            'output_format': self.output_format,
            'input_data_count': len(self.input_data),
            'sla_metrics': self.sla_metrics,
            'priority': self.priority,
            'submitted_at': self.submitted_at.isoformat()
        }


@dataclass
class TaskExecution:
    """Record of a single task execution"""
    execution_id: str
    work_order_id: str
    worker_id: str
    process_step: ProcessStep
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    status: WorkOrderStatus
    token_consumed: float = 0.0
    duration_minutes: float = 0.0
    quality_score: float = 1.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'work_order_id': self.work_order_id,
            'worker_id': self.worker_id,
            'process_step': self.process_step.value,
            'status': self.status.value,
            'token_consumed': self.token_consumed,
            'duration_minutes': self.duration_minutes,
            'quality_score': self.quality_score,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class WorkOrder:
    """Production work order"""
    work_order_id: str
    requirement_id: str
    product_name: str
    process_spec: ProcessSpec
    assigned_line_id: str
    status: WorkOrderStatus
    priority: int = 5
    expected_completion: Optional[datetime] = None
    quality_checks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'work_order_id': self.work_order_id,
            'requirement_id': self.requirement_id,
            'product_name': self.product_name,
            'assigned_line_id': self.assigned_line_id,
            'status': self.status.value,
            'priority': self.priority,
            'expected_completion': self.expected_completion.isoformat() if self.expected_completion else None,
            'quality_checks_count': len(self.quality_checks),
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class Worker:
    """Production line worker agent"""
    worker_id: str
    name: str
    assigned_line_id: str
    capability_level: float = 1.0  # 1.0 = standard capability
    tokens_consumed: float = 0.0
    tasks_completed: int = 0
    average_quality: float = 1.0
    status: str = "available"  # available, busy, unavailable

    def to_dict(self) -> Dict[str, Any]:
        return {
            'worker_id': self.worker_id,
            'name': self.name,
            'assigned_line_id': self.assigned_line_id,
            'capability_level': self.capability_level,
            'tokens_consumed': self.tokens_consumed,
            'tasks_completed': self.tasks_completed,
            'average_quality': self.average_quality,
            'status': self.status
        }


@dataclass
class ProductionLine:
    """Production line configuration and status"""
    line_id: str
    line_name: str
    process_spec: ProcessSpec
    workers: List[Worker] = field(default_factory=list)
    max_capacity: int = 100  # max items per hour
    status: ProductionLineStatus = ProductionLineStatus.IDLE
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_tokens_consumed: float = 0.0
    average_quality_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def utilization_rate(self) -> float:
        """Calculate production line utilization rate"""
        if not self.workers:
            return 0.0
        available = sum(1 for w in self.workers if w.status == "available")
        return 1.0 - (available / len(self.workers))

    @property
    def average_cost_per_item(self) -> float:
        """Calculate average token cost per item"""
        if self.completed_tasks == 0:
            return 0.0
        return self.total_tokens_consumed / self.completed_tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            'line_id': self.line_id,
            'line_name': self.line_name,
            'worker_count': len(self.workers),
            'max_capacity': self.max_capacity,
            'status': self.status.value,
            'active_tasks': self.active_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'total_tokens_consumed': self.total_tokens_consumed,
            'average_quality_score': self.average_quality_score,
            'utilization_rate': self.utilization_rate,
            'average_cost_per_item': self.average_cost_per_item,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class QualityCheckResult:
    """Quality inspection result"""
    check_id: str
    work_order_id: str
    execution_id: str
    inspector_id: str
    quality_score: float  # 0.0 to 1.0
    passed: bool
    issues: List[str] = field(default_factory=list)
    recommendations: str = ""
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'check_id': self.check_id,
            'work_order_id': self.work_order_id,
            'execution_id': self.execution_id,
            'inspector_id': self.inspector_id,
            'quality_score': self.quality_score,
            'passed': self.passed,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'checked_at': self.checked_at.isoformat()
        }


@dataclass
class FactoryMetrics:
    """Factory-level KPI metrics"""
    total_products_processed: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    overall_quality_rate: float = 1.0
    total_tokens_consumed: float = 0.0
    average_turnaround_minutes: float = 0.0
    active_production_lines: int = 0
    busy_workers: int = 0
    utilization_trend: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def quality_rate(self) -> float:
        """Calculate overall quality rate"""
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 1.0
        return self.total_tasks_completed / total

    @property
    def success_rate(self) -> float:
        """Calculate task success rate"""
        return self.quality_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_products_processed': self.total_products_processed,
            'total_tasks_completed': self.total_tasks_completed,
            'total_tasks_failed': self.total_tasks_failed,
            'quality_rate': self.quality_rate,
            'total_tokens_consumed': self.total_tokens_consumed,
            'average_turnaround_minutes': self.average_turnaround_minutes,
            'active_production_lines': self.active_production_lines,
            'busy_workers': self.busy_workers,
            'last_updated': self.last_updated.isoformat()
        }


class FactoryState:
    """Complete factory operational state"""

    def __init__(self, factory_name: str = "Data Factory"):
        self.factory_name = factory_name
        self.production_lines: Dict[str, ProductionLine] = {}
        self.work_orders: Dict[str, WorkOrder] = {}
        self.process_specs: Dict[str, ProcessSpec] = {}
        self.product_requirements: Dict[str, ProductRequirement] = {}
        self.task_executions: List[TaskExecution] = []
        self.quality_checks: List[QualityCheckResult] = []
        self.metrics = FactoryMetrics()
        self.created_at = datetime.now()
        self.status = "running"  # running, paused, maintenance

    def add_production_line(self, line: ProductionLine) -> None:
        """Register a new production line"""
        self.production_lines[line.line_id] = line
        self.metrics.active_production_lines = len(self.production_lines)

    def add_work_order(self, order: WorkOrder) -> None:
        """Register a new work order"""
        self.work_orders[order.work_order_id] = order

    def add_process_spec(self, spec: ProcessSpec) -> None:
        """Register a new process specification"""
        self.process_specs[spec.process_id] = spec

    def add_product_requirement(self, req: ProductRequirement) -> None:
        """Register a new product requirement"""
        self.product_requirements[req.requirement_id] = req

    def record_task_execution(self, execution: TaskExecution) -> None:
        """Record a task execution"""
        self.task_executions.append(execution)

    def record_quality_check(self, check: QualityCheckResult) -> None:
        """Record a quality check result"""
        self.quality_checks.append(check)

    def get_pending_work_orders(self) -> List[WorkOrder]:
        """Get all pending work orders"""
        return [
            order for order in self.work_orders.values()
            if order.status == WorkOrderStatus.PENDING
        ]

    def get_active_work_orders(self) -> List[WorkOrder]:
        """Get all active work orders"""
        return [
            order for order in self.work_orders.values()
            if order.status == WorkOrderStatus.IN_PROGRESS
        ]

    def get_production_line(self, line_id: str) -> Optional[ProductionLine]:
        """Get a production line by ID"""
        return self.production_lines.get(line_id)

    def get_work_order(self, order_id: str) -> Optional[WorkOrder]:
        """Get a work order by ID"""
        return self.work_orders.get(order_id)

    def update_metrics(self) -> None:
        """Update factory metrics from current state"""
        completed = sum(
            1 for exec in self.task_executions
            if exec.status == WorkOrderStatus.COMPLETED
        )
        failed = sum(
            1 for exec in self.task_executions
            if exec.status == WorkOrderStatus.FAILED
        )

        self.metrics.total_tasks_completed = completed
        self.metrics.total_tasks_failed = failed
        self.metrics.total_tokens_consumed = sum(
            exec.token_consumed for exec in self.task_executions
        )

        if self.task_executions:
            avg_duration = sum(
                exec.duration_minutes for exec in self.task_executions
            ) / len(self.task_executions)
            self.metrics.average_turnaround_minutes = avg_duration

            avg_quality = sum(
                exec.quality_score for exec in self.task_executions
            ) / len(self.task_executions)
            self.metrics.overall_quality_rate = avg_quality

        self.metrics.active_production_lines = len(self.production_lines)
        self.metrics.last_updated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert factory state to dictionary"""
        self.update_metrics()

        return {
            'factory_name': self.factory_name,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'production_lines': {
                line_id: line.to_dict()
                for line_id, line in self.production_lines.items()
            },
            'active_work_orders': len(self.get_active_work_orders()),
            'pending_work_orders': len(self.get_pending_work_orders()),
            'total_work_orders': len(self.work_orders),
            'metrics': self.metrics.to_dict()
        }

    def to_json(self) -> str:
        """Convert factory state to JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def generate_id(prefix: str) -> str:
    """Generate a unique ID with given prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
