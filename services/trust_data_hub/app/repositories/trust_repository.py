from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from services.trust_data_hub.app.execution.fetchers import fetch_payload
from services.trust_data_hub.app.execution.parsers import parse_raw_payload
from services.trust_data_hub.app.repositories.metadb_persister import MetaDbPersister
from services.trust_data_hub.app.repositories.trustdb_persister import TrustDbPersister

VALIDATION_SCHEMA_VERSION = "trust.validation.v1"

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _source_key(namespace: str, source_id: str) -> str:
    return f"{namespace}::{source_id}"


FIXTURE_DATASETS: dict[str, dict[str, Any]] = {
    "admin_v1": {
        "admin_division": [
            {"adcode": "330000", "name": "浙江省", "level": "province", "parent_adcode": None, "name_aliases": ["浙"]},
            {"adcode": "330100", "name": "杭州市", "level": "city", "parent_adcode": "330000", "name_aliases": ["杭州"]},
            {"adcode": "330106", "name": "西湖区", "level": "district", "parent_adcode": "330100", "name_aliases": ["西湖"]},
        ],
        "roads": [
            {"road_id": "r-330106-001", "name": "文三路", "normalized_name": "文三路", "admin_adcode": "330106"}
        ],
        "pois": [
            {
                "poi_id": "p-330106-001",
                "name": "西溪银泰城",
                "normalized_name": "西溪银泰城",
                "category": "mall",
                "admin_adcode": "330106",
                "centroid": "120.083,30.286",
            }
        ],
        "places": [
            {
                "place_id": "pl-330106-001",
                "name": "西溪",
                "normalized_name": "西溪",
                "type": "place",
                "admin_adcode": "330106",
                "confidence_hint": 0.85,
            }
        ],
    },
    "admin_v2": {
        "admin_division": [
            {"adcode": "330000", "name": "浙江省", "level": "province", "parent_adcode": None, "name_aliases": ["浙"]},
            {"adcode": "330100", "name": "杭州市", "level": "city", "parent_adcode": "330000", "name_aliases": ["杭州"]},
            {"adcode": "330110", "name": "余杭区", "level": "district", "parent_adcode": "330100", "name_aliases": ["余杭"]},
        ],
        "roads": [
            {"road_id": "r-330110-001", "name": "良睦路", "normalized_name": "良睦路", "admin_adcode": "330110"}
        ],
        "pois": [
            {
                "poi_id": "p-330110-001",
                "name": "未来科技城",
                "normalized_name": "未来科技城",
                "category": "business",
                "admin_adcode": "330110",
                "centroid": "120.020,30.285",
            }
        ],
        "places": [
            {
                "place_id": "pl-330110-001",
                "name": "未来科技城",
                "normalized_name": "未来科技城",
                "type": "place",
                "admin_adcode": "330110",
                "confidence_hint": 0.75,
            }
        ],
    },
    "osm_china_v1": {
        "admin_division": [],
        "roads": [
            {"road_id": "osm-r-001", "name": "中关村大街", "normalized_name": "中关村大街", "admin_adcode": "110108"}
        ],
        "pois": [
            {
                "poi_id": "osm-p-001",
                "name": "清华大学",
                "normalized_name": "清华大学",
                "category": "education",
                "admin_adcode": "110108",
                "centroid": "116.326,40.003",
            }
        ],
        "places": [],
    },
}


@dataclass
class _MemoryStore:
    source_registry: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_schedule: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    diff_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    published_snapshots: set[str] = field(default_factory=set)
    active_release: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    admin_division: list[dict[str, Any]] = field(default_factory=list)
    road_index: list[dict[str, Any]] = field(default_factory=list)
    poi_index: list[dict[str, Any]] = field(default_factory=list)
    place_name_index: list[dict[str, Any]] = field(default_factory=list)
    validation_replay_runs: list[dict[str, Any]] = field(default_factory=list)


class TrustRepository:
    def __init__(self) -> None:
        self._memory = _MemoryStore()
        self._metadb = MetaDbPersister()
        self._trustdb = TrustDbPersister()
        if not self._metadb.enabled():
            raise RuntimeError(
                "TRUST_META_DATABASE_URL/DATABASE_URL must be postgresql:// in PG-only mode for Trust Data Hub."
            )
        if not self._trustdb.enabled():
            raise RuntimeError(
                "TRUST_TRUSTDB_DSN/DATABASE_URL must be postgresql:// in PG-only mode for Trust Data Hub."
            )

    def _append_audit(
        self,
        namespace: str,
        actor: str,
        action: str,
        target_ref: str,
        event_json: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "event_id": str(uuid4()),
            "namespace": namespace,
            "actor": actor,
            "action": action,
            "target_ref": target_ref,
            "event_json": {"namespace": namespace, **event_json},
            "created_at": _utc_now().isoformat(),
        }
        self._memory.audit_events.append(event)
        if self._metadb.enabled():
            try:
                self._metadb.append_audit_event(namespace, event)
            except Exception:
                pass
        return event

    def upsert_source(self, namespace: str, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = _source_key(namespace, source_id)
        now = _utc_now().isoformat()
        old = self._memory.source_registry.get(key)
        row = {
            "namespace": namespace,
            "source_id": source_id,
            **payload,
            "created_at": old.get("created_at") if old else now,
            "updated_at": now,
        }
        self._memory.source_registry[key] = row
        if self._metadb.enabled():
            self._metadb.upsert_source(namespace, source_id, row)
        self._append_audit(namespace, "service", "source_upsert", source_id, {"source_id": source_id})
        return row

    def get_source(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        db_row = self._metadb.get_source(namespace, source_id)
        if db_row:
            self._memory.source_registry[_source_key(namespace, source_id)] = db_row
            return db_row
        row = self._memory.source_registry.get(_source_key(namespace, source_id))
        return row

    def bootstrap_sample_sources(self, namespace: str) -> list[dict[str, Any]]:
        samples = [
            {
                "source_id": "sample-admin-authoritative",
                "name": "Sample Authoritative Admin Division",
                "category": "admin_division",
                "trust_level": "authoritative",
                "license": "Open Government License",
                "entrypoint": "fixture://admin_division",
                "update_frequency": "daily",
                "fetch_method": "download",
                "parser_profile": {"dataset_variant": "admin_v1"},
                "validator_profile": {"max_null_ratio": 0.2},
                "enabled": True,
                "allowed_use_notes": "cache allowed for internal governance",
                "access_mode": "download",
                "robots_tos_flags": {"allow_automation": True, "require_attribution": True},
            },
            {
                "source_id": "sample-osm-geofabrik-china",
                "name": "Sample OSM Geofabrik China Extract",
                "category": "road_poi",
                "trust_level": "open_license",
                "license": "ODbL",
                "entrypoint": "fixture://osm_geofabrik_china",
                "update_frequency": "weekly",
                "fetch_method": "download",
                "parser_profile": {"dataset_variant": "osm_china_v1"},
                "validator_profile": {"max_null_ratio": 0.3},
                "enabled": True,
                "allowed_use_notes": "cache allowed with attribution",
                "access_mode": "download",
                "robots_tos_flags": {"allow_automation": True, "require_attribution": True},
            },
        ]
        upserted: list[dict[str, Any]] = []
        for sample in samples:
            source_id = sample.pop("source_id")
            upserted.append(self.upsert_source(namespace, source_id, sample))
        self._append_audit(namespace, "service", "bootstrap_samples", namespace, {"count": len(upserted)})
        return upserted

    def upsert_source_schedule(self, namespace: str, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        source = self.get_source(namespace, source_id)
        if not source:
            raise KeyError("source_not_found")
        key = _source_key(namespace, source_id)
        row = {
            "namespace": namespace,
            "source_id": source_id,
            **payload,
        }
        self._memory.source_schedule[key] = row
        if self._metadb.enabled():
            self._metadb.upsert_source_schedule(namespace, source_id, row)
        self._append_audit(namespace, "service", "schedule_upsert", source_id, {"source_id": source_id, **payload})
        return row

    def get_source_schedule(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        db_row = self._metadb.get_source_schedule(namespace, source_id)
        if db_row:
            self._memory.source_schedule[_source_key(namespace, source_id)] = db_row
            return db_row
        row = self._memory.source_schedule.get(_source_key(namespace, source_id))
        return row

    def list_audit_events(self, namespace: str) -> list[dict[str, Any]]:
        rows = self._metadb.list_audit_events(namespace)
        if rows:
            return rows
        events = [x for x in self._memory.audit_events if x.get("namespace") == namespace]
        return events

    def _load_fixture_payload(self, source: dict[str, Any]) -> dict[str, Any]:
        profile = source.get("parser_profile") or {}
        variant = str(profile.get("dataset_variant") or "admin_v1")
        return FIXTURE_DATASETS.get(variant, FIXTURE_DATASETS["admin_v1"])

    def _latest_snapshot(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        db_row = self._metadb.get_latest_snapshot(namespace, source_id)
        if db_row:
            return db_row
        rows = [
            s
            for s in self._memory.source_snapshots.values()
            if s["namespace"] == namespace and s["source_id"] == source_id
        ]
        if not rows:
            return None
        rows.sort(key=lambda x: x["fetched_at"], reverse=True)
        return rows[0]

    def fetch_now(self, namespace: str, source_id: str) -> dict[str, Any]:
        source = self.get_source(namespace, source_id)
        if not source:
            raise KeyError("source_not_found")
        if not source.get("enabled", True):
            raise PermissionError("source_disabled")

        entrypoint = str(source.get("entrypoint") or "")
        if entrypoint.startswith("fixture://"):
            payload = self._load_fixture_payload(source)
        else:
            raw = fetch_payload(source)
            payload = parse_raw_payload(raw, source.get("parser_profile") or {})

        content_hash = _hash_payload(payload)
        latest = self._latest_snapshot(namespace, source_id)
        snapshot_id = str(uuid4())
        now_iso = _utc_now().isoformat()
        row_count = sum(len(payload.get(k, [])) for k in ("admin_division", "roads", "pois", "places"))

        status = "success"
        if latest and latest.get("content_hash") == content_hash:
            status = "skipped"

        snapshot = {
            "namespace": namespace,
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "version_tag": now_iso.split("T")[0],
            "fetched_at": now_iso,
            "etag": content_hash[:16],
            "last_modified": now_iso,
            "content_hash": content_hash,
            "raw_uri": f"trust-store://raw/{namespace}/{source_id}/{snapshot_id}.json",
            "parsed_uri": f"trust-store://parsed/{namespace}/{source_id}/{snapshot_id}.json",
            "status": status,
            "row_count": row_count,
            "payload": payload,
        }
        self._memory.source_snapshots[snapshot_id] = snapshot
        if self._metadb.enabled():
            self._metadb.insert_snapshot(namespace, snapshot)
        self._append_audit(namespace, "service", "fetch", snapshot_id, {"source_id": source_id, "status": status})
        return snapshot

    def get_snapshot(self, namespace: str, snapshot_id: str) -> Optional[dict[str, Any]]:
        db_row = self._metadb.get_snapshot(namespace, snapshot_id)
        if db_row:
            db_row["namespace"] = namespace
            self._memory.source_snapshots[snapshot_id] = db_row
            return db_row
        snapshot = self._memory.source_snapshots.get(snapshot_id)
        if snapshot and snapshot.get("namespace") == namespace:
            return snapshot
        return None

    def _compute_diff(self, base: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        base_total = base.get("row_count", 0)
        new_total = new.get("row_count", 0)
        delta = new_total - base_total
        change_ratio = abs(delta) / max(base_total, 1)
        if change_ratio > 0.5:
            severity = "high"
        elif change_ratio > 0.2:
            severity = "medium"
        else:
            severity = "low"
        diff_json = {
            "base_row_count": base_total,
            "new_row_count": new_total,
            "delta": delta,
            "change_ratio": round(change_ratio, 4),
            "risk_hint": "review_required" if severity == "high" else "normal",
        }
        return {"diff_json": diff_json, "diff_severity": severity}

    def validate_snapshot(self, namespace: str, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(namespace, snapshot_id)
        if not snapshot:
            raise KeyError("snapshot_not_found")

        payload = snapshot["payload"]
        row_count = snapshot["row_count"]
        key_fields_missing = 0
        primary_key_conflicts = 0

        seen_keys: set[str] = set()
        for row in payload.get("admin_division", []):
            adcode = str(row.get("adcode") or "")
            if not adcode:
                key_fields_missing += 1
            if adcode in seen_keys:
                primary_key_conflicts += 1
            seen_keys.add(adcode)

        null_ratio = 0.0 if row_count == 0 else round(key_fields_missing / row_count, 4)
        quality_score = 100
        quality_score -= min(int(null_ratio * 100), 40)
        quality_score -= min(primary_key_conflicts * 5, 30)
        quality_score = max(0, quality_score)

        report = {
            "namespace": namespace,
            "snapshot_id": snapshot_id,
            "report_json": {
                "row_count": row_count,
                "null_ratio": null_ratio,
                "primary_key_conflicts": primary_key_conflicts,
                "encoding_valid": True,
                "name_normalization_reversible_sample": True,
            },
            "quality_score": quality_score,
            "validator_version": "v0.1",
        }

        source_id = snapshot["source_id"]
        previous = [
            s
            for s in self._memory.source_snapshots.values()
            if s["namespace"] == namespace
            and s["source_id"] == source_id
            and s["snapshot_id"] != snapshot_id
            and s["status"] in {"success", "skipped"}
        ]
        previous.sort(key=lambda x: x["fetched_at"], reverse=True)
        if previous:
            base = previous[0]
            diff = self._compute_diff(base, snapshot)
            self._memory.diff_reports[snapshot_id] = {
                "namespace": namespace,
                "base_snapshot_id": base["snapshot_id"],
                "new_snapshot_id": snapshot_id,
                **diff,
            }
            if self._metadb.enabled():
                self._metadb.upsert_diff_report(namespace, self._memory.diff_reports[snapshot_id])

        self._memory.quality_reports[snapshot_id] = report
        if self._metadb.enabled():
            self._metadb.upsert_quality_report(namespace, snapshot_id, report)
        self._append_audit(namespace, "service", "validate", snapshot_id, {"quality_score": quality_score})
        return report

    def publish_snapshot(self, namespace: str, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(namespace, snapshot_id)
        if not snapshot:
            raise KeyError("snapshot_not_found")

        quality = self._memory.quality_reports.get(snapshot_id)
        if not quality or quality.get("namespace") != namespace:
            raise PermissionError("snapshot_not_validated")
        if quality["quality_score"] < 60:
            raise PermissionError("quality_below_threshold")

        source_id = snapshot["source_id"]
        payload = snapshot["payload"]

        self._memory.admin_division = [
            x for x in self._memory.admin_division if not (x["namespace"] == namespace and x["source_id"] == source_id)
        ]
        self._memory.road_index = [
            x for x in self._memory.road_index if not (x["namespace"] == namespace and x["source_id"] == source_id)
        ]
        self._memory.poi_index = [
            x for x in self._memory.poi_index if not (x["namespace"] == namespace and x["source_id"] == source_id)
        ]
        self._memory.place_name_index = [
            x for x in self._memory.place_name_index if not (x["namespace"] == namespace and x["source_id"] == source_id)
        ]

        for row in payload.get("admin_division", []):
            self._memory.admin_division.append(
                {
                    **row,
                    "namespace": namespace,
                    "valid_from": snapshot["fetched_at"],
                    "valid_to": None,
                    "source_id": source_id,
                    "snapshot_id": snapshot_id,
                }
            )
        for row in payload.get("roads", []):
            self._memory.road_index.append({**row, "namespace": namespace, "source_id": source_id, "snapshot_id": snapshot_id})
        for row in payload.get("pois", []):
            self._memory.poi_index.append({**row, "namespace": namespace, "source_id": source_id, "snapshot_id": snapshot_id})
        for row in payload.get("places", []):
            self._memory.place_name_index.append(
                {**row, "namespace": namespace, "source_id": source_id, "snapshot_id": snapshot_id}
            )

        storage_backend = "memory"
        if self._trustdb.enabled():
            try:
                self._trustdb.persist_snapshot(namespace, source_id, snapshot_id, payload, snapshot["fetched_at"])
                storage_backend = "postgres"
            except Exception as exc:
                raise RuntimeError(f"trustdb_persist_failed:{exc}") from exc

        self._memory.published_snapshots.add(snapshot_id)
        job = {
            "publish_job_id": str(uuid4()),
            "namespace": namespace,
            "snapshot_id": snapshot_id,
            "status": "success",
            "storage_backend": storage_backend,
        }
        self._append_audit(namespace, "service", "publish", snapshot_id, {"publish_job_id": job["publish_job_id"]})
        return job

    def promote_active(
        self,
        namespace: str,
        source_id: str,
        snapshot_id: str,
        activated_by: str,
        activation_note: str,
        confirm_high_diff: bool,
    ) -> dict[str, Any]:
        snapshot = self.get_snapshot(namespace, snapshot_id)
        if not snapshot or snapshot.get("source_id") != source_id:
            raise PermissionError("snapshot_not_published")
        if snapshot_id not in self._memory.published_snapshots:
            raise PermissionError("snapshot_not_published")

        quality = self._memory.quality_reports.get(snapshot_id)
        if not quality or quality.get("quality_score", 0) < 60:
            raise PermissionError("quality_below_threshold")

        diff = self._memory.diff_reports.get(snapshot_id)
        if diff and diff.get("namespace") == namespace and diff.get("diff_severity") == "high" and not confirm_high_diff:
            raise PermissionError("high_diff_requires_confirmation")

        row = {
            "namespace": namespace,
            "source_id": source_id,
            "active_snapshot_id": snapshot_id,
            "activated_by": activated_by,
            "activated_at": _utc_now().isoformat(),
            "activation_note": activation_note,
        }
        self._memory.active_release[_source_key(namespace, source_id)] = row
        if self._metadb.enabled():
            self._metadb.upsert_active_release(namespace, source_id, row)
        self._append_audit(
            namespace,
            activated_by,
            "activate",
            snapshot_id,
            {"source_id": source_id, "activation_note": activation_note},
        )
        return row

    def diff_snapshots(self, namespace: str, base_snapshot_id: str, new_snapshot_id: str) -> dict[str, Any]:
        base = self.get_snapshot(namespace, base_snapshot_id)
        new = self.get_snapshot(namespace, new_snapshot_id)
        if not base or not new:
            raise KeyError("snapshot_not_found")

        diff = self._compute_diff(base, new)
        report = {
            "namespace": namespace,
            "base_snapshot_id": base_snapshot_id,
            "new_snapshot_id": new_snapshot_id,
            **diff,
        }
        self._memory.diff_reports[new_snapshot_id] = report
        if self._metadb.enabled():
            self._metadb.upsert_diff_report(namespace, report)
        return report

    def get_quality_report(self, namespace: str, snapshot_id: str) -> Optional[dict[str, Any]]:
        db_row = self._metadb.get_quality_report(namespace, snapshot_id)
        if db_row:
            db_row["namespace"] = namespace
            self._memory.quality_reports[snapshot_id] = db_row
            return db_row
        report = self._memory.quality_reports.get(snapshot_id)
        if report and report.get("namespace") == namespace:
            return report
        return None

    def get_active_release(self, namespace: str, source_id: str) -> Optional[dict[str, Any]]:
        db_row = self._metadb.get_active_release(namespace, source_id)
        if db_row:
            self._memory.active_release[_source_key(namespace, source_id)] = db_row
            return db_row
        row = self._memory.active_release.get(_source_key(namespace, source_id))
        return row

    def _active_snapshot_ids(self, namespace: str) -> set[str]:
        return {
            item["active_snapshot_id"]
            for item in self._memory.active_release.values()
            if item.get("namespace") == namespace
        }

    def query_admin_division(self, namespace: str, name: str, parent_hint: Optional[str] = None) -> list[dict[str, Any]]:
        rows = self._trustdb.query_admin_division(namespace, name, parent_hint)
        if rows:
            return rows
        active_ids = self._active_snapshot_ids(namespace)
        items: list[dict[str, Any]] = []
        for row in self._memory.admin_division:
            if row["namespace"] != namespace or row["snapshot_id"] not in active_ids:
                continue
            if name in str(row.get("name") or "") or name in "".join(row.get("name_aliases") or []):
                if parent_hint and parent_hint != row.get("parent_adcode"):
                    continue
                items.append(row)
        return items

    def query_road(self, namespace: str, name: str, adcode_hint: Optional[str] = None) -> list[dict[str, Any]]:
        rows = self._trustdb.query_road(namespace, name, adcode_hint)
        if rows:
            return rows
        active_ids = self._active_snapshot_ids(namespace)
        items: list[dict[str, Any]] = []
        for row in self._memory.road_index:
            if row["namespace"] != namespace or row["snapshot_id"] not in active_ids:
                continue
            if name in str(row.get("name") or "") or name in str(row.get("normalized_name") or ""):
                if adcode_hint and adcode_hint != row.get("admin_adcode"):
                    continue
                items.append(row)
        return items

    def query_poi(self, namespace: str, name: str, adcode_hint: Optional[str] = None, top_k: int = 5) -> list[dict[str, Any]]:
        rows = self._trustdb.query_poi(namespace, name, adcode_hint, top_k=top_k)
        if rows:
            return rows[:top_k]
        active_ids = self._active_snapshot_ids(namespace)
        items: list[dict[str, Any]] = []
        for row in self._memory.poi_index:
            if row["namespace"] != namespace or row["snapshot_id"] not in active_ids:
                continue
            if name in str(row.get("name") or "") or name in str(row.get("normalized_name") or ""):
                if adcode_hint and adcode_hint != row.get("admin_adcode"):
                    continue
                items.append(row)
        return items[:top_k]

    def _normalized_validation_inputs(self, payload: dict[str, Any]) -> dict[str, str]:
        return {
            "province": str(payload.get("province") or ""),
            "city": str(payload.get("city") or ""),
            "district": str(payload.get("district") or ""),
            "road": str(payload.get("road") or payload.get("street") or ""),
            "poi": str(payload.get("poi") or payload.get("detail") or ""),
        }

    def _to_governance_evidence_items(self, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for ref in refs:
            items.append(
                {
                    "source": "trust_data_hub",
                    "schema_version": VALIDATION_SCHEMA_VERSION,
                    "namespace": ref.get("namespace"),
                    "source_id": ref.get("source_id"),
                    "snapshot_id": ref.get("snapshot_id"),
                    "record_id": ref.get("record_id"),
                    "match_type": ref.get("match_type"),
                    "score": ref.get("score"),
                }
            )
        return items

    def build_validation_evidence(self, namespace: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalized_validation_inputs(payload)
        province = normalized["province"]
        city = normalized["city"]
        district = normalized["district"]
        road = normalized["road"]
        poi = normalized["poi"]

        admin_candidates = self.query_admin_division(namespace, city or district or province)
        road_candidates = self.query_road(namespace, road) if road else []
        poi_candidates = self.query_poi(namespace, poi, top_k=3) if poi else []

        evidence_refs = []
        for group, match_type in (
            (admin_candidates[:1], "admin_division"),
            (road_candidates[:2], "road"),
            (poi_candidates[:2], "poi"),
        ):
            for item in group:
                record_id = item.get("adcode") or item.get("road_id") or item.get("poi_id") or "unknown"
                evidence_refs.append(
                    {
                        "namespace": namespace,
                        "source_id": item["source_id"],
                        "snapshot_id": item["snapshot_id"],
                        "record_id": record_id,
                        "match_type": match_type,
                        "score": 0.9 if match_type == "admin_division" else 0.7,
                    }
                )

        ambiguity = "low" if len(admin_candidates) <= 1 else "medium"
        signals = {
            "admin_division_valid": {"value": bool(admin_candidates), "evidence_count": len(admin_candidates)},
            "road_exists": {"value": bool(road_candidates), "top_candidates": road_candidates[:3]},
            "poi_exists": {"value": bool(poi_candidates), "top_candidates": poi_candidates[:3]},
            "ambiguity_level": ambiguity,
        }
        score_hint = 0.3 + 0.35 * bool(admin_candidates) + 0.2 * bool(road_candidates) + 0.15 * bool(poi_candidates)

        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "namespace": namespace,
            "signals": signals,
            "validation_score_hint": round(min(score_hint, 1.0), 3),
            "evidence_refs": evidence_refs,
            "evidence": {"items": self._to_governance_evidence_items(evidence_refs)},
            "input_mapping": {
                "road": "road|street",
                "poi": "poi|detail",
            },
        }

    def build_validation_evidence_by_snapshot(
        self,
        namespace: str,
        snapshot_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = self.get_snapshot(namespace, snapshot_id)
        if not snapshot:
            raise KeyError("snapshot_not_found")

        normalized = self._normalized_validation_inputs(payload)
        city = normalized["city"] or normalized["district"] or normalized["province"]
        road = normalized["road"]
        poi = normalized["poi"]

        data = snapshot.get("payload", {})
        admin_candidates = [
            {
                **row,
                "namespace": namespace,
                "source_id": snapshot["source_id"],
                "snapshot_id": snapshot_id,
            }
            for row in data.get("admin_division", [])
            if city and (city in str(row.get("name") or "") or city in "".join(row.get("name_aliases") or []))
        ]
        road_candidates = [
            {
                **row,
                "namespace": namespace,
                "source_id": snapshot["source_id"],
                "snapshot_id": snapshot_id,
            }
            for row in data.get("roads", [])
            if road and (road in str(row.get("name") or "") or road in str(row.get("normalized_name") or ""))
        ]
        poi_candidates = [
            {
                **row,
                "namespace": namespace,
                "source_id": snapshot["source_id"],
                "snapshot_id": snapshot_id,
            }
            for row in data.get("pois", [])
            if poi and (poi in str(row.get("name") or "") or poi in str(row.get("normalized_name") or ""))
        ]

        evidence_refs: list[dict[str, Any]] = []
        for group, match_type in (
            (admin_candidates[:1], "admin_division"),
            (road_candidates[:2], "road"),
            (poi_candidates[:2], "poi"),
        ):
            for item in group:
                record_id = item.get("adcode") or item.get("road_id") or item.get("poi_id") or "unknown"
                evidence_refs.append(
                    {
                        "namespace": namespace,
                        "source_id": item["source_id"],
                        "snapshot_id": snapshot_id,
                        "record_id": record_id,
                        "match_type": match_type,
                        "score": 0.9 if match_type == "admin_division" else 0.7,
                    }
                )

        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "namespace": namespace,
            "snapshot_id": snapshot_id,
            "signals": {
                "admin_division_valid": {"value": bool(admin_candidates), "evidence_count": len(admin_candidates)},
                "road_exists": {"value": bool(road_candidates), "top_candidates": road_candidates[:3]},
                "poi_exists": {"value": bool(poi_candidates), "top_candidates": poi_candidates[:3]},
                "ambiguity_level": "low" if len(admin_candidates) <= 1 else "medium",
            },
            "validation_score_hint": round(
                min(0.3 + 0.35 * bool(admin_candidates) + 0.2 * bool(road_candidates) + 0.15 * bool(poi_candidates), 1.0),
                3,
            ),
            "evidence_refs": evidence_refs,
            "evidence": {"items": self._to_governance_evidence_items(evidence_refs)},
            "input_mapping": {
                "road": "road|street",
                "poi": "poi|detail",
            },
        }

    def replay_validation_evidence_by_snapshot(
        self,
        namespace: str,
        snapshot_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        result = self.build_validation_evidence_by_snapshot(namespace, snapshot_id, payload)
        replay_id = str(uuid4())
        created_at = _utc_now().isoformat()

        replay_run = {
            "namespace": namespace,
            "replay_id": replay_id,
            "snapshot_id": snapshot_id,
            "request_payload": self._normalized_validation_inputs(payload),
            "replay_result": {
                "signals": result.get("signals") or {},
                "validation_score_hint": result.get("validation_score_hint"),
                "evidence_refs": result.get("evidence_refs") or [],
            },
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "created_at": created_at,
        }

        storage_backend = "memory"
        self._memory.validation_replay_runs.insert(0, replay_run)
        if self._metadb.enabled():
            try:
                self._metadb.insert_validation_replay_run(namespace, replay_run)
                storage_backend = "postgres"
            except Exception as exc:
                raise RuntimeError(f"replay_persist_failed:{exc}") from exc

        self._append_audit(
            namespace,
            "service",
            "validation_replay",
            replay_id,
            {"snapshot_id": snapshot_id, "storage_backend": storage_backend},
        )

        return {
            **result,
            "replay_id": replay_id,
            "replayed_at": created_at,
            "storage_backend": storage_backend,
        }

    def list_validation_replay_runs(
        self,
        namespace: str,
        snapshot_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        local_rows = [x for x in self._memory.validation_replay_runs if x.get("namespace") == namespace]
        if snapshot_id:
            local_rows = [x for x in local_rows if x.get("snapshot_id") == snapshot_id]
        if local_rows:
            return local_rows[:safe_limit]
        if self._metadb.enabled():
            try:
                rows = self._metadb.list_validation_replay_runs(namespace, snapshot_id=snapshot_id, limit=safe_limit)
                for item in rows:
                    namespaced = {
                        "namespace": namespace,
                        "replay_id": item.get("replay_id"),
                        "snapshot_id": item.get("snapshot_id"),
                        "request_payload": item.get("request_payload") or {},
                        "replay_result": item.get("replay_result") or {},
                        "schema_version": item.get("schema_version") or VALIDATION_SCHEMA_VERSION,
                        "created_at": item.get("created_at"),
                    }
                    if not any(existing.get("replay_id") == namespaced["replay_id"] for existing in self._memory.validation_replay_runs):
                        self._memory.validation_replay_runs.append(namespaced)
                return rows
            except Exception:
                return []
        return []


trust_repository = TrustRepository()
