from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_expert_human_loop import ProcessExpertHumanLoopRunner


class _FakeLLMService:
    def generate_plan(self, requirement: str):
        return {
            "plan": {
                "auto_execute": False,
                "max_duration_sec": 120,
                "quality_threshold": 0.9,
                "priority": "high",
                "steps": ["多源核验", "证据链整理", "人工复核"],
            }
        }


class ProcessExpertHumanLoopTests(unittest.TestCase):
    def test_human_loop_runner_writes_decision_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            runner = ProcessExpertHumanLoopRunner(
                llm_service=_FakeLLMService(),
                output_dir=output_dir,
            )
            result = runner.run(
                requirement="请设计地址核实工艺并输出人工评审模板",
                process_code="PROC_HUMAN_LOOP_UT",
                domain="verification",
            )

            self.assertEqual(result.summary.get("status"), "ok")
            self.assertEqual(result.summary.get("mode"), "human_llm_semi_auto")

            run_dir = result.run_dir
            self.assertTrue(run_dir.exists())
            self.assertTrue((run_dir / "final_summary.json").exists())
            self.assertTrue((run_dir / "design_result.json").exists())
            self.assertTrue((run_dir / "human_decision_template.json").exists())

            decision_template = json.loads((run_dir / "human_decision_template.json").read_text(encoding="utf-8"))
            self.assertIn("decision", decision_template)
            self.assertIn("change_request", decision_template)

    def test_human_loop_runner_applies_decision_change_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            runner = ProcessExpertHumanLoopRunner(
                llm_service=_FakeLLMService(),
                output_dir=output_dir,
            )
            result = runner.run(
                requirement="先生成草案",
                process_code="PROC_HUMAN_LOOP_UT2",
                domain="verification",
                decision_payload={
                    "decision": "revise",
                    "change_request": "补充证据链字段和冲突仲裁判定规则",
                    "goal": "提升可审计性",
                },
            )

            self.assertTrue(result.summary.get("decision_applied"))
            self.assertIsNotNone(result.modified_result)
            self.assertEqual((result.modified_result or {}).get("status"), "ok")
            self.assertTrue((result.run_dir / "modified_result.json").exists())


if __name__ == "__main__":
    unittest.main()
