#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.factory_cli.session import FactorySession


def _execute_command(args: argparse.Namespace, session: FactorySession) -> int:
    if args.command == "generate":
        result = session.chat(args.prompt)
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

    # generate 子命令
    generate_parser = subparsers.add_parser("generate", help="对话式生成治理脚本")
    generate_parser.add_argument("prompt", help="生成脚本的提示")

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
