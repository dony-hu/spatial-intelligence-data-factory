"""工人执行与质检服务。"""

from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from database.factory_db import FactoryDB
from tools.factory_agents import QualityInspector, Worker
from tools.factory_framework import (
    FactoryState,
    GraphNode,
    GraphRelationship,
    ProcessSpec,
    ProcessStep,
    ProductionLine,
    ProductionLineStatus,
    ProductRequirement,
    WorkOrder,
    WorkOrderStatus,
)


class WorkerExecutionService:
    """工人+质检执行服务：清洗产线、图谱产线执行与门禁。"""

    def __init__(
        self,
        factory_state: FactoryState,
        db: FactoryDB,
        workers: Dict[str, Worker],
        inspector: QualityInspector,
        graph_node_ids: Set[str],
        graph_relationship_ids: Set[str],
    ):
        self.factory_state = factory_state
        self.db = db
        self.workers = workers
        self.inspector = inspector
        self.graph_node_ids = graph_node_ids
        self.graph_relationship_ids = graph_relationship_ids

    def execute_cleaning_pipeline(
        self,
        order: WorkOrder,
        spec: ProcessSpec,
        input_item: Dict[str, Any],
        requirement: ProductRequirement,
    ) -> Dict[str, Any]:
        line = self.factory_state.get_production_line(order.assigned_line_id)
        if not line or not line.workers:
            return {}

        worker = self.workers.get(line.workers[0].worker_id)
        if not worker:
            return {}

        self._mark_line_task_started(line)
        cleaning_output: Dict[str, Any] = {}
        order_tokens = 0.0
        order_quality_scores: List[float] = []
        quality_threshold = requirement.sla_metrics.get("quality_threshold", 0.9)

        for step in spec.steps:
            execution = worker.execute(
                self.factory_state,
                {
                    "action": "execute_task",
                    "work_order": order,
                    "input_data": input_item,
                    "process_step": step,
                },
            )["execution"]

            self.factory_state.record_task_execution(execution)
            self.db.save_task_execution(execution)
            order_tokens += float(execution.token_consumed or 0.0)
            order_quality_scores.append(float(execution.quality_score or 0.0))

            if step == ProcessStep.STANDARDIZATION:
                cleaning_output = {
                    "standardized_address": execution.output_data.get("standardized_address", ""),
                    "components": execution.output_data.get("components", {}),
                    "aliases": execution.output_data.get("aliases", []),
                    "confidence": execution.output_data.get("confidence", 0.0),
                }

            check = self.inspector.execute(
                self.factory_state,
                {
                    "action": "inspect",
                    "execution": execution,
                    "quality_threshold": quality_threshold,
                },
            )["check_result"]
            self.factory_state.record_quality_check(check)
            self.db.save_quality_check(check)

        cleaning_ok = bool(cleaning_output.get("standardized_address")) and bool(cleaning_output.get("components"))
        if cleaning_ok:
            order.status = WorkOrderStatus.COMPLETED
            order.completed_at = datetime.now()
            self.db.save_work_order(order)
        else:
            order.status = WorkOrderStatus.FAILED
            order.completed_at = datetime.now()
            self.db.save_work_order(order)
            self._mark_line_task_failed(
                line=line,
                tokens=order_tokens,
                quality_score=(sum(order_quality_scores) / len(order_quality_scores)) if order_quality_scores else 0.0,
            )
            return {}

        self._mark_line_task_completed(
            line=line,
            tokens=order_tokens,
            quality_score=(sum(order_quality_scores) / len(order_quality_scores)) if order_quality_scores else 1.0,
        )
        return cleaning_output

    def execute_graph_pipeline(
        self,
        order: WorkOrder,
        spec: ProcessSpec,
        cleaning_output: Dict[str, Any],
        requirement: ProductRequirement,
        source_address_id: str,
    ) -> Tuple[List[GraphNode], List[GraphRelationship], Dict[str, Any], Dict[str, Any]]:
        line = self.factory_state.get_production_line(order.assigned_line_id)
        if not line or not line.workers:
            return [], [], {"pass": False, "reason": "LINE_NOT_READY"}, {
                "nodes_merged": 0,
                "relationships_merged": 0,
                "nodes": [],
                "relationships": [],
            }

        worker = self.workers.get(line.workers[0].worker_id)
        if not worker:
            return [], [], {"pass": False, "reason": "WORKER_NOT_READY"}, {
                "nodes_merged": 0,
                "relationships_merged": 0,
                "nodes": [],
                "relationships": [],
            }

        self._mark_line_task_started(line)
        graph_nodes: List[GraphNode] = []
        graph_relationships: List[GraphRelationship] = []
        merged_node_count = 0
        merged_relationship_count = 0
        order_tokens = 0.0
        order_quality_scores: List[float] = []
        quality_threshold = requirement.sla_metrics.get("quality_threshold", 0.9)

        for step in spec.steps:
            execution = worker.execute(
                self.factory_state,
                {
                    "action": "execute_task",
                    "work_order": order,
                    "input_data": cleaning_output,
                    "process_step": step,
                },
            )["execution"]

            self.factory_state.record_task_execution(execution)
            self.db.save_task_execution(execution)
            order_tokens += float(execution.token_consumed or 0.0)
            order_quality_scores.append(float(execution.quality_score or 0.0))

            if step == ProcessStep.EXTRACTION:
                output = execution.output_data
                for node_data in output.get("nodes", []):
                    node_id = str(node_data.get("node_id", "")).strip()
                    if not node_id:
                        continue
                    node = GraphNode(
                        node_id=node_id,
                        node_type=node_data.get("type", "location"),
                        name=node_data.get("name", ""),
                        properties=node_data.get("properties", {}),
                        source_address=source_address_id,
                    )
                    graph_nodes.append(node)
                    if node.node_id not in self.graph_node_ids:
                        self.graph_node_ids.add(node.node_id)
                        merged_node_count += 1
                        self.factory_state.add_graph_node(node)
                        self.db.save_graph_node(node)

                for rel_data in output.get("relationships", []):
                    relationship_id = str(rel_data.get("relationship_id", "")).strip()
                    if not relationship_id:
                        continue
                    relationship = GraphRelationship(
                        relationship_id=relationship_id,
                        source_node_id=rel_data.get("source", ""),
                        target_node_id=rel_data.get("target", ""),
                        relationship_type=rel_data.get("type", "related"),
                        properties=rel_data.get("properties", {}),
                        source_address=source_address_id,
                    )
                    graph_relationships.append(relationship)
                    if relationship.relationship_id not in self.graph_relationship_ids:
                        self.graph_relationship_ids.add(relationship.relationship_id)
                        merged_relationship_count += 1
                        self.factory_state.add_graph_relationship(relationship)
                        self.db.save_graph_relationship(relationship)

            check = self.inspector.execute(
                self.factory_state,
                {
                    "action": "inspect",
                    "execution": execution,
                    "quality_threshold": quality_threshold,
                },
            )["check_result"]
            self.factory_state.record_quality_check(check)
            self.db.save_quality_check(check)

        graph_gate = {
            "pass": len(graph_nodes) > 0 and len(graph_relationships) > 0,
            "reason": "ok" if len(graph_nodes) > 0 and len(graph_relationships) > 0 else "GRAPH_EMPTY_OUTPUT",
        }
        if graph_gate["pass"]:
            order.status = WorkOrderStatus.COMPLETED
            order.completed_at = datetime.now()
            self.db.save_work_order(order)
        else:
            order.status = WorkOrderStatus.FAILED
            order.completed_at = datetime.now()
            self.db.save_work_order(order)
            self._mark_line_task_failed(
                line=line,
                tokens=order_tokens,
                quality_score=(sum(order_quality_scores) / len(order_quality_scores)) if order_quality_scores else 0.0,
            )
            return graph_nodes, graph_relationships, graph_gate, {
                "nodes_merged": merged_node_count,
                "relationships_merged": merged_relationship_count,
                "nodes": [n.to_dict() for n in graph_nodes],
                "relationships": [r.to_dict() for r in graph_relationships],
            }

        self._mark_line_task_completed(
            line=line,
            tokens=order_tokens,
            quality_score=(sum(order_quality_scores) / len(order_quality_scores)) if order_quality_scores else 1.0,
        )
        return graph_nodes, graph_relationships, graph_gate, {
            "nodes_merged": merged_node_count,
            "relationships_merged": merged_relationship_count,
            "nodes": [n.to_dict() for n in graph_nodes],
            "relationships": [r.to_dict() for r in graph_relationships],
        }

    def _mark_line_task_started(self, line: ProductionLine) -> None:
        line.active_tasks += 1
        line.status = ProductionLineStatus.RUNNING
        self.db.save_production_line(line)

    def _mark_line_task_completed(self, line: ProductionLine, tokens: float, quality_score: float) -> None:
        previous_completed = line.completed_tasks
        line.active_tasks = max(0, line.active_tasks - 1)
        line.completed_tasks += 1
        line.total_tokens_consumed += float(tokens or 0.0)

        if previous_completed <= 0:
            line.average_quality_score = float(quality_score or 1.0)
        else:
            line.average_quality_score = (
                (line.average_quality_score * previous_completed) + float(quality_score or 1.0)
            ) / (previous_completed + 1)

        if line.active_tasks == 0:
            line.status = ProductionLineStatus.IDLE

        self.db.save_production_line(line)

    def _mark_line_task_failed(self, line: ProductionLine, tokens: float, quality_score: float) -> None:
        line.active_tasks = max(0, line.active_tasks - 1)
        line.failed_tasks += 1
        line.total_tokens_consumed += float(tokens or 0.0)
        if line.active_tasks == 0:
            line.status = ProductionLineStatus.IDLE
        if quality_score:
            line.average_quality_score = min(line.average_quality_score, float(quality_score))
        self.db.save_production_line(line)
