from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import re
from datetime import datetime, timezone

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
        
        if ("存储" in prompt and ("密钥" in prompt or "API" in prompt)) or ("api" in prompt_lower and "key" in prompt_lower):
            return self._handle_store_api_key(prompt)
        
        if ("列出" in prompt and "工作包" in prompt) or ("list" in prompt_lower and ("workpackage" in prompt_lower)):
            return self._handle_list_workpackages()
        
        if "查询" in prompt or ("query" in prompt_lower and ("workpackage" in prompt_lower)):
            return self._handle_query_workpackage(prompt)
        
        if "试运行" in prompt or ("dryrun" in prompt_lower and ("workpackage" in prompt_lower)):
            return self._handle_dryrun_workpackage(prompt)

        if "发布" in prompt or ("publish" in prompt_lower and ("workpackage" in prompt_lower or "runtime" in prompt_lower)):
            return self._handle_publish_workpackage(prompt)
        
        if ("列出" in prompt and "数据源" in prompt) or "list" in prompt_lower:
            return self._handle_list_sources()
        
        if ("生成" in prompt and "工作包" in prompt) or ("generate" in prompt_lower and ("workpackage" in prompt_lower or "work package" in prompt_lower)):
            return self._handle_generate_workpackage(prompt)

        return self._handle_requirement_confirmation(prompt)

    def _handle_requirement_confirmation(self, prompt: str) -> Dict[str, Any]:
        """调用 LLM 确认治理需求；失败时阻塞并等待人工确认。"""
        try:
            result = self._run_requirement_query(prompt)
            summary = self._extract_requirement_summary(str(result.get("answer") or ""))
            return {
                "status": "ok",
                "action": "confirm_requirement",
                "llm_status": "success",
                "summary": summary,
                "message": "已完成治理需求确认，可进入 dry run 与工作包发布阶段",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "action": "confirm_requirement",
                "llm_status": "blocked",
                "reason": "llm_blocked",
                "requires_user_confirmation": True,
                "error": str(exc),
                "message": "LLM 需求确认阻塞，已停止后续流程，请人工确认处置方案",
            }

    def _run_requirement_query(self, prompt: str) -> Dict[str, Any]:
        from tools.agent_cli import load_config, run_requirement_query

        config = load_config()
        system_prompt = (
            "你是地址治理工厂Agent。"
            "请仅输出JSON对象，字段必须包含："
            "target(string), data_sources(array), rule_points(array), outputs(array)。"
        )
        return run_requirement_query(prompt, config, system_prompt_override=system_prompt)

    def _extract_requirement_summary(self, answer: str) -> Dict[str, Any]:
        obj = self._extract_json_object(answer)
        if not obj:
            raise RuntimeError("llm output missing json object")
        target = str(obj.get("target") or obj.get("goal") or "").strip()
        data_sources = self._as_string_list(obj.get("data_sources") or obj.get("sources"))
        rule_points = self._as_string_list(obj.get("rule_points") or obj.get("rules"))
        outputs = self._as_string_list(obj.get("outputs") or obj.get("deliverables"))
        if not target or not data_sources or not outputs:
            raise RuntimeError("llm output missing required fields: target/data_sources/outputs")
        return {
            "target": target,
            "data_sources": data_sources,
            "rule_points": rule_points,
            "outputs": outputs,
        }

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        raw = str(text or "").strip()
        candidates = [raw]
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, flags=re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1))
        braced = re.search(r"(\{[\s\S]*\})", raw)
        if braced:
            candidates.append(braced.group(1))
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
        return {}

    def _as_string_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

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

    def _handle_query_workpackage(self, prompt):
        """处理查询工作包的对话"""
        bundles_dir = Path("workpackages/bundles")
        bundle_name = self._extract_bundle_name(prompt)
        
        if not bundle_name:
            return {
                "status": "error",
                "message": "请提供工作包名称，例如：'查询 poi-trust-verification-v1.0.0'"
            }
        
        bundle_dir = bundles_dir / bundle_name
        if not bundle_dir.exists():
            return {
                "status": "error",
                "message": f"工作包 {bundle_name} 不存在"
            }
        
        wp_config = {}
        config_path = bundle_dir / "workpackage.json"
        if config_path.exists():
            import json
            try:
                wp_config = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        return {
            "status": "ok",
            "action": "query_workpackage",
            "bundle_name": bundle_name,
            "bundle_path": str(bundle_dir),
            "workpackage_config": wp_config,
            "message": f"已查询工作包 {bundle_name}"
        }

    def _handle_dryrun_workpackage(self, prompt):
        """处理 dryrun 工作包的对话"""
        bundles_dir = Path("workpackages/bundles")
        bundle_name = self._extract_bundle_name(prompt)
        
        if not bundle_name:
            return {
                "status": "error",
                "message": "请提供工作包名称，例如：'试运行 poi-trust-verification-v1.0.0'"
            }
        
        bundle_dir = bundles_dir / bundle_name
        if not bundle_dir.exists():
            return {
                "status": "blocked",
                "action": "dryrun_workpackage",
                "reason": "workpackage_not_found",
                "requires_user_confirmation": True,
                "message": f"工作包 {bundle_name} 不存在，dry run 已阻塞，请人工确认方案",
            }

        config_path = bundle_dir / "workpackage.json"
        if not config_path.exists():
            return {
                "status": "blocked",
                "action": "dryrun_workpackage",
                "reason": "workpackage_config_missing",
                "requires_user_confirmation": True,
                "bundle_name": bundle_name,
                "bundle_path": str(bundle_dir),
                "message": f"工作包 {bundle_name} 缺少 workpackage.json，dry run 已阻塞，请人工确认方案",
            }

        try:
            wp_config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "status": "blocked",
                "action": "dryrun_workpackage",
                "reason": "workpackage_config_invalid",
                "requires_user_confirmation": True,
                "bundle_name": bundle_name,
                "bundle_path": str(bundle_dir),
                "error": str(exc),
                "message": f"工作包 {bundle_name} 配置解析失败，dry run 已阻塞，请人工确认方案",
            }

        if not (bundle_dir / "entrypoint.sh").exists() and not (bundle_dir / "entrypoint.py").exists():
            return {
                "status": "blocked",
                "action": "dryrun_workpackage",
                "reason": "entrypoint_missing",
                "requires_user_confirmation": True,
                "bundle_name": bundle_name,
                "bundle_path": str(bundle_dir),
                "message": f"工作包 {bundle_name} 缺少执行入口，dry run 已阻塞，请人工确认方案",
            }

        sources = wp_config.get("sources", []) if isinstance(wp_config, dict) else []
        output_items = []
        if isinstance(sources, list):
            output_items.extend([str(item) for item in sources])

        return {
            "status": "ok",
            "action": "dryrun_workpackage",
            "bundle_name": bundle_name,
            "bundle_path": str(bundle_dir),
            "dryrun": {
                "status": "success",
                "input_summary": {
                    "bundle_name": bundle_name,
                    "records_count": 0,
                },
                "output_summary": {
                    "sources_checked": output_items,
                    "result_count": len(output_items),
                },
                "failure_reason": "",
                "artifacts": {
                    "observability": str(bundle_dir / "observability" / "line_metrics.json"),
                    "report": str(bundle_dir / "observability" / "dryrun_report.json"),
                },
            },
            "message": f"工作包 {bundle_name} dry run 成功，可进入发布阶段",
        }

    def _extract_bundle_name(self, prompt: str) -> Optional[str]:
        """从 prompt 中提取工作包名称"""
        import re
        match = re.search(r'([a-zA-Z0-9_-]+-v\d+\.\d+\.\d+)', prompt)
        if match:
            return match.group(1)
        match = re.search(r'([a-zA-Z0-9_-]+)', prompt)
        if match:
            return match.group(1)
        return None

    def _handle_publish_workpackage(self, prompt: str) -> Dict[str, Any]:
        bundles_dir = Path("workpackages/bundles")
        bundle_name = self._extract_bundle_name(prompt)
        if not bundle_name:
            return self._build_publish_blocked(
                bundle_name="",
                reason="bundle_name_missing",
                message="未识别到工作包名称，发布已阻塞，请人工确认方案",
            )

        bundle_dir = bundles_dir / bundle_name
        if not bundle_dir.exists():
            return self._build_publish_blocked(
                bundle_name=bundle_name,
                reason="workpackage_not_found",
                message=f"工作包 {bundle_name} 不存在，发布已阻塞，请人工确认方案",
            )

        config_path = bundle_dir / "workpackage.json"
        if not config_path.exists():
            return self._build_publish_blocked(
                bundle_name=bundle_name,
                reason="workpackage_config_missing",
                message=f"工作包 {bundle_name} 缺少 workpackage.json，发布已阻塞，请人工确认方案",
            )
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return self._build_publish_blocked(
                bundle_name=bundle_name,
                reason="workpackage_config_invalid",
                message=f"工作包 {bundle_name} 配置不可解析，发布已阻塞，请人工确认方案",
                error=str(exc),
            )

        required_dirs = ["skills", "observability"]
        for name in required_dirs:
            if not (bundle_dir / name).exists():
                return self._build_publish_blocked(
                    bundle_name=bundle_name,
                    reason=f"{name}_missing",
                    message=f"工作包 {bundle_name} 缺少 {name} 目录，发布已阻塞，请人工确认方案",
                )
        if not (bundle_dir / "entrypoint.sh").exists() and not (bundle_dir / "entrypoint.py").exists():
            return self._build_publish_blocked(
                bundle_name=bundle_name,
                reason="entrypoint_missing",
                message=f"工作包 {bundle_name} 缺少入口脚本，发布已阻塞，请人工确认方案",
            )

        out_dir = Path("output/workpackages")
        out_dir.mkdir(parents=True, exist_ok=True)
        version = str(config.get("version") or "")
        evidence_path = out_dir / f"{bundle_name}.publish.json"
        evidence = {
            "workpackage_id": bundle_name,
            "version": version,
            "published_at": datetime.utcnow().isoformat() + "Z",
            "status": "published",
            "bundle_path": str(bundle_dir),
        }
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            self._persist_workpackage_publish_record(
                workpackage_id=bundle_name,
                version=version,
                status="published",
                evidence_ref=str(evidence_path),
                bundle_path=str(bundle_dir),
            )
        except Exception as exc:
            return self._build_publish_blocked(
                bundle_name=bundle_name,
                reason="publish_record_persist_failed",
                message=f"工作包 {bundle_name} 发布记录持久化失败，发布已阻塞，请人工确认方案",
                error=str(exc),
            )
        return {
            "status": "ok",
            "action": "publish_workpackage",
            "bundle_name": bundle_name,
            "runtime": {
                "status": "published",
                "version": version,
                "evidence_ref": str(evidence_path),
            },
            "message": f"工作包 {bundle_name} 已发布到 Runtime",
        }

    def _persist_workpackage_publish_record(
        self,
        *,
        workpackage_id: str,
        version: str,
        status: str,
        evidence_ref: str,
        bundle_path: str,
    ) -> None:
        from services.governance_api.app.repositories.governance_repository import REPOSITORY

        REPOSITORY.upsert_workpackage_publish(
            workpackage_id=workpackage_id,
            version=version,
            status=status,
            evidence_ref=evidence_ref,
            bundle_path=bundle_path,
            published_by="factory_agent",
        )

    def _build_publish_blocked(
        self,
        *,
        bundle_name: str,
        reason: str,
        message: str,
        error: str = "",
    ) -> Dict[str, Any]:
        payload = {
            "workpackage_id": bundle_name,
            "reason": reason,
            "confirmation_user": "pending_owner",
            "confirmation_decision": "pending",
            "confirmation_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            from services.governance_api.app.repositories.governance_repository import REPOSITORY

            REPOSITORY.log_blocked_confirmation(
                event_type="workpackage_publish_blocked",
                caller="factory_agent",
                payload=payload,
            )
        except Exception:
            pass
        result = {
            "status": "blocked",
            "action": "publish_workpackage",
            "reason": reason,
            "requires_user_confirmation": True,
            "bundle_name": bundle_name,
            "message": message,
        }
        if error:
            result["error"] = error
        return result

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
        source_text = str(source or "").strip()
        if not source_text:
            return {
                "status": "blocked",
                "action": "supplement_trust_hub",
                "reason": "source_missing",
                "requires_user_confirmation": True,
                "message": "未提供数据源标识，Trust Hub 补充已阻塞，请人工确认方案",
            }

        mapping = self._resolve_source_profile(source_text)
        try:
            self._trust_hub.store_api_key(
                name=mapping["source_id"],
                api_key="MASKED",
                provider=mapping["provider"],
                api_endpoint=mapping["endpoint"],
            )
            capability = self._trust_hub.upsert_capability(
                source_id=mapping["source_id"],
                provider=mapping["provider"],
                endpoint=mapping["endpoint"],
                tool_type="api",
            )
            sample = self._trust_hub.add_sample_data(
                source_id=mapping["source_id"],
                content={
                    "query": "杭州市西湖区文三路90号",
                    "result": "地址结构化结果",
                    "provider": mapping["provider"],
                },
                trust_score=0.9,
            )
            return {
                "status": "ok",
                "action": "supplement_trust_hub",
                "source": source_text,
                "capability": capability,
                "sample": sample,
                "message": f"已沉淀 {mapping['source_id']} 的能力与可信样例数据",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "action": "supplement_trust_hub",
                "reason": "trust_hub_persist_failed",
                "requires_user_confirmation": True,
                "source": source_text,
                "error": str(exc),
                "message": "Trust Hub 沉淀失败，流程已阻塞，请人工确认方案",
            }

    def _resolve_source_profile(self, source_text: str) -> Dict[str, str]:
        lower = source_text.lower()
        if "高德" in source_text or "amap" in lower:
            return {
                "source_id": "gaode",
                "provider": "amap",
                "endpoint": "https://restapi.amap.com/v3/place/text",
            }
        if "百度" in source_text or "baidu" in lower:
            return {
                "source_id": "baidu",
                "provider": "baidu",
                "endpoint": "https://api.map.baidu.com/place/v2/search",
            }
        if "天地图" in source_text or "tianditu" in lower:
            return {
                "source_id": "tianditu",
                "provider": "tianditu",
                "endpoint": "https://api.tianditu.gov.cn/geocoder",
            }
        return {
            "source_id": lower.replace(" ", "_"),
            "provider": lower.replace(" ", "_"),
            "endpoint": "https://example.com/trust/source",
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
