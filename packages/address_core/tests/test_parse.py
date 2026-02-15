from packages.address_core.parse import parse_components


def test_parse_components_partial_fields() -> None:
    parsed = parse_components("深圳市南山区科技园科苑路15号")
    assert parsed.get("city") == "深圳市"
    assert "district" in parsed
    assert parsed.get("house_no") == "15号"
