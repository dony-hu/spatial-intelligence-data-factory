from __future__ import annotations

from typing import Literal


AgentIntent = Literal[
    "store_api_key",
    "list_workpackages",
    "query_workpackage",
    "dryrun_workpackage",
    "publish_workpackage",
    "list_sources",
    "generate_workpackage",
    "confirm_requirement",
]


def detect_agent_intent(prompt: str) -> AgentIntent:
    text = str(prompt or "")
    lower = text.lower()

    if ("存储" in text and ("密钥" in text or "API" in text)) or ("api" in lower and "key" in lower):
        return "store_api_key"
    if ("列出" in text and "工作包" in text) or ("list" in lower and ("workpackage" in lower)):
        return "list_workpackages"
    if "查询" in text or ("query" in lower and ("workpackage" in lower)):
        return "query_workpackage"
    if "试运行" in text or ("dryrun" in lower and ("workpackage" in lower)):
        return "dryrun_workpackage"
    if "发布" in text or ("publish" in lower and ("workpackage" in lower or "runtime" in lower)):
        return "publish_workpackage"
    if ("列出" in text and "数据源" in text) or "list" in lower:
        return "list_sources"
    if ("生成" in text and "工作包" in text) or (
        "generate" in lower and ("workpackage" in lower or "work package" in lower)
    ):
        return "generate_workpackage"
    return "confirm_requirement"
