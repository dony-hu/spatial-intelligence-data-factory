from __future__ import annotations

import json
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

    def query_dialogue(self, prompt: str, history: list[dict[str, str]] | None = None) -> Dict[str, Any]:
        from tools.agent_cli import load_config, run_requirement_query

        config_path = Path(__file__).resolve().parents[2] / "config" / "llm_api.json"
        try:
            config = load_config(str(config_path))
        except TypeError:
            config = load_config()
        config["timeout_sec"] = min(int(config.get("timeout_sec") or 60), 25)
        system_prompt = (
            "你是数据治理工厂Agent。"
            "请与用户自然沟通，给出清晰、简短、可执行的建议。"
            "除非用户明确要求工作包/结构化需求，否则不要强制输出JSON模板。"
        )
        history_lines: list[str] = []
        for row in (history or [])[-6:]:
            role = str(row.get("role") or "").strip()
            content = str(row.get("content") or "").strip()
            if not role or not content:
                continue
            history_lines.append(f"{role}: {content}")
        dialogue_input = str(prompt or "")
        if history_lines:
            dialogue_input = "历史对话：\n" + "\n".join(history_lines) + "\n\n当前用户输入：\n" + dialogue_input
        return run_requirement_query(dialogue_input, config, system_prompt_override=system_prompt)

    def query_workpackage_blueprint(
        self,
        *,
        user_prompt: str,
        context: dict[str, Any],
        feedback: list[str] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        from tools.agent_cli import load_config, run_requirement_query

        config_path = Path(__file__).resolve().parents[2] / "config" / "llm_api.json"
        try:
            config = load_config(str(config_path))
        except TypeError:
            config = load_config()
        system_prompt = (
            "你是数据治理工厂的工作包设计Agent。"
            "先基于上下文完成需求对齐（架构上下文、I/O结构、已注册API、缺失API扩展方案、运行环境与脚本计划），"
            "再输出最终工作包蓝图。"
            "必须输出一个JSON对象，不要输出额外说明。"
            "JSON必须包含字段："
            "workpackage{name,version,objective},"
            "architecture_context{factory_architecture,runtime_env},"
            "io_contract{input_schema,output_schema},"
            "api_plan{registered_apis_used,missing_apis},"
            "execution_plan{steps},"
            "scripts[{name,purpose,runtime,entry}]。"
            "其中missing_apis每项至少包含name,endpoint,reason,requires_key。"
        )
        payload_lines: list[str] = []
        if history:
            turns = []
            for row in history[-8:]:
                role = str(row.get("role") or "").strip()
                content = str(row.get("content") or "").strip()
                if role and content:
                    turns.append({"role": role, "content": content})
            if turns:
                payload_lines.append("历史对话:")
                payload_lines.append(json.dumps(turns, ensure_ascii=False))
        payload_lines.append("架构与API上下文:")
        payload_lines.append(json.dumps(context, ensure_ascii=False))
        if feedback:
            payload_lines.append("上轮schema校验问题(请修复后重写完整JSON):")
            payload_lines.append(json.dumps(feedback, ensure_ascii=False))
        payload_lines.append("用户当前请求:")
        payload_lines.append(str(user_prompt or ""))
        prompt = "\n".join(payload_lines)
        return run_requirement_query(prompt, config, system_prompt_override=system_prompt)
