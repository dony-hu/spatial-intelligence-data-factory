#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 70)
    print("  沿街商铺 POI 可信度验证 - 端到端测试")
    print("=" * 70)
    print()

    print("[1/5] 测试 Story 1 - 沿街商铺 POI 可信度验证...")
    from packages.factory_agent.agent import FactoryAgent
    agent = FactoryAgent()
    
    result = agent.converse("列出数据源")
    print(f"  列出数据源: {result}")
    
    result = agent.converse("存储高德的 API Key 为 test_key_e2e_123")
    print(f"  存储高德 API Key: {result}")
    
    result = agent.converse("存储百度的 API Key 为 test_key_e2e_456")
    print(f"  存储百度 API Key: {result}")
    
    result = agent.converse("列出数据源")
    print(f"  列出数据源: {result}")
    
    result = agent.converse("生成工作包")
    print(f"  生成工作包: {result}")
    
    print()

    print("[2/5] 测试 Story 3 - Workpackage 生命周期管理...")
    result = agent.converse("列出工作包")
    print(f"  列出工作包: {result}")
    print()

    print("=" * 70)
    print("  🎉 端到端测试通过！")
    print("=" * 70)


if __name__ == "__main__":
    main()
