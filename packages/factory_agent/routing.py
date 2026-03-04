from __future__ import annotations

import re
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
    compact = "".join(text.split())

    if ("存储" in text and ("密钥" in text or "API" in text)) or (
        ("store" in lower or "save" in lower or "set" in lower)
        and "api" in lower
        and "key" in lower
    ):
        return "store_api_key"
    if (
        bool(re.search(r"(列出|查看|展示)\s*工作包", text))
        or bool(re.search(r"\blist\s+workpackage", lower))
    ) and not (("创建" in text or "生成" in text) and "工作包" in text):
        return "list_workpackages"
    if "查询" in text or ("query" in lower and ("workpackage" in lower)):
        return "query_workpackage"
    has_bundle_ref = bool(re.search(r"[a-zA-Z0-9_-]+-v\d+\.\d+\.\d+", text))
    if ("试运行" in text and ("工作包" in text or has_bundle_ref)) or ("dryrun" in lower and ("workpackage" in lower or has_bundle_ref)):
        return "dryrun_workpackage"
    explicit_publish = any(
        marker in compact
        for marker in (
            "发布工作包",
            "立即发布",
            "执行发布",
            "confirm_publish",
        )
    ) or ("publish" in lower and ("workpackage" in lower or "runtime" in lower))
    if not explicit_publish and "发布" in text:
        publish_target = bool(re.search(r"[a-zA-Z0-9_-]+-v\d+\.\d+\.\d+", text)) or ("runtime" in lower) or ("工作包" in text)
        explicit_publish = publish_target
    if explicit_publish:
        return "publish_workpackage"
    if bool(re.search(r"(列出|查看|展示)\s*数据源", text)) or bool(re.search(r"\blist\s+sources?\b", lower)):
        return "list_sources"
    if (("生成" in text or "创建" in text or "新建" in text) and "工作包" in text) or (
        "generate" in lower and ("workpackage" in lower or "work package" in lower)
    ) or (
        "create" in lower and ("workpackage" in lower or "work package" in lower)
    ):
        return "generate_workpackage"
    return "confirm_requirement"
