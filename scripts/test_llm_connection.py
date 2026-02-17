#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.agent_runtime.adapters.openhands_runtime import OpenHandsRuntime


def main():
    print("=" * 60)
    print("  测试 LLM 连接")
    print("=" * 60)
    print()
    
    config_path = "config/llm_api.json"
    print(f"使用配置文件: {config_path}")
    print()
    
    runtime = OpenHandsRuntime(config_path=config_path)
    
    print("正在发送测试请求...")
    print()
    
    task_context = {
        "addr_raw": "上海市浦东新区张江高科技园区博云路2号"
    }
    ruleset = {
        "ruleset_id": "test_connection"
    }
    
    try:
        result = runtime.run_task(task_context, ruleset)
        print("✅ LLM 连接成功！")
        print()
        print("返回结果:")
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"❌ LLM 连接失败: {e}")
        import traceback
        print()
        print("详细错误:")
        traceback.print_exc()
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
