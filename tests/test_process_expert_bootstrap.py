from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_expert_bootstrap import ProcessExpertBootstrapRunner
from tools.process_expert_llm_bridge import RealProcessExpertLLMBridge


class ProcessExpertBootstrapTests(unittest.TestCase):
    @unittest.skipUnless(os.getenv("FACTORY_REAL_BOOTSTRAP_TEST") == "1", "set FACTORY_REAL_BOOTSTRAP_TEST=1 to enable real-mode bootstrap test")
    def test_bootstrap_runner_writes_round_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases_file = root / "cases.json"
            cases_file.write_text(
                json.dumps(
                    {
                        "meta": {"name": "ut_cases"},
                        "cases": [
                            {
                                "case_id": "C1",
                                "priority": "P0",
                                "category": "mainline",
                                "expected": {"verification_status": "VERIFIED_EXISTS"},
                            },
                            {
                                "case_id": "C2",
                                "priority": "P1",
                                "category": "conflict",
                                "expected": {"verification_status": "UNVERIFIABLE_ONLINE"},
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            output_dir = root / "out"
            llm_config = PROJECT_ROOT / "config" / "llm_api.json"
            self.assertTrue(llm_config.exists(), "llm_api.json is required for real bootstrap test")

            runner = ProcessExpertBootstrapRunner(
                llm_bridge=RealProcessExpertLLMBridge(str(llm_config)),
                cases_file=cases_file,
                output_dir=output_dir,
                max_rounds=3,
                score_threshold=0.8,
            )
            result = runner.run(process_code="PROC_BOOTSTRAP_UT")

            self.assertEqual(result.get("status"), "ok")
            self.assertIn("rounds", result)
            self.assertGreaterEqual(len(result.get("rounds") or []), 1)

            run_id = result.get("run_id")
            self.assertTrue(run_id)
            run_dir = output_dir / run_id
            self.assertTrue(run_dir.exists())
            self.assertTrue((run_dir / "final_summary.json").exists())

            first_round_dirs = [p for p in run_dir.iterdir() if p.is_dir() and p.name.startswith("round_")]
            self.assertTrue(first_round_dirs)

            round0 = first_round_dirs[0]
            self.assertTrue((round0 / "process_doc.md").exists())
            self.assertTrue((round0 / "audit.json").exists())
            self.assertTrue((round0 / "result.json").exists())
            self.assertTrue((round0 / "tool_scripts").exists())


if __name__ == "__main__":
    unittest.main()
