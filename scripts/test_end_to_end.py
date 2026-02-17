#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("=" * 70)
    print("  空间智能数据工厂 - 智能体架构增强端到端测试")
    print("=" * 70)
    print()

    all_passed = True

    # 1. 测试 1: 工厂 CLI
    print("[1/5] 测试工厂 CLI...")
    try:
        from packages.factory_cli.session import FactorySession
        session = FactorySession()
        result = session.chat("测试")
        print(f"  ✅ 工厂 CLI 正常: {result['status']}")
    except Exception as e:
        print(f"  ❌ 工厂 CLI 失败: {e}")
        all_passed = False
    print()

    # 2. 测试 2: 工厂 Agent
    print("[2/5] 测试工厂 Agent...")
    try:
        from packages.factory_agent.agent import FactoryAgent
        agent = FactoryAgent()
        skill_result = agent.output_skill(
            "test_skill_e2e",
            {"description": "测试技能"}
        )
        print(f"  ✅ 工厂 Agent 正常: {skill_result['skill_name']}")
    except Exception as e:
        print(f"  ❌ 工厂 Agent 失败: {e}")
        all_passed = False
    print()

    # 3. 测试 3: 治理 Runtime
    print("[3/5] 测试治理 Runtime 技能框架...")
    try:
        from packages.governance_runtime import GovernanceRuntime, Skill
        runtime = GovernanceRuntime()
        skill = Skill(
            name="test_skill",
            description="测试技能",
            entrypoint="test"
        )
        runtime.register_skill(skill)
        skills = runtime.list_skills()
        print(f"  ✅ 治理 Runtime 正常: {skills}")
    except Exception as e:
        print(f"  ❌ 治理 Runtime 失败: {e}")
        all_passed = False
    print()

    # 4. 测试 4: Runtime Selector
    print("[4/5] 测试 Runtime 选择器...")
    try:
        from packages.agent_runtime.runtime_selector import get_runtime
        runtime = get_runtime()
        print(f"  ✅ Runtime 选择器正常")
    except Exception as e:
        print(f"  ❌ Runtime 选择器失败: {e}")
        all_passed = False
    print()

    # 5. 测试 5: 治理 Runtime 加载技能
    print("[5/5] 测试治理 Runtime 加载技能...")
    try:
        from packages.governance_runtime import GovernanceRuntime
        runtime = GovernanceRuntime()
        runtime.load_skills_from_directory(Path("workpackages/skills"))
        skills = runtime.list_skills()
        print(f"  ✅ 加载技能成功: {skills}")
    except Exception as e:
        print(f"  ⚠️  加载技能可选: {e}")
    print()

    print("=" * 70)
    if all_passed:
        print("  🎉 所有核心功能测试通过！")
    else:
        print("  ⚠️  部分测试失败，请检查")
    print("=" * 70)


if __name__ == "__main__":
    main()
