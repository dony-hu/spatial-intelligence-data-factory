from __future__ import annotations

import json
import os
from typing import Any, Optional


class MetaDbPersister:
    def __init__(self) -> None:
        # Unified PG mode: use DATABASE_URL as the primary DSN.
        self._dsn = os.getenv("DATABASE_URL") or os.getenv("TRUST_META_DATABASE_URL")

    def enabled(self) -> bool:
        return bool(self._dsn and str(self._dsn).startswith("postgresql"))

    def _engine(self):
        from sqlalchemy import create_engine

        return create_engine(self._dsn)

    def upsert_source(self, namespace: str, source_id: str, payload: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.source_registry
                    (namespace_id, source_id, name, category, trust_level, license, entrypoint, update_frequency,
                     fetch_method, parser_profile, validator_profile, enabled, allowed_use_notes, access_mode,
                     robots_tos_flags, created_at, updated_at)
                    VALUES
                    (:namespace_id, :source_id, :name, :category, :trust_level, :license, :entrypoint, :update_frequency,
                     :fetch_method, CAST(:parser_profile AS jsonb), CAST(:validator_profile AS jsonb), :enabled,
                     :allowed_use_notes, :access_mode, CAST(:robots_tos_flags AS jsonb), NOW(), NOW())
                    ON CONFLICT (namespace_id, source_id)
                    DO UPDATE SET
                      name = EXCLUDED.name,
                      category = EXCLUDED.category,
                      trust_level = EXCLUDED.trust_level,
                      license = EXCLUDED.license,
                      entrypoint = EXCLUDED.entrypoint,
                      update_frequency = EXCLUDED.update_frequency,
                      fetch_method = EXCLUDED.fetch_method,
                      parser_profile = EXCLUDED.parser_profile,
                      validator_profile = EXCLUDED.validator_profile,
                      enabled = EXCLUDED.enabled,
                      allowed_use_notes = EXCLUDED.allowed_use_notes,
                      access_mode = EXCLUDED.access_mode,
                      robots_tos_flags = EXCLUDED.robots_tos_flags,
                      updated_at = NOW()
                    """
                ),
                {
                    "namespace_id": namespace,
                    "source_id": source_id,
                    "name": payload.get("name"),
                    "category": payload.get("category"),
                    "trust_level": payload.get("trust_level"),
                    "license": payload.get("license"),
                    "entrypoint": payload.get("entrypoint"),
                    "update_frequency": payload.get("update_frequency"),
                    "fetch_method": payload.get("fetch_method"),
                    "parser_profile": json.dumps(payload.get("parser_profile") or {}, ensure_ascii=False),
                    "validator_profile": json.dumps(payload.get("validator_profile") or {}, ensure_ascii=False),
                    "enabled": bool(payload.get("enabled", True)),
                    "allowed_use_notes": payload.get("allowed_use_notes"),
                    "access_mode": payload.get("access_mode"),
                    "robots_tos_flags": json.dumps(payload.get("robots_tos_flags") or {}, ensure_ascii=False),
                },
            )

    def get_source(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, source_id, name, category, trust_level, license, entrypoint, update_frequency,
                           fetch_method, parser_profile, validator_profile, enabled, allowed_use_notes, access_mode,
                           robots_tos_flags, created_at, updated_at
                    FROM trust_meta.source_registry
                    WHERE namespace_id=:namespace_id AND source_id=:source_id
                    """
                ),
                {"namespace_id": namespace, "source_id": source_id},
            ).mappings().first()
            if not row:
                return None
            return dict(row)

    def upsert_source_schedule(self, namespace: str, source_id: str, payload: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.source_schedule
                    (namespace_id, source_id, schedule_type, schedule_spec, window_policy, enabled)
                    VALUES
                    (:namespace_id, :source_id, :schedule_type, :schedule_spec, CAST(:window_policy AS jsonb), :enabled)
                    ON CONFLICT (namespace_id, source_id)
                    DO UPDATE SET
                      schedule_type = EXCLUDED.schedule_type,
                      schedule_spec = EXCLUDED.schedule_spec,
                      window_policy = EXCLUDED.window_policy,
                      enabled = EXCLUDED.enabled
                    """
                ),
                {
                    "namespace_id": namespace,
                    "source_id": source_id,
                    "schedule_type": payload.get("schedule_type"),
                    "schedule_spec": payload.get("schedule_spec"),
                    "window_policy": json.dumps(payload.get("window_policy") or {}, ensure_ascii=False),
                    "enabled": bool(payload.get("enabled", True)),
                },
            )

    def get_source_schedule(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, source_id, schedule_type, schedule_spec, window_policy, enabled
                    FROM trust_meta.source_schedule
                    WHERE namespace_id=:namespace_id AND source_id=:source_id
                    """
                ),
                {"namespace_id": namespace, "source_id": source_id},
            ).mappings().first()
            return dict(row) if row else None

    def insert_snapshot(self, namespace: str, snapshot: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.source_snapshot
                    (namespace_id, snapshot_id, source_id, version_tag, fetched_at, etag, last_modified,
                     content_hash, raw_uri, parsed_uri, parsed_payload, status, row_count)
                    VALUES
                    (:namespace_id, :snapshot_id, :source_id, :version_tag, :fetched_at, :etag, :last_modified,
                     :content_hash, :raw_uri, :parsed_uri, CAST(:parsed_payload AS jsonb), :status, :row_count)
                    ON CONFLICT (snapshot_id)
                    DO UPDATE SET
                      source_id = EXCLUDED.source_id,
                      version_tag = EXCLUDED.version_tag,
                      fetched_at = EXCLUDED.fetched_at,
                      etag = EXCLUDED.etag,
                      last_modified = EXCLUDED.last_modified,
                      content_hash = EXCLUDED.content_hash,
                      raw_uri = EXCLUDED.raw_uri,
                      parsed_uri = EXCLUDED.parsed_uri,
                      parsed_payload = EXCLUDED.parsed_payload,
                      status = EXCLUDED.status,
                      row_count = EXCLUDED.row_count
                    """
                ),
                {
                    "namespace_id": namespace,
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "source_id": snapshot.get("source_id"),
                    "version_tag": snapshot.get("version_tag"),
                    "fetched_at": snapshot.get("fetched_at"),
                    "etag": snapshot.get("etag"),
                    "last_modified": snapshot.get("last_modified"),
                    "content_hash": snapshot.get("content_hash"),
                    "raw_uri": snapshot.get("raw_uri"),
                    "parsed_uri": snapshot.get("parsed_uri"),
                    "parsed_payload": json.dumps(snapshot.get("payload") or {}, ensure_ascii=False),
                    "status": snapshot.get("status"),
                    "row_count": int(snapshot.get("row_count") or 0),
                },
            )

    def get_snapshot(self, namespace: str, snapshot_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, snapshot_id, source_id, version_tag, fetched_at, etag, last_modified,
                           content_hash, raw_uri, parsed_uri, parsed_payload, status, row_count
                    FROM trust_meta.source_snapshot
                    WHERE namespace_id=:namespace_id AND snapshot_id=:snapshot_id
                    """
                ),
                {"namespace_id": namespace, "snapshot_id": snapshot_id},
            ).mappings().first()
            if not row:
                return None
            result = dict(row)
            payload = result.get("parsed_payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            result["payload"] = payload or {}
            return result

    def get_latest_snapshot(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, snapshot_id, source_id, version_tag, fetched_at, etag, last_modified,
                           content_hash, raw_uri, parsed_uri, parsed_payload, status, row_count
                    FROM trust_meta.source_snapshot
                    WHERE namespace_id=:namespace_id AND source_id=:source_id
                    ORDER BY fetched_at DESC
                    LIMIT 1
                    """
                ),
                {"namespace_id": namespace, "source_id": source_id},
            ).mappings().first()
            if not row:
                return None
            result = dict(row)
            payload = result.get("parsed_payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            result["payload"] = payload or {}
            return result

    def upsert_quality_report(self, namespace: str, snapshot_id: str, report: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.snapshot_quality_report
                    (namespace_id, snapshot_id, report_json, quality_score, validator_version)
                    VALUES
                    (:namespace_id, :snapshot_id, CAST(:report_json AS jsonb), :quality_score, :validator_version)
                    ON CONFLICT (namespace_id, snapshot_id)
                    DO UPDATE SET
                      report_json = EXCLUDED.report_json,
                      quality_score = EXCLUDED.quality_score,
                      validator_version = EXCLUDED.validator_version
                    """
                ),
                {
                    "namespace_id": namespace,
                    "snapshot_id": snapshot_id,
                    "report_json": json.dumps(report.get("report_json") or {}, ensure_ascii=False),
                    "quality_score": int(report.get("quality_score") or 0),
                    "validator_version": report.get("validator_version") or "v0.1",
                },
            )

    def get_quality_report(self, namespace: str, snapshot_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, snapshot_id, report_json, quality_score, validator_version
                    FROM trust_meta.snapshot_quality_report
                    WHERE namespace_id=:namespace_id AND snapshot_id=:snapshot_id
                    """
                ),
                {"namespace_id": namespace, "snapshot_id": snapshot_id},
            ).mappings().first()
            return dict(row) if row else None

    def upsert_diff_report(self, namespace: str, report: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.snapshot_diff_report
                    (namespace_id, base_snapshot_id, new_snapshot_id, diff_json, diff_severity)
                    VALUES
                    (:namespace_id, :base_snapshot_id, :new_snapshot_id, CAST(:diff_json AS jsonb), :diff_severity)
                    ON CONFLICT (namespace_id, new_snapshot_id)
                    DO UPDATE SET
                      base_snapshot_id = EXCLUDED.base_snapshot_id,
                      diff_json = EXCLUDED.diff_json,
                      diff_severity = EXCLUDED.diff_severity
                    """
                ),
                {
                    "namespace_id": namespace,
                    "base_snapshot_id": report.get("base_snapshot_id"),
                    "new_snapshot_id": report.get("new_snapshot_id"),
                    "diff_json": json.dumps(report.get("diff_json") or {}, ensure_ascii=False),
                    "diff_severity": report.get("diff_severity") or "low",
                },
            )

    def get_diff_report(self, namespace: str, snapshot_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, base_snapshot_id, new_snapshot_id, diff_json, diff_severity
                    FROM trust_meta.snapshot_diff_report
                    WHERE namespace_id=:namespace_id AND new_snapshot_id=:snapshot_id
                    """
                ),
                {"namespace_id": namespace, "snapshot_id": snapshot_id},
            ).mappings().first()
            return dict(row) if row else None

    def upsert_active_release(self, namespace: str, source_id: str, row: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.active_release
                    (namespace_id, source_id, active_snapshot_id, activated_by, activated_at, activation_note)
                    VALUES
                    (:namespace_id, :source_id, :active_snapshot_id, :activated_by, :activated_at, :activation_note)
                    ON CONFLICT (namespace_id, source_id)
                    DO UPDATE SET
                      active_snapshot_id = EXCLUDED.active_snapshot_id,
                      activated_by = EXCLUDED.activated_by,
                      activated_at = EXCLUDED.activated_at,
                      activation_note = EXCLUDED.activation_note
                    """
                ),
                {
                    "namespace_id": namespace,
                    "source_id": source_id,
                    "active_snapshot_id": row.get("active_snapshot_id"),
                    "activated_by": row.get("activated_by"),
                    "activated_at": row.get("activated_at"),
                    "activation_note": row.get("activation_note"),
                },
            )

    def get_active_release(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled():
            return None
        from sqlalchemy import text

        with self._engine().begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT namespace_id, source_id, active_snapshot_id, activated_by, activated_at, activation_note
                    FROM trust_meta.active_release
                    WHERE namespace_id=:namespace_id AND source_id=:source_id
                    """
                ),
                {"namespace_id": namespace, "source_id": source_id},
            ).mappings().first()
            return dict(row) if row else None

    def append_audit_event(self, namespace: str, event: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.audit_event
                    (namespace_id, event_id, actor, action, target_ref, event_json, created_at)
                    VALUES
                    (:namespace_id, :event_id, :actor, :action, :target_ref, CAST(:event_json AS jsonb), :created_at)
                    ON CONFLICT (event_id) DO NOTHING
                    """
                ),
                {
                    "namespace_id": namespace,
                    "event_id": event.get("event_id"),
                    "actor": event.get("actor"),
                    "action": event.get("action"),
                    "target_ref": event.get("target_ref"),
                    "event_json": json.dumps(event.get("event_json") or {}, ensure_ascii=False),
                    "created_at": event.get("created_at"),
                },
            )

    def list_audit_events(self, namespace: str) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        from sqlalchemy import text

        with self._engine().begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT namespace_id, event_id, actor, action, target_ref, event_json, created_at
                    FROM trust_meta.audit_event
                    WHERE namespace_id=:namespace_id
                    ORDER BY created_at ASC
                    """
                ),
                {"namespace_id": namespace},
            ).mappings().all()
            return [dict(x) for x in rows]

    def insert_validation_replay_run(self, namespace: str, replay_run: dict[str, Any]) -> None:
        if not self.enabled():
            return
        from sqlalchemy import text

        with self._engine().begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO trust_meta.validation_replay_run
                    (namespace_id, replay_id, snapshot_id, request_payload, replay_result, schema_version, created_at)
                    VALUES
                    (:namespace_id, :replay_id, :snapshot_id, CAST(:request_payload AS jsonb), CAST(:replay_result AS jsonb), :schema_version, :created_at)
                    ON CONFLICT (replay_id)
                    DO UPDATE SET
                      snapshot_id = EXCLUDED.snapshot_id,
                      request_payload = EXCLUDED.request_payload,
                      replay_result = EXCLUDED.replay_result,
                      schema_version = EXCLUDED.schema_version,
                      created_at = EXCLUDED.created_at
                    """
                ),
                {
                    "namespace_id": namespace,
                    "replay_id": replay_run.get("replay_id"),
                    "snapshot_id": replay_run.get("snapshot_id"),
                    "request_payload": json.dumps(replay_run.get("request_payload") or {}, ensure_ascii=False),
                    "replay_result": json.dumps(replay_run.get("replay_result") or {}, ensure_ascii=False),
                    "schema_version": replay_run.get("schema_version") or "trust.validation.v1",
                    "created_at": replay_run.get("created_at"),
                },
            )

    def list_validation_replay_runs(
        self,
        namespace: str,
        snapshot_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        from sqlalchemy import text

        safe_limit = max(1, min(int(limit), 200))
        with self._engine().begin() as conn:
            if snapshot_id:
                rows = conn.execute(
                    text(
                        """
                        SELECT namespace_id, replay_id, snapshot_id, request_payload, replay_result, schema_version, created_at
                        FROM trust_meta.validation_replay_run
                        WHERE namespace_id=:namespace_id AND snapshot_id=:snapshot_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"namespace_id": namespace, "snapshot_id": snapshot_id, "limit": safe_limit},
                ).mappings().all()
            else:
                rows = conn.execute(
                    text(
                        """
                        SELECT namespace_id, replay_id, snapshot_id, request_payload, replay_result, schema_version, created_at
                        FROM trust_meta.validation_replay_run
                        WHERE namespace_id=:namespace_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"namespace_id": namespace, "limit": safe_limit},
                ).mappings().all()

            result: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                for key in ("request_payload", "replay_result"):
                    value = item.get(key)
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except Exception:
                            value = {}
                    item[key] = value or {}
                result.append(item)
            return result
