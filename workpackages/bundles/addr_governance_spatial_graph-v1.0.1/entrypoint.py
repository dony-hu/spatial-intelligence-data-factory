#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

BUNDLE_DIR = Path(__file__).parent.resolve()


def main():
    print("======================================")
    print(f"  执行 WorkPackage: {BUNDLE_DIR.name}")
    print("======================================")
    
    print("加载技能...")
    skills_dir = BUNDLE_DIR / "skills"
    if skills_dir.exists():
        for skill_file in skills_dir.glob("*.md"):
            print(f"  - {skill_file.name}")
    
    print("执行脚本...")
    scripts_dir = BUNDLE_DIR / "scripts"
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.py"):
            print(f"  - {script_file.name}")
            subprocess.run(["python3", str(script_file)], cwd=str(BUNDLE_DIR), check=True)
    
    print("执行产线观测...")
    observe_script = BUNDLE_DIR / "observability" / "line_observe.py"
    if observe_script.exists():
        subprocess.run(["python3", str(observe_script)], cwd=str(BUNDLE_DIR), check=True)
    
    print("======================================")
    print("  WorkPackage 执行完成")
    print("======================================")


if __name__ == "__main__":
    main()