import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.gates import run_minimum_gates


class AgentGateTests(unittest.TestCase):
    def test_gate_fail_when_missing_idempotency(self):
        changeset = {
            "requires_approvals": ["SECURITY"],
            "operations": [
                {
                    "op_id": "op_ddl_1",
                    "op_type": "DDL",
                    "payload": {"sql": "CREATE TABLE IF NOT EXISTS t1 (id TEXT);"},
                    "idempotency_key": "",
                    "dry_run_supported": True,
                }
            ],
        }
        approvals = ["SECURITY"]
        profiling_report = {
            "quality_summary": {"max_null_ratio": 0.01, "has_schema_drift": False}
        }

        report = run_minimum_gates(changeset, approvals, profiling_report)
        self.assertEqual(report["status"], "FAIL")
        names = [c["name"] for c in report["checks"] if c["status"] == "FAIL"]
        self.assertIn("Idempotency Gate", names)

    def test_gate_pass_minimum_set(self):
        changeset = {
            "requires_approvals": ["SECURITY"],
            "operations": [
                {
                    "op_id": "op_ddl_1",
                    "op_type": "DDL",
                    "payload": {"sql": "CREATE TABLE IF NOT EXISTS t1 (id TEXT);"},
                    "idempotency_key": "k1",
                    "dry_run_supported": True,
                }
            ],
        }
        approvals = ["SECURITY"]
        profiling_report = {
            "quality_summary": {"max_null_ratio": 0.01, "has_schema_drift": False}
        }

        report = run_minimum_gates(changeset, approvals, profiling_report)
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
