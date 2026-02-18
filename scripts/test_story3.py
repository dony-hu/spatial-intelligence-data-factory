#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 70)
    print("  Story 3: Workpackage 生命周期管理 - 测试")
    print("=" * 70)
    print()

    from packages.factory_agent.agent import FactoryAgent
    agent = FactoryAgent()

    print("[1/1] 测试列出工作包...")
    result = agent.converse("列出工作包")
    print(f"  {result}")
    print()

    print("=" * 70)
    print("  🎉 Story 3 测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
