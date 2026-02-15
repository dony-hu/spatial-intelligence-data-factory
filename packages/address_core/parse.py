from __future__ import annotations

import re
from typing import Dict


def parse_components(normalized_text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    province_match = re.search(r"(.{2,8}省|北京市|上海市|天津市|重庆市)", normalized_text)
    if province_match:
        result["province"] = province_match.group(1)

    city_match = re.search(r"(.{2,8}市)", normalized_text)
    if city_match:
        result["city"] = city_match.group(1)

    district_match = re.search(r"(.{2,12}(区|县))", normalized_text)
    if district_match:
        result["district"] = district_match.group(1)

    road_match = re.search(r"(.{1,20}(路|街|道))", normalized_text)
    if road_match:
        result["road"] = road_match.group(1)

    house_match = re.search(r"(\d+号)", normalized_text)
    if house_match:
        result["house_no"] = house_match.group(1)

    return result
