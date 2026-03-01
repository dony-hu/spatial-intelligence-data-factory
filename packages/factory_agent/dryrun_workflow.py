from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class WorkpackageDryrunWorkflow:
    def __init__(
        self,
        *,
        bundle_root: Path,
        extract_bundle_name: Callable[[str], Optional[str]],
        execute_entrypoint: Callable[..., Dict[str, Any]],
    ) -> None:
        self._bundle_root = bundle_root
        self._extract_bundle_name = extract_bundle_name
        self._execute_entrypoint = execute_entrypoint

    def run(self, prompt: str) -> Dict[str, Any]:
        bundle_name = self._extract_bundle_name(prompt)
        if not bundle_name:
            return {
                "status": "error",
                "message": "请提供工作包名称，例如：'试运行 poi-trust-verification-v1.0.0'",
            }

        bundle_dir = self._bundle_root / bundle_name
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
        output_items: list[str] = []
        if isinstance(sources, list):
            output_items.extend([str(item) for item in sources])

        try:
            execution = self._execute_entrypoint(
                bundle_dir=bundle_dir,
                bundle_name=bundle_name,
                report_name="dryrun_report.json",
            )
        except Exception as exc:
            return {
                "status": "blocked",
                "action": "dryrun_workpackage",
                "reason": "dryrun_execution_error",
                "requires_user_confirmation": True,
                "bundle_name": bundle_name,
                "bundle_path": str(bundle_dir),
                "error": str(exc),
                "message": f"工作包 {bundle_name} dry run 执行异常，已阻塞，请人工确认方案",
            }

        if not execution["success"]:
            return {
                "status": "blocked",
                "action": "dryrun_workpackage",
                "reason": "dryrun_execution_failed",
                "requires_user_confirmation": True,
                "bundle_name": bundle_name,
                "bundle_path": str(bundle_dir),
                "dryrun": {
                    "status": "failed",
                    "input_summary": {"bundle_name": bundle_name, "records_count": 0},
                    "output_summary": {"sources_checked": output_items, "result_count": 0},
                    "failure_reason": f"entrypoint_return_code={execution['return_code']}",
                    "artifacts": {"observability": execution["metrics_path"], "report": execution["report_path"]},
                },
                "message": f"工作包 {bundle_name} dry run 失败并已阻塞，请人工确认方案",
            }

        return {
            "status": "ok",
            "action": "dryrun_workpackage",
            "bundle_name": bundle_name,
            "bundle_path": str(bundle_dir),
            "dryrun": {
                "status": "success",
                "input_summary": {"bundle_name": bundle_name, "records_count": 0},
                "output_summary": {"sources_checked": output_items, "result_count": len(output_items)},
                "failure_reason": "",
                "artifacts": {"observability": execution["metrics_path"], "report": execution["report_path"]},
            },
            "message": f"工作包 {bundle_name} dry run 成功，可进入发布阶段",
        }
