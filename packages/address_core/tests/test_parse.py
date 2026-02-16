from packages.address_core.parse import parse_components


def test_parse_components_partial_fields() -> None:
    parsed = parse_components("广东省深圳市南山区科技园科苑路15号")
    assert parsed.get("province") == "广东省"
    assert parsed.get("city") == "深圳市"
    assert parsed.get("district") == "南山区"
    assert parsed.get("road") == "科技园科苑路"
    assert parsed.get("house_no") == "15号"


def test_parse_components_municipality() -> None:
    parsed = parse_components("上海市上海市浦东新区世纪大道8号东方明珠花园4栋6单元111室")
    assert parsed.get("province") == "上海市"
    assert parsed.get("city") == "上海市"
    assert parsed.get("district") == "浦东新区"
    assert parsed.get("road") == "世纪大道"
    assert parsed.get("house_no") == "8号"
    assert parsed.get("building") == "4栋"
    assert parsed.get("unit") == "6单元"
    assert parsed.get("room") == "111室"


def test_parse_components_normalizes_raw_input_before_parse() -> None:
    parsed = parse_components(" 深圳市 南山区科苑路15號 ")
    assert parsed.get("province") == "广东省"
    assert parsed.get("city") == "深圳市"
    assert parsed.get("district") == "南山区"
    assert parsed.get("road") == "科苑路"
    assert parsed.get("house_no") == "15号"
