#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.factory_agent.agent import FactoryAgent


def main():
    agent = FactoryAgent()
    print("=" * 60)
    print("  测试工厂 Agent")
    print("=" * 60)
    print()
    
    print("1. 测试 converse()")
    result = agent.converse("你好，请生成一个地址标准化脚本")
    print(f"  结果: {result}")
    print()
    
    print("2. 测试 output_skill()")
    skill_result = agent.output_skill(
        "normalize_address",
        {
            "description": "地址标准化技能 - 将原始地址标准化为规范格式"
        }
    )
    print(f"  结果: {skill_result}")
    print()
    
    print("=" * 60)
    print("  测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
