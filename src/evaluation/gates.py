from typing import Dict, List, Optional

from src.tools.ddl_tool import DDLTool


def approval_gate(changeset: Dict, approvals: List[str]) -> Dict:
    required = set(changeset.get("requires_approvals", []))
    granted = set(approvals or [])
    missing = sorted(list(required - granted))
    passed = not missing
    return {
        "name": "Approval Gate",
        "status": "PASS" if passed else "FAIL",
        "details": "all approvals satisfied" if passed else f"missing={','.join(missing)}",
        "missing": missing,
    }


def ddl_dry_run_gate(changeset: Dict, ddl_tool: Optional[DDLTool] = None) -> Dict:
    tool = ddl_tool or DDLTool()
    failures = []

    for op in changeset.get("operations", []):
        if op.get("op_type") != "DDL":
            continue
        sql = op.get("payload", {}).get("sql", "")
        result = tool.dry_run(sql)
        if not result.get("pass"):
            failures.append({"op_id": op.get("op_id"), "reason": result.get("reason")})

    passed = len(failures) == 0
    return {
        "name": "DDL Dry-run Gate",
        "status": "PASS" if passed else "FAIL",
        "details": "ddl dry-run passed" if passed else str(failures),
        "failures": failures,
    }


def idempotency_gate(changeset: Dict) -> Dict:
    invalid = []
    for op in changeset.get("operations", []):
        if not op.get("idempotency_key"):
            invalid.append(op.get("op_id", "unknown"))

    passed = len(invalid) == 0
    return {
        "name": "Idempotency Gate",
        "status": "PASS" if passed else "FAIL",
        "details": "all operations have idempotency_key" if passed else f"missing={','.join(invalid)}",
        "missing_ops": invalid,
    }


def data_quality_gate(profiling_report: Dict) -> Dict:
    summary = profiling_report.get("quality_summary", {})
    max_null_ratio = float(summary.get("max_null_ratio", 1.0))
    has_schema_drift = bool(summary.get("has_schema_drift", True))

    passed = max_null_ratio <= 0.2 and not has_schema_drift
    details = f"max_null_ratio={max_null_ratio}, has_schema_drift={has_schema_drift}"
    return {
        "name": "Data Quality Gate",
        "status": "PASS" if passed else "FAIL",
        "details": details,
    }


def run_minimum_gates(changeset: Dict, approvals: List[str], profiling_report: Dict) -> Dict:
    checks = [
        approval_gate(changeset, approvals),
        ddl_dry_run_gate(changeset),
        idempotency_gate(changeset),
        data_quality_gate(profiling_report),
    ]

    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    return {"status": status, "checks": checks}
