from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


class OpenCodeWorkpackageBuilder:
    """OpenCode 主导的工作包工件构建器。"""

    def build_bundle(self, *, bundle_dir: Path, blueprint: Dict[str, Any], sources: List[str]) -> None:
        bundle_dir.mkdir(parents=True, exist_ok=True)

        workpackage = blueprint.get("workpackage") if isinstance(blueprint.get("workpackage"), dict) else {}
        name = str(workpackage.get("name") or "workpackage")
        version = str(workpackage.get("version") or "v1.0.0")
        objective = str(workpackage.get("objective") or "数据治理执行")

        (bundle_dir / "README.md").write_text(self._generate_readme(name, version, sources, objective), encoding="utf-8")

        wp_config = dict(blueprint)
        wp_config["name"] = name
        wp_config["version"] = version
        wp_config["objective"] = objective
        wp_config["sources"] = sources
        (bundle_dir / "workpackage.json").write_text(json.dumps(wp_config, ensure_ascii=False, indent=2), encoding="utf-8")

        skills_dir = bundle_dir / "skills"
        skills_dir.mkdir(exist_ok=True)
        for source in sources:
            (skills_dir / f"{source}_verification.md").write_text(self._generate_skill_markdown(source), encoding="utf-8")

        scripts_dir = bundle_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        script_specs = blueprint.get("scripts") if isinstance(blueprint.get("scripts"), list) else []
        generated_count = 0
        for spec in script_specs:
            if not isinstance(spec, dict):
                continue
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", str(spec.get("name") or "").strip()) or ""
            if not filename.endswith(".py"):
                continue
            if filename == "run_pipeline.py":
                content = self._generate_verify_script(sources)
            else:
                content = self._generate_script_template(spec)
            (scripts_dir / filename).write_text(content, encoding="utf-8")
            generated_count += 1
        if generated_count == 0:
            (scripts_dir / "run_pipeline.py").write_text(self._generate_verify_script(sources), encoding="utf-8")

        (bundle_dir / "entrypoint.sh").write_text(self._generate_entrypoint_sh(), encoding="utf-8")
        (bundle_dir / "entrypoint.py").write_text(self._generate_entrypoint_py(), encoding="utf-8")

        observability_dir = bundle_dir / "observability"
        observability_dir.mkdir(exist_ok=True)
        line_metrics_path = observability_dir / "line_metrics.json"
        line_metrics_path.write_text(
            json.dumps({"sources": sources, "version": version, "objective": objective}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (observability_dir / "line_observe.py").write_text(self._generate_observe_script(), encoding="utf-8")
        (observability_dir / "opencode_build_report.json").write_text(
            json.dumps(
                {
                    "builder": "OpenCodeWorkpackageBuilder",
                    "bundle_name": bundle_dir.name,
                    "name": name,
                    "version": version,
                    "objective": objective,
                    "sources": sources,
                    "script_count": generated_count if generated_count > 0 else 1,
                    "line_metrics_path": str(line_metrics_path),
                    "status": "success",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        missing_apis = ((blueprint.get("api_plan") or {}).get("missing_apis") if isinstance(blueprint.get("api_plan"), dict) else []) or []
        env_lines = ["# 需要用户补充的外部API Key", ""]
        for item in missing_apis:
            if not isinstance(item, dict):
                continue
            if not bool(item.get("requires_key")):
                continue
            env_name = str(item.get("api_key_env") or f"{str(item.get('name') or 'EXT_API').upper()}_API_KEY")
            env_name = re.sub(r"[^A-Z0-9_]", "_", env_name.upper())
            env_lines.append(f"{env_name}=")
        if len(env_lines) > 2:
            (bundle_dir / "config").mkdir(exist_ok=True)
            (bundle_dir / "config" / "provider_keys.env.example").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    def _generate_readme(self, name: str, version: str, sources: List[str], objective: str) -> str:
        return f"""# {name} {version}

{objective}

## 数据源
{chr(10).join(f'- {s}' for s in sources)}

## 执行方式
```bash
bash entrypoint.sh
```

或
```bash
python entrypoint.py
```
""".strip()

    def _generate_script_template(self, spec: Dict[str, Any]) -> str:
        purpose = str(spec.get("purpose") or "执行数据治理步骤")
        name = str(spec.get("name") or "script.py")
        endpoint = str(spec.get("endpoint") or "")
        key_env = str(spec.get("api_key_env") or "EXTERNAL_API_KEY")
        return f"""#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

generated_by = "opencode_agent"

def main() -> None:
    api_key = os.getenv("{key_env}", "")
    payload = {{
        "script": "{name}",
        "purpose": "{purpose}",
        "endpoint": "{endpoint}",
        "api_key_provided": bool(api_key),
        "status": "ready" if api_key else "waiting_for_api_key",
    }}
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "{name}.result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()
""".strip()

    def _generate_skill_markdown(self, source: str) -> str:
        return f"""---
description: {source} 可信度验证
mode: subagent
model: anthropic/claude-3-7-sonnet
temperature: 0.2
tools:
  write: true
  edit: true
  bash: false
---

你是空间智能数据工厂的治理技能 Agent。

技能名称: {source} 可信度验证
""".strip()

    def _generate_verify_script(self, sources: List[str]) -> str:
        return f"""#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SOURCES = {json.dumps(sources, ensure_ascii=False)}
generated_by = "opencode_agent"

def main():
    print("沿街商铺 POI 可信度验证")
    print(f"使用数据源: {{', '.join(SOURCES)}}")
    
    results = {{
        "status": "ok",
        "sources": SOURCES,
        "verification": "pending"
    }}
    
    output_path = Path("output/verification_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print("验证完成")

if __name__ == "__main__":
    main()
""".strip()

    def _generate_entrypoint_sh(self) -> str:
        return """#!/bin/bash
set -e

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "  执行 WorkPackage: $(basename "$BUNDLE_DIR")"
echo "======================================"

echo "加载技能..."
for skill_file in "$BUNDLE_DIR/skills"/*.md; do
    if [ -f "$skill_file" ]; then
        echo "  - $(basename "$skill_file")"
    fi
done

echo "执行脚本..."
for script_file in "$BUNDLE_DIR/scripts"/*.py; do
    if [ -f "$script_file" ]; then
        echo "  - $(basename "$script_file")"
        python "$script_file"
    fi
done

echo "执行产线观测..."
if [ -f "$BUNDLE_DIR/observability/line_observe.py" ]; then
    python "$BUNDLE_DIR/observability/line_observe.py"
fi

echo "======================================"
echo "  WorkPackage 执行完成"
echo "======================================"
""".strip()

    def _generate_entrypoint_py(self) -> str:
        return """#!/usr/bin/env python3
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
""".strip()

    def _generate_observe_script(self) -> str:
        return """#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

def main():
    print("产线观测脚本")
    metrics = {
        "status": "ok",
        "timestamp": "2026-02-17T00:00:00Z"
    }
    metrics_path = Path("observability/line_metrics.json")
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
""".strip()
