from __future__ import annotations

from typing import Any, Dict


class FactorySession:
    """工厂会话 - 工厂 CLI 与工厂 Agent 的交互层"""

    def __init__(self):
        self._agent = None

    def _get_agent(self):
        if self._agent is None:
            try:
                from packages.factory_agent.agent import FactoryAgent
                self._agent = FactoryAgent()
            except ImportError:
                self._agent = None
        return self._agent

    def chat(self, prompt):
        """对话接口"""
        agent = self._get_agent()
        if agent:
            return agent.converse(prompt)
        return {
            "status": "blocked",
            "reason": "agent_unavailable",
            "requires_user_confirmation": True,
            "message": "工厂 Agent 不可用，流程已阻塞，等待人工确认方案",
            "prompt": prompt,
        }

    def generate_governance_script(self, description):
        """生成治理脚本"""
        agent = self._get_agent()
        if agent:
            return agent.generate_script(description)
        return {
            "status": "blocked",
            "reason": "agent_unavailable",
            "requires_user_confirmation": True,
            "message": "工厂 Agent 不可用，脚本生成已阻塞，等待人工确认方案",
            "description": description,
        }

    def supplement_trust_hub(self, source):
        """补充可信数据 HUB"""
        agent = self._get_agent()
        if agent:
            return agent.supplement_trust_hub(source)
        return {
            "status": "blocked",
            "reason": "agent_unavailable",
            "requires_user_confirmation": True,
            "message": "工厂 Agent 不可用，Trust Hub 补充已阻塞，等待人工确认方案",
            "source": source,
        }
