from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4
import os

from services.governance_api.app.repositories.governance_repository import GovernanceGateError, REPOSITORY
from services.governance_worker.app.core.queue import enqueue_task
from services.governance_worker.app.jobs.review_reconcile_job import run as run_review_reconcile


class GovernanceService:
    """Application service layer for governance API flows."""

    def __init__(self) -> None:
        self._repo = REPOSITORY

    def __getattr__(self, name: str):
        # Pass-through for read-only/simple repository operations.
        return getattr(self._repo, name)

    def submit_task(self, batch_name: str, ruleset_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        task_id = f"task_{uuid4().hex[:12]}"
        trace_id = f"trace_{uuid4().hex[:12]}"
        task_payload = {
            "task_id": task_id,
            "trace_id": trace_id,
            "batch_name": batch_name,
            "ruleset_id": ruleset_id,
            "records": records,
        }

        self._repo.create_task(
            task_id=task_id,
            batch_name=batch_name,
            ruleset_id=ruleset_id,
            status="PENDING",
            queue_backend="pending",
            queue_message="created",
            trace_id=trace_id,
        )
        self._repo.record_observation_event(
            source_service="governance_api",
            event_type="task_submitted",
            status="success",
            trace_id=trace_id,
            task_id=task_id,
            ruleset_id=ruleset_id,
            payload={"batch_name": batch_name, "record_count": len(records)},
        )

        enqueue_result = enqueue_task(task_payload)
        self._repo.record_observation_event(
            source_service="governance_api",
            event_type="task_enqueued" if enqueue_result.queued else "task_enqueue_failed",
            status="success" if enqueue_result.queued else "error",
            severity="info" if enqueue_result.queued else "error",
            trace_id=trace_id,
            task_id=task_id,
            ruleset_id=ruleset_id,
            payload={"backend": enqueue_result.backend, "message": enqueue_result.message},
        )

        if not enqueue_result.queued:
            self._repo.set_task_status(task_id, "BLOCKED")

        task = self._repo.get_task(task_id)
        if task:
            task["queue_backend"] = enqueue_result.backend
            task["queue_message"] = enqueue_result.message
        status = (task or {}).get("status", "BLOCKED")
        return {"task_id": task_id, "trace_id": trace_id, "status": status}

    def submit_review_decision(self, task_id: str, review_data: dict[str, Any]) -> dict[str, Any]:
        self._repo.upsert_review(task_id, review_data)
        reconcile_result = run_review_reconcile({"task_id": task_id, "review_data": review_data})
        return {
            "updated_count": int(reconcile_result.get("updated_count", 0)),
            "target_raw_id": reconcile_result.get("target_raw_id"),
        }

    def submit_runtime_uploaded_batch(
        self,
        *,
        batch_name: str,
        ruleset_id: str,
        addresses: list[str],
        actor: str = "",
    ) -> dict[str, Any]:
        normalized: list[str] = []
        for item in addresses:
            text = str(item or "").strip()
            if text:
                normalized.append(text)
        if not normalized:
            raise ValueError("addresses is required")
        if len(normalized) > 2000:
            raise ValueError("addresses exceeds limit(2000)")

        records = [
            {
                "raw_id": f"raw_upload_{uuid4().hex[:16]}_{idx:04d}",
                "raw_text": text,
            }
            for idx, text in enumerate(normalized)
        ]

        original_mode = os.getenv("GOVERNANCE_QUEUE_MODE")
        os.environ["GOVERNANCE_QUEUE_MODE"] = "sync"
        try:
            submitted = self.submit_task(
                batch_name=str(batch_name or "runtime-upload-batch"),
                ruleset_id=str(ruleset_id or "default"),
                records=records,
            )
        finally:
            if original_mode is None:
                os.environ.pop("GOVERNANCE_QUEUE_MODE", None)
            else:
                os.environ["GOVERNANCE_QUEUE_MODE"] = original_mode

        task_id = str(submitted.get("task_id") or "")
        self._repo.log_audit_event(
            event_type="runtime_upload_batch_submitted",
            caller=str(actor or "runtime_upload"),
            payload={
                "task_id": task_id,
                "batch_name": str(batch_name or "runtime-upload-batch"),
                "ruleset_id": str(ruleset_id or "default"),
                "record_count": len(records),
            },
        )
        latest_task = self._repo.get_task(task_id) if task_id else None
        return {
            "task_id": task_id,
            "trace_id": str(submitted.get("trace_id") or ""),
            "status": str((latest_task or {}).get("status") or submitted.get("status") or ""),
            "record_count": len(records),
        }

    def ack_observation_alert(self, *, alert_id: str, actor: str) -> dict[str, Any] | None:
        acked = self._repo.ack_observation_alert(alert_id, actor)
        if not acked:
            return None
        self._repo.log_audit_event(
            event_type="observation_alert_acked",
            caller=str(actor or "unknown"),
            payload={
                "alert_id": str(alert_id or ""),
                "severity": str(acked.get("severity") or ""),
                "alert_rule": str(acked.get("alert_rule") or ""),
                "status": str(acked.get("status") or ""),
            },
        )
        return acked

    def _parse_window_hours(self, window: str) -> int:
        raw = str(window or "24h").strip().lower()
        if raw.endswith("h"):
            return max(1, int(float(raw[:-1] or 24)))
        if raw.endswith("d"):
            return max(1, int(float(raw[:-1] or 1) * 24))
        return 24

    def _task_in_window(self, task: dict[str, Any], *, recent_hours: int) -> bool:
        created = task.get("created_at")
        if isinstance(created, datetime):
            ts = created.astimezone(timezone.utc).timestamp()
        else:
            try:
                text = str(created or "").replace("Z", "+00:00")
                parsed = datetime.fromisoformat(text)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                ts = parsed.timestamp()
            except Exception:
                return False
        cutoff = datetime.now(timezone.utc).timestamp() - float(recent_hours) * 3600.0
        return ts >= cutoff

    def _parse_iso_ts(self, value: str) -> float:
        text = str(value or "").strip()
        if not text:
            return 0.0
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except Exception:
            return 0.0

    def _created_in_window(self, created_at: str, *, recent_hours: int) -> bool:
        ts = self._parse_iso_ts(created_at)
        if ts <= 0:
            return False
        cutoff = datetime.now(timezone.utc).timestamp() - float(recent_hours) * 3600.0
        return ts >= cutoff

    def _percentile(self, values: list[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(float(v or 0.0) for v in values)
        idx = int(round((len(sorted_values) - 1) * float(p)))
        idx = max(0, min(idx, len(sorted_values) - 1))
        return float(sorted_values[idx])

    def runtime_summary(self, *, window: str = "24h", ruleset_id: str = "") -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        tasks = self._repo.list_tasks(limit=5000)
        selected: list[dict[str, Any]] = []
        for item in tasks:
            if not self._task_in_window(item, recent_hours=recent_hours):
                continue
            if ruleset_id and str(item.get("ruleset_id") or "") != str(ruleset_id):
                continue
            selected.append(item)

        total = len(selected)
        status_counts: dict[str, int] = {}
        confidence_values: list[float] = []
        latest_ts = ""
        reviewed_tasks = 0
        pending_review_tasks = 0

        for task in selected:
            task_id = str(task.get("task_id") or "")
            status = str(task.get("status") or "UNKNOWN").upper()
            status_counts[status] = status_counts.get(status, 0) + 1
            latest_ts = max(latest_ts, str(task.get("created_at") or ""))

            review = self._repo.get_review(task_id) if task_id else None
            if review:
                reviewed_tasks += 1

            results = self._repo.get_results(task_id) if task_id else []
            if results and not review:
                pending_review_tasks += 1
            for result in results:
                try:
                    confidence_values.append(float(result.get("confidence", 0.0)))
                except Exception:
                    confidence_values.append(0.0)

        avg_confidence = (sum(confidence_values) / float(len(confidence_values))) if confidence_values else 0.0
        return {
            "total_tasks": total,
            "status_counts": status_counts,
            "avg_confidence": round(avg_confidence, 6),
            "pending_review_tasks": pending_review_tasks,
            "reviewed_tasks": reviewed_tasks,
            "latest_task_at": latest_ts,
        }

    def runtime_risk_distribution(self, *, window: str = "24h") -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        tasks = self._repo.list_tasks(limit=5000)

        confidence_buckets = {
            "ge_085": 0,
            "between_060_085": 0,
            "lt_060": 0,
        }
        blocked_reason_count: dict[str, int] = {}
        low_confidence_pattern_count: dict[str, int] = {}

        for task in tasks:
            if not self._task_in_window(task, recent_hours=recent_hours):
                continue
            status = str(task.get("status") or "").upper()
            if status == "BLOCKED":
                reason = str(task.get("queue_message") or "unknown")
                blocked_reason_count[reason] = blocked_reason_count.get(reason, 0) + 1

            task_id = str(task.get("task_id") or "")
            for result in self._repo.get_results(task_id):
                confidence = float(result.get("confidence", 0.0))
                if confidence >= 0.85:
                    confidence_buckets["ge_085"] += 1
                elif confidence >= 0.60:
                    confidence_buckets["between_060_085"] += 1
                else:
                    confidence_buckets["lt_060"] += 1
                    strategy = str(result.get("strategy") or "unknown")
                    low_confidence_pattern_count[strategy] = low_confidence_pattern_count.get(strategy, 0) + 1

        blocked_reason_top = [
            {"reason": k, "count": v}
            for k, v in sorted(blocked_reason_count.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ]
        low_confidence_pattern_top = [
            {"pattern": k, "count": v}
            for k, v in sorted(low_confidence_pattern_count.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ]
        return {
            "confidence_buckets": confidence_buckets,
            "blocked_reason_top": blocked_reason_top,
            "low_confidence_pattern_top": low_confidence_pattern_top,
        }

    def runtime_version_compare(self, *, baseline: str, candidate: str) -> dict[str, Any]:
        # MVP implementation: no strict ID coupling yet, return neutral delta if no comparable tasks.
        _ = baseline
        _ = candidate
        return {
            "success_rate_delta": 0.0,
            "blocked_rate_delta": 0.0,
            "avg_confidence_delta": 0.0,
        }

    def runtime_tasks(
        self,
        *,
        window: str = "24h",
        status: str = "",
        ruleset_id: str = "",
        limit: int = 50,
        page: int = 1,
    ) -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        safe_limit = max(1, min(int(limit), 200))
        safe_page = max(1, int(page))
        status_filter = str(status or "").upper().strip()
        ruleset_filter = str(ruleset_id or "").strip()

        tasks = self._repo.list_tasks(limit=5000)
        selected: list[dict[str, Any]] = []
        for task in tasks:
            if not self._task_in_window(task, recent_hours=recent_hours):
                continue
            if status_filter and str(task.get("status") or "").upper() != status_filter:
                continue
            if ruleset_filter and str(task.get("ruleset_id") or "") != ruleset_filter:
                continue
            selected.append(task)

        selected.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        total = len(selected)
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
        rows = selected[start:end]

        items: list[dict[str, Any]] = []
        for task in rows:
            task_id = str(task.get("task_id") or "")
            results = self._repo.get_results(task_id) if task_id else []
            source_records = self._repo.list_raw_records_by_task(task_id) if task_id else []
            review = self._repo.get_review(task_id) if task_id else None
            first = results[0] if results else {}
            avg_confidence = 0.0
            if results:
                avg_confidence = sum(float(item.get("confidence", 0.0) or 0.0) for item in results) / float(len(results))
            items.append(
                {
                    "task_id": task_id,
                    "status": str(task.get("status") or ""),
                    "ruleset_id": str(task.get("ruleset_id") or "default"),
                    "confidence": float(avg_confidence),
                    "strategy": str(first.get("strategy") or ""),
                    "review_status": str((review or {}).get("review_status") or ""),
                    "updated_at": str(task.get("created_at") or ""),
                    "batch_size": len(source_records),
                }
            )
        return {"page": safe_page, "limit": safe_limit, "total": total, "items": items}

    def runtime_task_detail(self, *, task_id: str) -> dict[str, Any] | None:
        target_id = str(task_id or "").strip()
        if not target_id:
            return None
        task = self._repo.get_task(target_id)
        if not task:
            return None

        results = self._repo.get_results(target_id)
        review = self._repo.get_review(target_id) or {}
        trace_id = str(task.get("trace_id") or "")

        obs_logs = self._repo.list_observation_events(task_id=target_id, limit=200)
        audit_logs_all = self._repo.list_audit_events()
        audit_logs = []
        for evt in audit_logs_all:
            payload = evt.get("payload") if isinstance(evt.get("payload"), dict) else {}
            if str(payload.get("task_id") or "") == target_id or str(payload.get("task_run_id") or "") == target_id:
                audit_logs.append(evt)

        source_records = self._repo.list_raw_records_by_task(target_id)

        governance_results = []
        for item in results:
            governance_results.append(
                {
                    "raw_id": str(item.get("raw_id") or ""),
                    "canon_text": str(item.get("canon_text") or ""),
                    "confidence": float(item.get("confidence", 0.0) or 0.0),
                    "strategy": str(item.get("strategy") or ""),
                    "evidence": item.get("evidence") if isinstance(item.get("evidence"), dict) else {},
                }
            )

        return {
            "task": task,
            "trace_id": trace_id,
            "source_data": source_records,
            "governance_results": governance_results,
            "review": review,
            "process_logs": {
                "observation_events": obs_logs,
                "audit_events": audit_logs,
            },
        }

    def runtime_workpackage_pipeline(self, *, window: str = "24h", client_type: str = "") -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        client_filter = str(client_type or "").strip()
        stage_order = ["created", "llm_confirmed", "packaged", "submitted", "accepted", "running", "finished"]
        stage_rank = {stage: idx for idx, stage in enumerate(stage_order)}

        all_events = self._repo.list_observation_events(limit=10000)
        groups: dict[str, dict[str, Any]] = {}
        for evt in all_events:
            created_at = str(evt.get("created_at") or "")
            if not self._created_in_window(created_at, recent_hours=recent_hours):
                continue
            workpackage_id = str(evt.get("workpackage_id") or "").strip()
            if not workpackage_id:
                continue
            payload = evt.get("payload_json") if isinstance(evt.get("payload_json"), dict) else {}
            version = str(payload.get("version") or "")
            event_client_type = str(payload.get("client_type") or "")
            if client_filter and event_client_type != client_filter:
                continue
            pipeline_stage = str(payload.get("pipeline_stage") or "").strip()
            if pipeline_stage not in stage_order:
                continue
            key = f"{workpackage_id}::{version}"
            item = groups.setdefault(
                key,
                {
                    "workpackage_id": workpackage_id,
                    "version": version,
                    "client_type": event_client_type,
                    "stage_ts": {},
                    "stages": set(),
                    "latest_event_at": created_at,
                    "runtime_receipt_id": "",
                    "checksum": "",
                    "skills_count": 0,
                    "artifact_count": 0,
                    "submit_status": "",
                    "submit_status_rank": -1,
                },
            )
            ts = self._parse_iso_ts(created_at)
            item["stages"].add(pipeline_stage)
            if str(created_at) > str(item.get("latest_event_at") or ""):
                item["latest_event_at"] = created_at
            existing_ts = float((item.get("stage_ts") or {}).get(pipeline_stage) or 0.0)
            if existing_ts <= 0 or (ts > 0 and ts < existing_ts):
                item["stage_ts"][pipeline_stage] = ts
            if event_client_type and not item.get("client_type"):
                item["client_type"] = event_client_type
            receipt_id = str(payload.get("runtime_receipt_id") or "")
            if receipt_id:
                item["runtime_receipt_id"] = receipt_id
            checksum = str(payload.get("checksum") or "")
            if checksum:
                item["checksum"] = checksum
            skills_count = int(payload.get("skills_count") or 0)
            artifact_count = int(payload.get("artifact_count") or 0)
            submit_status = str(payload.get("submit_status") or "")
            if skills_count > 0:
                item["skills_count"] = skills_count
            if artifact_count > 0:
                item["artifact_count"] = artifact_count
            if submit_status:
                rank = int(stage_rank.get(pipeline_stage, -1))
                if rank >= int(item.get("submit_status_rank") or -1):
                    item["submit_status"] = submit_status
                    item["submit_status_rank"] = rank

        total_workpackages = len(groups)
        stage_counts = {stage: 0 for stage in stage_order}
        end_to_end_success = 0
        submitted_count = 0
        accepted_count = 0
        end_to_end_latency: list[float] = []
        cli_interaction_latency: list[float] = []
        agent_planning_latency: list[float] = []
        runtime_submit_latency: list[float] = []

        for item in groups.values():
            stages = item.get("stages") or set()
            stage_ts = item.get("stage_ts") or {}
            for stage in stage_order:
                if stage in stages:
                    stage_counts[stage] += 1
            if "finished" in stages:
                end_to_end_success += 1
            if "submitted" in stages:
                submitted_count += 1
            if "accepted" in stages:
                accepted_count += 1

            created_ts = float(stage_ts.get("created") or 0.0)
            llm_confirmed_ts = float(stage_ts.get("llm_confirmed") or 0.0)
            packaged_ts = float(stage_ts.get("packaged") or 0.0)
            submitted_ts = float(stage_ts.get("submitted") or 0.0)
            accepted_ts = float(stage_ts.get("accepted") or 0.0)
            finished_ts = float(stage_ts.get("finished") or 0.0)

            if created_ts > 0 and llm_confirmed_ts >= created_ts:
                cli_interaction_latency.append((llm_confirmed_ts - created_ts) * 1000.0)
            if llm_confirmed_ts > 0 and packaged_ts >= llm_confirmed_ts:
                agent_planning_latency.append((packaged_ts - llm_confirmed_ts) * 1000.0)
            if submitted_ts > 0 and accepted_ts >= submitted_ts:
                runtime_submit_latency.append((accepted_ts - submitted_ts) * 1000.0)
            if created_ts > 0 and finished_ts >= created_ts:
                end_to_end_latency.append((finished_ts - created_ts) * 1000.0)

        end_to_end_success_rate = float(end_to_end_success) / float(total_workpackages) if total_workpackages else 0.0
        runtime_submit_success_rate = float(accepted_count) / float(submitted_count) if submitted_count else 0.0
        latency_breakdown = {
            "cli_interaction_ms": {
                "p50": round(self._percentile(cli_interaction_latency, 0.50), 3),
                "p90": round(self._percentile(cli_interaction_latency, 0.90), 3),
            },
            "agent_planning_ms": {
                "p50": round(self._percentile(agent_planning_latency, 0.50), 3),
                "p90": round(self._percentile(agent_planning_latency, 0.90), 3),
            },
            "runtime_submit_ms": {
                "p50": round(self._percentile(runtime_submit_latency, 0.50), 3),
                "p90": round(self._percentile(runtime_submit_latency, 0.90), 3),
            },
            "end_to_end_ms": {
                "p50": round(self._percentile(end_to_end_latency, 0.50), 3),
                "p90": round(self._percentile(end_to_end_latency, 0.90), 3),
            },
        }
        items: list[dict[str, Any]] = []
        for item in groups.values():
            item_stages = item.get("stages") or set()
            current_stage = ""
            for stage in reversed(stage_order):
                if stage in item_stages:
                    current_stage = stage
                    break
            items.append(
                {
                    "workpackage_id": str(item.get("workpackage_id") or ""),
                    "version": str(item.get("version") or ""),
                    "client_type": str(item.get("client_type") or ""),
                    "current_stage": current_stage,
                    "stage_count": len(item_stages),
                    "runtime_receipt_id": str(item.get("runtime_receipt_id") or ""),
                    "checksum": str(item.get("checksum") or ""),
                    "skills_count": int(item.get("skills_count") or 0),
                    "artifact_count": int(item.get("artifact_count") or 0),
                    "submit_status": str(item.get("submit_status") or ""),
                    "updated_at": str(item.get("latest_event_at") or ""),
                }
            )
        items.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
        return {
            "total_workpackages": total_workpackages,
            "stage_counts": stage_counts,
            "end_to_end_success_rate": round(end_to_end_success_rate, 6),
            "latency_breakdown_ms_p50_p90": latency_breakdown,
            "runtime_submit_success_rate": round(runtime_submit_success_rate, 6),
            "items": items[:50],
        }

    def runtime_workpackage_events(
        self,
        *,
        workpackage_id: str,
        version: str = "",
        window: str = "24h",
        client_type: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        target_workpackage = str(workpackage_id or "").strip()
        if not target_workpackage:
            raise ValueError("workpackage_id is required")
        target_version = str(version or "").strip()
        target_client = str(client_type or "").strip()
        safe_limit = max(1, min(int(limit), 1000))
        recent_hours = self._parse_window_hours(window)

        events = self._repo.list_observation_events(limit=10000)
        items: list[dict[str, Any]] = []
        for evt in events:
            if str(evt.get("workpackage_id") or "") != target_workpackage:
                continue
            if not self._created_in_window(str(evt.get("created_at") or ""), recent_hours=recent_hours):
                continue
            payload = evt.get("payload_json") if isinstance(evt.get("payload_json"), dict) else {}
            event_version = str(payload.get("version") or "")
            event_client = str(payload.get("client_type") or "")
            if target_version and event_version != target_version:
                continue
            if target_client and event_client != target_client:
                continue
            payload_summary = {
                "pipeline_stage": str(payload.get("pipeline_stage") or ""),
                "client_type": event_client,
                "version": event_version,
                "runtime_receipt_id": str(payload.get("runtime_receipt_id") or ""),
                "model": str(payload.get("model") or ""),
                "message": str(payload.get("message") or ""),
            }
            items.append(
                {
                    "trace_id": str(evt.get("trace_id") or ""),
                    "span_id": str(evt.get("span_id") or ""),
                    "parent_span_id": str(payload.get("parent_span_id") or ""),
                    "source": str(evt.get("source_service") or ""),
                    "event_type": str(evt.get("event_type") or ""),
                    "occurred_at": str(evt.get("created_at") or ""),
                    "status": str(evt.get("status") or ""),
                    "payload_summary": payload_summary,
                }
            )
        items.sort(key=lambda item: str(item.get("occurred_at") or ""))
        sliced = items[:safe_limit]
        return {"total": len(sliced), "items": sliced}

    def runtime_llm_interactions(
        self,
        *,
        window: str = "24h",
        workpackage_id: str = "",
        version: str = "",
        limit: int = 200,
    ) -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        target_workpackage = str(workpackage_id or "").strip()
        target_version = str(version or "").strip()
        safe_limit = max(1, min(int(limit), 1000))

        events = self._repo.list_observation_events(limit=10000)
        selected: list[dict[str, Any]] = []
        for evt in events:
            source = str(evt.get("source_service") or "").lower()
            event_type = str(evt.get("event_type") or "").lower()
            if source != "llm" and "llm" not in event_type:
                continue
            if not self._created_in_window(str(evt.get("created_at") or ""), recent_hours=recent_hours):
                continue
            evt_workpackage_id = str(evt.get("workpackage_id") or "").strip()
            if target_workpackage and evt_workpackage_id != target_workpackage:
                continue
            payload = evt.get("payload_json") if isinstance(evt.get("payload_json"), dict) else {}
            evt_version = str(payload.get("version") or "")
            if target_version and evt_version != target_version:
                continue
            selected.append(dict(evt))

        request_count = len(selected)
        success_count = 0
        failure_count = 0
        latencies: list[float] = []
        token_usage = {"prompt": 0, "completion": 0, "total": 0}
        failure_reasons: dict[str, int] = {}
        model = ""
        base_url = ""
        samples: list[dict[str, Any]] = []

        for evt in selected:
            status = str(evt.get("status") or "").lower()
            payload = evt.get("payload_json") if isinstance(evt.get("payload_json"), dict) else {}
            if status == "success":
                success_count += 1
            else:
                failure_count += 1
            latency_ms = float(payload.get("latency_ms") or 0.0)
            if latency_ms > 0:
                latencies.append(latency_ms)
            usage = payload.get("token_usage") if isinstance(payload.get("token_usage"), dict) else {}
            token_usage["prompt"] += int(usage.get("prompt") or 0)
            token_usage["completion"] += int(usage.get("completion") or 0)
            token_usage["total"] += int(usage.get("total") or 0)
            reason = str(payload.get("failure_reason") or "").strip()
            if reason:
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            if not model:
                model = str(payload.get("model") or "")
            if not base_url:
                base_url = str(payload.get("base_url") or "")
            samples.append(
                {
                    "event_id": str(evt.get("event_id") or ""),
                    "workpackage_id": str(evt.get("workpackage_id") or ""),
                    "version": str(payload.get("version") or ""),
                    "prompt": str(payload.get("prompt") or ""),
                    "response": str(payload.get("response") or ""),
                    "status": str(evt.get("status") or ""),
                    "occurred_at": str(evt.get("created_at") or ""),
                }
            )

        failure_reasons_top = [
            {"reason": key, "count": value}
            for key, value in sorted(failure_reasons.items(), key=lambda item: item[1], reverse=True)[:5]
        ]
        samples.sort(key=lambda item: str(item.get("occurred_at") or ""), reverse=True)
        return {
            "model": model,
            "base_url": base_url,
            "request_count": request_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "latency_ms_p50": round(self._percentile(latencies, 0.50), 3),
            "latency_ms_p90": round(self._percentile(latencies, 0.90), 3),
            "token_usage": token_usage,
            "failure_reasons_top": failure_reasons_top,
            "samples": samples[:safe_limit],
        }

    def runtime_seed_demo_cases(self, *, total: int = 60) -> dict[str, Any]:
        safe_total = max(20, min(int(total), 300))
        now_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        addresses = [
            "上海市徐汇区肇嘉浜路111号",
            "北京市朝阳区建国路88号",
            "广州市天河区体育西路100号",
            "深圳市南山区科技园南区8栋",
            "成都市高新区天府大道北段1700号",
            "杭州市西湖区文三路478号",
            "武汉市洪山区珞喻路1037号",
            "西安市雁塔区高新路52号",
            "南京市鼓楼区中山北路1号",
            "苏州市工业园区星湖街328号",
        ]
        blocked_reasons = ["missing_required_fields", "poi_conflict", "road_ambiguity", "provider_timeout", "district_mismatch"]
        status_targets = {
            "SUCCEEDED": int(round(float(safe_total) * 0.47)),
            "REVIEWED": int(round(float(safe_total) * 0.23)),
            "BLOCKED": int(round(float(safe_total) * 0.17)),
        }
        assigned = sum(status_targets.values())
        status_targets["FAILED"] = max(0, safe_total - assigned)
        while sum(status_targets.values()) < safe_total:
            status_targets["SUCCEEDED"] += 1
        while sum(status_targets.values()) > safe_total and status_targets["SUCCEEDED"] > 0:
            status_targets["SUCCEEDED"] -= 1

        status_mix: list[str] = []
        for key in ("SUCCEEDED", "REVIEWED", "BLOCKED", "FAILED"):
            status_mix.extend([key] * int(status_targets.get(key, 0)))
        summary = {"SUCCEEDED": 0, "REVIEWED": 0, "BLOCKED": 0, "FAILED": 0}
        total_input_records = 0

        for idx, status in enumerate(status_mix):
            task_id = f"task_runtime_demo_{now_tag}_{idx:03d}"
            trace_id = f"trace_runtime_demo_{now_tag}_{idx:03d}"
            queue_message = "seeded_demo"
            if status == "BLOCKED":
                queue_message = blocked_reasons[idx % len(blocked_reasons)]
            elif status == "FAILED":
                queue_message = "execution_failed"

            self._repo.create_task(
                task_id=task_id,
                batch_name="runtime-demo-seed",
                ruleset_id="default",
                status="PENDING",
                queue_backend="sync",
                queue_message=queue_message,
                trace_id=trace_id,
            )

            batch_size = 3 + (idx % 5)
            total_input_records += batch_size
            raw_records = []
            for j in range(batch_size):
                raw_id = f"raw_runtime_demo_{now_tag}_{idx:03d}_{j:02d}"
                addr = addresses[(idx + j) % len(addresses)]
                raw_records.append({"raw_id": raw_id, "raw_text": addr})
            self._repo.save_raw_records(task_id=task_id, raw_records=raw_records)

            if status in {"SUCCEEDED", "REVIEWED"}:
                results = []
                base_confidence = 0.9 - (idx % 4) * 0.08
                strategy = "auto_accept" if base_confidence >= 0.85 else "human_required"
                for j, raw_item in enumerate(raw_records):
                    raw_id = str(raw_item.get("raw_id") or "")
                    addr = str(raw_item.get("raw_text") or "")
                    confidence = max(0.45, base_confidence - j * 0.03)
                    results.append(
                        {
                            "raw_id": raw_id,
                            "canon_text": addr,
                            "confidence": confidence,
                            "strategy": strategy if confidence >= 0.75 else "human_required",
                            "evidence": {"items": [{"kind": "seed_demo", "provider": "internal"}]},
                        }
                    )
                self._repo.save_results(
                    task_id=task_id,
                    results=results,
                    raw_records=raw_records,
                )

            self._repo.set_task_status(task_id, status)
            self._repo.record_observation_event(
                source_service="governance_worker",
                event_type=f"task_{status.lower()}",
                status="success" if status in {"SUCCEEDED", "REVIEWED"} else "error",
                severity="info" if status in {"SUCCEEDED", "REVIEWED"} else "warning",
                trace_id=trace_id,
                task_id=task_id,
                ruleset_id="default",
                payload={
                    "batch_name": "runtime-demo-seed",
                    "queue_message": queue_message,
                    "batch_size": batch_size,
                    "source": "runtime_workflow_seed",
                },
            )
            self._repo.log_audit_event(
                event_type="runtime_seed_task",
                caller="runtime-demo-seeder",
                payload={
                    "task_id": task_id,
                    "status": status,
                    "reason": queue_message,
                    "batch_size": batch_size,
                    "source": "runtime_workflow_seed",
                },
            )
            if status == "REVIEWED":
                review_raw_id = f"raw_runtime_demo_{now_tag}_{idx:03d}_00"
                self._repo.upsert_review(
                    task_id,
                    {
                        "raw_id": review_raw_id,
                        "review_status": "approved",
                        "reviewer": "runtime-demo-reviewer",
                        "comment": "seed review approved",
                    },
                )
            summary[status] = summary.get(status, 0) + 1

        return {
            "total_seeded": len(status_mix),
            "status_counts": summary,
            "batch_name": "runtime-demo-seed",
            "total_input_records": total_input_records,
        }

    def runtime_seed_workpackage_demo_cases(self, *, total: int = 12) -> dict[str, Any]:
        safe_total = max(3, min(int(total), 200))
        now_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        stage_order = [
            ("created", "factory_cli", "workpackage_created"),
            ("llm_confirmed", "factory_agent", "requirements_confirmed"),
            ("packaged", "factory_agent", "workpackage_packaged"),
            ("submitted", "governance_runtime", "runtime_submit_requested"),
            ("accepted", "governance_runtime", "runtime_submit_accepted"),
            ("running", "governance_runtime", "runtime_task_running"),
            ("finished", "governance_runtime", "runtime_task_finished"),
        ]
        stage_counts = {stage: 0 for stage, _, _ in stage_order}
        client_types = ["user", "test_client"]

        for idx in range(safe_total):
            workpackage_id = f"wp_runtime_demo_{now_tag}_{idx:03d}"
            version = f"v1.{idx % 3}.{idx % 7}"
            trace_id = f"trace_wp_{now_tag}_{idx:03d}"
            client_type = client_types[idx % len(client_types)]
            runtime_receipt_id = f"receipt_{now_tag}_{idx:03d}"

            for step, source, event_type in stage_order:
                REPOSITORY.record_observation_event(
                    source_service=source,
                    event_type=event_type,
                    status="success",
                    trace_id=trace_id,
                    span_id=f"span_{idx:03d}_{step}",
                    workpackage_id=workpackage_id,
                    payload={
                        "pipeline_stage": step,
                        "client_type": client_type,
                        "version": version,
                        "runtime_receipt_id": runtime_receipt_id,
                        "latency_ms": 60 + (idx % 5) * 20,
                        "model": "doubao-seed-2-0-pro-260215" if step == "llm_confirmed" else "",
                        "base_url": "https://ark.cn-beijing.volces.com/api/v3" if step == "llm_confirmed" else "",
                        "token_usage": {"prompt": 30 + idx, "completion": 20 + idx, "total": 50 + 2 * idx}
                        if step == "llm_confirmed"
                        else {},
                        "prompt": f"请确认工作包 {workpackage_id} 的治理需求" if step == "llm_confirmed" else "",
                        "response": f"工作包 {workpackage_id} 需求确认完成" if step == "llm_confirmed" else "",
                    },
                )
                stage_counts[step] += 1
            REPOSITORY.log_audit_event(
                event_type="runtime_seed_workpackage_pipeline",
                caller="runtime-workpackage-seeder",
                payload={
                    "workpackage_id": workpackage_id,
                    "version": version,
                    "trace_id": trace_id,
                    "runtime_receipt_id": runtime_receipt_id,
                    "client_type": client_type,
                },
            )

        return {
            "total_seeded": safe_total,
            "stage_counts": stage_counts,
            "window": "24h",
        }

    def runtime_reliability_summary(self, *, window: str = "24h") -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        tasks = [item for item in self._repo.list_tasks(limit=10000) if self._task_in_window(item, recent_hours=recent_hours)]
        total_tasks = len(tasks)
        success_tasks = sum(1 for item in tasks if str(item.get("status") or "").upper() in {"SUCCEEDED", "REVIEWED"})
        availability = float(success_tasks) / float(total_tasks) if total_tasks else 1.0

        duration_values: list[float] = []
        for evt in self._repo.list_observation_events(limit=5000):
            payload = evt.get("payload_json") if isinstance(evt.get("payload_json"), dict) else {}
            if "duration_ms" not in payload:
                continue
            task_id = str(evt.get("task_id") or "")
            if task_id and not any(str(t.get("task_id") or "") == task_id for t in tasks):
                continue
            duration_values.append(float(payload.get("duration_ms") or 0.0))
        duration_values.sort()
        def _percentile(values: list[float], p: float) -> float:
            if not values:
                return 0.0
            idx = int(round((len(values) - 1) * p))
            idx = max(0, min(idx, len(values) - 1))
            return float(values[idx])
        latency_p95 = _percentile(duration_values, 0.95)
        latency_p99 = _percentile(duration_values, 0.99)

        latest_task_at = ""
        for item in tasks:
            latest_task_at = max(latest_task_at, str(item.get("created_at") or ""))
        freshness_minutes = 999999.0
        if latest_task_at:
            try:
                parsed = datetime.fromisoformat(latest_task_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                freshness_minutes = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 60.0
            except Exception:
                freshness_minutes = 999999.0

        confidences: list[float] = []
        for task in tasks:
            for result in self._repo.get_results(str(task.get("task_id") or "")):
                confidences.append(float(result.get("confidence", 0.0) or 0.0))
        correctness = (sum(confidences) / float(len(confidences))) if confidences else 0.0

        sli = {
            "availability": round(availability, 6),
            "latency_p95_ms": round(latency_p95, 3),
            "latency_p99_ms": round(latency_p99, 3),
            "freshness_minutes": round(freshness_minutes, 3),
            "correctness": round(correctness, 6),
        }
        slo = {
            "availability_gte": 0.95,
            "latency_p95_ms_lte": 1500.0,
            "freshness_minutes_lte": 30.0,
            "correctness_gte": 0.85,
        }
        violations = []
        if sli["availability"] < slo["availability_gte"]:
            violations.append({"metric": "availability", "actual": sli["availability"], "target": slo["availability_gte"]})
        if sli["latency_p95_ms"] > slo["latency_p95_ms_lte"]:
            violations.append({"metric": "latency_p95_ms", "actual": sli["latency_p95_ms"], "target": slo["latency_p95_ms_lte"]})
        if sli["freshness_minutes"] > slo["freshness_minutes_lte"]:
            violations.append({"metric": "freshness_minutes", "actual": sli["freshness_minutes"], "target": slo["freshness_minutes_lte"]})
        if sli["correctness"] < slo["correctness_gte"]:
            violations.append({"metric": "correctness", "actual": sli["correctness"], "target": slo["correctness_gte"]})

        error_budget = {
            "availability_remaining": round(max(0.0, sli["availability"] - slo["availability_gte"]), 6),
            "correctness_remaining": round(max(0.0, sli["correctness"] - slo["correctness_gte"]), 6),
        }

        for metric_name, metric_value in sli.items():
            self._repo.upsert_observation_metric(
                metric_name=f"runtime.sli.{metric_name}",
                metric_value=float(metric_value),
                labels={"window": window},
            )

        open_alerts = self._repo.list_observation_alerts(status="open", limit=200)
        return {
            "window": window,
            "sli": sli,
            "slo": slo,
            "error_budget": error_budget,
            "violations": violations,
            "open_alerts": open_alerts,
        }

    def runtime_reliability_evaluate(self, *, window: str = "24h", suppress_minutes: int = 30) -> dict[str, Any]:
        summary = self.runtime_reliability_summary(window=window)
        violations = list(summary.get("violations") or [])
        triggered_alerts: list[dict[str, Any]] = []
        now_ts = datetime.now(timezone.utc).timestamp()
        existing_open = self._repo.list_observation_alerts(status="open", limit=500)

        for item in violations:
            metric = str(item.get("metric") or "unknown")
            rule_name = f"slo_violation_{metric}"
            recent_open = None
            for alert in existing_open:
                if str(alert.get("alert_rule") or "") != rule_name:
                    continue
                created_at = str(alert.get("created_at") or "")
                try:
                    created_ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                except Exception:
                    created_ts = 0.0
                if created_ts >= now_ts - float(suppress_minutes) * 60.0:
                    recent_open = alert
                    break
            if recent_open:
                continue

            actual = float(item.get("actual") or 0.0)
            target = float(item.get("target") or 0.0)
            severity = "P3"
            gap = abs(actual - target)
            if gap >= 0.2:
                severity = "P1"
            elif gap >= 0.1:
                severity = "P2"
            created = self._repo.create_observation_alert(
                alert_rule=rule_name,
                severity=severity,
                trigger_value=actual,
                threshold_value=target,
                owner="runtime-observability",
            )
            self._repo.log_audit_event(
                event_type="observation_alert_triggered",
                caller="runtime_reliability_evaluator",
                payload={
                    "alert_id": str(created.get("alert_id") or ""),
                    "rule": rule_name,
                    "severity": severity,
                    "window": window,
                },
            )
            triggered_alerts.append(created)

        return {
            "window": window,
            "violation_count": len(violations),
            "triggered_count": len(triggered_alerts),
            "triggered_alerts": triggered_alerts,
            "suppress_minutes": int(suppress_minutes),
        }

    def runtime_freshness_latency_summary(
        self,
        *,
        window: str = "24h",
        ruleset_id: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        tasks = []
        for item in self._repo.list_tasks(limit=10000):
            if not self._task_in_window(item, recent_hours=recent_hours):
                continue
            if ruleset_id and str(item.get("ruleset_id") or "") != str(ruleset_id):
                continue
            if status and str(item.get("status") or "").upper() != str(status).upper():
                continue
            tasks.append(item)
        task_ids = {str(item.get("task_id") or "") for item in tasks}

        now_ts = datetime.now(timezone.utc).timestamp()
        latest_event_ts = 0.0
        for evt in self._repo.list_observation_events(limit=5000):
            task_id = str(evt.get("task_id") or "")
            if task_id and task_id not in task_ids:
                continue
            latest_event_ts = max(latest_event_ts, self._parse_iso_ts(str(evt.get("created_at") or "")))

        latest_metric_ts = 0.0
        for metric_name in ("runtime.sli.availability", "runtime.sli.latency_p95_ms", "runtime.sli.freshness_minutes", "runtime.sli.correctness"):
            series = self._repo.query_observation_metric_series(metric_name=metric_name, limit=20)
            for point in series:
                latest_metric_ts = max(latest_metric_ts, self._parse_iso_ts(str(point.get("created_at") or "")))

        latest_task_ts = 0.0
        for task in tasks:
            latest_task_ts = max(latest_task_ts, self._parse_iso_ts(str(task.get("created_at") or "")))

        event_lag_seconds = max(0.0, now_ts - latest_event_ts) if latest_event_ts else 999999.0
        aggregation_lag_seconds = max(0.0, now_ts - latest_metric_ts) if latest_metric_ts else 999999.0
        dashboard_data_age_seconds = max(0.0, now_ts - latest_task_ts) if latest_task_ts else 999999.0

        metrics = {
            "event_lag_seconds": round(event_lag_seconds, 3),
            "aggregation_lag_seconds": round(aggregation_lag_seconds, 3),
            "dashboard_data_age_seconds": round(dashboard_data_age_seconds, 3),
            "latest_task_at": datetime.fromtimestamp(latest_task_ts, tz=timezone.utc).isoformat() if latest_task_ts else "",
        }
        thresholds = {
            "event_lag_seconds_lte": 120.0,
            "aggregation_lag_seconds_lte": 180.0,
            "dashboard_data_age_seconds_lte": 300.0,
        }
        violations = []
        for key in ("event_lag_seconds", "aggregation_lag_seconds", "dashboard_data_age_seconds"):
            limit_key = f"{key}_lte"
            if float(metrics[key]) > float(thresholds[limit_key]):
                violations.append({"metric": key, "actual": metrics[key], "target": thresholds[limit_key]})

        layer_map = {
            "event_lag_seconds": "ingestion",
            "aggregation_lag_seconds": "aggregation",
            "dashboard_data_age_seconds": "query",
        }
        bottleneck_layer = "healthy"
        if violations:
            worst = sorted(violations, key=lambda x: float(x.get("actual", 0.0) - x.get("target", 0.0)), reverse=True)[0]
            bottleneck_layer = layer_map.get(str(worst.get("metric") or ""), "unknown")

        for metric_name, metric_value in metrics.items():
            if metric_name == "latest_task_at":
                continue
            self._repo.upsert_observation_metric(
                metric_name=f"runtime.latency.{metric_name}",
                metric_value=float(metric_value),
                labels={"window": window, "layer": layer_map.get(metric_name, "unknown")},
            )

        return {
            "window": window,
            "filters": {"ruleset_id": ruleset_id, "status": status},
            "metrics": metrics,
            "thresholds": thresholds,
            "violations": violations,
            "bottleneck_layer": bottleneck_layer,
        }

    def runtime_freshness_latency_evaluate(
        self,
        *,
        window: str = "24h",
        ruleset_id: str = "",
        status: str = "",
        suppress_minutes: int = 30,
    ) -> dict[str, Any]:
        summary = self.runtime_freshness_latency_summary(window=window, ruleset_id=ruleset_id, status=status)
        violations = list(summary.get("violations") or [])
        existing_open = self._repo.list_observation_alerts(status="open", limit=500)
        now_ts = datetime.now(timezone.utc).timestamp()
        triggered_alerts: list[dict[str, Any]] = []
        for item in violations:
            metric = str(item.get("metric") or "")
            rule_name = f"latency_violation_{metric}"
            recent_open = False
            for alert in existing_open:
                if str(alert.get("alert_rule") or "") != rule_name:
                    continue
                created_ts = self._parse_iso_ts(str(alert.get("created_at") or ""))
                if created_ts >= now_ts - float(suppress_minutes) * 60.0:
                    recent_open = True
                    break
            if recent_open:
                continue
            actual = float(item.get("actual") or 0.0)
            target = float(item.get("target") or 0.0)
            gap_ratio = (actual - target) / target if target > 0 else 1.0
            severity = "P3"
            if gap_ratio >= 2.0:
                severity = "P1"
            elif gap_ratio >= 1.0:
                severity = "P2"
            created = self._repo.create_observation_alert(
                alert_rule=rule_name,
                severity=severity,
                trigger_value=actual,
                threshold_value=target,
                owner=f"runtime-{summary.get('bottleneck_layer')}",
            )
            self._repo.log_audit_event(
                event_type="runtime_latency_alert_triggered",
                caller="runtime_freshness_latency_evaluator",
                payload={
                    "alert_id": str(created.get("alert_id") or ""),
                    "metric": metric,
                    "window": window,
                    "bottleneck_layer": summary.get("bottleneck_layer"),
                },
            )
            triggered_alerts.append(created)

        return {
            "window": window,
            "violation_count": len(violations),
            "triggered_count": len(triggered_alerts),
            "triggered_alerts": triggered_alerts,
            "bottleneck_layer": summary.get("bottleneck_layer"),
            "suppress_minutes": int(suppress_minutes),
        }

    def _get_quality_baseline_metrics(self, *, baseline_profile: str) -> dict[str, float] | None:
        metric_keys = [
            "normalization_coverage",
            "district_match_rate",
            "low_confidence_ratio",
            "blocked_reason_stability",
        ]
        out: dict[str, float] = {}
        for key in metric_keys:
            series = self._repo.query_observation_metric_series(metric_name=f"runtime.quality.{key}", limit=200)
            matched = None
            for point in series:
                labels = point.get("labels_json") if isinstance(point.get("labels_json"), dict) else {}
                if str(labels.get("profile") or "") == baseline_profile:
                    matched = point
                    break
            if not matched:
                return None
            out[key] = float(matched.get("metric_value") or 0.0)
        return out

    def runtime_quality_drift_summary(
        self,
        *,
        window: str = "24h",
        ruleset_id: str = "",
        status: str = "",
        baseline_profile: str = "rolling-7d",
    ) -> dict[str, Any]:
        recent_hours = self._parse_window_hours(window)
        selected = []
        for task in self._repo.list_tasks(limit=10000):
            if not self._task_in_window(task, recent_hours=recent_hours):
                continue
            if ruleset_id and str(task.get("ruleset_id") or "") != str(ruleset_id):
                continue
            if status and str(task.get("status") or "").upper() != str(status).upper():
                continue
            selected.append(task)

        total = len(selected)
        done = sum(1 for t in selected if str(t.get("status") or "").upper() in {"SUCCEEDED", "REVIEWED"})
        blocked = [t for t in selected if str(t.get("status") or "").upper() == "BLOCKED"]
        blocked_total = len(blocked)
        district_mismatch_blocked = sum(1 for t in blocked if str(t.get("queue_message") or "") == "district_mismatch")

        confidences: list[float] = []
        low_conf_count = 0
        sample_low_conf_task_ids: list[str] = []
        for task in selected:
            task_id = str(task.get("task_id") or "")
            results = self._repo.get_results(task_id)
            for row in results:
                confidence = float(row.get("confidence", 0.0) or 0.0)
                confidences.append(confidence)
                if confidence < 0.85:
                    low_conf_count += 1
                    if task_id and task_id not in sample_low_conf_task_ids:
                        sample_low_conf_task_ids.append(task_id)

        blocked_reason_count: dict[str, int] = {}
        for task in blocked:
            reason = str(task.get("queue_message") or "unknown")
            blocked_reason_count[reason] = blocked_reason_count.get(reason, 0) + 1
        reason_total = sum(blocked_reason_count.values()) or 1
        diversity = 1.0 - sum((count / float(reason_total)) ** 2 for count in blocked_reason_count.values())

        candidate_metrics = {
            "normalization_coverage": round(float(done) / float(total), 6) if total else 1.0,
            "district_match_rate": round(1.0 - (float(district_mismatch_blocked) / float(blocked_total)), 6) if blocked_total else 1.0,
            "low_confidence_ratio": round(float(low_conf_count) / float(len(confidences)), 6) if confidences else 0.0,
            "blocked_reason_stability": round(max(0.0, min(1.0, diversity)), 6),
        }
        for metric_name, metric_value in candidate_metrics.items():
            self._repo.upsert_observation_metric(
                metric_name=f"runtime.quality.{metric_name}",
                metric_value=float(metric_value),
                labels={"window": window, "profile": "candidate"},
            )

        baseline_metrics = self._get_quality_baseline_metrics(baseline_profile=baseline_profile)
        baseline_missing = False
        if not baseline_metrics:
            baseline_metrics = dict(candidate_metrics)
            baseline_missing = True

        drift = {
            key: round(float(candidate_metrics[key]) - float(baseline_metrics.get(key, 0.0)), 6)
            for key in candidate_metrics.keys()
        }
        thresholds = {
            "normalization_coverage_drop": -0.05,
            "district_match_rate_drop": -0.05,
            "low_confidence_ratio_rise": 0.05,
            "blocked_reason_stability_drop": -0.10,
        }
        anomalies = []
        if drift["normalization_coverage"] <= thresholds["normalization_coverage_drop"]:
            anomalies.append({"metric": "normalization_coverage", "delta": drift["normalization_coverage"], "severity": "P2"})
        if drift["district_match_rate"] <= thresholds["district_match_rate_drop"]:
            anomalies.append({"metric": "district_match_rate", "delta": drift["district_match_rate"], "severity": "P1"})
        if drift["low_confidence_ratio"] >= thresholds["low_confidence_ratio_rise"]:
            anomalies.append({"metric": "low_confidence_ratio", "delta": drift["low_confidence_ratio"], "severity": "P1"})
        if drift["blocked_reason_stability"] <= thresholds["blocked_reason_stability_drop"]:
            anomalies.append({"metric": "blocked_reason_stability", "delta": drift["blocked_reason_stability"], "severity": "P2"})

        sample_task_ids = [str(t.get("task_id") or "") for t in blocked[:3] if str(t.get("task_id") or "")]
        for task_id in sample_low_conf_task_ids[:3]:
            if task_id not in sample_task_ids:
                sample_task_ids.append(task_id)

        return {
            "window": window,
            "filters": {"ruleset_id": ruleset_id, "status": status},
            "baseline_profile": baseline_profile,
            "baseline_missing": baseline_missing,
            "candidate_metrics": candidate_metrics,
            "baseline_metrics": baseline_metrics,
            "drift": drift,
            "thresholds": thresholds,
            "anomalies": anomalies,
            "sample_task_ids": sample_task_ids,
        }

    def runtime_quality_drift_evaluate(
        self,
        *,
        window: str = "24h",
        ruleset_id: str = "",
        status: str = "",
        baseline_profile: str = "rolling-7d",
        suppress_minutes: int = 30,
    ) -> dict[str, Any]:
        summary = self.runtime_quality_drift_summary(
            window=window,
            ruleset_id=ruleset_id,
            status=status,
            baseline_profile=baseline_profile,
        )
        anomalies = list(summary.get("anomalies") or [])
        existing_open = self._repo.list_observation_alerts(status="open", limit=500)
        now_ts = datetime.now(timezone.utc).timestamp()
        triggered_alerts: list[dict[str, Any]] = []
        for item in anomalies:
            metric = str(item.get("metric") or "unknown")
            severity = str(item.get("severity") or "P2")
            rule_name = f"quality_drift_{metric}"
            suppressed = False
            for alert in existing_open:
                if str(alert.get("alert_rule") or "") != rule_name:
                    continue
                created_ts = self._parse_iso_ts(str(alert.get("created_at") or ""))
                if created_ts >= now_ts - float(suppress_minutes) * 60.0:
                    suppressed = True
                    break
            if suppressed:
                continue
            delta = float(item.get("delta") or 0.0)
            created = self._repo.create_observation_alert(
                alert_rule=rule_name,
                severity=severity,
                trigger_value=delta,
                threshold_value=0.0,
                owner="runtime-quality-drift",
            )
            self._repo.log_audit_event(
                event_type="runtime_quality_drift_alert_triggered",
                caller="runtime_quality_drift_evaluator",
                payload={
                    "alert_id": str(created.get("alert_id") or ""),
                    "metric": metric,
                    "delta": delta,
                    "sample_task_ids": summary.get("sample_task_ids") or [],
                },
            )
            triggered_alerts.append(created)
        return {
            "window": window,
            "baseline_profile": baseline_profile,
            "violation_count": len(anomalies),
            "triggered_count": len(triggered_alerts),
            "triggered_alerts": triggered_alerts,
            "sample_task_ids": summary.get("sample_task_ids") or [],
            "suppress_minutes": int(suppress_minutes),
        }

    def runtime_performance_summary(
        self,
        *,
        window: str = "24h",
        aggregate_threshold_ms: float = 1500.0,
        detail_threshold_ms: float = 800.0,
    ) -> dict[str, Any]:
        start = perf_counter()
        _summary = self.runtime_summary(window=window)
        _risk = self.runtime_risk_distribution(window=window)
        _tasks = self.runtime_tasks(window=window, limit=50, page=1)
        aggregate_ms = (perf_counter() - start) * 1000.0

        detail_ms = 0.0
        task_id = str((_tasks.get("items") or [{}])[0].get("task_id") or "")
        if task_id:
            start_detail = perf_counter()
            _detail = self.runtime_task_detail(task_id=task_id)
            _ = _detail
            detail_ms = (perf_counter() - start_detail) * 1000.0

        archive = {
            "retention_hot_days": 14,
            "retention_warm_days": 90,
            "retention_cold_days": 365,
            "partition_key": "created_at",
        }
        metrics = {
            "aggregate_api_ms": round(aggregate_ms, 3),
            "task_detail_api_ms": round(detail_ms, 3),
        }
        thresholds = {
            "aggregate_api_ms_lte": float(aggregate_threshold_ms),
            "task_detail_api_ms_lte": float(detail_threshold_ms),
        }
        violations = []
        if metrics["aggregate_api_ms"] > thresholds["aggregate_api_ms_lte"]:
            violations.append({"metric": "aggregate_api_ms", "actual": metrics["aggregate_api_ms"], "target": thresholds["aggregate_api_ms_lte"]})
        if task_id and metrics["task_detail_api_ms"] > thresholds["task_detail_api_ms_lte"]:
            violations.append({"metric": "task_detail_api_ms", "actual": metrics["task_detail_api_ms"], "target": thresholds["task_detail_api_ms_lte"]})

        for metric_name, metric_value in metrics.items():
            self._repo.upsert_observation_metric(
                metric_name=f"runtime.performance.{metric_name}",
                metric_value=float(metric_value),
                labels={"window": window},
            )
        return {
            "window": window,
            "metrics": metrics,
            "thresholds": thresholds,
            "violations": violations,
            "sample_task_id": task_id,
            "archive": archive,
        }

    def runtime_performance_evaluate(
        self,
        *,
        window: str = "24h",
        aggregate_threshold_ms: float = 1500.0,
        detail_threshold_ms: float = 800.0,
        suppress_minutes: int = 30,
    ) -> dict[str, Any]:
        summary = self.runtime_performance_summary(
            window=window,
            aggregate_threshold_ms=aggregate_threshold_ms,
            detail_threshold_ms=detail_threshold_ms,
        )
        violations = list(summary.get("violations") or [])
        existing_open = self._repo.list_observation_alerts(status="open", limit=500)
        now_ts = datetime.now(timezone.utc).timestamp()
        triggered_alerts: list[dict[str, Any]] = []
        for item in violations:
            metric = str(item.get("metric") or "")
            rule_name = f"runtime_perf_{metric}"
            suppressed = False
            for alert in existing_open:
                if str(alert.get("alert_rule") or "") != rule_name:
                    continue
                created_ts = self._parse_iso_ts(str(alert.get("created_at") or ""))
                if created_ts >= now_ts - float(suppress_minutes) * 60.0:
                    suppressed = True
                    break
            if suppressed:
                continue
            actual = float(item.get("actual") or 0.0)
            target = float(item.get("target") or 0.0)
            severity = "P2" if actual > target * 2.0 else "P3"
            created = self._repo.create_observation_alert(
                alert_rule=rule_name,
                severity=severity,
                trigger_value=actual,
                threshold_value=target,
                owner="runtime-performance",
                task_id=str(summary.get("sample_task_id") or ""),
            )
            self._repo.log_audit_event(
                event_type="runtime_performance_alert_triggered",
                caller="runtime_performance_evaluator",
                payload={
                    "alert_id": str(created.get("alert_id") or ""),
                    "metric": metric,
                    "actual": actual,
                    "target": target,
                    "sample_task_id": str(summary.get("sample_task_id") or ""),
                },
            )
            triggered_alerts.append(created)
        return {
            "window": window,
            "violation_count": len(violations),
            "triggered_count": len(triggered_alerts),
            "triggered_alerts": triggered_alerts,
            "sample_task_id": str(summary.get("sample_task_id") or ""),
            "suppress_minutes": int(suppress_minutes),
        }


GOVERNANCE_SERVICE = GovernanceService()

__all__ = ["GOVERNANCE_SERVICE", "GovernanceGateError"]
