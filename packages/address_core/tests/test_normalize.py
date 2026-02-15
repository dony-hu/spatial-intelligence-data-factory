from packages.address_core.normalize import normalize_text


def test_normalize_text_basic() -> None:
    value = normalize_text(" 深圳市 南山区前海大道1號 ")
    assert " " not in value
    assert "号" in value
    assert "路" in value
