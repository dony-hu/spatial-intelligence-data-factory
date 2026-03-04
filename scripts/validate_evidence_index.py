#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PATH_PATTERN = re.compile(
    r"((?:tests|services|docs|output|_bmad-output)/[A-Za-z0-9_\-./]*(?:\.[A-Za-z0-9]+|/))"
)


def _category_for_path(path: str) -> str:
    if path.startswith("tests/") or path.startswith("services/"):
        return "test_file"
    if path.startswith("docs/acceptance/"):
        return "acceptance_report"
    if path.startswith("output/"):
        return "artifact"
    return "document"


def build_evidence_index(doc_paths: list[Path], *, repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for doc in doc_paths:
        text = doc.read_text(encoding="utf-8")
        seen: set[str] = set()
        for match in PATH_PATTERN.findall(text):
            target = str(match).strip().rstrip(".,)")
            if not target or target in seen:
                continue
            seen.add(target)
            rows.append(
                {
                    "doc": str(doc.relative_to(repo_root)),
                    "category": _category_for_path(target),
                    "target_path": target,
                    "exists": (repo_root / target).exists(),
                }
            )
    return rows


def validate_evidence_index_rows(rows: list[dict[str, Any]], *, repo_root: Path) -> list[str]:
    errors: list[str] = []
    required = ("doc", "category", "target_path", "exists")
    for idx, row in enumerate(rows):
        for key in required:
            if key not in row:
                errors.append(f"row[{idx}] missing field: {key}")
        path = str(row.get("target_path") or "")
        if not path:
            errors.append(f"row[{idx}] target_path is empty")
            continue
        if not (repo_root / path).exists():
            errors.append(f"path not found: {path}")
    return errors


def _render_markdown(rows: list[dict[str, Any]], errors: list[str]) -> str:
    lines = [
        f"# Epic3 证据索引映射（{datetime.now().date().isoformat()}）",
        "",
        f"- 总条数：`{len(rows)}`",
        f"- 校验结论：`{'PASS' if not errors else 'BLOCKED'}`",
        "",
        "| 来源文档 | 类别 | 目标路径 | 存在性 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('doc','-')} | {row.get('category','-')} | `{row.get('target_path','-')}` | {'YES' if row.get('exists') else 'NO'} |"
        )
    lines.extend(["", "## 校验错误"])
    if not errors:
        lines.append("- 无")
    else:
        lines.extend(f"- {item}" for item in errors)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate evidence index mapping for epic3 docs")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="_bmad-output/implementation-artifacts/epic3-evidence-index-map-latest.md")
    parser.add_argument(
        "--docs",
        nargs="*",
        default=[
            "docs/epic-runtime-observability-v2-review-2026-03-02.md",
            "docs/epic-runtime-observability-v2-retrospective-2026-03-02.md",
            "_bmad-output/implementation-artifacts/epic3-status-review-and-task-list-2026-03-02.md",
            "_bmad-output/implementation-artifacts/epic3-linear-pr-mapping-2026-03-02.md",
        ],
    )
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    docs = [(repo_root / p) for p in args.docs]
    missing_docs = [str(p) for p in docs if not p.exists()]
    if missing_docs:
        for item in missing_docs:
            print(f"[ERROR] doc not found: {item}")
        return 2
    rows = build_evidence_index(docs, repo_root=repo_root)
    errors = validate_evidence_index_rows(rows, repo_root=repo_root)
    out_path = (repo_root / args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render_markdown(rows, errors), encoding="utf-8")
    print(f"Evidence index: {out_path}")
    if errors:
        for item in errors:
            print(f"[ERROR] {item}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
