from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class _MemoryStore:
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    rulesets: dict[str, dict[str, Any]] = field(default_factory=dict)


class GovernanceRepository:
    def __init__(self) -> None:
        self._memory = _MemoryStore(
            rulesets={
                "default": {
                    "ruleset_id": "default",
                    "version": "v0",
                    "is_active": True,
                    "config_json": {"thresholds": {"t_high": 0.85, "t_low": 0.6}},
                }
            }
        )

    def _database_url(self) -> str | None:
        return os.getenv("DATABASE_URL")

    def _db_enabled(self) -> bool:
        url = self._database_url()
        return bool(url and url.startswith("postgresql"))

    def _execute(self, sql: str, params: dict[str, Any]) -> bool:
        if not self._db_enabled():
            return False
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self._database_url())
            with engine.begin() as conn:
                conn.execute(text(sql), params)
            return True
        except Exception:
            return False

    def create_task(
        self,
        task_id: str,
        batch_name: str,
        ruleset_id: str,
        status: str,
        queue_backend: str,
        queue_message: str,
    ) -> None:
        batch_id = task_id
        created_at = datetime.now(timezone.utc)
        self._memory.tasks[task_id] = {
            "task_id": task_id,
            "batch_id": batch_id,
            "created_at": created_at,
            "status": status,
            "batch_name": batch_name,
            "ruleset_id": ruleset_id,
            "queue_backend": queue_backend,
            "queue_message": queue_message,
        }
        self._execute(
            """
            INSERT INTO addr_batch (batch_id, batch_name, status, created_at, updated_at)
            VALUES (:batch_id, :batch_name, :status, NOW(), NOW())
            ON CONFLICT (batch_id)
            DO UPDATE SET batch_name = EXCLUDED.batch_name, status = EXCLUDED.status, updated_at = NOW();
            """,
            {
                "batch_id": batch_id,
                "batch_name": batch_name,
                "status": status,
            },
        )
        self._execute(
            """
            INSERT INTO addr_task_run (task_id, batch_id, status, error_message, runtime, created_at, updated_at)
            VALUES (:task_id, :batch_id, :status, :error_message, :runtime, NOW(), NOW())
            ON CONFLICT (task_id)
            DO UPDATE SET batch_id = EXCLUDED.batch_id, status = EXCLUDED.status, error_message = EXCLUDED.error_message,
                          runtime = EXCLUDED.runtime, updated_at = NOW();
            """,
            {
                "task_id": task_id,
                "batch_id": batch_id,
                "status": status,
                "error_message": queue_message,
                "runtime": queue_backend,
            },
        )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._memory.tasks.get(task_id)

    def set_task_status(self, task_id: str, status: str) -> None:
        if task_id in self._memory.tasks:
            self._memory.tasks[task_id]["status"] = status
        self._execute(
            """
            UPDATE addr_task_run
            SET status = :status, updated_at = NOW(), finished_at = CASE WHEN :status IN ('SUCCEEDED','FAILED') THEN NOW() ELSE finished_at END
            WHERE task_id = :task_id;
            """,
            {"task_id": task_id, "status": status},
        )

    def save_results(
        self,
        task_id: str,
        results: list[dict[str, Any]],
        raw_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self._memory.results[task_id] = results
        task = self._memory.tasks.get(task_id, {})
        batch_id = task.get("batch_id", task_id)
        raw_by_id = {item.get("raw_id"): item for item in (raw_records or [])}
        for item in results:
            raw_id = item.get("raw_id")
            if not raw_id:
                continue
            raw_input = raw_by_id.get(raw_id, {})
            raw_text = raw_input.get("raw_text") or item.get("canon_text", "")
            self._execute(
                """
                INSERT INTO addr_raw (raw_id, batch_id, raw_text, province, city, district, street, detail, raw_hash, ingested_at)
                VALUES (:raw_id, :batch_id, :raw_text, :province, :city, :district, :street, :detail, :raw_hash, NOW())
                ON CONFLICT (raw_id)
                DO UPDATE SET batch_id = EXCLUDED.batch_id, raw_text = EXCLUDED.raw_text,
                              province = EXCLUDED.province, city = EXCLUDED.city, district = EXCLUDED.district,
                              street = EXCLUDED.street, detail = EXCLUDED.detail;
                """,
                {
                    "raw_id": raw_id,
                    "batch_id": batch_id,
                    "raw_text": raw_text,
                    "province": raw_input.get("province"),
                    "city": raw_input.get("city"),
                    "district": raw_input.get("district"),
                    "street": raw_input.get("street"),
                    "detail": raw_input.get("detail"),
                    "raw_hash": f"rawhash_{raw_id}",
                },
            )

            evidence_json = json.dumps(item.get("evidence", {"items": []}), ensure_ascii=False)
            self._execute(
                """
                INSERT INTO addr_canonical (canonical_id, raw_id, canon_text, confidence, strategy, evidence, ruleset_version, created_at, updated_at)
                VALUES (:canonical_id, :raw_id, :canon_text, :confidence, :strategy, CAST(:evidence AS jsonb), :ruleset_version, NOW(), NOW())
                ON CONFLICT (canonical_id)
                DO UPDATE SET canon_text = EXCLUDED.canon_text, confidence = EXCLUDED.confidence,
                              strategy = EXCLUDED.strategy, evidence = EXCLUDED.evidence, updated_at = NOW();
                """,
                {
                    "canonical_id": f"canon_{raw_id}",
                    "raw_id": raw_id,
                    "canon_text": item.get("canon_text", ""),
                    "confidence": float(item.get("confidence", 0.0)),
                    "strategy": item.get("strategy", "human_required"),
                    "evidence": evidence_json,
                    "ruleset_version": task.get("ruleset_id", "default"),
                },
            )

    def get_results(self, task_id: str) -> list[dict[str, Any]]:
        return self._memory.results.get(task_id, [])

    def upsert_review(self, task_id: str, review_data: dict[str, Any]) -> None:
        self._memory.reviews[task_id] = review_data
        now_value = datetime.now(timezone.utc)
        task_results = self._memory.results.get(task_id, [])
        resolved_raw_id = review_data.get("raw_id")
        if not resolved_raw_id and task_results:
            resolved_raw_id = task_results[0].get("raw_id")
        if not resolved_raw_id:
            resolved_raw_id = task_id
        self._execute(
            """
            INSERT INTO addr_review (review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at)
            VALUES (:review_id, :raw_id, :review_status, :final_canon_text, :reviewer, :comment, :reviewed_at, NOW(), NOW())
            ON CONFLICT (review_id)
            DO UPDATE SET review_status = EXCLUDED.review_status, final_canon_text = EXCLUDED.final_canon_text, reviewer = EXCLUDED.reviewer,
                          comment = EXCLUDED.comment, reviewed_at = EXCLUDED.reviewed_at, updated_at = NOW();
            """,
            {
                "review_id": f"review_{task_id}",
                "raw_id": resolved_raw_id,
                "review_status": review_data.get("review_status", "approved"),
                "final_canon_text": review_data.get("final_canon_text"),
                "reviewer": review_data.get("reviewer"),
                "comment": review_data.get("comment"),
                "reviewed_at": now_value,
            },
        )

    def get_review(self, task_id: str) -> dict[str, Any] | None:
        return self._memory.reviews.get(task_id)

    def _increment_ruleset_feedback(self, ruleset_id: str, review_status: str) -> dict[str, int]:
        ruleset = self._memory.rulesets.get(ruleset_id)
        if not ruleset:
            return {}
        config_json = dict(ruleset.get("config_json", {}))
        counters = dict(config_json.get("feedback_counters", {}))
        status_key = f"review_{review_status}"
        counters[status_key] = int(counters.get(status_key, 0)) + 1
        counters["total_reviews"] = int(counters.get("total_reviews", 0)) + 1
        config_json["feedback_counters"] = counters
        ruleset["config_json"] = config_json
        self._execute(
            """
            UPDATE addr_ruleset
            SET config_json = CAST(:config_json AS jsonb), updated_at = NOW()
            WHERE ruleset_id = :ruleset_id;
            """,
            {"ruleset_id": ruleset_id, "config_json": json.dumps(config_json, ensure_ascii=False)},
        )
        return counters

    def reconcile_review(self, task_id: str, review_data: dict[str, Any] | None = None) -> dict[str, Any]:
        review = review_data or self._memory.reviews.get(task_id) or {}
        target_raw_id = review.get("raw_id")
        review_status = review.get("review_status", "approved")
        reviewer = review.get("reviewer")
        comment = review.get("comment")
        final_canon_text = (review.get("final_canon_text") or "").strip()

        results = self._memory.results.get(task_id, [])
        updated_count = 0
        for item in results:
            if target_raw_id and item.get("raw_id") != target_raw_id:
                continue
            evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
            evidence_items = evidence.get("items") if isinstance(evidence.get("items"), list) else []
            evidence_items.append(
                {
                    "source": "human_review",
                    "review_status": review_status,
                    "reviewer": reviewer,
                    "comment": comment,
                    "raw_id": item.get("raw_id"),
                }
            )
            item["evidence"] = {"items": evidence_items}

            current_confidence = float(item.get("confidence", 0.0))
            if review_status == "edited" and final_canon_text:
                item["canon_text"] = final_canon_text
                item["strategy"] = "human_edited"
                item["confidence"] = max(current_confidence, 0.95)
                updated_count += 1
            elif review_status == "rejected":
                item["strategy"] = "human_rejected"
                item["confidence"] = min(current_confidence, 0.5)
                updated_count += 1
            else:
                item["strategy"] = "human_approved"
                item["confidence"] = max(current_confidence, 0.9)
                updated_count += 1

            self._execute(
                """
                UPDATE addr_canonical
                SET canon_text = :canon_text,
                    confidence = :confidence,
                    strategy = :strategy,
                    evidence = CAST(:evidence AS jsonb),
                    updated_at = NOW()
                WHERE raw_id = :raw_id;
                """,
                {
                    "raw_id": item.get("raw_id"),
                    "canon_text": item.get("canon_text", ""),
                    "confidence": float(item.get("confidence", 0.0)),
                    "strategy": item.get("strategy", "human_required"),
                    "evidence": json.dumps(item.get("evidence", {"items": []}), ensure_ascii=False),
                },
            )

        self._memory.results[task_id] = results
        task = self._memory.tasks.get(task_id, {})
        ruleset_id = task.get("ruleset_id", "default")
        feedback_counters = self._increment_ruleset_feedback(ruleset_id, review_status)
        self.set_task_status(task_id, "REVIEWED")
        return {
            "task_id": task_id,
            "status": "RECONCILED",
            "updated_count": updated_count,
            "target_raw_id": target_raw_id,
            "ruleset_id": ruleset_id,
            "feedback_counters": feedback_counters,
        }

    def get_ruleset(self, ruleset_id: str) -> dict[str, Any] | None:
        return self._memory.rulesets.get(ruleset_id)

    def get_ops_summary(
        self,
        task_id: str | None = None,
        batch_name: str | None = None,
        ruleset_id: str | None = None,
        status_list: list[str] | None = None,
        recent_hours: int | None = None,
        t_low_override: float | None = None,
        t_high_override: float | None = None,
    ) -> dict[str, Any]:
        tasks = list(self._memory.tasks.values())
        if task_id:
            tasks = [item for item in tasks if item.get("task_id") == task_id]
        if batch_name:
            tasks = [item for item in tasks if item.get("batch_name") == batch_name]
        if ruleset_id:
            tasks = [item for item in tasks if item.get("ruleset_id") == ruleset_id]
        if status_list:
            allowed = {status.upper() for status in status_list if status}
            tasks = [item for item in tasks if str(item.get("status", "")).upper() in allowed]
        if recent_hours is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - float(recent_hours) * 3600.0

            def _to_ts(value: Any) -> float:
                if isinstance(value, datetime):
                    return value.timestamp()
                if isinstance(value, str):
                    try:
                        normalized = value.replace("Z", "+00:00")
                        parsed = datetime.fromisoformat(normalized)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        return parsed.timestamp()
                    except Exception:
                        return 0.0
                return 0.0

            tasks = [item for item in tasks if _to_ts(item.get("created_at")) >= cutoff]

        total_tasks = len(tasks)
        status_counts: dict[str, int] = {}
        for task in tasks:
            status = str(task.get("status", "UNKNOWN"))
            status_counts[status] = status_counts.get(status, 0) + 1

        selected_task_ids = {str(task.get("task_id")) for task in tasks}
        all_results: list[dict[str, Any]] = []
        for result_task_id, values in self._memory.results.items():
            if selected_task_ids and result_task_id not in selected_task_ids:
                continue
            all_results.extend(values)
        total_results = len(all_results)
        avg_confidence = (
            sum(float(item.get("confidence", 0.0)) for item in all_results) / float(total_results)
            if total_results
            else 0.0
        )

        active_ruleset = None
        for ruleset in self._memory.rulesets.values():
            if ruleset.get("is_active"):
                active_ruleset = ruleset
                break
        if not active_ruleset:
            active_ruleset = self._memory.rulesets.get("default")

        thresholds = (active_ruleset or {}).get("config_json", {}).get("thresholds", {})
        default_t_low = float(thresholds.get("t_low", 0.6))
        default_t_high = float(thresholds.get("t_high", 0.85))
        t_low = float(t_low_override) if t_low_override is not None else default_t_low
        t_high = float(t_high_override) if t_high_override is not None else default_t_high
        low_confidence_results = sum(1 for item in all_results if float(item.get("confidence", 0.0)) < t_low)

        pending_review_tasks = status_counts.get("SUCCEEDED", 0)
        reviewed_tasks = status_counts.get("REVIEWED", 0)
        quality_gate_reasons: list[str] = []
        if pending_review_tasks > 0:
            quality_gate_reasons.append("pending_review_exists")
        if low_confidence_results > 0:
            quality_gate_reasons.append("low_confidence_exists")
        if t_low > t_high:
            quality_gate_reasons.append("invalid_threshold_range")
        quality_gate_passed = len(quality_gate_reasons) == 0

        return {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "total_results": total_results,
            "avg_confidence": round(avg_confidence, 6),
            "pending_review_tasks": pending_review_tasks,
            "reviewed_tasks": reviewed_tasks,
            "active_ruleset_id": (active_ruleset or {}).get("ruleset_id", "default"),
            "thresholds": {"t_low": t_low, "t_high": t_high},
            "low_confidence_results": low_confidence_results,
            "quality_gate_passed": quality_gate_passed,
            "quality_gate_reasons": quality_gate_reasons,
        }

    def upsert_ruleset(self, ruleset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        item = {
            "ruleset_id": ruleset_id,
            "version": payload["version"],
            "is_active": payload.get("is_active", False),
            "config_json": payload["config_json"],
        }
        self._memory.rulesets[ruleset_id] = item
        self._execute(
            """
            INSERT INTO addr_ruleset (ruleset_id, version, is_active, config_json, created_at, updated_at)
            VALUES (:ruleset_id, :version, :is_active, CAST(:config_json AS jsonb), NOW(), NOW())
            ON CONFLICT (ruleset_id)
            DO UPDATE SET version = EXCLUDED.version, is_active = EXCLUDED.is_active, config_json = EXCLUDED.config_json, updated_at = NOW();
            """,
            {
                "ruleset_id": ruleset_id,
                "version": item["version"],
                "is_active": item["is_active"],
                "config_json": str(item["config_json"]).replace("'", '"'),
            },
        )
        return item

    def publish_ruleset(self, ruleset_id: str, operator: str, reason: str) -> dict[str, Any] | None:
        target = self._memory.rulesets.get(ruleset_id)
        if not target:
            return None
        for key in self._memory.rulesets:
            self._memory.rulesets[key]["is_active"] = False
        target["is_active"] = True
        target["published_by"] = operator
        target["published_reason"] = reason
        self._execute("UPDATE addr_ruleset SET is_active = FALSE WHERE is_active = TRUE;", {})
        self._execute(
            "UPDATE addr_ruleset SET is_active = TRUE, updated_at = NOW() WHERE ruleset_id = :ruleset_id;",
            {"ruleset_id": ruleset_id},
        )
        return target


REPOSITORY = GovernanceRepository()
