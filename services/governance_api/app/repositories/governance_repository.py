from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, text


@dataclass
class _MemoryStore:
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    rulesets: dict[str, dict[str, Any]] = field(default_factory=dict)
    change_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    workpackage_publishes: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    observation_events: list[dict[str, Any]] = field(default_factory=list)
    observation_metrics: list[dict[str, Any]] = field(default_factory=list)
    observation_alerts: dict[str, dict[str, Any]] = field(default_factory=dict)


class GovernanceGateError(Exception):
    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class GovernanceRepository:
    def __init__(self) -> None:
        db_url = str(os.getenv("DATABASE_URL") or "").strip()

        if not db_url.startswith("postgresql://"):
            raise RuntimeError(
                "DATABASE_URL must be postgresql:// in persistent runtime mode."
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
        self._engine = None
        self._engine = self._build_engine()

    def _database_url(self) -> str | None:
        return os.getenv("DATABASE_URL")

    def _build_engine(self):
        pool_size = max(1, int(str(os.getenv("PG_POOL_SIZE") or "10")))
        max_overflow = max(0, int(str(os.getenv("PG_MAX_OVERFLOW") or "20")))
        return create_engine(
            self._database_url(),
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=1800,
            future=True,
        )

    def _get_engine(self):
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    def _db_enabled(self) -> bool:
        return True

    def _sql_now(self) -> str:
        return "NOW()"

    def _sql_json_cast(self, param: str) -> str:
        return f"CAST({param} AS jsonb)"

    def _execute(self, sql: str, params: dict[str, Any]) -> bool:
        if not self._db_enabled():
            return False
        # If DB is enabled, we expect strict consistency. Failures should propagate.
        engine = self._get_engine()
        with engine.begin() as conn:
            # Postgres search path setup
            if self._database_url().startswith("postgresql"):
                conn.execute(text("SET search_path TO governance, runtime, trust_meta, trust_data, audit, public"))
            conn.execute(text(sql), params)
        return True

    def _query(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not self._db_enabled():
            return []
        # If DB is enabled, we expect strict consistency. Failures should propagate.
        engine = self._get_engine()
        with engine.begin() as conn:
            # Postgres search path setup
            if self._database_url().startswith("postgresql"):
                conn.execute(text("SET search_path TO governance, runtime, trust_meta, trust_data, audit, public"))
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(item) for item in rows]

    def upsert_workpackage_publish(
        self,
        *,
        workpackage_id: str,
        version: str,
        status: str,
        evidence_ref: str,
        bundle_path: str = "",
        published_by: str = "",
        confirmation_user: str = "",
        confirmation_decision: str = "",
        confirmation_timestamp: str = "",
    ) -> dict[str, Any]:
        if not str(workpackage_id).strip():
            raise ValueError("workpackage_id is required")
        if not str(version).strip():
            raise ValueError("version is required")
        if not str(status).strip():
            raise ValueError("status is required")
        if not str(evidence_ref).strip():
            raise ValueError("evidence_ref is required")
        key = f"{workpackage_id}::{version}"
        existing = self._memory.workpackage_publishes.get(key)
        created_at = (existing or {}).get("created_at") or self._now_iso()
        published_at = (existing or {}).get("published_at") or self._now_iso()
        if str(status).lower() == "published":
            published_at = self._now_iso()
        item = {
            "publish_id": (existing or {}).get("publish_id") or f"wpp_{uuid4().hex[:16]}",
            "workpackage_id": workpackage_id,
            "version": version,
            "status": status,
            "evidence_ref": evidence_ref,
            "published_at": published_at,
            "bundle_path": bundle_path,
            "published_by": published_by,
            "confirmation_user": confirmation_user,
            "confirmation_decision": confirmation_decision,
            "confirmation_timestamp": confirmation_timestamp,
            "created_at": created_at,
            "updated_at": self._now_iso(),
        }
        self._memory.workpackage_publishes[key] = item
        now_func = self._sql_now()
        self._execute(
            f"""
            INSERT INTO runtime.publish_record (
                publish_id, workpackage_id, version, status, evidence_ref, published_at, bundle_path, published_by,
                confirmation_user, confirmation_decision, confirmation_timestamp, created_at, updated_at
            ) VALUES (
                :publish_id, :workpackage_id, :version, :status, :evidence_ref, :published_at, :bundle_path, :published_by,
                :confirmation_user, :confirmation_decision, :confirmation_timestamp, {now_func}, {now_func}
            )
            ON CONFLICT (workpackage_id, version)
            DO UPDATE SET
                status = EXCLUDED.status,
                evidence_ref = EXCLUDED.evidence_ref,
                published_at = EXCLUDED.published_at,
                bundle_path = EXCLUDED.bundle_path,
                published_by = EXCLUDED.published_by,
                confirmation_user = EXCLUDED.confirmation_user,
                confirmation_decision = EXCLUDED.confirmation_decision,
                confirmation_timestamp = EXCLUDED.confirmation_timestamp,
                updated_at = {now_func};
            """,
            {
                "publish_id": item["publish_id"],
                "workpackage_id": item["workpackage_id"],
                "version": item["version"],
                "status": item["status"],
                "evidence_ref": item["evidence_ref"],
                "published_at": item["published_at"],
                "bundle_path": item["bundle_path"],
                "published_by": item["published_by"],
                "confirmation_user": item["confirmation_user"],
                "confirmation_decision": item["confirmation_decision"],
                "confirmation_timestamp": item["confirmation_timestamp"],
            },
        )
        return dict(item)

    def get_workpackage_publish(self, workpackage_id: str, version: str) -> dict[str, Any] | None:
        key = f"{workpackage_id}::{version}"
        if self._db_enabled():
            rows = self._query(
                """
                SELECT publish_id, workpackage_id, version, status, evidence_ref, bundle_path, published_by,
                       published_at, confirmation_user, confirmation_decision, confirmation_timestamp, created_at, updated_at
                FROM runtime.publish_record
                WHERE workpackage_id = :workpackage_id AND version = :version
                LIMIT 1;
                """,
                {"workpackage_id": workpackage_id, "version": version},
            )
            if rows:
                row = self._serialize_record(rows[0])
                self._memory.workpackage_publishes[key] = dict(row)
                return dict(row)
            return None
        item = self._memory.workpackage_publishes.get(key)
        if item:
            return self._serialize_record(dict(item))
        return None

    def _serialize_record(self, item: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in item.items():
            if isinstance(value, datetime):
                out[key] = value.astimezone(timezone.utc).isoformat()
            elif value is None:
                out[key] = ""
            else:
                out[key] = value
        return out

    def _normalize_json_value(self, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
                try:
                    return json.loads(text)
                except Exception:
                    return value
        return value

    def list_workpackage_publishes(
        self,
        *,
        workpackage_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not str(workpackage_id).strip():
            raise ValueError("workpackage_id is required")
        normalized_status = str(status or "").strip().lower()
        safe_limit = max(1, min(int(limit), 1000))

        if self._db_enabled():
            sql = """
                SELECT publish_id, workpackage_id, version, status, evidence_ref, published_at, bundle_path, published_by,
                       confirmation_user, confirmation_decision, confirmation_timestamp, created_at, updated_at
                FROM runtime.publish_record
                WHERE workpackage_id = :workpackage_id
            """
            params: dict[str, Any] = {"workpackage_id": workpackage_id, "limit": safe_limit}
            if normalized_status:
                sql += " AND LOWER(status) = :status"
                params["status"] = normalized_status
            sql += " ORDER BY COALESCE(published_at, created_at) DESC, version DESC LIMIT :limit"
            rows = self._query(sql, params)
            db_items = [self._serialize_record(row) for row in rows]
            for row in db_items:
                key = f"{row.get('workpackage_id')}::{row.get('version')}"
                self._memory.workpackage_publishes[key] = dict(row)
            db_items.sort(key=lambda x: str(x.get("published_at") or x.get("created_at") or ""), reverse=True)
            return db_items[:safe_limit]

        memory_items = []
        for item in self._memory.workpackage_publishes.values():
            if str(item.get("workpackage_id") or "") != workpackage_id:
                continue
            if normalized_status and str(item.get("status") or "").lower() != normalized_status:
                continue
            memory_items.append(self._serialize_record(dict(item)))
        memory_items.sort(key=lambda x: str(x.get("published_at") or x.get("created_at") or ""), reverse=True)
        return memory_items[:safe_limit]

    def compare_workpackage_publish_versions(
        self,
        *,
        workpackage_id: str,
        baseline_version: str,
        candidate_version: str,
    ) -> dict[str, Any] | None:
        baseline = self.get_workpackage_publish(workpackage_id, baseline_version)
        candidate = self.get_workpackage_publish(workpackage_id, candidate_version)
        if (not baseline or not candidate) and str(workpackage_id).endswith(f"-{baseline_version}"):
            prefix = str(workpackage_id)[: -len(f"-{baseline_version}")]
            baseline_id = f"{prefix}-{baseline_version}"
            candidate_id = f"{prefix}-{candidate_version}"
            baseline = baseline or self.get_workpackage_publish(baseline_id, baseline_version)
            candidate = candidate or self.get_workpackage_publish(candidate_id, candidate_version)
        if not baseline or not candidate:
            return None
        baseline_item = self._serialize_record(dict(baseline))
        candidate_item = self._serialize_record(dict(candidate))
        compare_fields = [
            "status",
            "evidence_ref",
            "published_at",
            "bundle_path",
            "published_by",
            "confirmation_user",
            "confirmation_decision",
            "confirmation_timestamp",
        ]
        changed_fields = [field for field in compare_fields if baseline_item.get(field) != candidate_item.get(field)]
        return {
            "workpackage_id": workpackage_id,
            "baseline_version": baseline_version,
            "candidate_version": candidate_version,
            "baseline": baseline_item,
            "candidate": candidate_item,
            "changed_fields": changed_fields,
        }

    def create_task(
        self,
        task_id: str,
        batch_name: str,
        ruleset_id: str,
        status: str,
        queue_backend: str,
        queue_message: str,
        trace_id: str = "",
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
            "trace_id": trace_id,
        }
        now_func = self._sql_now()
        self._execute(
            f"""
            INSERT INTO governance.batch (batch_id, batch_name, status, created_at, updated_at)
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
            INSERT INTO governance.task_run (task_id, batch_id, status, error_message, runtime, trace_id, created_at, updated_at)
            VALUES (:task_id, :batch_id, :status, :error_message, :runtime, :trace_id, {now_func}, {now_func})
            ON CONFLICT (task_id)
            DO UPDATE SET batch_id = EXCLUDED.batch_id, status = EXCLUDED.status, error_message = EXCLUDED.error_message,
                          runtime = EXCLUDED.runtime, trace_id = EXCLUDED.trace_id, updated_at = {now_func};
            """,
            {
                "task_id": task_id,
                "batch_id": batch_id,
                "status": status,
                "error_message": queue_message,
                "runtime": queue_backend,
                "trace_id": trace_id,
            },
        )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        if self._db_enabled():
            rows = self._query(
                """
                SELECT
                    tr.task_id,
                    tr.batch_id,
                    tr.status,
                    tr.created_at,
                    b.batch_name,
                    tr.runtime AS queue_backend,
                    tr.error_message AS queue_message,
                    tr.trace_id
                FROM governance.task_run tr
                LEFT JOIN governance.batch b
                    ON b.batch_id = tr.batch_id
                WHERE tr.task_id = :task_id
                LIMIT 1;
                """,
                {"task_id": task_id},
            )
            if not rows:
                return None
            row = self._serialize_record(rows[0])
            self._memory.tasks[task_id] = dict(row)
            return dict(row)
        return self._memory.tasks.get(task_id)

    def list_tasks(self, *, status: str = "", limit: int = 200) -> list[dict[str, Any]]:
        safe_limit = max(1, min(1000, int(limit)))
        status_filter = str(status or "").strip().upper()
        if self._db_enabled():
            sql = """
                SELECT
                    tr.task_id,
                    tr.batch_id,
                    tr.status,
                    tr.created_at,
                    b.batch_name,
                    tr.runtime AS queue_backend,
                    tr.error_message AS queue_message,
                    tr.trace_id
                FROM governance.task_run tr
                LEFT JOIN governance.batch b
                    ON b.batch_id = tr.batch_id
                WHERE (:status = '' OR UPPER(tr.status) = :status)
                ORDER BY tr.created_at DESC
                LIMIT :limit;
            """
            rows = self._query(sql, {"status": status_filter, "limit": safe_limit})
            normalized = [self._serialize_record(item) for item in rows]
            for row in normalized:
                task_id = str(row.get("task_id") or "")
                if task_id:
                    self._memory.tasks[task_id] = dict(row)
            return normalized

        rows = [dict(item) for item in self._memory.tasks.values()]
        if status_filter:
            rows = [item for item in rows if str(item.get("status") or "").upper() == status_filter]
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return rows[:safe_limit]

    def set_task_status(self, task_id: str, status: str) -> None:
        if task_id in self._memory.tasks:
            self._memory.tasks[task_id]["status"] = status
        now_func = self._sql_now()
        self._execute(
            f"""
            UPDATE governance.task_run
            SET status = :status, updated_at = {now_func}, finished_at = CASE WHEN :status IN ('SUCCEEDED','FAILED','BLOCKED') THEN {now_func} ELSE finished_at END
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
        self.save_raw_records(task_id=task_id, raw_records=(raw_records or []))
        now_func = self._sql_now()
        evidence_cast = self._sql_json_cast(":evidence")

        for item in results:
            raw_id = item.get("raw_id")
            if not raw_id:
                continue
            evidence_json = json.dumps(item.get("evidence", {"items": []}), ensure_ascii=False)
            self._execute(
                f"""
                INSERT INTO governance.canonical_record (canonical_id, raw_id, canon_text, confidence, strategy, evidence, ruleset_version, created_at, updated_at)
                VALUES (:canonical_id, :raw_id, :canon_text, :confidence, :strategy, {evidence_cast}, :ruleset_version, {now_func}, {now_func})
                ON CONFLICT (canonical_id)
                DO UPDATE SET canon_text = EXCLUDED.canon_text, confidence = EXCLUDED.confidence,
                              strategy = EXCLUDED.strategy, evidence = EXCLUDED.evidence, updated_at = {now_func};
                """,
                {
                    "canonical_id": self._canonical_id(str(raw_id)),
                    "raw_id": raw_id,
                    "canon_text": item.get("canon_text", ""),
                    "confidence": float(item.get("confidence", 0.0)),
                    "strategy": item.get("strategy", "human_required"),
                    "evidence": evidence_json,
                    "ruleset_version": task.get("ruleset_id", "default"),
                },
            )

    def save_raw_records(self, *, task_id: str, raw_records: list[dict[str, Any]]) -> None:
        if not raw_records:
            return
        task = self._memory.tasks.get(task_id, {})
        batch_id = task.get("batch_id", task_id)
        now_func = self._sql_now()
        for raw_input in raw_records:
            raw_id = raw_input.get("raw_id")
            if not raw_id:
                continue
            raw_text = raw_input.get("raw_text") or ""
            self._execute(
                f"""
                INSERT INTO governance.raw_record (raw_id, batch_id, raw_text, province, city, district, street, detail, raw_hash, ingested_at)
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

    def get_results(self, task_id: str) -> list[dict[str, Any]]:
        if self._db_enabled():
            rows = self._query(
                """
                SELECT
                    raw.raw_id,
                    canon.canon_text,
                    canon.confidence,
                    canon.strategy,
                    canon.evidence
                FROM governance.task_run tr
                JOIN governance.raw_record raw
                    ON raw.batch_id = tr.batch_id
                JOIN governance.canonical_record canon
                    ON canon.raw_id = raw.raw_id
                WHERE tr.task_id = :task_id
                ORDER BY raw.raw_id ASC;
                """,
                {"task_id": task_id},
            )
            normalized: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["evidence"] = self._normalize_json_value(item.get("evidence"))
                normalized.append(item)
            self._memory.results[task_id] = normalized
            return normalized
        return self._memory.results.get(task_id, [])

    def list_raw_records_by_task(self, task_id: str) -> list[dict[str, Any]]:
        if self._db_enabled():
            rows = self._query(
                """
                SELECT raw.raw_id, raw.raw_text
                FROM governance.task_run tr
                JOIN governance.raw_record raw
                    ON raw.batch_id = tr.batch_id
                WHERE tr.task_id = :task_id
                ORDER BY raw.raw_id ASC;
                """,
                {"task_id": task_id},
            )
            normalized = [{"raw_id": str(row.get("raw_id") or ""), "raw_text": str(row.get("raw_text") or "")} for row in rows]
            return normalized
        records: list[dict[str, Any]] = []
        for item in self._memory.results.get(task_id, []):
            records.append({"raw_id": str(item.get("raw_id") or ""), "raw_text": str(item.get("canon_text") or "")})
        return records

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
            INSERT INTO governance.review (review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at)
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
        if self._db_enabled():
            rows = self._query(
                """
                SELECT raw_id, review_status, final_canon_text, reviewer, comment
                FROM governance.review
                WHERE review_id = :review_id
                ORDER BY COALESCE(reviewed_at, updated_at, created_at) DESC
                LIMIT 1;
                """,
                {"review_id": f"review_{task_id}"},
            )
            if not rows:
                return None
            row = self._serialize_record(rows[0])
            self._memory.reviews[task_id] = dict(row)
            return dict(row)
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
            UPDATE governance.ruleset
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
                UPDATE governance.canonical_record
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
        if self._db_enabled():
            rows = self._query(
                """
                SELECT ruleset_id, version, is_active, config_json
                FROM governance.ruleset
                WHERE ruleset_id = :ruleset_id
                LIMIT 1;
                """,
                {"ruleset_id": ruleset_id},
            )
            if not rows:
                return None
            row = self._serialize_record(rows[0])
            row["config_json"] = self._normalize_json_value(row.get("config_json"))
            self._memory.rulesets[ruleset_id] = dict(row)
            return dict(row)
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
                    FROM governance.review
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
                FROM governance.task_run tr
                JOIN governance.raw_record raw
                    ON raw.batch_id = tr.batch_id
                JOIN governance.canonical_record canon
                    ON canon.raw_id = raw.raw_id
                LEFT JOIN review_latest rl
                    ON rl.raw_id = raw.raw_id
                WHERE (
                        canon.strategy IN ('human_required', 'human_rejected', 'low_confidence')
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
                INSERT INTO governance.review (review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at)
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
                    UPDATE governance.canonical_record
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
                    UPDATE governance.canonical_record
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
                    UPDATE governance.canonical_record
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
                UPDATE governance.task_run
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

    def _canonical_id(self, raw_id: str) -> str:
        raw = str(raw_id or "").strip()
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        return f"canon_{raw[:40]}_{digest}"

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
            INSERT INTO audit.event_log (event_id, event_type, caller, payload, related_change_id, created_at)
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

    def record_observation_event(
        self,
        *,
        source_service: str,
        event_type: str,
        status: str,
        trace_id: str,
        severity: str = "info",
        span_id: str = "",
        task_id: str = "",
        workpackage_id: str = "",
        ruleset_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not str(trace_id).strip():
            raise ValueError("trace_id is required")
        event = {
            "event_id": f"obsevt_{uuid4().hex[:12]}",
            "trace_id": str(trace_id),
            "span_id": str(span_id or ""),
            "source_service": str(source_service or "unknown"),
            "event_type": str(event_type or "unknown"),
            "status": str(status or "unknown"),
            "severity": str(severity or "info"),
            "task_id": str(task_id or ""),
            "workpackage_id": str(workpackage_id or ""),
            "ruleset_id": str(ruleset_id or ""),
            "payload_json": payload or {},
            "created_at": self._now_iso(),
        }
        self._memory.observation_events.append(event)
        now_func = self._sql_now()
        payload_cast = self._sql_json_cast(":payload_json")
        self._execute(
            f"""
            INSERT INTO governance.observation_event (
                event_id, trace_id, span_id, source_service, event_type, status, severity,
                task_id, workpackage_id, ruleset_id, payload_json, created_at
            ) VALUES (
                :event_id, :trace_id, :span_id, :source_service, :event_type, :status, :severity,
                :task_id, :workpackage_id, :ruleset_id, {payload_cast}, {now_func}
            );
            """,
            {
                "event_id": event["event_id"],
                "trace_id": event["trace_id"],
                "span_id": event["span_id"],
                "source_service": event["source_service"],
                "event_type": event["event_type"],
                "status": event["status"],
                "severity": event["severity"],
                "task_id": event["task_id"],
                "workpackage_id": event["workpackage_id"],
                "ruleset_id": event["ruleset_id"],
                "payload_json": json.dumps(event["payload_json"], ensure_ascii=False),
            },
        )
        return dict(event)

    def list_observation_events(
        self,
        *,
        trace_id: str = "",
        task_id: str = "",
        status: str = "",
        event_type: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = [dict(item) for item in self._memory.observation_events]
        if self._db_enabled():
            db_rows = self._query(
                """
                SELECT event_id, trace_id, span_id, source_service, event_type, status, severity,
                       task_id, workpackage_id, ruleset_id, payload_json, created_at
                FROM governance.observation_event
                ORDER BY created_at DESC
                LIMIT :limit
                """,
                {"limit": safe_limit},
            )
            if db_rows:
                rows = []
                for item in db_rows:
                    normalized = self._serialize_record(item)
                    normalized["payload_json"] = self._normalize_json_value(normalized.get("payload_json") or {})
                    rows.append(normalized)
        if trace_id:
            rows = [item for item in rows if str(item.get("trace_id") or "") == trace_id]
        if task_id:
            rows = [item for item in rows if str(item.get("task_id") or "") == task_id]
        if status:
            rows = [item for item in rows if str(item.get("status") or "").lower() == str(status).lower()]
        if event_type:
            rows = [item for item in rows if str(item.get("event_type") or "") == event_type]
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return rows[:safe_limit]

    def get_trace_replay(self, trace_id: str, limit: int = 500) -> list[dict[str, Any]]:
        items = self.list_observation_events(trace_id=trace_id, limit=limit)
        items.sort(key=lambda item: str(item.get("created_at") or ""))
        return items

    def upsert_observation_metric(
        self,
        *,
        metric_name: str,
        metric_value: float,
        labels: dict[str, Any] | None = None,
        window_start: str = "",
        window_end: str = "",
    ) -> dict[str, Any]:
        item = {
            "metric_id": f"obsmet_{uuid4().hex[:12]}",
            "metric_name": str(metric_name or "").strip(),
            "metric_value": float(metric_value),
            "labels_json": labels or {},
            "window_start": str(window_start or ""),
            "window_end": str(window_end or ""),
            "created_at": self._now_iso(),
        }
        if not item["metric_name"]:
            raise ValueError("metric_name is required")
        self._memory.observation_metrics.append(item)
        now_func = self._sql_now()
        labels_cast = self._sql_json_cast(":labels_json")
        self._execute(
            f"""
            INSERT INTO governance.observation_metric (
                metric_id, metric_name, metric_value, labels_json, window_start, window_end, created_at
            ) VALUES (
                :metric_id, :metric_name, :metric_value, {labels_cast}, :window_start, :window_end, {now_func}
            );
            """,
            {
                "metric_id": item["metric_id"],
                "metric_name": item["metric_name"],
                "metric_value": item["metric_value"],
                "labels_json": json.dumps(item["labels_json"], ensure_ascii=False),
                "window_start": item["window_start"] or None,
                "window_end": item["window_end"] or None,
            },
        )
        return dict(item)

    def query_observation_metric_series(self, metric_name: str, limit: int = 200) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = [dict(item) for item in self._memory.observation_metrics if str(item.get("metric_name") or "") == metric_name]
        if self._db_enabled():
            db_rows = self._query(
                """
                SELECT metric_id, metric_name, metric_value, labels_json, window_start, window_end, created_at
                FROM governance.observation_metric
                WHERE metric_name = :metric_name
                ORDER BY COALESCE(window_end, created_at) DESC
                LIMIT :limit
                """,
                {"metric_name": metric_name, "limit": safe_limit},
            )
            if db_rows:
                rows = []
                for item in db_rows:
                    normalized = self._serialize_record(item)
                    normalized["labels_json"] = self._normalize_json_value(normalized.get("labels_json") or {})
                    rows.append(normalized)
        rows.sort(key=lambda item: str(item.get("window_end") or item.get("created_at") or ""), reverse=True)
        return rows[:safe_limit]

    def create_observation_alert(
        self,
        *,
        alert_rule: str,
        severity: str,
        trigger_value: float,
        threshold_value: float,
        trace_id: str = "",
        task_id: str = "",
        workpackage_id: str = "",
        owner: str = "",
    ) -> dict[str, Any]:
        if not str(alert_rule).strip():
            raise ValueError("alert_rule is required")
        item = {
            "alert_id": f"obsalt_{uuid4().hex[:12]}",
            "alert_rule": str(alert_rule),
            "severity": str(severity or "warn"),
            "status": "open",
            "trigger_value": float(trigger_value),
            "threshold_value": float(threshold_value),
            "trace_id": str(trace_id or ""),
            "task_id": str(task_id or ""),
            "workpackage_id": str(workpackage_id or ""),
            "owner": str(owner or ""),
            "ack_by": "",
            "ack_at": None,
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }
        self._memory.observation_alerts[item["alert_id"]] = item
        now_func = self._sql_now()
        self._execute(
            f"""
            INSERT INTO governance.alert_event (
                alert_id, alert_rule, severity, status, trigger_value, threshold_value,
                trace_id, task_id, workpackage_id, owner, ack_by, ack_at, created_at, updated_at
            ) VALUES (
                :alert_id, :alert_rule, :severity, :status, :trigger_value, :threshold_value,
                :trace_id, :task_id, :workpackage_id, :owner, :ack_by, :ack_at, {now_func}, {now_func}
            );
            """,
            item,
        )
        return dict(item)

    def list_observation_alerts(self, status: str = "", limit: int = 200) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = [dict(item) for item in self._memory.observation_alerts.values()]
        if self._db_enabled():
            db_rows = self._query(
                """
                SELECT alert_id, alert_rule, severity, status, trigger_value, threshold_value, trace_id,
                       task_id, workpackage_id, owner, ack_by, ack_at, created_at, updated_at
                FROM governance.alert_event
                ORDER BY created_at DESC
                LIMIT :limit
                """,
                {"limit": safe_limit},
            )
            if db_rows:
                rows = [self._serialize_record(item) for item in db_rows]
        if status:
            rows = [item for item in rows if str(item.get("status") or "").lower() == str(status).lower()]
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return rows[:safe_limit]

    def ack_observation_alert(self, alert_id: str, actor: str) -> dict[str, Any] | None:
        item = self._memory.observation_alerts.get(alert_id)
        if not item and self._db_enabled():
            rows = self._query(
                """
                SELECT alert_id, alert_rule, severity, status, trigger_value, threshold_value, trace_id,
                       task_id, workpackage_id, owner, ack_by, ack_at, created_at, updated_at
                FROM governance.alert_event
                WHERE alert_id = :alert_id
                LIMIT 1
                """,
                {"alert_id": alert_id},
            )
            if rows:
                item = self._serialize_record(rows[0])
                self._memory.observation_alerts[alert_id] = dict(item)
        if not item:
            return None
        item["status"] = "acked"
        item["ack_by"] = str(actor or "")
        item["ack_at"] = self._now_iso()
        item["updated_at"] = self._now_iso()
        now_func = self._sql_now()
        self._execute(
            f"""
            UPDATE governance.alert_event
            SET status = :status, ack_by = :ack_by, ack_at = :ack_at, updated_at = {now_func}
            WHERE alert_id = :alert_id;
            """,
            {
                "alert_id": alert_id,
                "status": item["status"],
                "ack_by": item["ack_by"],
                "ack_at": item["ack_at"],
            },
        )
        return dict(item)

    def get_observability_snapshot(self, env: str = "dev") -> dict[str, Any]:
        tasks = list(self._memory.tasks.values())
        total_tasks = len(tasks)
        succeeded = sum(1 for item in tasks if str(item.get("status") or "").upper() == "SUCCEEDED")
        blocked = sum(1 for item in tasks if str(item.get("status") or "").upper() == "BLOCKED")
        failed = sum(1 for item in tasks if str(item.get("status") or "").upper() == "FAILED")
        success_rate = float(succeeded) / float(total_tasks) if total_tasks else 0.0
        open_alerts = self.list_observation_alerts(status="open", limit=500)
        latest_metrics = self._memory.observation_metrics[-20:]
        return {
            "environment": str(env or "dev"),
            "kpis": {
                "total_tasks": total_tasks,
                "success_rate": round(success_rate, 6),
                "blocked_tasks": blocked,
                "failed_tasks": failed,
            },
            "metrics": [dict(item) for item in latest_metrics],
            "alerts": open_alerts,
        }

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
            INSERT INTO governance.ruleset (ruleset_id, version, is_active, config_json, created_at, updated_at)
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
            INSERT INTO governance.change_request (
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
            UPDATE governance.change_request
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
        self._execute("UPDATE governance.ruleset SET is_active = FALSE WHERE is_active = TRUE;", {})
        self._execute(
            f"UPDATE governance.ruleset SET is_active = TRUE, updated_at = {now_func} WHERE ruleset_id = :ruleset_id;",
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
        if self._db_enabled():
            sql = """
                SELECT event_id, event_type, caller, payload, related_change_id, created_at
                FROM audit.event_log
            """
            params: dict[str, Any] = {}
            if related_change_id:
                sql += " WHERE related_change_id = :related_change_id"
                params["related_change_id"] = related_change_id
            sql += " ORDER BY created_at ASC LIMIT 20000"
            rows = self._query(sql, params)
            normalized: list[dict[str, Any]] = []
            for row in rows:
                item = self._serialize_record(row)
                item["payload"] = self._normalize_json_value(item.get("payload") or {})
                normalized.append(item)
            # Keep memory cache warm for in-process reads.
            self._memory.audit_events = list(normalized)
            return normalized
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

    def log_blocked_confirmation(
        self,
        event_type: str,
        caller: str,
        payload: dict[str, Any],
        related_change_id: str | None = None,
    ) -> dict[str, Any]:
        required = ["reason", "confirmation_user", "confirmation_decision", "confirmation_timestamp"]
        missing = [field for field in required if not str(payload.get(field) or "").strip()]
        if missing:
            raise ValueError(f"missing blocked confirmation fields: {','.join(missing)}")
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
        self._execute("UPDATE governance.ruleset SET is_active = FALSE WHERE is_active = TRUE;", {})
        self._execute(
            f"UPDATE governance.ruleset SET is_active = TRUE, updated_at = {now_func} WHERE ruleset_id = :ruleset_id;",
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
