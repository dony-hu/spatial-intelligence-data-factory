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
                pass
        return self._agent

    def chat(self, prompt):
        """对话接口"""
        agent = self._get_agent()
        if agent:
            return agent.converse(prompt)
        return {
            "status": "pending",
            "message": "工厂 Agent 尚未实现",
            "prompt": prompt
        }

    def generate_governance_script(self, description):
        """生成治理脚本"""
        agent = self._get_agent()
        if agent:
            return agent.generate_script(description)
        return {
            "status": "pending",
            "message": "工厂 Agent 尚未实现",
            "description": description
        }

    def supplement_trust_hub(self, source):
        """补充可信数据 HUB"""
        agent = self._get_agent()
        if agent:
            return agent.supplement_trust_hub(source)
        return {
            "status": "pending",
            "message": "工厂 Agent 尚未实现",
            "source": source
        }
