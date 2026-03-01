from __future__ import annotations

import pytest

from packages.trust_hub import TrustHub


def test_query_trust_tables_blocked_without_database_url(tmp_path) -> None:
    hub = TrustHub(storage_path=tmp_path / "trust_hub.json", database_url="")
    with pytest.raises(ValueError, match="blocked"):
        hub.list_trust_meta_sources(namespace_id="cn_demo", limit=10)


def test_query_trust_tables_blocked_with_non_pg_url(tmp_path) -> None:
    hub = TrustHub(storage_path=tmp_path / "trust_hub.json", database_url="mysql://user:pass@localhost/db")
    with pytest.raises(ValueError, match="blocked"):
        hub.list_trust_meta_sources(namespace_id="cn_demo", limit=10)


def test_capability_and_sample_strict_when_non_pg_url(tmp_path) -> None:
    hub = TrustHub(storage_path=tmp_path / "trust_hub_a.json", database_url="mysql://user:pass@localhost/db")
    cap = hub.upsert_capability(
        source_id="gaode",
        provider="amap",
        endpoint="https://restapi.amap.com/v3/place/text",
        tool_type="api",
    )
    sample = hub.add_sample_data(
        source_id="gaode",
        content={"query": "杭州市西湖区文三路90号", "result": "ok"},
        trust_score=0.91,
    )
    assert cap["source_id"] == "gaode"
    assert sample["source_id"] == "gaode"

    reloaded = TrustHub(storage_path=tmp_path / "trust_hub_a.json", database_url="")
    caps = reloaded.list_capabilities("gaode")
    rows = reloaded.query_samples("gaode")
    assert len(caps) >= 1
    assert any(str(item.get("endpoint") or "").startswith("https://restapi.amap.com") for item in caps)
    assert len(rows) >= 1
    assert any(float(item.get("trust_score") or 0.0) == 0.91 for item in rows)
