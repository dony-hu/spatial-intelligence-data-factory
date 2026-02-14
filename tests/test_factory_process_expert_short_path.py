from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_compiler import ProcessCompiler
from tools.process_tools.design_process_tool import DesignProcessTool
from tools.address_toolpack_builder import AddressToolpackBuilder
from tools.agent_cli import load_config, run_requirement_query, parse_plan_from_answer


class _InMemoryRuntimeStore:
    def __init__(self) -> None:
        self._drafts = {}
        self._process_defs = {
            "PROC_TOOLPACK": {
                "id": "procdef_toolpack_001",
                "code": "PROC_TOOLPACK",
                "name": "PROC_TOOLPACK 工艺",
                "domain": "verification",
            }
        }

    def upsert_process_draft(self, **kwargs):
        draft_id = kwargs.get("draft_id")
        self._drafts[draft_id] = dict(kwargs)
        return {"draft_id": draft_id, "updated_at": "2026-02-14T00:00:00", "status": kwargs.get("status", "editable")}

    def find_process_definition(self, code: str):
        return self._process_defs.get(code)


class _RealLLMService:
    def __init__(self, config_path: str) -> None:
        self.config = load_config(config_path)

    def generate_plan(self, requirement: str):
        result = run_requirement_query(
            requirement=(
                "请基于以下需求输出JSON计划字段："
                "auto_execute,max_duration,quality_threshold,priority,addresses。\n"
                f"需求：{requirement}"
            ),
            config=self.config,
        )
        answer = str(result.get("answer") or "")
        plan = parse_plan_from_answer(answer)
        return {"plan": plan}


class FactoryProcessExpertShortPathTests(unittest.TestCase):
    @unittest.skipUnless(os.getenv("FACTORY_REAL_SHORT_PATH") == "1", "set FACTORY_REAL_SHORT_PATH=1 to enable real-mode test")
    def test_real_mode_llm_and_map_api(self):
        map_api_url = str(os.getenv("MAP_TOOLPACK_API_URL") or "").strip()
        if not map_api_url:
            self.skipTest("MAP_TOOLPACK_API_URL is required in real mode")

        llm_config_path = str(PROJECT_ROOT / "config" / "llm_api.json")
        llm_service = _RealLLMService(llm_config_path)
        runtime_store = _InMemoryRuntimeStore()
        compiler = ProcessCompiler()

        design_tool = DesignProcessTool(runtime_store=runtime_store, process_compiler=compiler, llm_service=llm_service)
        design_result = design_tool.execute(
            {
                "requirement": "通过地图API采样并生成工具包脚本，支持后续离线地址产线调用",
                "process_code": "PROC_TOOLPACK",
                "domain": "verification",
            },
            session_id="ut_short_path_real_001",
        )
        self.assertEqual(design_result.get("status"), "ok")
        self.assertTrue((design_result.get("compilation") or {}).get("success"))

        builder = AddressToolpackBuilder(
            map_api_url=map_api_url,
            map_api_key=str(os.getenv("MAP_TOOLPACK_API_KEY") or "").strip(),
            llm_config_path=llm_config_path,
            enable_llm_iteration=True,
        )
        seed = str(os.getenv("MAP_TOOLPACK_SEED_ADDRESS") or "上海市黄浦区中山东一路1号").strip()
        toolpack = builder.build([seed])

        self.assertEqual(toolpack.get("generation_mode"), "factory_generated")
        self.assertEqual(int(toolpack.get("seed_count") or 0), 1)
        self.assertIn("cities", toolpack)


if __name__ == "__main__":
    unittest.main()
