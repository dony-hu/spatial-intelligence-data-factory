from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_nightly_quality_gate import _build_gate_judgement_card, _classify_failures


class TestNightlyQualityGateHardening(unittest.TestCase):
    def test_classify_failures_contains_persistent_web_e2e(self) -> None:
        web_e2e = {
            "passed": False,
            "attempts": [
                {"attempt": 1, "return_code": 1},
                {"attempt": 2, "return_code": 1},
            ],
        }
        sql_security = {
            "passed": True,
            "attempts": [
                {"attempt": 1, "return_code": 0},
            ],
        }

        failures = _classify_failures(web_e2e=web_e2e, sql_security=sql_security)
        self.assertTrue(any(item["failure_type"] == "persistent_test_failure" for item in failures))
        self.assertTrue(any(item["gate_impact"] == "NO_GO" for item in failures))

    def test_classify_failures_marks_recovered_transient(self) -> None:
        web_e2e = {
            "passed": True,
            "attempts": [
                {"attempt": 1, "return_code": 1},
                {"attempt": 2, "return_code": 0},
            ],
        }
        sql_security = {
            "passed": True,
            "attempts": [
                {"attempt": 1, "return_code": 0},
            ],
        }

        failures = _classify_failures(web_e2e=web_e2e, sql_security=sql_security)
        self.assertTrue(any(item["failure_type"] == "transient_recovered_by_retry" for item in failures))

    def test_build_gate_judgement_card_has_traceability_fields(self) -> None:
        card = _build_gate_judgement_card(
            generated_at="2026-02-15T15:30:00+00:00",
            web_e2e={"attempts": [{"attempt": 1, "return_code": 0}]},
            sql_security={"attempts": [{"attempt": 1, "return_code": 0}]},
            release_decision="GO",
            failures=[],
            gate_path=Path("output/workpackages/nightly-quality-gate-20260215_153000.md"),
        )

        self.assertEqual(card["workpackage_id"], "wp-quality-gate-nightly-hardening-v0.2.0")
        self.assertEqual(card["task_batch_id"], "dispatch-address-line-closure-004")
        self.assertIn("gate_thresholds", card)
        self.assertIn("evidence_paths", card)


if __name__ == "__main__":
    unittest.main()
