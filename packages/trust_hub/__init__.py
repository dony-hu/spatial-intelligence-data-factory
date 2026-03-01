from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import json
import os
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class DataSource:
    name: str
    provider: str
    api_key: str
    api_endpoint: str
    is_active: bool = True


class TrustHub:
    """可信数据 HUB - 管理外部数据源 API Key"""

    def __init__(self, storage_path: Optional[Path] = None, database_url: Optional[str] = None):
        self._storage_path = storage_path or Path("data/trust_hub.json")
        self._database_url = str(database_url if database_url is not None else os.getenv("DATABASE_URL", "")).strip()
        self._sources: Dict[str, DataSource] = {}
        self._capabilities: List[Dict[str, str]] = []
        self._samples: List[Dict[str, object]] = []
        self._load()

    def _load(self):
        if self._storage_path.exists():
            try:
                with self._storage_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "sources" in data:
                    for name, source_data in (data.get("sources") or {}).items():
                        self._sources[name] = DataSource(**source_data)
                    self._capabilities = list(data.get("capabilities") or [])
                    self._samples = list(data.get("samples") or [])
                elif isinstance(data, dict):
                    # 兼容旧格式
                    for name, source_data in data.items():
                        self._sources[name] = DataSource(**source_data)
            except Exception:
                pass

    def _save(self):
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        sources = {
            name: {
                "name": source.name,
                "provider": source.provider,
                "api_key": source.api_key,
                "api_endpoint": source.api_endpoint,
                "is_active": source.is_active
            }
            for name, source in self._sources.items()
        }
        data = {
            "sources": sources,
            "capabilities": self._capabilities,
            "samples": self._samples,
        }
        with self._storage_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def store_api_key(
        self,
        name: str,
        api_key: str,
        provider: str = "",
        api_endpoint: str = ""
    ):
        source = DataSource(
            name=name,
            provider=provider,
            api_key=api_key,
            api_endpoint=api_endpoint
        )
        self._sources[name] = source
        self._save()

    def get_api_key(self, name: str) -> Optional[str]:
        source = self._sources.get(name)
        return source.api_key if source else None

    def get_source(self, name: str) -> Optional[DataSource]:
        return self._sources.get(name)

    def list_sources(self) -> List[str]:
        return list(self._sources.keys())

    def upsert_capability(
        self,
        *,
        source_id: str,
        provider: str,
        endpoint: str,
        tool_type: str = "api",
        status: str = "active",
    ) -> Dict[str, str]:
        endpoint_text = str(endpoint or "").strip()
        if not endpoint_text.startswith("http"):
            raise ValueError("blocked: invalid capability endpoint")
        source_text = str(source_id or "").strip()
        if not source_text:
            raise ValueError("blocked: source_id is required")
        item = {
            "capability_id": f"cap_{uuid4().hex[:12]}",
            "source_id": source_text,
            "provider": str(provider or "").strip(),
            "endpoint": endpoint_text,
            "tool_type": str(tool_type or "api").strip(),
            "status": str(status or "active").strip(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        replaced = False
        for idx, existing in enumerate(self._capabilities):
            if existing.get("source_id") == source_text and existing.get("endpoint") == endpoint_text:
                item["capability_id"] = str(existing.get("capability_id") or item["capability_id"])
                self._capabilities[idx] = item
                replaced = True
                break
        if not replaced:
            self._capabilities.append(item)
        self._save()
        if self._db_enabled():
            self._upsert_capability_db(item)
            db_items = self._query_capabilities_db(source_id=source_text, endpoint=endpoint_text, limit=1)
            if db_items:
                return db_items[0]
        return item

    def list_capabilities(self, source_id: str = "") -> List[Dict[str, str]]:
        if self._db_enabled():
            return self._query_capabilities_db(source_id=source_id, endpoint="", limit=1000)
        if source_id:
            return [item for item in self._capabilities if str(item.get("source_id") or "") == source_id]
        return list(self._capabilities)

    def add_sample_data(
        self,
        *,
        source_id: str,
        content: Dict[str, object],
        trust_score: float = 1.0,
    ) -> Dict[str, object]:
        source_text = str(source_id or "").strip()
        if not source_text:
            raise ValueError("blocked: source_id is required")
        if not isinstance(content, dict) or not content:
            raise ValueError("blocked: sample content is empty")
        score = float(trust_score)
        if score < 0.0 or score > 1.0:
            raise ValueError("blocked: trust_score out of range")
        item = {
            "sample_id": f"smp_{uuid4().hex[:12]}",
            "source_id": source_text,
            "trust_score": round(score, 6),
            "content": content,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        self._samples.append(item)
        self._save()
        if self._db_enabled():
            self._insert_sample_db(item)
        return item

    def query_samples(self, source_id: str = "", limit: int = 20) -> List[Dict[str, object]]:
        if self._db_enabled():
            return self._query_samples_db(source_id=source_id, limit=limit)
        rows = list(self._samples)
        if source_id:
            rows = [item for item in rows if str(item.get("source_id") or "") == source_id]
        rows.sort(key=lambda item: str(item.get("collected_at") or ""), reverse=True)
        return rows[: max(1, int(limit))]

    def _db_enabled(self) -> bool:
        return self._database_url.startswith("postgresql")

    def _query_db(self, sql: str, params: Dict[str, object]) -> List[Dict[str, object]]:
        if not self._db_enabled():
            raise ValueError("blocked: DATABASE_URL is required for trust_meta/trust_data query")
        try:
            from sqlalchemy import create_engine, text
        except Exception as exc:  # pragma: no cover - 依赖异常
            raise ValueError(f"blocked: sqlalchemy unavailable: {exc}") from exc

        engine = create_engine(self._database_url)
        try:
            with engine.begin() as conn:
                if self._database_url.startswith("postgresql"):
                    conn.execute(text("SET search_path TO trust_meta, trust_data, public"))
                rows = conn.execute(text(sql), params).mappings().all()
            return [dict(row) for row in rows]
        except Exception as exc:
            raise ValueError(f"blocked: trust query failed: {exc}") from exc

    def _execute_db(self, sql: str, params: Dict[str, object]) -> None:
        if not self._db_enabled():
            return
        try:
            from sqlalchemy import create_engine, text
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"blocked: sqlalchemy unavailable: {exc}") from exc

        engine = create_engine(self._database_url)
        try:
            with engine.begin() as conn:
                if self._database_url.startswith("postgresql"):
                    conn.execute(text("SET search_path TO trust_meta, trust_data, public"))
                conn.execute(text(sql), params)
        except Exception as exc:
            raise ValueError(f"blocked: trust write failed: {exc}") from exc

    def _upsert_capability_db(self, item: Dict[str, str]) -> None:
        self._execute_db(
            """
            INSERT INTO trust_meta.capability_registry (
                capability_id, source_id, provider, endpoint, tool_type, status, updated_at
            ) VALUES (
                :capability_id, :source_id, :provider, :endpoint, :tool_type, :status, :updated_at
            )
            ON CONFLICT(source_id, endpoint)
            DO UPDATE SET
                provider = excluded.provider,
                tool_type = excluded.tool_type,
                status = excluded.status,
                updated_at = excluded.updated_at;
            """,
            item,
        )

    def _query_capabilities_db(self, *, source_id: str, endpoint: str, limit: int) -> List[Dict[str, str]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = self._query_db(
            """
            SELECT capability_id, source_id, provider, endpoint, tool_type, status, updated_at
            FROM trust_meta.capability_registry
            WHERE (:source_id = '' OR source_id = :source_id)
              AND (:endpoint = '' OR endpoint = :endpoint)
            ORDER BY updated_at DESC
            LIMIT :limit
            """,
            {"source_id": str(source_id or ""), "endpoint": str(endpoint or ""), "limit": safe_limit},
        )
        return [{k: str(v) for k, v in row.items()} for row in rows]

    def _insert_sample_db(self, item: Dict[str, object]) -> None:
        params = {
            "sample_id": str(item.get("sample_id") or ""),
            "source_id": str(item.get("source_id") or ""),
            "trust_score": float(item.get("trust_score") or 0.0),
            "content_json": json.dumps(item.get("content") or {}, ensure_ascii=False),
            "collected_at": str(item.get("collected_at") or datetime.now(timezone.utc).isoformat()),
        }
        self._execute_db(
            """
            INSERT INTO trust_data.sample_data (
                sample_id, source_id, trust_score, content_json, collected_at
            ) VALUES (
                :sample_id, :source_id, :trust_score, CAST(:content_json AS JSONB), :collected_at
            );
            """,
            params,
        )

    def _query_samples_db(self, *, source_id: str, limit: int) -> List[Dict[str, object]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = self._query_db(
            """
            SELECT sample_id, source_id, trust_score, content_json, collected_at
            FROM trust_data.sample_data
            WHERE (:source_id = '' OR source_id = :source_id)
            ORDER BY collected_at DESC
            LIMIT :limit
            """,
            {"source_id": str(source_id or ""), "limit": safe_limit},
        )
        parsed: List[Dict[str, object]] = []
        for row in rows:
            content_raw = row.get("content_json")
            content: Dict[str, object]
            if isinstance(content_raw, dict):
                content = content_raw
            else:
                try:
                    content = json.loads(str(content_raw or "{}"))
                except Exception:
                    content = {}
            parsed.append(
                {
                    "sample_id": str(row.get("sample_id") or ""),
                    "source_id": str(row.get("source_id") or ""),
                    "trust_score": float(row.get("trust_score") or 0.0),
                    "content": content,
                    "collected_at": str(row.get("collected_at") or ""),
                }
            )
        return parsed

    def list_trust_meta_sources(self, namespace_id: str = "", limit: int = 20) -> List[Dict[str, object]]:
        safe_limit = max(1, min(int(limit), 1000))
        table = "trust_meta.source_registry" if self._database_url.startswith("postgresql") else "trust_meta_source_registry"
        sql = f"""
            SELECT namespace_id, source_id, source_name, source_type, authority_score, status, owner, created_at
            FROM {table}
            WHERE (:namespace_id = '' OR namespace_id = :namespace_id)
            ORDER BY created_at DESC
            LIMIT :limit
        """
        return self._query_db(sql, {"namespace_id": str(namespace_id or ""), "limit": safe_limit})

    def list_trust_data_admin_division(self, namespace_id: str = "", limit: int = 20) -> List[Dict[str, object]]:
        safe_limit = max(1, min(int(limit), 1000))
        table = "trust_data.admin_division" if self._database_url.startswith("postgresql") else "trust_data_admin_division"
        sql = f"""
            SELECT namespace_id, source_id, division_id, name, level, parent_id, adcode, snapshot_id
            FROM {table}
            WHERE (:namespace_id = '' OR namespace_id = :namespace_id)
            ORDER BY division_id ASC
            LIMIT :limit
        """
        return self._query_db(sql, {"namespace_id": str(namespace_id or ""), "limit": safe_limit})
