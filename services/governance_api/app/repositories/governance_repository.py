from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class _MemoryStore:
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    rulesets: dict[str, dict[str, Any]] = field(default_factory=dict)
    change_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)


class GovernanceGateError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class GovernanceRepository:
    def __init__(self) -> None:
        self._allow_memory_fallback = str(os.getenv("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "0")).strip() == "1"
        db_url = str(os.getenv("DATABASE_URL") or "").strip()
        
        # Allow SQLite for local "real DB" simulation when Docker is unavailable
        if not self._allow_memory_fallback and not db_url.startswith("postgresql") and not db_url.startswith("sqlite"):
            raise RuntimeError(
                "DATABASE_URL must be postgresql:// or sqlite:// in persistent runtime mode. "
                "Set GOVERNANCE_ALLOW_MEMORY_FALLBACK=1 for temporary local fallback."
            )
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
        if self._allow_memory_fallback:
            return False
        url = self._database_url()
        return bool(url and (url.startswith("postgresql") or url.startswith("sqlite")))

    def _sql_now(self) -> str:
        url = self._database_url() or ""
        return "CURRENT_TIMESTAMP" if url.startswith("sqlite") else "NOW()"

    def _sql_json_cast(self, param: str) -> str:
        url = self._database_url() or ""
        return param if url.startswith("sqlite") else f"CAST({param} AS jsonb)"

    def _execute(self, sql: str, params: dict[str, Any]) -> bool:
        if not self._db_enabled():
            return False
        # If DB is enabled, we expect strict consistency. Failures should propagate.
        from sqlalchemy import create_engine, text

        engine = create_engine(self._database_url())
        with engine.begin() as conn:
            # Postgres specific search path, skip for SQLite
            if self._database_url().startswith("postgresql"):
                conn.execute(text("SET search_path TO address_line, control_plane, trust_meta, trust_db, public"))
            conn.execute(text(sql), params)
        return True

    def _query(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not self._db_enabled():
            return []
        # If DB is enabled, we expect strict consistency. Failures should propagate.
        from sqlalchemy import create_engine, text

        engine = create_engine(self._database_url())
        with engine.begin() as conn:
            # Postgres specific search path, skip for SQLite
            if self._database_url().startswith("postgresql"):
                conn.execute(text("SET search_path TO address_line, control_plane, trust_meta, trust_db, public"))
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(item) for item in rows]

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
        now_func = self._sql_now()
        self._execute(
            f"""
            INSERT INTO addr_batch (batch_id, batch_name, status, created_at, updated_at)
            VALUES (:batch_id, :batch_name, :status, {now_func}, {now_func})
            ON CONFLICT (batch_id)
            DO UPDATE SET batch_name = EXCLUDED.batch_name, status = EXCLUDED.status, updated_at = {now_func};
            """,
            {
                "batch_id": batch_id,
                "batch_name": batch_name,
                "status": status,
            },
        )
        self._execute(
            f"""
            INSERT INTO addr_task_run (task_id, batch_id, status, error_message, runtime, created_at, updated_at)
            VALUES (:task_id, :batch_id, :status, :error_message, :runtime, {now_func}, {now_func})
            ON CONFLICT (task_id)
            DO UPDATE SET batch_id = EXCLUDED.batch_id, status = EXCLUDED.status, error_message = EXCLUDED.error_message,
                          runtime = EXCLUDED.runtime, updated_at = {now_func};
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
        now_func = self._sql_now()
        self._execute(
            f"""
            UPDATE addr_task_run
            SET status = :status, updated_at = {now_func}, finished_at = CASE WHEN :status IN ('SUCCEEDED','FAILED') THEN {now_func} ELSE finished_at END
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
        now_func = self._sql_now()
        evidence_cast = self._sql_json_cast(":evidence")
        
        for item in results:
            raw_id = item.get("raw_id")
            if not raw_id:
                continue
            raw_input = raw_by_id.get(raw_id, {})
            raw_text = raw_input.get("raw_text") or item.get("canon_text", "")
            self._execute(
                f"""
                INSERT INTO addr_raw (raw_id, batch_id, raw_text, province, city, district, street, detail, raw_hash, ingested_at)
                VALUES (:raw_id, :batch_id, :raw_text, :province, :city, :district, :street, :detail, :raw_hash, {now_func})
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
                f"""
                INSERT INTO addr_canonical (canonical_id, raw_id, canon_text, confidence, strategy, evidence, ruleset_version, created_at, updated_at)
                VALUES (:canonical_id, :raw_id, :canon_text, :confidence, :strategy, {evidence_cast}, :ruleset_version, {now_func}, {now_func})
                ON CONFLICT (canonical_id)
                DO UPDATE SET canon_text = EXCLUDED.canon_text, confidence = EXCLUDED.confidence,
                              strategy = EXCLUDED.strategy, evidence = EXCLUDED.evidence, updated_at = {now_func};
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
        
        now_func = self._sql_now()
        self._execute(
            f"""
            INSERT INTO addr_review (review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at)
            VALUES (:review_id, :raw_id, :review_status, :final_canon_text, :reviewer, :comment, :reviewed_at, {now_func}, {now_func})
            ON CONFLICT (review_id)
            DO UPDATE SET review_status = EXCLUDED.review_status, final_canon_text = EXCLUDED.final_canon_text, reviewer = EXCLUDED.reviewer,
                          comment = EXCLUDED.comment, reviewed_at = EXCLUDED.reviewed_at, updated_at = {now_func};
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
        
        now_func = self._sql_now()
        config_cast = self._sql_json_cast(":config_json")
        self._execute(
            f"""
            UPDATE addr_ruleset
            SET config_json = {config_cast}, updated_at = {now_func}
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

            now_func = self._sql_now()
            evidence_cast = self._sql_json_cast(":evidence")
            self._execute(
                f"""
                UPDATE addr_canonical
                SET canon_text = :canon_text,
                    confidence = :confidence,
                    strategy = :strategy,
                    evidence = {evidence_cast},
                    updated_at = {now_func}
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

    def list_manual_review_items(self, *, pending_only: bool = True, limit: int = 200) -> list[dict[str, Any]]:
        if self._db_enabled():
            rows = self._query(
                """
                WITH review_latest AS (
                    SELECT DISTINCT ON (raw_id)
                        raw_id,
                        review_status,
                        reviewer,
                        comment,
                        reviewed_at,
                        updated_at
                    FROM addr_review
                    ORDER BY raw_id, COALESCE(reviewed_at, updated_at, created_at) DESC
                )
                SELECT
                    tr.task_id,
                    tr.status AS task_status,
                    tr.created_at AS task_created_at,
                    tr.updated_at AS task_updated_at,
                    raw.raw_id,
                    raw.raw_text,
                    canon.canon_text,
                    canon.confidence,
                    canon.strategy,
                    canon.updated_at AS canonical_updated_at,
                    rl.review_status,
                    rl.reviewer,
                    rl.comment AS review_comment,
                    rl.reviewed_at
                FROM addr_task_run tr
                JOIN addr_raw raw
                    ON raw.batch_id = tr.batch_id
                JOIN addr_canonical canon
                    ON canon.raw_id = raw.raw_id
                LEFT JOIN review_latest rl
                    ON rl.raw_id = raw.raw_id
                WHERE (
                        canon.strategy IN ('human_required', 'human_rejected', 'low_confidence', 'fallback')
                        OR canon.confidence < :confidence_gate
                        OR tr.status IN ('SUCCEEDED', 'REVIEWED')
                    )
                    AND (:pending_only = FALSE OR rl.review_status IS NULL)
                ORDER BY
                    CASE WHEN rl.review_status IS NULL THEN 0 ELSE 1 END ASC,
                    canon.confidence ASC,
                    tr.updated_at DESC
                LIMIT :limit;
                """,
                {
                    "pending_only": bool(pending_only),
                    "limit": int(limit),
                    "confidence_gate": 0.85,
                },
            )
            normalized: list[dict[str, Any]] = []
            for row in rows:
                confidence = float(row.get("confidence", 0.0) or 0.0)
                review_status = str(row.get("review_status") or "")
                task_status = str(row.get("task_status") or "")
                strategy = str(row.get("strategy") or "")
                if review_status:
                    risk_level = "low"
                    stage = "已人工决策"
                else:
                    stage = "待人工确认"
                    if task_status.upper() == "FAILED" or confidence < 0.6 or strategy == "human_rejected":
                        risk_level = "high"
                    elif confidence < 0.85:
                        risk_level = "medium"
                    else:
                        risk_level = "low"
                normalized.append(
                    {
                        "task_id": str(row.get("task_id") or ""),
                        "raw_id": str(row.get("raw_id") or ""),
                        "raw_text": str(row.get("raw_text") or ""),
                        "canon_text": str(row.get("canon_text") or ""),
                        "confidence": round(confidence, 6),
                        "strategy": strategy,
                        "task_status": task_status,
                        "review_status": review_status,
                        "reviewer": str(row.get("reviewer") or ""),
                        "review_comment": str(row.get("review_comment") or ""),
                        "reviewed_at": str(row.get("reviewed_at") or ""),
                        "task_created_at": str(row.get("task_created_at") or ""),
                        "task_updated_at": str(row.get("task_updated_at") or ""),
                        "canonical_updated_at": str(row.get("canonical_updated_at") or ""),
                        "stage": stage,
                        "risk_level": risk_level,
                        "evidence_ref": f"/v1/governance/tasks/{str(row.get('task_id') or '')}/result",
                    }
                )
            return normalized

        items: list[dict[str, Any]] = []
        for task_id, task in self._memory.tasks.items():
            task_status = str(task.get("status") or "")
            for result in self._memory.results.get(task_id, []):
                raw_id = str(result.get("raw_id") or "")
                review = self._memory.reviews.get(task_id, {})
                review_status = str(review.get("review_status") or "")
                is_reviewed = bool(review_status and (not review.get("raw_id") or review.get("raw_id") == raw_id))
                if pending_only and is_reviewed:
                    continue
                confidence = float(result.get("confidence", 0.0) or 0.0)
                strategy = str(result.get("strategy") or "")
                needs_manual = strategy in {"human_required", "human_rejected"} or confidence < 0.85 or task_status in {"SUCCEEDED", "REVIEWED"}
                if not needs_manual:
                    continue
                risk_level = "high" if confidence < 0.6 else ("medium" if confidence < 0.85 else "low")
                stage = "已人工决策" if is_reviewed else "待人工确认"
                items.append(
                    {
                        "task_id": task_id,
                        "raw_id": raw_id,
                        "raw_text": str(result.get("canon_text") or ""),
                        "canon_text": str(result.get("canon_text") or ""),
                        "confidence": round(confidence, 6),
                        "strategy": strategy,
                        "task_status": task_status,
                        "review_status": review_status,
                        "reviewer": str(review.get("reviewer") or ""),
                        "review_comment": str(review.get("comment") or ""),
                        "reviewed_at": "",
                        "task_created_at": str(task.get("created_at") or ""),
                        "task_updated_at": "",
                        "canonical_updated_at": "",
                        "stage": stage,
                        "risk_level": risk_level,
                        "evidence_ref": f"/v1/governance/tasks/{task_id}/result",
                    }
                )
        items.sort(key=lambda row: (row["stage"] != "待人工确认", row["confidence"]))
        return items[:limit]

    def submit_manual_review_decision(
        self,
        *,
        task_id: str,
        raw_id: str,
        review_status: str,
        reviewer: str,
        next_route: str,
        comment: str = "",
        final_canon_text: str | None = None,
    ) -> dict[str, Any]:
        normalized_status = review_status.strip().lower()
        if normalized_status not in {"approved", "rejected", "edited"}:
            raise ValueError("review_status must be one of approved/rejected/edited")
        merged_comment = f"[route:{next_route}] {comment}".strip()

        if self._db_enabled():
            review_id = f"rv_{uuid4().hex[:24]}"
            now_func = self._sql_now()
            self._execute(
                f"""
                INSERT INTO addr_review (review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at)
                VALUES (:review_id, :raw_id, :review_status, :final_canon_text, :reviewer, :comment, {now_func}, {now_func}, {now_func});
                """,
                {
                    "review_id": review_id,
                    "raw_id": raw_id,
                    "review_status": normalized_status,
                    "final_canon_text": final_canon_text,
                    "reviewer": reviewer,
                    "comment": merged_comment,
                },
            )
            if normalized_status == "approved":
                self._execute(
                    f"""
                    UPDATE addr_canonical
                    SET
                        canon_text = CASE WHEN :final_canon_text IS NOT NULL AND :final_canon_text <> '' THEN :final_canon_text ELSE canon_text END,
                        confidence = GREATEST(confidence, 0.90),
                        strategy = 'human_approved',
                        updated_at = {now_func}
                    WHERE raw_id = :raw_id;
                    """,
                    {"raw_id": raw_id, "final_canon_text": final_canon_text},
                )
            elif normalized_status == "rejected":
                self._execute(
                    f"""
                    UPDATE addr_canonical
                    SET
                        confidence = LEAST(confidence, 0.50),
                        strategy = 'human_rejected',
                        updated_at = {now_func}
                    WHERE raw_id = :raw_id;
                    """,
                    {"raw_id": raw_id},
                )
            else:
                self._execute(
                    f"""
                    UPDATE addr_canonical
                    SET
                        canon_text = CASE WHEN :final_canon_text IS NOT NULL AND :final_canon_text <> '' THEN :final_canon_text ELSE canon_text END,
                        confidence = GREATEST(confidence, 0.95),
                        strategy = 'human_edited',
                        updated_at = {now_func}
                    WHERE raw_id = :raw_id;
                    """,
                    {"raw_id": raw_id, "final_canon_text": final_canon_text},
                )
            self._execute(
                f"""
                UPDATE addr_task_run
                SET status = CASE WHEN status = 'FAILED' THEN status ELSE 'REVIEWED' END,
                    updated_at = {now_func}
                WHERE task_id = :task_id;
                """,
                {"task_id": task_id},
            )
            event = self._append_audit_event(
                event_type="manual_review_decision",
                caller=reviewer,
                payload={
                    "task_id": task_id,
                    "raw_id": raw_id,
                    "review_status": normalized_status,
                    "next_route": next_route,
                    "comment": comment,
                },
                related_change_id=None,
            )
            return {
                "accepted": True,
                "task_id": task_id,
                "raw_id": raw_id,
                "review_status": normalized_status,
                "next_route": next_route,
                "audit_event_id": str(event.get("event_id") or ""),
            }

        review_data = {
            "raw_id": raw_id,
            "review_status": normalized_status,
            "reviewer": reviewer,
            "comment": merged_comment,
            "final_canon_text": final_canon_text,
        }
        self.upsert_review(task_id, review_data)
        reconciled = self.reconcile_review(task_id, review_data)
        return {
            "accepted": True,
            "task_id": task_id,
            "raw_id": raw_id,
            "review_status": normalized_status,
            "next_route": next_route,
            "updated_count": int(reconciled.get("updated_count", 0)),
            "audit_event_id": "",
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _append_audit_event(
        self,
        event_type: str,
        caller: str,
        payload: dict[str, Any],
        related_change_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = f"evt_{uuid4().hex[:12]}"
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "caller": caller,
            "payload": payload,
            "related_change_id": related_change_id,
            "created_at": self._now_iso(),
        }
        self._memory.audit_events.append(event)
        now_func = self._sql_now()
        payload_cast = self._sql_json_cast(":payload")
        self._execute(
            f"""
            INSERT INTO addr_audit_event (event_id, event_type, caller, payload, related_change_id, created_at)
            VALUES (:event_id, :event_type, :caller, {payload_cast}, :related_change_id, {now_func})
            ON CONFLICT (event_id) DO NOTHING;
            """,
            {
                "event_id": event_id,
                "event_type": event_type,
                "caller": caller,
                "payload": json.dumps(payload, ensure_ascii=False),
                "related_change_id": related_change_id,
            },
        )
        return event

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
        now_func = self._sql_now()
        config_cast = self._sql_json_cast(":config_json")
        self._execute(
            f"""
            INSERT INTO addr_ruleset (ruleset_id, version, is_active, config_json, created_at, updated_at)
            VALUES (:ruleset_id, :version, :is_active, {config_cast}, {now_func}, {now_func})
            ON CONFLICT (ruleset_id)
            DO UPDATE SET version = EXCLUDED.version, is_active = EXCLUDED.is_active, config_json = EXCLUDED.config_json, updated_at = {now_func};
            """,
            {
                "ruleset_id": ruleset_id,
                "version": item["version"],
                "is_active": item["is_active"],
                "config_json": str(item["config_json"]).replace("'", '"'),
            },
        )
        return item

    def create_change_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        change_id = f"chg_{uuid4().hex[:12]}"
        now_iso = self._now_iso()
        item = {
            "change_id": change_id,
            "from_ruleset_id": payload["from_ruleset_id"],
            "to_ruleset_id": payload["to_ruleset_id"],
            "baseline_task_id": payload["baseline_task_id"],
            "candidate_task_id": payload["candidate_task_id"],
            "diff": payload.get("diff", {}),
            "scorecard": payload.get("scorecard", {}),
            "recommendation": payload["recommendation"],
            "status": "pending",
            "approved_by": None,
            "approved_at": None,
            "review_comment": None,
            "evidence_bullets": payload.get("evidence_bullets", []),
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        self._memory.change_requests[change_id] = item
        now_func = self._sql_now()
        diff_cast = self._sql_json_cast(":diff_json")
        scorecard_cast = self._sql_json_cast(":scorecard_json")
        evidence_cast = self._sql_json_cast(":evidence_bullets")
        self._execute(
            f"""
            INSERT INTO addr_change_request (
                change_id, from_ruleset_id, to_ruleset_id, baseline_task_id, candidate_task_id,
                diff_json, scorecard_json, recommendation, status, approved_by, approved_at,
                review_comment, evidence_bullets, created_at, updated_at
            ) VALUES (
                :change_id, :from_ruleset_id, :to_ruleset_id, :baseline_task_id, :candidate_task_id,
                {diff_cast}, {scorecard_cast}, :recommendation, :status, :approved_by, :approved_at,
                :review_comment, {evidence_cast}, {now_func}, {now_func}
            )
            ON CONFLICT (change_id)
            DO UPDATE SET
                from_ruleset_id = EXCLUDED.from_ruleset_id,
                to_ruleset_id = EXCLUDED.to_ruleset_id,
                baseline_task_id = EXCLUDED.baseline_task_id,
                candidate_task_id = EXCLUDED.candidate_task_id,
                diff_json = EXCLUDED.diff_json,
                scorecard_json = EXCLUDED.scorecard_json,
                recommendation = EXCLUDED.recommendation,
                status = EXCLUDED.status,
                approved_by = EXCLUDED.approved_by,
                approved_at = EXCLUDED.approved_at,
                review_comment = EXCLUDED.review_comment,
                evidence_bullets = EXCLUDED.evidence_bullets,
                updated_at = {now_func};
            """,
            {
                "change_id": change_id,
                "from_ruleset_id": item["from_ruleset_id"],
                "to_ruleset_id": item["to_ruleset_id"],
                "baseline_task_id": item["baseline_task_id"],
                "candidate_task_id": item["candidate_task_id"],
                "diff_json": json.dumps(item["diff"], ensure_ascii=False),
                "scorecard_json": json.dumps(item["scorecard"], ensure_ascii=False),
                "recommendation": item["recommendation"],
                "status": item["status"],
                "approved_by": item["approved_by"],
                "approved_at": item["approved_at"],
                "review_comment": item["review_comment"],
                "evidence_bullets": json.dumps(item["evidence_bullets"], ensure_ascii=False),
            },
        )
        self._append_audit_event(
            event_type="change_request_created",
            caller="system",
            payload={
                "change_id": change_id,
                "from_ruleset_id": item["from_ruleset_id"],
                "to_ruleset_id": item["to_ruleset_id"],
                "task_run_id": item["candidate_task_id"],
                "recommendation": item["recommendation"],
                "reason": "change_request_submitted",
            },
            related_change_id=change_id,
        )
        return item

    def get_change_request(self, change_id: str) -> dict[str, Any] | None:
        return self._memory.change_requests.get(change_id)

    def update_change_request_status(
        self,
        change_id: str,
        *,
        status: str,
        actor: str,
        comment: str | None = None,
    ) -> dict[str, Any] | None:
        item = self._memory.change_requests.get(change_id)
        if not item:
            return None
        now_iso = self._now_iso()
        item["status"] = status
        item["updated_at"] = now_iso
        if status == "approved":
            item["approved_by"] = actor
            item["approved_at"] = now_iso
        else:
            item["approved_by"] = None
            item["approved_at"] = None
        if comment:
            item["review_comment"] = comment
        now_func = self._sql_now()
        self._execute(
            f"""
            UPDATE addr_change_request
            SET status = :status,
                approved_by = :approved_by,
                approved_at = :approved_at,
                review_comment = :review_comment,
                updated_at = {now_func}
            WHERE change_id = :change_id;
            """,
            {
                "change_id": change_id,
                "status": item["status"],
                "approved_by": item["approved_by"],
                "approved_at": item["approved_at"],
                "review_comment": item["review_comment"],
            },
        )
        self._append_audit_event(
            event_type="approval_changed",
            caller=actor,
            payload={
                "change_id": change_id,
                "status": status,
                "task_run_id": item.get("candidate_task_id"),
                "comment": comment,
                "reason": comment,
            },
            related_change_id=change_id,
        )
        return item

    def activate_ruleset(
        self,
        *,
        ruleset_id: str,
        change_id: str,
        caller: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        change = self._memory.change_requests.get(change_id)

        def _block(code: str, message: str, status_code: int, gate_reason: str) -> None:
            task_run_id = None
            if isinstance(change, dict):
                task_run_id = change.get("candidate_task_id")
            self._append_audit_event(
                event_type="ruleset_activation_blocked",
                caller=caller,
                payload={
                    "ruleset_id": ruleset_id,
                    "change_id": change_id,
                    "task_run_id": task_run_id,
                    "reason": reason,
                    "gate_reason": gate_reason,
                    "gate_code": code,
                },
                related_change_id=change_id if isinstance(change, dict) else None,
            )
            raise GovernanceGateError(code=code, message=message, status_code=status_code)

        if caller.lower() != "admin":
            _block("CALLER_NOT_AUTHORIZED", "caller must be admin", 403, "caller_not_admin")

        if not isinstance(change, dict):
            _block("APPROVAL_MISSING", "change request not found", 409, "missing_change_request")

        if change.get("status") == "rejected":
            _block("APPROVAL_REJECTED", "change request is rejected", 409, "approval_rejected")
        if change.get("status") != "approved":
            _block("APPROVAL_PENDING", "change request is not approved", 409, "approval_not_ready")
        if not change.get("approved_by") or not change.get("approved_at"):
            _block("APPROVAL_MISSING", "approval metadata is missing", 409, "approval_metadata_missing")
        if change.get("to_ruleset_id") != ruleset_id:
            _block("CHANGE_TARGET_MISMATCH", "change request does not match target ruleset", 409, "target_mismatch")
        if ruleset_id not in self._memory.rulesets:
            _block("RULESET_NOT_FOUND", "ruleset not found", 404, "ruleset_not_found")

        for key in self._memory.rulesets:
            self._memory.rulesets[key]["is_active"] = False
        target = self._memory.rulesets[ruleset_id]
        target["is_active"] = True
        target["published_by"] = caller
        target["published_reason"] = reason or f"activated via change {change_id}"

        now_func = self._sql_now()
        self._execute("UPDATE addr_ruleset SET is_active = FALSE WHERE is_active = TRUE;", {})
        self._execute(
            f"UPDATE addr_ruleset SET is_active = TRUE, updated_at = {now_func} WHERE ruleset_id = :ruleset_id;",
            {"ruleset_id": ruleset_id},
        )
        self._append_audit_event(
            event_type="ruleset_activated",
            caller=caller,
            payload={
                "ruleset_id": ruleset_id,
                "change_id": change_id,
                "task_run_id": change.get("candidate_task_id"),
                "reason": reason,
            },
            related_change_id=change_id,
        )
        return target

    def list_audit_events(self, related_change_id: str | None = None) -> list[dict[str, Any]]:
        if not related_change_id:
            return list(self._memory.audit_events)
        return [evt for evt in self._memory.audit_events if evt.get("related_change_id") == related_change_id]

    def log_audit_event(
        self,
        event_type: str,
        caller: str,
        payload: dict[str, Any],
        related_change_id: str | None = None,
    ) -> dict[str, Any]:
        return self._append_audit_event(
            event_type=event_type,
            caller=caller,
            payload=payload,
            related_change_id=related_change_id,
        )

    def publish_ruleset(self, ruleset_id: str, operator: str, reason: str) -> dict[str, Any] | None:
        target = self._memory.rulesets.get(ruleset_id)
        if not target:
            return None
        for key in self._memory.rulesets:
            self._memory.rulesets[key]["is_active"] = False
        target["is_active"] = True
        target["published_by"] = operator
        target["published_reason"] = reason
        now_func = self._sql_now()
        self._execute("UPDATE addr_ruleset SET is_active = FALSE WHERE is_active = TRUE;", {})
        self._execute(
            f"UPDATE addr_ruleset SET is_active = TRUE, updated_at = {now_func} WHERE ruleset_id = :ruleset_id;",
            {"ruleset_id": ruleset_id},
        )
        return target

    def _task_thresholds(self, task_id: str, t_low_override: float | None, t_high_override: float | None) -> tuple[float, float]:
        task = self._memory.tasks.get(task_id, {})
        ruleset = self._memory.rulesets.get(task.get("ruleset_id", "default"), self._memory.rulesets.get("default", {}))
        thresholds = (ruleset or {}).get("config_json", {}).get("thresholds", {})
        t_low = float(t_low_override) if t_low_override is not None else float(thresholds.get("t_low", 0.6))
        t_high = float(t_high_override) if t_high_override is not None else float(thresholds.get("t_high", 0.85))
        return t_low, t_high

    def _task_metrics(self, task_id: str, t_low: float, t_high: float) -> dict[str, float]:
        results = list(self._memory.results.get(task_id, []))
        total = len(results)
        if total <= 0:
            return {
                "auto_pass_rate": 0.0,
                "review_rate": 0.0,
                "human_required_rate": 0.0,
                "consistency_score": 1.0,
                "quality_gate_pass_rate": 1.0,
                "review_accept_rate": 0.0,
            }

        auto_pass = 0
        review_bucket = 0
        human_required = 0
        gate_pass = 0
        groups: dict[str, set[str]] = {}
        for item in results:
            confidence = float(item.get("confidence", 0.0))
            if confidence >= t_high:
                auto_pass += 1
            elif confidence >= t_low:
                review_bucket += 1
            else:
                human_required += 1
            if confidence >= t_low:
                gate_pass += 1
            raw_key = str(item.get("raw_id") or "")
            canon = str(item.get("canon_text") or "")
            groups.setdefault(raw_key, set()).add(canon)

        conflict_groups = 0
        duplicated_groups = 0
        for _, outputs in groups.items():
            if len(outputs) > 1:
                duplicated_groups += 1
                conflict_groups += 1
        consistency_score = 1.0
        if duplicated_groups > 0:
            consistency_score = max(0.0, 1.0 - (float(conflict_groups) / float(duplicated_groups)))

        review_item = self._memory.reviews.get(task_id)
        review_accept_rate = 0.0
        if review_item:
            review_status = str(review_item.get("review_status") or "").lower()
            review_accept_rate = 1.0 if review_status in {"approved", "edited"} else 0.0

        return {
            "auto_pass_rate": round(float(auto_pass) / float(total), 6),
            "review_rate": round(float(review_bucket) / float(total), 6),
            "human_required_rate": round(float(human_required) / float(total), 6),
            "consistency_score": round(consistency_score, 6),
            "quality_gate_pass_rate": round(float(gate_pass) / float(total), 6),
            "review_accept_rate": round(review_accept_rate, 6),
        }

    def compute_scorecard(
        self,
        baseline_task_id: str,
        candidate_task_id: str,
        t_low_override: float | None = None,
        t_high_override: float | None = None,
    ) -> dict[str, Any]:
        t_low_b, t_high_b = self._task_thresholds(baseline_task_id, t_low_override, t_high_override)
        t_low_c, t_high_c = self._task_thresholds(candidate_task_id, t_low_override, t_high_override)
        baseline = self._task_metrics(baseline_task_id, t_low=t_low_b, t_high=t_high_b)
        candidate = self._task_metrics(candidate_task_id, t_low=t_low_c, t_high=t_high_c)
        delta = {
            key: round(float(candidate.get(key, 0.0)) - float(baseline.get(key, 0.0)), 6)
            for key in baseline.keys()
        }

        reasons: list[str] = []
        if (
            delta["auto_pass_rate"] > 0
            and delta["human_required_rate"] <= 0
            and delta["consistency_score"] >= 0
            and delta["quality_gate_pass_rate"] >= 0
        ):
            recommendation = "accept"
            reasons.append("auto_pass_rate_up")
            reasons.append("human_required_not_up")
            reasons.append("consistency_not_down")
            reasons.append("quality_gate_not_worse")
        elif (
            delta["human_required_rate"] > 0
            or delta["consistency_score"] < -0.05
            or delta["quality_gate_pass_rate"] < 0
        ):
            recommendation = "reject"
            if delta["human_required_rate"] > 0:
                reasons.append("human_required_up")
            if delta["consistency_score"] < -0.05:
                reasons.append("consistency_down")
            if delta["quality_gate_pass_rate"] < 0:
                reasons.append("quality_gate_worse")
        else:
            recommendation = "needs-human"
            reasons.append("tradeoff_or_uncertain_gain")

        return {
            "baseline_task_id": baseline_task_id,
            "candidate_task_id": candidate_task_id,
            "thresholds": {"t_low": t_low_b, "t_high": t_high_b},
            "baseline": baseline,
            "candidate": candidate,
            "delta": delta,
            "recommendation": recommendation,
            "reasons": reasons,
        }


REPOSITORY = GovernanceRepository()
