#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 70)
    print("  Story 1: 沿街商铺 POI 可信度验证 - 测试")
    print("=" * 70)
    print()

    from packages.factory_agent.agent import FactoryAgent
    agent = FactoryAgent()

    print("[1/5] 测试列出数据源...")
    result = agent.converse("列出数据源")
    print(f"  {result}")
    print()

    print("[2/5] 测试存储高德 API Key...")
    result = agent.converse("存储高德的 API Key 为 test_key_123")
    print(f"  {result}")
    print()

    print("[3/5] 测试存储百度 API Key...")
    result = agent.converse("存储百度的 API Key 为 test_key_456")
    print(f"  {result}")
    print()

    print("[4/5] 再次列出数据源...")
    result = agent.converse("列出数据源")
    print(f"  {result}")
    print()

    print("[5/5] 测试生成工作包...")
    result = agent.converse("生成沿街商铺 POI 可信度验证工作包")
    print(f"  {result}")
    print()

    print("=" * 70)
    print("  🎉 Story 1 测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
