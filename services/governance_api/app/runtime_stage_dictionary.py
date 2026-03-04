from __future__ import annotations

from typing import Final


RUNTIME_PIPELINE_STAGE_ORDER: Final[tuple[str, ...]] = (
    "created",
    "llm_confirmed",
    "packaged",
    "dryrun_finished",
    "publish_confirmed",
    "submitted",
    "accepted",
    "running",
    "finished",
)

RUNTIME_PIPELINE_STAGE_ZH: Final[dict[str, str]] = {
    "created": "已创建",
    "llm_confirmed": "需求已确认",
    "packaged": "已打包",
    "dryrun_finished": "试运行已完成",
    "publish_confirmed": "发布已确认",
    "submitted": "已提交",
    "accepted": "已受理",
    "running": "运行中",
    "finished": "已完成",
}


def ensure_known_pipeline_stage(stage: str) -> str:
    name = str(stage or "").strip()
    if not name:
        return ""
    if name not in RUNTIME_PIPELINE_STAGE_ZH:
        raise ValueError(f"unknown pipeline stage: {name}")
    return name
