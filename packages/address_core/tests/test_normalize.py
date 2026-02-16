from packages.address_core.normalize import normalize_text


def test_normalize_text_basic() -> None:
    value = normalize_text(" 深圳市 南山区前海大道1號 ")
    assert " " not in value
    assert "号" in value
    assert "大道" in value
    assert value.startswith("广东省深圳市")


def test_normalize_text_municipality_prefix() -> None:
    value = normalize_text("上海市浦东新区世纪大道8号")
    assert value.startswith("上海市上海市")


def test_normalize_text_convert_building_suffix() -> None:
    value = normalize_text("随州市广水市解放大道43号未来城19幢166室")
    assert "19栋" in value
    assert value.startswith("湖北省随州市")
