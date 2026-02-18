from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class DataSource:
    name: str
    provider: str
    api_key: str
    api_endpoint: str
    is_active: bool = True


class TrustHub:
    """可信数据 HUB - 管理外部数据源 API Key"""

    def __init__(self, storage_path: Optional[Path] = None):
        self._storage_path = storage_path or Path("data/trust_hub.json")
        self._sources: Dict[str, DataSource] = {}
        self._load()

    def _load(self):
        if self._storage_path.exists():
            try:
                with self._storage_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                for name, source_data in data.items():
                    self._sources[name] = DataSource(**source_data)
            except Exception:
                pass

    def _save(self):
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            name: {
                "name": source.name,
                "provider": source.provider,
                "api_key": source.api_key,
                "api_endpoint": source.api_endpoint,
                "is_active": source.is_active
            }
            for name, source in self._sources.items()
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
