from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json

from packages.trust_hub import TrustHub


class FactoryAgent:
    """工厂 Agent - 生成治理脚本、补充可信数据 HUB、输出 Skills"""

    def __init__(self):
        self._opencode_available = self._check_opencode()
        self._trust_hub = TrustHub()
        self._state: Dict[str, Any] = {}

    def _check_opencode(self):
        """检查 OpenCode 是否可用"""
        try:
            import subprocess
            subprocess.run(["opencode", "--version"], capture_output=True, check=True)
            return True
        except Exception:
            return False

    def converse(self, prompt):
        """对话接口 - 支持确定数据源、存储 API Key、生成工作包、workpackage 生命周期管理"""
        prompt_lower = prompt.lower()
        
        if ("api" in prompt_lower and "key" in prompt_lower) or ("存储" in prompt and ("密钥" in prompt or "API" in prompt)):
            return self._handle_store_api_key(prompt)
        
        if ("list" in prompt_lower and ("workpackage" in prompt_lower or "工作包" in prompt)) or ("列出" in prompt and ("工作包" in prompt or "workpackage" in prompt)):
            return self._handle_list_workpackages()
        
        if "list" in prompt_lower or ("列出" in prompt and ("数据源" in prompt or "source" in prompt)):
            return self._handle_list_sources()
        
        if ("generate" in prompt_lower and ("workpackage" in prompt_lower or "work package" in prompt_lower)) or ("生成" in prompt and ("工作包" in prompt or "workpackage" in prompt)):
            return self._handle_generate_workpackage(prompt)
        
        return {
            "status": "ok",
            "opencode_available": self._opencode_available,
            "prompt": prompt,
            "message": "工厂 Agent 就绪，请告诉我需要做什么（存储 API Key、生成工作包、列出数据源等）"
        }

    def _handle_store_api_key(self, prompt):
        """处理存储 API Key 的对话"""
        name = self._extract_name(prompt)
        api_key = self._extract_api_key(prompt)
        provider = self._extract_provider(prompt)
        
        if not name or not api_key:
            return {
                "status": "error",
                "message": "请提供数据源名称和 API Key，例如：'存储高德的 API Key 为 xxx'"
            }
        
        self._trust_hub.store_api_key(
            name=name,
            api_key=api_key,
            provider=provider
        )
        
        return {
            "status": "ok",
            "action": "store_api_key",
            "name": name,
            "provider": provider,
            "message": f"已存储 {name} 的 API Key"
        }

    def _handle_list_sources(self):
        """处理列出数据源的对话"""
        sources = self._trust_hub.list_sources()
        return {
            "status": "ok",
            "action": "list_sources",
            "sources": sources,
            "message": f"已配置 {len(sources)} 个数据源"
        }

    def _handle_list_workpackages(self):
        """处理列出工作包的对话"""
        bundles_dir = Path("workpackages/bundles")
        workpackages = []
        if bundles_dir.exists():
            for bundle_dir in bundles_dir.iterdir():
                if bundle_dir.is_dir():
                    workpackages.append(bundle_dir.name)
        return {
            "status": "ok",
            "action": "list_workpackages",
            "workpackages": workpackages,
            "message": f"已发布 {len(workpackages)} 个工作包"
        }

    def _handle_generate_workpackage(self, prompt):
        """处理生成工作包的对话"""
        name = self._extract_name(prompt) or "poi-trust-verification"
        version = "v1.0.0"
        bundle_name = f"{name}-{version}"
        
        sources = self._trust_hub.list_sources()
        if len(sources) < 2:
            return {
                "status": "error",
                "message": f"需要至少 2 个数据源，当前只有 {len(sources)} 个，请先存储 API Key"
            }
        
        bundle_dir = Path(f"workpackages/bundles/{bundle_name}")
        self._create_workpackage_bundle(bundle_dir, name, version, sources[:3])
        
        return {
            "status": "ok",
            "action": "generate_workpackage",
            "bundle_name": bundle_name,
            "bundle_path": str(bundle_dir),
            "sources_used": sources[:3],
            "message": f"工作包 {bundle_name} 已生成"
        }

    def _create_workpackage_bundle(self, bundle_dir: Path, name: str, version: str, sources: List[str]):
        """创建工作包 bundle"""
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        (bundle_dir / "README.md").write_text(
            self._generate_readme(name, version, sources),
            encoding="utf-8"
        )
        
        wp_config = {
            "name": name,
            "version": version,
            "sources": sources
        }
        (bundle_dir / "workpackage.json").write_text(
            json.dumps(wp_config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        skills_dir = bundle_dir / "skills"
        skills_dir.mkdir(exist_ok=True)
        
        for source in sources:
            skill_path = skills_dir / f"{source}_verification.md"
            skill_path.write_text(
                self._generate_skill_markdown(source),
                encoding="utf-8"
            )
        
        scripts_dir = bundle_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        (scripts_dir / "verify_poi.py").write_text(
            self._generate_verify_script(sources),
            encoding="utf-8"
        )
        
        (bundle_dir / "entrypoint.sh").write_text(
            self._generate_entrypoint_sh(),
            encoding="utf-8"
        )
        (bundle_dir / "entrypoint.py").write_text(
            self._generate_entrypoint_py(),
            encoding="utf-8"
        )
        
        observability_dir = bundle_dir / "observability"
        observability_dir.mkdir(exist_ok=True)
        (observability_dir / "line_metrics.json").write_text(
            json.dumps({"sources": sources, "version": version}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        (observability_dir / "line_observe.py").write_text(
            self._generate_observe_script(),
            encoding="utf-8"
        )

    def _extract_name(self, prompt: str) -> Optional[str]:
        if "高德" in prompt:
            return "高德"
        if "百度" in prompt:
            return "百度"
        if "天地图" in prompt:
            return "天地图"
        return None

    def _extract_api_key(self, prompt: str) -> Optional[str]:
        import re
        match = re.search(r"(?:api.*key|key.*api|密钥)[\s:：]*([a-zA-Z0-9_-]+)", prompt, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_provider(self, prompt: str) -> str:
        if "高德" in prompt:
            return "amap"
        if "百度" in prompt:
            return "baidu"
        if "天地图" in prompt:
            return "tianditu"
        return "unknown"

    def _generate_readme(self, name: str, version: str, sources: List[str]) -> str:
        return f"""# {name} {version}

沿街商铺 POI 可信度验证工作包。

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
            exec(script_file.read_text(encoding="utf-8"))
    
    print("执行产线观测...")
    observe_script = BUNDLE_DIR / "observability" / "line_observe.py"
    if observe_script.exists():
        exec(observe_script.read_text(encoding="utf-8"))
    
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

    def generate_script(self, description):
        """生成治理脚本"""
        return {
            "status": "pending",
            "description": description,
            "message": "脚本生成功能待实现（需要 OpenCode 集成）"
        }

    def supplement_trust_hub(self, source):
        """补充可信数据 HUB"""
        return {
            "status": "pending",
            "source": source,
            "message": "可信数据 HUB 补充功能待实现"
        }

    def output_skill(self, skill_name, skill_spec):
        """输出 Skill 包"""
        skill_path = Path(f"workpackages/skills/{skill_name}.md")
        skill_content = self._generate_skill_markdown(skill_name)
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(skill_content, encoding="utf-8")
        return {
            "status": "ok",
            "skill_path": str(skill_path),
            "skill_name": skill_name
        }
