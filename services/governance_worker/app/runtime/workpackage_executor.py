from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WorkpackageExecutionResult:
    records: list[dict[str, Any]]
    runtime_result: dict[str, Any]
    bundle_dir: str
    report_path: str


class WorkpackageExecutor:
    """Worker-side executor: only executes workpackage bundle entrypoint."""

    def __init__(self, *, bundle_root: Path | None = None) -> None:
        self._bundle_root = bundle_root or Path("workpackages/bundles")

    def execute(
        self,
        *,
        workpackage_id: str,
        version: str,
        task_context: dict[str, Any],
        ruleset: dict[str, Any],
    ) -> WorkpackageExecutionResult:
        wid = str(workpackage_id or "").strip()
        ver = str(version or "").strip()
        if not wid or not ver:
            raise RuntimeError("blocked: workpackage_id/version is required for worker execution")

        bundle_dir = self._resolve_bundle_dir(wid, ver)
        if not bundle_dir.exists():
            raise RuntimeError(f"blocked: workpackage bundle not found: {wid}@{ver}")

        workpackage_config_path = bundle_dir / "workpackage.json"
        if not workpackage_config_path.exists():
            raise RuntimeError(f"blocked: workpackage.json missing: {wid}@{ver}")

        observability_dir = bundle_dir / "observability"
        observability_dir.mkdir(parents=True, exist_ok=True)
        report_path = observability_dir / "runtime_execution_report.json"
        output_dir = bundle_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        if (bundle_dir / "entrypoint.sh").exists():
            cmd = ["bash", "entrypoint.sh"]
        elif (bundle_dir / "entrypoint.py").exists():
            cmd = ["python3", "entrypoint.py"]
        else:
            raise RuntimeError(f"blocked: entrypoint missing: {wid}@{ver}")

        env = {
            **dict(os.environ),
            "WORKPACKAGE_TASK_CONTEXT_JSON": json.dumps(task_context, ensure_ascii=False),
            "WORKPACKAGE_RULESET_JSON": json.dumps(ruleset, ensure_ascii=False),
            "WORKPACKAGE_ID": wid,
            "WORKPACKAGE_VERSION": ver,
        }

        proc = subprocess.run(
            cmd,
            cwd=str(bundle_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        report_payload = {
            "workpackage_id": wid,
            "version": ver,
            "command": cmd,
            "return_code": int(proc.returncode),
            "stdout": str(proc.stdout or ""),
            "stderr": str(proc.stderr or ""),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if int(proc.returncode) != 0:
            raise RuntimeError(f"blocked: workpackage execution failed rc={int(proc.returncode)}")

        runtime_output_path = output_dir / "runtime_output.json"
        if not runtime_output_path.exists():
            raise RuntimeError("blocked: workpackage output/runtime_output.json not found")
        try:
            runtime_output = json.loads(runtime_output_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"blocked: runtime_output.json invalid: {exc}") from exc

        records = self._extract_canonical_records(runtime_output)
        if not records:
            raise RuntimeError("blocked: runtime_output.json has no executable records")

        runtime_result = {
            "strategy": "workpackage_entrypoint",
            "confidence": self._average_confidence(records),
            "evidence": {
                "items": [
                    {
                        "runtime": "workpackage",
                        "message": "workpackage_entrypoint_success",
                        "workpackage_id": wid,
                        "version": ver,
                        "report_path": str(report_path),
                    }
                ]
            },
        }

        return WorkpackageExecutionResult(
            records=records,
            runtime_result=runtime_result,
            bundle_dir=str(bundle_dir),
            report_path=str(report_path),
        )

    def _resolve_bundle_dir(self, workpackage_id: str, version: str) -> Path:
        candidates = [
            self._bundle_root / f"{workpackage_id}-{version}",
            self._bundle_root / workpackage_id,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _extract_canonical_records(self, runtime_output: dict[str, Any]) -> list[dict[str, Any]]:
        rows = runtime_output.get("records") if isinstance(runtime_output.get("records"), list) else []
        out: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            input_obj = row.get("input") if isinstance(row.get("input"), dict) else {}
            normalization = row.get("normalization") if isinstance(row.get("normalization"), dict) else {}
            validation = row.get("address_validation") if isinstance(row.get("address_validation"), dict) else {}
            raw_id = str(input_obj.get("raw_id") or "").strip()
            if not raw_id:
                continue
            canon_text = str(
                normalization.get("normalized_address")
                or normalization.get("standard_address")
                or input_obj.get("raw_text")
                or ""
            ).strip()
            score = validation.get("score")
            conf = normalization.get("confidence")
            try:
                confidence = float(score if score is not None else (conf if conf is not None else 0.5))
            except Exception:
                confidence = 0.5
            decision = str(row.get("record_decision") or "").upper()
            strategy = "match_dict" if decision == "ACCEPTED" else "human_required"
            out.append(
                {
                    "raw_id": raw_id,
                    "canon_text": canon_text,
                    "confidence": max(0.0, min(1.0, confidence)),
                    "strategy": strategy,
                    "evidence": {
                        "items": [
                            {
                                "step": "workpackage_record",
                                "decision": decision or "UNKNOWN",
                            }
                        ]
                    },
                }
            )
        return out

    def _average_confidence(self, records: list[dict[str, Any]]) -> float:
        if not records:
            return 0.0
        total = 0.0
        for row in records:
            try:
                total += float(row.get("confidence") or 0.0)
            except Exception:
                total += 0.0
        return max(0.0, min(1.0, total / float(len(records))))
