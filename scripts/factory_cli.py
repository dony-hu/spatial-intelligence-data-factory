#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.factory_cli.session import FactorySession


def _record_cli_observation(
    *,
    workpackage_id: str = "",
    event_type: str,
    status: str = "success",
    payload: dict | None = None,
) -> None:
    try:
        from services.governance_api.app.repositories.governance_repository import REPOSITORY

        trace_id = f"trace_cli_{uuid4().hex[:12]}"
        REPOSITORY.record_observation_event(
            source_service="factory_cli",
            event_type=event_type,
            status=status,
            trace_id=trace_id,
            workpackage_id=str(workpackage_id or ""),
            payload={
                "pipeline_stage": "created",
                "client_type": "user",
                "version": "",
                "occurred_from": "factory_cli",
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                **(payload or {}),
            },
        )
    except Exception:
        # CLI should not be blocked by observability write failures.
        return


def _execute_command(args: argparse.Namespace, session: FactorySession) -> int:
    if args.command in {"generate", "confirm"}:
        _record_cli_observation(
            workpackage_id="",
            event_type="workpackage_created",
            payload={"command": str(args.command), "prompt": str(args.prompt or "")[:200]},
        )
        result = session.chat(args.prompt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if str(result.get("status", "")).lower() in {"blocked", "error"}:
            return 2
        return 0
    if args.command == "dryrun":
        _record_cli_observation(
            workpackage_id=str(args.workpackage or ""),
            event_type="workpackage_created",
            payload={"command": "dryrun", "prompt": f"试运行 {args.workpackage}"},
        )
        result = session.chat(f"试运行 {args.workpackage}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if str(result.get("status", "")).lower() in {"blocked", "error"}:
            return 2
        return 0
    if args.command == "publish":
        _record_cli_observation(
            workpackage_id=str(args.workpackage or ""),
            event_type="workpackage_created",
            payload={"command": "publish", "prompt": f"发布 {args.workpackage} 到 runtime"},
        )
        result = session.chat(f"发布 {args.workpackage} 到 runtime")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if str(result.get("status", "")).lower() in {"blocked", "error"}:
            return 2
        return 0
    if args.command == "query-workpackage":
        result = session.chat(f"查询 {args.workpackage}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if str(result.get("status", "")).lower() in {"blocked", "error"}:
            return 2
        return 0
    if args.command == "list-workpackages":
        result = session.chat("列出工作包")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if str(result.get("status", "")).lower() in {"blocked", "error"}:
            return 2
        return 0
    if args.command == "list-skills":
        skills_dir = Path("workpackages/skills")
        if skills_dir.exists():
            skills = list(skills_dir.glob("*.md"))
            print(f"找到 {len(skills)} 个技能:")
            for skill in skills:
                print(f"  - {skill.stem}")
        else:
            print("暂无技能")
        return 0
    if args.command == "run-skill":
        print(f"运行技能: {args.skill_name}")
        print("(功能待实现)")
        return 0
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="空间智能数据工厂 - 工厂 CLI"
    )
    subparsers = parser.add_subparsers(title="子命令", dest="command")

    # generate 子命令（兼容旧入口）
    generate_parser = subparsers.add_parser("generate", help="对话式生成治理脚本")
    generate_parser.add_argument("prompt", help="生成脚本的提示")

    # confirm 子命令
    confirm_parser = subparsers.add_parser("confirm", help="对话确认治理需求（A1）")
    confirm_parser.add_argument("prompt", help="治理需求描述")

    # dryrun 子命令
    dryrun_parser = subparsers.add_parser("dryrun", help="试运行工作包（A2）")
    dryrun_parser.add_argument("workpackage", help="工作包名称，如 demo-v1.0.0")

    # publish 子命令
    publish_parser = subparsers.add_parser("publish", help="发布工作包到 Runtime（A3）")
    publish_parser.add_argument("workpackage", help="工作包名称，如 demo-v1.0.0")

    # query-workpackage 子命令
    query_wp_parser = subparsers.add_parser("query-workpackage", help="查询工作包详情")
    query_wp_parser.add_argument("workpackage", help="工作包名称，如 demo-v1.0.0")

    # list-workpackages 子命令
    subparsers.add_parser("list-workpackages", help="列出工作包")

    # list-skills 子命令
    list_skills_parser = subparsers.add_parser("list-skills", help="列出可用技能")

    # run-skill 子命令
    run_skill_parser = subparsers.add_parser("run-skill", help="运行指定技能")
    run_skill_parser.add_argument("skill_name", help="技能名称")

    args = parser.parse_args()
    session = FactorySession()

    if not args.command:
        parser.print_help()
        return 0
    return _execute_command(args, session)


if __name__ == "__main__":
    raise SystemExit(main())
