from __future__ import annotations

import json
import os
from typing import Any, Optional


class TrustDbPersister:
    def __init__(self) -> None:
        self._dsn = (
            os.getenv("DATABASE_URL")
            or os.getenv("TRUST_TRUSTDB_DSN")
            or os.getenv("TRUST_META_DATABASE_URL")
        )

    def enabled(self) -> bool:
        return bool(self._dsn and str(self._dsn).startswith("postgresql"))

    def persist_snapshot(
        self,
        namespace: str,
        source_id: str,
        snapshot_id: str,
        payload: dict[str, Any],
        fetched_at: str,
    ) -> None:
        if not self.enabled():
            return

        from sqlalchemy import create_engine, text

        engine = create_engine(self._dsn)
        admin_rows = list(payload.get("admin_division") or [])
        road_rows = list(payload.get("roads") or [])
        poi_rows = list(payload.get("pois") or [])
        place_rows = list(payload.get("places") or [])

        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM trust_db.admin_division WHERE namespace_id=:ns AND source_id=:sid"),
                {"ns": namespace, "sid": source_id},
            )
            conn.execute(
                text("DELETE FROM trust_db.road_index WHERE namespace_id=:ns AND source_id=:sid"),
                {"ns": namespace, "sid": source_id},
            )
            conn.execute(
                text("DELETE FROM trust_db.poi_index WHERE namespace_id=:ns AND source_id=:sid"),
                {"ns": namespace, "sid": source_id},
            )
            conn.execute(
                text("DELETE FROM trust_db.place_name_index WHERE namespace_id=:ns AND source_id=:sid"),
                {"ns": namespace, "sid": source_id},
            )

            for row in admin_rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO trust_db.admin_division
                        (namespace_id, adcode, name, level, parent_adcode, name_aliases, valid_from, valid_to, source_id, snapshot_id)
                        VALUES
                        (:ns, :adcode, :name, :level, :parent_adcode, CAST(:name_aliases AS jsonb), :valid_from, :valid_to, :source_id, :snapshot_id)
                        """
                    ),
                    {
                        "ns": namespace,
                        "adcode": row.get("adcode"),
                        "name": row.get("name"),
                        "level": row.get("level"),
                        "parent_adcode": row.get("parent_adcode"),
                        "name_aliases": json.dumps(row.get("name_aliases") or [], ensure_ascii=False),
                        "valid_from": fetched_at,
                        "valid_to": None,
                        "source_id": source_id,
                        "snapshot_id": snapshot_id,
                    },
                )

            for row in road_rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO trust_db.road_index
                        (namespace_id, road_id, name, normalized_name, admin_adcode, geometry_ref, source_id, snapshot_id)
                        VALUES
                        (:ns, :road_id, :name, :normalized_name, :admin_adcode, :geometry_ref, :source_id, :snapshot_id)
                        """
                    ),
                    {
                        "ns": namespace,
                        "road_id": row.get("road_id"),
                        "name": row.get("name"),
                        "normalized_name": row.get("normalized_name"),
                        "admin_adcode": row.get("admin_adcode"),
                        "geometry_ref": row.get("geometry_ref"),
                        "source_id": source_id,
                        "snapshot_id": snapshot_id,
                    },
                )

            for row in poi_rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO trust_db.poi_index
                        (namespace_id, poi_id, name, normalized_name, category, admin_adcode, centroid, source_id, snapshot_id)
                        VALUES
                        (:ns, :poi_id, :name, :normalized_name, :category, :admin_adcode, :centroid, :source_id, :snapshot_id)
                        """
                    ),
                    {
                        "ns": namespace,
                        "poi_id": row.get("poi_id"),
                        "name": row.get("name"),
                        "normalized_name": row.get("normalized_name"),
                        "category": row.get("category"),
                        "admin_adcode": row.get("admin_adcode"),
                        "centroid": row.get("centroid"),
                        "source_id": source_id,
                        "snapshot_id": snapshot_id,
                    },
                )

            for row in place_rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO trust_db.place_name_index
                        (namespace_id, place_id, name, normalized_name, type, admin_adcode, centroid, confidence_hint, source_id, snapshot_id)
                        VALUES
                        (:ns, :place_id, :name, :normalized_name, :type, :admin_adcode, :centroid, :confidence_hint, :source_id, :snapshot_id)
                        """
                    ),
                    {
                        "ns": namespace,
                        "place_id": row.get("place_id"),
                        "name": row.get("name"),
                        "normalized_name": row.get("normalized_name"),
                        "type": row.get("type"),
                        "admin_adcode": row.get("admin_adcode"),
                        "centroid": row.get("centroid"),
                        "confidence_hint": row.get("confidence_hint"),
                        "source_id": source_id,
                        "snapshot_id": snapshot_id,
                    },
                )

    def query_admin_division(self, namespace: str, name: str, parent_hint: Optional[str] = None) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        from sqlalchemy import create_engine, text

        engine = create_engine(self._dsn)
        sql = """
            SELECT d.adcode, d.name, d.level, d.parent_adcode, d.name_aliases,
                   d.source_id, d.snapshot_id
            FROM trust_db.admin_division d
            JOIN trust_meta.active_release ar
              ON ar.namespace_id = d.namespace_id
             AND ar.source_id = d.source_id
             AND ar.active_snapshot_id = d.snapshot_id
            WHERE d.namespace_id = :ns
              AND (d.name ILIKE :kw OR CAST(d.name_aliases AS text) ILIKE :kw)
        """
        params: dict[str, Any] = {"ns": namespace, "kw": f"%{name}%"}
        if parent_hint:
            sql += " AND d.parent_adcode = :parent_hint"
            params["parent_hint"] = parent_hint
        sql += " ORDER BY d.level, d.name LIMIT 50"
        with engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]

    def query_road(self, namespace: str, name: str, adcode_hint: Optional[str] = None) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        from sqlalchemy import create_engine, text

        engine = create_engine(self._dsn)
        sql = """
            SELECT r.road_id, r.name, r.normalized_name, r.admin_adcode, r.geometry_ref,
                   r.source_id, r.snapshot_id
            FROM trust_db.road_index r
            JOIN trust_meta.active_release ar
              ON ar.namespace_id = r.namespace_id
             AND ar.source_id = r.source_id
             AND ar.active_snapshot_id = r.snapshot_id
            WHERE r.namespace_id = :ns
              AND (r.name ILIKE :kw OR r.normalized_name ILIKE :kw)
        """
        params: dict[str, Any] = {"ns": namespace, "kw": f"%{name}%"}
        if adcode_hint:
            sql += " AND r.admin_adcode = :adcode_hint"
            params["adcode_hint"] = adcode_hint
        sql += " ORDER BY r.name LIMIT 50"
        with engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]

    def query_poi(
        self,
        namespace: str,
        name: str,
        adcode_hint: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not self.enabled():
            return []
        from sqlalchemy import create_engine, text

        engine = create_engine(self._dsn)
        sql = """
            SELECT p.poi_id, p.name, p.normalized_name, p.category, p.admin_adcode, p.centroid,
                   p.source_id, p.snapshot_id
            FROM trust_db.poi_index p
            JOIN trust_meta.active_release ar
              ON ar.namespace_id = p.namespace_id
             AND ar.source_id = p.source_id
             AND ar.active_snapshot_id = p.snapshot_id
            WHERE p.namespace_id = :ns
              AND (p.name ILIKE :kw OR p.normalized_name ILIKE :kw)
        """
        params: dict[str, Any] = {"ns": namespace, "kw": f"%{name}%"}
        if adcode_hint:
            sql += " AND p.admin_adcode = :adcode_hint"
            params["adcode_hint"] = adcode_hint
        sql += " ORDER BY p.name LIMIT :top_k"
        params["top_k"] = max(1, int(top_k))
        with engine.begin() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
