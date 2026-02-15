from packages.address_core.pipeline import run


def test_pipeline_smoke() -> None:
    outputs = run(
        records=[{"raw_id": "r1", "raw_text": "杭州市西湖区文三路90号"}],
        ruleset={"ruleset_id": "default"},
    )
    assert len(outputs) == 1
    assert outputs[0]["raw_id"] == "r1"
    assert 0 <= outputs[0]["confidence"] <= 1
    assert outputs[0]["strategy"]
    assert outputs[0]["evidence"]["items"]
