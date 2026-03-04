from __future__ import annotations

from scripts.run_epic3_core_acceptance import validate_report_payload


def _base_payload() -> dict:
    return {
        "decision": "GO",
        "commands": ["pytest -q a.py"],
        "results": [{"suite": "pipeline", "passed": True, "summary": "1 passed"}],
        "failure_analysis": [],
        "no_fallback_verdict": "PASS",
        "covered_modules": ["pipeline", "events", "llm", "rbac", "upload-batch"],
    }


def test_validate_report_payload_requires_core_fields() -> None:
    payload = _base_payload()
    payload.pop("commands")
    errors = validate_report_payload(payload)
    assert any("commands" in item for item in errors)


def test_validate_report_payload_requires_core_module_coverage() -> None:
    payload = _base_payload()
    payload["covered_modules"] = ["pipeline", "events", "rbac"]
    errors = validate_report_payload(payload)
    assert any("upload-batch" in item for item in errors)
    assert any("llm" in item for item in errors)


def test_validate_report_payload_requires_no_go_when_critical_failure() -> None:
    payload = _base_payload()
    payload["decision"] = "GO"
    payload["results"] = [
        {"suite": "pipeline", "passed": True, "summary": "ok"},
        {"suite": "upload-batch", "passed": False, "summary": "1 failed"},
    ]
    errors = validate_report_payload(payload)
    assert any("NO_GO" in item for item in errors)
