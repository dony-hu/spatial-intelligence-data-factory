from packages.address_core.dedup import dedup_records


def test_dedup_records_removes_exact_duplicates() -> None:
    rows = [
        {"raw_id": "a", "raw_text": "广东省深圳市罗湖区南京西路190号星河湾2栋8单元397室"},
        {"raw_id": "a2", "raw_text": "广东省深圳市罗湖区南京西路190号星河湾2栋8单元397室"},
    ]
    unique = dedup_records(rows)
    assert len(unique) == 1


def test_dedup_records_merges_normalized_variants() -> None:
    rows = [
        {"raw_id": "v1", "raw_text": "深圳市罗湖区南京西路190号星河湾2幢8单元397室"},
        {"raw_id": "v2", "raw_text": "广东省深圳市罗湖区南京西路190号星河湾2栋8单元397室"},
    ]
    unique = dedup_records(rows)
    assert len(unique) == 1
