from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional


@dataclass
class WorkpackagePublishWorkflow:
    bundle_root: Path
    output_root: Path
    extract_bundle_name: Callable[[str], Optional[str]]
    execute_entrypoint: Callable[..., Dict[str, Any]]
    persist_publish: Callable[..., None]
    log_blocked: Callable[[Dict[str, Any]], None]

    def run(self, prompt: str) -> Dict[str, Any]:
        bundle_name = self.extract_bundle_name(prompt)
        if not bundle_name:
            return self._blocked(
                bundle_name="",
                reason="bundle_name_missing",
                message="未识别到工作包名称，发布已阻塞，请人工确认方案",
            )

        bundle_dir = self.bundle_root / bundle_name
        if not bundle_dir.exists():
            return self._blocked(
                bundle_name=bundle_name,
                reason="workpackage_not_found",
                message=f"工作包 {bundle_name} 不存在，发布已阻塞，请人工确认方案",
            )

        config_path = bundle_dir / "workpackage.json"
        if not config_path.exists():
            return self._blocked(
                bundle_name=bundle_name,
                reason="workpackage_config_missing",
                message=f"工作包 {bundle_name} 缺少 workpackage.json，发布已阻塞，请人工确认方案",
            )
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return self._blocked(
                bundle_name=bundle_name,
                reason="workpackage_config_invalid",
                message=f"工作包 {bundle_name} 配置不可解析，发布已阻塞，请人工确认方案",
                error=str(exc),
            )

        for name in ["skills", "observability"]:
            if not (bundle_dir / name).exists():
                return self._blocked(
                    bundle_name=bundle_name,
                    reason=f"{name}_missing",
                    message=f"工作包 {bundle_name} 缺少 {name} 目录，发布已阻塞，请人工确认方案",
                )
        if not (bundle_dir / "entrypoint.sh").exists() and not (bundle_dir / "entrypoint.py").exists():
            return self._blocked(
                bundle_name=bundle_name,
                reason="entrypoint_missing",
                message=f"工作包 {bundle_name} 缺少入口脚本，发布已阻塞，请人工确认方案",
            )

        self.output_root.mkdir(parents=True, exist_ok=True)
        version = str(config.get("version") or "")
        evidence_path = self.output_root / f"{bundle_name}.publish.json"
        evidence = {
            "workpackage_id": bundle_name,
            "version": version,
            "published_at": datetime.utcnow().isoformat() + "Z",
            "status": "published",
            "bundle_path": str(bundle_dir),
        }
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            execution = self.execute_entrypoint(
                bundle_dir=bundle_dir,
                bundle_name=bundle_name,
                report_name="publish_execution_report.json",
            )
        except Exception as exc:
            return self._blocked(
                bundle_name=bundle_name,
                reason="runtime_execution_error",
                message=f"工作包 {bundle_name} 发布后执行异常，发布已阻塞，请人工确认方案",
                error=str(exc),
            )
        if not execution["success"]:
            try:
                self.persist_publish(
                    workpackage_id=bundle_name,
                    version=version,
                    status="blocked",
                    evidence_ref=str(evidence_path),
                    bundle_path=str(bundle_dir),
                )
            except Exception:
                pass
            return self._blocked(
                bundle_name=bundle_name,
                reason="runtime_execution_failed",
                message=f"工作包 {bundle_name} 发布后执行失败，发布已阻塞，请人工确认方案",
                error=f"entrypoint_return_code={execution['return_code']}",
            )

        try:
            self.persist_publish(
                workpackage_id=bundle_name,
                version=version,
                status="published",
                evidence_ref=str(evidence_path),
                bundle_path=str(bundle_dir),
            )
        except Exception as exc:
            return self._blocked(
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
                "execution": {
                    "status": "success",
                    "return_code": int(execution["return_code"]),
                    "report": execution["report_path"],
                },
            },
            "message": f"工作包 {bundle_name} 已发布到 Runtime",
        }

    def _blocked(self, *, bundle_name: str, reason: str, message: str, error: str = "") -> Dict[str, Any]:
        payload = {
            "workpackage_id": bundle_name,
            "reason": reason,
            "confirmation_user": "pending_owner",
            "confirmation_decision": "pending",
            "confirmation_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.log_blocked(payload)
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
