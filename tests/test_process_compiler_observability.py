import os
import shutil
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_compiler import ProcessCompiler


class ProcessCompilerObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.bundle_root = PROJECT_ROOT / "workpackages" / "bundles"

    def tearDown(self):
        # 仅清理测试生成目录，不影响现有实包目录
        for p in self.bundle_root.glob("addrobstest*_v1-1-0-0"):
            if p.exists():
                shutil.rmtree(p)

    def test_compile_generates_observability_bundle_and_error_codes(self):
        compiler = ProcessCompiler()
        draft = {
            "requirement": "请先验证地址再标准化，并做质量评估后入库",
            "process_name": "Address Obs Test",
            "process_code": "ADDR_OBS_TEST",
            "domain": "address_governance",
            "goal": "测试观测代码生成",
            "process_doc_markdown": "步骤：验证、标准化、质量评估、入库",
        }
        result = compiler.compile(draft)
        # 现有编译链路可能因外部工具生成失败进入 partial/manual，但观测包必须生成
        self.assertIn(result.execution_readiness, {"ready", "partial", "manual_required"})
        self.assertIn("observability_bundle", result.process_spec)

        bundle = result.process_spec["observability_bundle"]
        self.assertIn("entrypoints", bundle)
        self.assertGreaterEqual(len(bundle["entrypoints"]), 2)

        for p in bundle["entrypoints"]:
            self.assertTrue(os.path.exists(p), f"missing generated file: {p}")

        steps = result.process_spec.get("steps", [])
        self.assertGreaterEqual(len(steps), 1)
        for step in steps:
            self.assertIn("error_code", step)
            self.assertTrue(str(step["error_code"]).startswith("STEP_"))


if __name__ == "__main__":
    unittest.main()
