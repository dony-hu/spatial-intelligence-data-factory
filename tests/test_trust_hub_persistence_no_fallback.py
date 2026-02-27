from pathlib import Path

import pytest

from packages.trust_hub import TrustHub


def test_register_capability_blocks_on_invalid_endpoint(tmp_path) -> None:
    hub = TrustHub(storage_path=tmp_path / "trust_hub.json")
    with pytest.raises(ValueError, match="blocked"):
        hub.upsert_capability(
            source_id="gaode",
            provider="amap",
            endpoint="invalid-endpoint",
            tool_type="api",
        )


def test_capability_and_sample_persist_after_reload(tmp_path) -> None:
    storage = tmp_path / "trust_hub.json"
    hub = TrustHub(storage_path=storage)
    hub.store_api_key(name="gaode", api_key="k1", provider="amap", api_endpoint="https://restapi.amap.com")
    cap = hub.upsert_capability(
        source_id="gaode",
        provider="amap",
        endpoint="https://restapi.amap.com/v3/place/text",
        tool_type="api",
    )
    sample = hub.add_sample_data(
        source_id="gaode",
        content={"query": "杭州市西湖区文三路90号", "result": "匹配到西湖区"},
        trust_score=0.92,
    )
    assert cap["source_id"] == "gaode"
    assert sample["source_id"] == "gaode"

    reloaded = TrustHub(storage_path=storage)
    caps = reloaded.list_capabilities("gaode")
    samples = reloaded.query_samples("gaode")
    assert len(caps) == 1
    assert caps[0]["endpoint"].startswith("https://")
    assert len(samples) == 1
    assert samples[0]["trust_score"] == 0.92
