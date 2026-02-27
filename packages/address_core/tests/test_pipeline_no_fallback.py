import pytest

from packages.address_core.pipeline import run


def test_pipeline_blocks_when_records_empty() -> None:
    with pytest.raises(ValueError, match="blocked"):
        run(records=[], ruleset={"ruleset_id": "default"})


def test_pipeline_blocks_when_raw_text_empty() -> None:
    with pytest.raises(ValueError, match="blocked"):
        run(records=[{"raw_id": "r1", "raw_text": "   "}], ruleset={"ruleset_id": "default"})
