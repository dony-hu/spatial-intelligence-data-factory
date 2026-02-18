# WorkPackage 目录与文件结构设计

## Why
需要明确 workpackage 的目录和文件结构，确保 workpackage 由 skills 和程序脚本（sh、py 等）组成，并包含标准工作入口，能够被数据治理 Runtime 理解和执行。

## WorkPackage 目录结构

```
workpackages/
├── wp-*.json                    # WorkPackage 配置文件（符合 schema）
├── skills/                      # 技能目录
│   └── *.md                     # 技能 Markdown 配置
└── bundles/                     # 版本发布目录
    └── &lt;bundle-name&gt;-v&lt;version&gt;/
        ├── README.md             # 版本说明
        ├── workpackage.json      # WorkPackage 配置（副本）
        ├── skills/               # 技能目录
        │   └── *.md             # 技能 Markdown 配置
        ├── scripts/              # 程序脚本目录
        │   ├── *.sh             # Shell 脚本
        │   ├── *.py             # Python 脚本
        │   └── ...              # 其他类型脚本
        ├── entrypoint.sh         # 标准工作入口（Shell）
        ├── entrypoint.py         # 标准工作入口（Python）
        └── observability/        # 可观测性目录
            ├── line_metrics.json # 产线指标
            └── line_observe.py   # 产线观测脚本
```

## 目录与文件说明

| 目录/文件 | 说明 | 谁生成 | 谁消费 |
|---|---|---|---|
| `wp-*.json` | WorkPackage 配置文件（根目录） | 工厂 Agent | 治理产线 |
| `skills/` | 技能配置目录 | 工厂 Agent | 治理 Runtime |
| `bundles/&lt;bundle&gt;-v&lt;version&gt;/` | 版本发布目录 | 工厂 Agent | 治理产线 |
| `bundles/.../README.md` | 版本说明 | 工厂 Agent | 用户/产线 |
| `bundles/.../workpackage.json` | WorkPackage 配置（副本） | 工厂 Agent | 治理产线 |
| `bundles/.../skills/` | 技能配置目录（副本） | 工厂 Agent | 治理 Runtime |
| `bundles/.../scripts/` | 程序脚本目录 | 工厂 Agent | 治理产线 |
| `bundles/.../entrypoint.sh` | 标准工作入口（Shell） | 工厂 Agent | 治理 Runtime |
| `bundles/.../entrypoint.py` | 标准工作入口（Python） | 工厂 Agent | 治理 Runtime |
| `bundles/.../observability/` | 可观测性目录 | 工厂 Agent | 可观测性看板 |

---

## 标准工作入口设计

### entrypoint.sh（Shell 入口）
```bash
#!/bin/bash
# WorkPackage 标准工作入口 - Shell 版本

set -e

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &amp;&amp; pwd)"

echo "======================================"
echo "  执行 WorkPackage: $(basename "$BUNDLE_DIR")"
echo "======================================"

# 1. 加载技能
echo "加载技能..."
for skill_file in "$BUNDLE_DIR/skills"/*.md; do
    if [ -f "$skill_file" ]; then
        echo "  - $(basename "$skill_file")"
    fi
done

# 2. 执行脚本
echo "执行脚本..."
for script_file in "$BUNDLE_DIR/scripts"/*.{sh,py}; do
    if [ -f "$script_file" ]; then
        echo "  - $(basename "$script_file")"
        if [[ "$script_file" == *.py ]]; then
            python "$script_file"
        else
            bash "$script_file"
        fi
    fi
done

# 3. 执行产线观测
echo "执行产线观测..."
if [ -f "$BUNDLE_DIR/observability/line_observe.py" ]; then
    python "$BUNDLE_DIR/observability/line_observe.py"
fi

echo "======================================"
echo "  WorkPackage 执行完成"
echo "======================================"
```

---

### entrypoint.py（Python 入口）
```python
#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

BUNDLE_DIR = Path(__file__).parent.resolve()


def main():
    print("======================================")
    print(f"  执行 WorkPackage: {BUNDLE_DIR.name}")
    print("======================================")
    
    # 1. 加载技能
    print("加载技能...")
    skills_dir = BUNDLE_DIR / "skills"
    if skills_dir.exists():
        for skill_file in skills_dir.glob("*.md"):
            print(f"  - {skill_file.name}")
    
    # 2. 执行脚本
    print("执行脚本...")
    scripts_dir = BUNDLE_DIR / "scripts"
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.py"):
            print(f"  - {script_file.name}")
            exec(script_file.read_text(encoding="utf-8"))
    
    # 3. 执行产线观测
    print("执行产线观测...")
    observe_script = BUNDLE_DIR / "observability" / "line_observe.py"
    if observe_script.exists():
        exec(observe_script.read_text(encoding="utf-8"))
    
    print("======================================")
    print("  WorkPackage 执行完成")
    print("======================================")


if __name__ == "__main__":
    main()
```

---

## WorkPackage 生命周期与对应目录结构

| 阶段 | 说明 | 目录/文件 |
|---|---|---|
| **Dryrun** | 试运行测试效果 | `workpackages/skills/` + 临时 `scripts/` |
| **Release** | 版本发布 | `workpackages/bundles/&lt;bundle&gt;-v&lt;version&gt;/` |
| **执行** | 治理产线执行 | `bundles/.../entrypoint.sh` 或 `entrypoint.py` |

---

## 与现有系统的对应

| 现有文件 | 新结构位置 |
|---|---|
| `workpackages/wp-*.json` | 根目录保留，同时在 `bundles/.../workpackage.json` 有副本 |
| `workpackages/skills/*.md` | 根目录保留，同时在 `bundles/.../skills/` 有副本 |
| `workpackages/bundles/*/observability/` | 保留在 `bundles/.../observability/` |
