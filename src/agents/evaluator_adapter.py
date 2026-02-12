from typing import Dict


class EvaluatorAdapter:
    """Evaluator that produces EvalReport from execution outputs."""

    def evaluate(self, task_spec: Dict, changeset: Dict, execution_result: Dict) -> Dict:
        checks = []
        gate_checks = execution_result.get("gates", {}).get("checks", [])
        checks.extend(gate_checks)

        execution_ok = execution_result.get("status") == "PASS"
        checks.append(
            {
                "name": "Execution Gate",
                "status": "PASS" if execution_ok else "FAIL",
                "details": execution_result.get("stage", "unknown"),
            }
        )

        budget_steps = task_spec.get("constraints", {}).get("budget", {}).get("max_steps", 0)
        used_steps = len(changeset.get("operations", []))
        budget_ok = used_steps <= budget_steps if budget_steps else True
        checks.append(
            {
                "name": "Budget Step Gate",
                "status": "PASS" if budget_ok else "WARN",
                "details": f"used_steps={used_steps}, max_steps={budget_steps}",
            }
        )

        if all(c["status"] == "PASS" for c in checks):
            status = "PASS"
        elif any(c["status"] == "FAIL" for c in checks):
            status = "FAIL"
        else:
            status = "NEEDS_HUMAN"

        return {
            "task_id": task_spec["task_id"],
            "status": status,
            "checks": checks,
        }
