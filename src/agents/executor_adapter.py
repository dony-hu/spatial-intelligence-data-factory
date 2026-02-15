from datetime import datetime, timezone
from typing import Dict, List

from tools.address_verification import AddressVerificationOrchestrator, UNVERIFIABLE_ONLINE
from tools.factory_framework import ProductRequirement, ProductType, generate_id
from tools.factory_workflow import FactoryWorkflow
from src.evaluation.gates import run_minimum_gates
from src.tools.profiling_tool import ProfilingTool
from src.tools.airflow_tool import AirflowTool


class ExecutorAdapter:
    """Executor that enforces changeset validation before running workflow."""

    APPROVAL_MAP = {
        "METRIC_DEFINITION": "kpi_frozen",
        "SECURITY": "compliance_approved",
        "PROD_RELEASE": "release_window_confirmed",
        "COST_BUDGET": "kpi_frozen",
    }

    def __init__(self, runtime_store: Optional[Any] = None):
        self.runtime_store = runtime_store
        self.verifier = AddressVerificationOrchestrator(runtime_store=runtime_store)

    def execute(self, task_spec: Dict, changeset: Dict, approvals: List[str]) -> Dict:
        profiling_report = ProfilingTool().run(task_spec)
        gate_report = run_minimum_gates(changeset, approvals, profiling_report)
        if gate_report["status"] != "PASS":
            return {
                "status": "FAIL",
                "stage": "GATE_CHECK",
                "details": gate_report,
                "profiling_report": profiling_report,
            }

        self._generate_dag_artifact(task_spec, changeset)

        workflow = FactoryWorkflow(factory_name=f"Agent-{task_spec['task_id']}")
        for ap in approvals:
            gate = self.APPROVAL_MAP.get(ap)
            if gate:
                workflow.approve_gate(gate, approver="executor", note="approved by adapter")

        task_run_id = str((task_spec.get("context") or {}).get("task_run_id") or "")
        requirement = self._build_requirement(task_spec, task_run_id=task_run_id)
        workflow.submit_product_requirement(requirement)
        wf_result = workflow.create_production_workflow(requirement, auto_execute=True)
        verification_bundle = self._run_address_verification(workflow_result=wf_result, task_run_id=task_run_id)
        task_exec = wf_result.setdefault("stages", {}).setdefault("task_executions", {})
        task_exec["verification_summary"] = verification_bundle["summary"]
        task_exec["verification_case_details"] = verification_bundle["results"]
        task_exec["unverifiable_online_list"] = verification_bundle["unverifiable_online_list"]
        task_exec["strategy_patch"] = verification_bundle["strategy_patch"]

        ok = wf_result.get("status") == "completed"
        return {
            "status": "PASS" if ok else "FAIL",
            "stage": "EXECUTION",
            "gates": gate_report,
            "profiling_report": profiling_report,
            "workflow_result": wf_result,
            "verification_summary": verification_bundle["summary"],
            "summary": workflow.get_workflow_summary(),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_dag_artifact(self, task_spec: Dict, changeset: Dict) -> None:
        for op in changeset.get("operations", []):
            if op.get("op_type") != "DAG":
                continue
            payload = op.get("payload", {})
            AirflowTool().generate_dag(
                dag_id=payload.get("dag_id", f"agent_{task_spec['task_id']}"),
                schedule=payload.get("schedule", "@daily"),
                output_dir=f"output/agent_demo/{task_spec['task_id']}/artifacts",
            )
            break

    def _build_requirement(self, task_spec: Dict, task_run_id: str = "") -> ProductRequirement:
        context = task_spec.get("context", {})
        constraints = task_spec.get("constraints", {})
        data_sources = context.get("data_sources", [])
        input_data = [
            {
                "id": i + 1,
                "raw": f"from:{src}",
                "source": src,
                "task_run_id": task_run_id,
            }
            for i, src in enumerate(data_sources)
        ]
        if not input_data:
            input_data = [{"id": 1, "raw": "default input", "source": "default", "task_run_id": task_run_id}]

        domain = (context.get("domain") or "").lower()
        product_type = ProductType.ADDRESS_TO_GRAPH if "address" in domain else ProductType.DATA_VALIDATION

        return ProductRequirement(
            requirement_id=generate_id("req"),
            product_name=task_spec.get("goal", "agent_task"),
            product_type=product_type,
            input_format="task_spec_sources",
            output_format="changeset_execution_report",
            input_data=input_data,
            sla_metrics={
                "max_duration": constraints.get("budget", {}).get("max_steps", 60),
                "quality_threshold": 0.9,
            },
            priority=1,
        )

    def _run_address_verification(self, workflow_result: Dict, task_run_id: str) -> Dict[str, Any]:
        task_exec = ((workflow_result.get("stages") or {}).get("task_executions") or {})
        cleaning_items = task_exec.get("cleaning_case_details", []) or []
        results: List[Dict[str, Any]] = []
        unverifiable_online_list: List[Dict[str, Any]] = []
        found_count = 0

        for item in cleaning_items:
            source_id = str(item.get("source_id") or item.get("order_id") or "")
            input_item = dict(item.get("input_item") or {})
            input_item["task_run_id"] = task_run_id
            cleaning_output = dict(item.get("output") or {})
            if not cleaning_output.get("standardized_address"):
                continue
            verification = self.verifier.verify(
                record_id=source_id or "unknown",
                input_item=input_item,
                cleaning_output=cleaning_output,
                policy_overrides={},
            )
            results.append(verification)
            if verification.get("verification_status") == UNVERIFIABLE_ONLINE:
                unverifiable_online_list.append(
                    verification.get("unverifiable_item")
                    or {
                        "record_id": source_id,
                        "failed_reason_codes": verification.get("reason_codes", []),
                    }
                )
            elif verification.get("verification_status") == "VERIFIED_EXISTS":
                found_count += 1

        total = len(results)
        unverifiable_count = len(unverifiable_online_list)
        summary = {
            "verified_total": total,
            "verified_exists": found_count,
            "unverifiable_online_count": unverifiable_count,
            "task_run_id": task_run_id,
        }
        strategy_patch: List[Dict[str, Any]] = []
        if unverifiable_count > 0:
            strategy_patch.append(
                {
                    "action": "expand_public_source_coverage",
                    "params": {"expand_public_source_coverage": True},
                    "reason": "UNVERIFIABLE_ONLINE_EXISTS",
                    "target": "address_verification",
                }
            )
        return {
            "results": results,
            "unverifiable_online_list": unverifiable_online_list,
            "summary": summary,
            "strategy_patch": strategy_patch,
        }
