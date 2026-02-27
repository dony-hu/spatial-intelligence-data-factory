#!/usr/bin/env python3
"""校验 bmad-story-deliver 所需的标准输入。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


ALLOWED_STATUS = {"backlog", "ready-for-dev", "in-progress", "done"}


def validate(base_dir: Path) -> tuple[list[str], str | None]:
    errors: list[str] = []
    next_story: str | None = None

    status_path = base_dir / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml"
    if not status_path.exists():
        return [f"缺少文件: {status_path}"], None

    try:
        payload = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - 防御性分支
        return [f"sprint-status.yaml 解析失败: {exc}"], None

    stories = payload.get("stories")
    if not isinstance(stories, dict) or not stories:
        return ["sprint-status.yaml 中 stories 为空或格式错误"], None

    backlog_candidates: list[tuple[int, int, str]] = []

    for key, status in stories.items():
        if status not in ALLOWED_STATUS:
            errors.append(f"非法状态: {key} -> {status}")
        m = re.match(r"^(\d+)-(\d+)-[a-z0-9-]+$", str(key))
        if not m:
            errors.append(f"非法 story key 格式: {key} (应为 X-Y-story-name)")
            continue

        epic_num, story_num = int(m.group(1)), int(m.group(2))
        if status == "backlog":
            backlog_candidates.append((epic_num, story_num, key))

        story_path = status_path.parent / f"{key}.md"
        if not story_path.exists():
            errors.append(f"缺少 story 文档: {story_path}")
            continue

        text = story_path.read_text(encoding="utf-8")
        status_match = re.search(r"^Status:\s*(.+?)\s*$", text, flags=re.MULTILINE)
        if not status_match:
            errors.append(f"文档缺少 Status 行: {story_path}")
        else:
            doc_status = status_match.group(1).strip()
            if doc_status != status:
                errors.append(f"状态不一致: {key} yaml={status} doc={doc_status}")

        if "## Tasks" not in text and "## 任务清单" not in text:
            errors.append(f"文档缺少 Tasks/任务清单段落: {story_path}")
        if "- [ ]" not in text and "- [x]" not in text:
            errors.append(f"文档缺少任务勾选项: {story_path}")

    if backlog_candidates:
        backlog_candidates.sort(key=lambda x: (x[0], x[1]))
        _, _, story_key = backlog_candidates[0]
        story_number = ".".join(story_key.split("-")[:2])
        next_story = story_number

    return errors, next_story


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bmad-story-deliver inputs")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="仓库根目录（默认当前目录）",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    errors, next_story = validate(base_dir)
    if errors:
        print("FAIL: bmad-story-deliver 标准输入校验失败")
        for item in errors:
            print(f"- {item}")
        return 1

    print("PASS: bmad-story-deliver 标准输入校验通过")
    if next_story:
        print(f"NEXT_BACKLOG_STORY={next_story}")
    else:
        print("NEXT_BACKLOG_STORY=NONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
