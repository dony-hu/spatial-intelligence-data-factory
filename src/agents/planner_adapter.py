import uuid
from typing import Dict, List, Tuple

from src.tools.ddl_tool import DDLTool


class PlannerAdapter:
    """Template-based planner that emits Plan + ApprovalPack + ChangeSet."""

    def plan(self, task_spec: Dict) -> Tuple[Dict, Dict]:
        task_id = task_spec["task_id"]
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        context = task_spec.get("context", {})

        steps = [
            {
                "step_id": "s1",
                "intent": "做源数据探查",
                "tool": "profiling_tool",
                "inputs": {"sources": context.get("data_sources", [])},
                "expected_output": "profiling_report.json",
            },
            {
                "step_id": "s2",
                "intent": "生成建表变更",
                "tool": "ddl_tool",
                "inputs": {"domain": context.get("domain", "generic")},
                "expected_output": "ddl_changes.sql",
            },
            {
                "step_id": "s3",
                "intent": "生成调度产物",
                "tool": "airflow_tool",
                "inputs": {"target_platform": context.get("target_platform", "airflow")},
                "expected_output": "dag_generated.py",
            },
        ]

        plan = {
            "plan_id": plan_id,
            "task_id": task_id,
            "steps": steps,
            "deliverables": [
                "profiling_report.json",
                "ddl_changes.sql",
                "dag_generated.py",
                "changeset.json",
            ],
            "assumptions": [
                "源系统连通且字段可读",
                "dev 环境具备 dry-run 能力",
            ],
            "risks": [
                "字段漂移导致 DDL 不兼容",
                "审批未通过导致执行阻断",
            ],
        }

        approval_pack = self._build_approval_pack(task_spec)
        return plan, approval_pack

    def build_changeset(self, task_spec: Dict, plan: Dict, approval_pack: Dict) -> Dict:
        task_id = task_spec["task_id"]
        env = task_spec.get("constraints", {}).get("env", "dev")
        domain = task_spec.get("context", {}).get("domain", "generic")
        ddl_payload = DDLTool().generate(domain)

        operations = [
            {
                "op_id": "op_ddl_001",
                "op_type": "DDL",
                "payload": ddl_payload,
                "idempotency_key": f"ddl-{task_id}-v1",
                "dry_run_supported": True,
            },
            {
                "op_id": "op_dag_001",
                "op_type": "DAG",
                "payload": {
                    "dag_id": f"agent_{task_id}",
                    "schedule": "@daily",
                },
                "idempotency_key": f"dag-{task_id}-v1",
                "dry_run_supported": True,
            },
        ]

        requires_approvals = [
            item["type"] for item in approval_pack.get("items", []) if item.get("blocking", True)
        ]

        return {
            "changeset_id": f"cs_{uuid.uuid4().hex[:12]}",
            "task_id": task_id,
            "env": env,
            "operations": operations,
            "rollback": {
                "strategy": "sql_rollback",
                "payload": {
                    "sql": "DROP TABLE IF EXISTS dwd_agent_task_result;"
                },
            },
            "requires_approvals": requires_approvals,
        }

    def _build_approval_pack(self, task_spec: Dict) -> Dict:
        task_id = task_spec["task_id"]
        env = task_spec.get("constraints", {}).get("env", "dev")
        safety = task_spec.get("constraints", {}).get("safety_level", "medium")

        items: List[Dict] = [
            {
                "approval_id": f"ap_{uuid.uuid4().hex[:8]}",
                "type": "METRIC_DEFINITION",
                "summary": "确认指标口径与验收标准",
                "owner_role": "product_owner",
                "blocking": True,
            },
            {
                "approval_id": f"ap_{uuid.uuid4().hex[:8]}",
                "type": "SECURITY",
                "summary": "确认权限和脱敏策略",
                "owner_role": "security_officer",
                "blocking": True,
            },
        ]

        if env == "prod" or safety == "high":
            items.append(
                {
                    "approval_id": f"ap_{uuid.uuid4().hex[:8]}",
                    "type": "PROD_RELEASE",
                    "summary": "确认生产发布窗口",
                    "owner_role": "release_owner",
                    "blocking": True,
                }
            )

        return {
            "pack_id": f"pack_{uuid.uuid4().hex[:10]}",
            "task_id": task_id,
            "items": items,
        }
