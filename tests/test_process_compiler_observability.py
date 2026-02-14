import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_compiler import ProcessCompiler


class ProcessCompilerObservabilityTests(unittest.TestCase):
    def test_compile_generates_observability_bundle_and_step_error_codes(self):
        draft = {
            "draft_id": "draft_observe_001",
            "requirement": "设计地址标准化与质量校验工艺，并入库",
            "process_name": "地址标准化流程",
            "domain": "address_governance",
            "goal": "地址标准化并输出质量结论",
            "process_doc_markdown": "步骤包括验证、标准化、质量检查与入库",
        }

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                result = ProcessCompiler().compile(draft, session_id="test")
            finally:
                os.chdir(old_cwd)

            self.assertIn("observability_bundle", result.process_spec)

            bundle = result.observability_bundle
            self.assertEqual(bundle.get("generator"), "factory_observability_generator")
            self.assertEqual(len(bundle.get("entrypoints", [])), 2)

            for step in result.process_spec.get("steps", []):
                self.assertIn("error_code", step)
                self.assertTrue(step["error_code"].endswith("_FAILED"))

            observe_path = Path(td) / bundle["entrypoints"][0]
            metrics_path = Path(td) / bundle["entrypoints"][1]
            self.assertTrue(observe_path.exists())
            self.assertTrue(metrics_path.exists())

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            self.assertIn("step_error_codes", metrics)
            self.assertIn("INPUT_VALIDATION", metrics["step_error_codes"])
            self.assertEqual(
                metrics["step_error_codes"]["INPUT_VALIDATION"],
                "INPUT_VALIDATION_FAILED",
            )


if __name__ == "__main__":
    unittest.main()
