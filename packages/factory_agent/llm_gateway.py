from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class RequirementLLMGateway:
    """地址治理需求确认的 LLM 访问网关。"""

    def query(self, prompt: str) -> Dict[str, Any]:
        from tools.agent_cli import load_config, run_requirement_query

        config_path = Path(__file__).resolve().parents[2] / "config" / "llm_api.json"
        try:
            config = load_config(str(config_path))
        except TypeError:
            # Backward-compatible with mocks or legacy wrappers that accept no args.
            config = load_config()
        system_prompt = (
            "你是地址治理工厂Agent。"
            "请仅输出JSON对象，字段必须包含："
            "target(string), data_sources(array), rule_points(array), outputs(array)。"
        )
        return run_requirement_query(prompt, config, system_prompt_override=system_prompt)
