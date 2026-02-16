import os

from packages.address_core.match import recall_candidates


def test_recall_candidates_returns_multiple_ranked_items() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    candidates = recall_candidates("广东省深圳市罗湖区南京西路190号星河湾2栋8单元397室")
    assert len(candidates) >= 2
    assert candidates[0].score >= candidates[-1].score


def test_recall_candidates_truncate_invalid_road_tail() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    text = "广东省深圳市罗湖区不存在路64号龙湖天街"
    candidates = recall_candidates(text)
    names = {item.name for item in candidates}
    assert "广东省深圳市罗湖区不存在路64号" in names


def test_recall_candidates_normalizes_raw_input() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    candidates = recall_candidates(" 深圳市南山区科苑路15號 ")
    names = {item.name for item in candidates}
    assert "广东省深圳市南山区科苑路15号" in names
