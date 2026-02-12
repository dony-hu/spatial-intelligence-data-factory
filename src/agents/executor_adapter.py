from datetime import datetime
from typing import Dict, List

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

        requirement = self._build_requirement(task_spec)
        workflow.submit_product_requirement(requirement)
        wf_result = workflow.create_production_workflow(requirement, auto_execute=True)

        ok = wf_result.get("status") == "completed"
        return {
            "status": "PASS" if ok else "FAIL",
            "stage": "EXECUTION",
            "gates": gate_report,
            "profiling_report": profiling_report,
            "workflow_result": wf_result,
            "summary": workflow.get_workflow_summary(),
            "executed_at": datetime.utcnow().isoformat(),
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

    def _build_requirement(self, task_spec: Dict) -> ProductRequirement:
        context = task_spec.get("context", {})
        constraints = task_spec.get("constraints", {})
        data_sources = context.get("data_sources", [])
        input_data = [{"id": i + 1, "raw": f"from:{src}", "source": src} for i, src in enumerate(data_sources)]
        if not input_data:
            input_data = [{"id": 1, "raw": "default input", "source": "default"}]

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
