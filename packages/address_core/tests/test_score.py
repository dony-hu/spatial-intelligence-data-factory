from packages.address_core.score import score_confidence
from packages.address_core.types import MatchCandidate


def test_score_confidence_rejects_invalid_road() -> None:
    parsed = {
        "province": "广东省",
        "city": "深圳市",
        "district": "罗湖区",
        "road": "不存在路",
        "house_no": "64号",
    }
    candidates = [
        MatchCandidate(name="广东省深圳市罗湖区不存在路64号", score=0.92, source="invalid_road_truncate"),
        MatchCandidate(name="广东省深圳市罗湖区不存在路64号龙湖天街", score=0.75, source="normalized_text"),
    ]
    confidence, strategy = score_confidence(parsed, candidates)
    assert confidence < 0.62
    assert strategy == "human_required"


def test_score_confidence_accepts_complete_address() -> None:
    parsed = {
        "province": "上海市",
        "city": "上海市",
        "district": "浦东新区",
        "road": "世纪大道",
        "house_no": "8号",
    }
    candidates = [
        MatchCandidate(name="上海市上海市浦东新区世纪大道8号东方明珠花园4栋6单元111室", score=0.86, source="parsed_recompose")
    ]
    confidence, strategy = score_confidence(parsed, candidates)
    assert confidence >= 0.88
    assert strategy == "rule_only"


def test_score_confidence_marks_building_room_without_unit_as_review() -> None:
    parsed = {
        "province": "江苏省",
        "city": "苏州市",
        "district": "虎丘区",
        "road": "人民路",
        "house_no": "113号",
        "building": "9栋",
        "room": "276室",
    }
    candidates = [MatchCandidate(name="江苏省苏州市虎丘区人民路113号未来城9栋276室", score=0.86, source="normalized_text")]
    confidence, strategy = score_confidence(parsed, candidates)
    assert 0.62 <= confidence < 0.88
    assert strategy == "match_dict"
