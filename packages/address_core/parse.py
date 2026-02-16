from __future__ import annotations

import re
from typing import Dict

from packages.address_core.normalize import normalize_text


def parse_components(normalized_text: str) -> Dict[str, str]:
    # Normalize at parse entry so direct parse calls stay aligned with pipeline behavior.
    text = normalize_text(str(normalized_text or ""))
    if not text:
        return {}

    result: Dict[str, str] = {}
    remaining = text

    province_match = re.match(r"^(北京市|上海市|天津市|重庆市|[^省]{2,8}省)", remaining)
    if province_match:
        province = province_match.group(1)
        result["province"] = province
        remaining = remaining[len(province) :]

    city_match = re.match(r"^([^市区县]{1,10}市)", remaining)
    if city_match:
        city = city_match.group(1)
        result["city"] = city
        remaining = remaining[len(city) :]

    district_match = re.match(r"^([^区县市]{1,12}(?:区|县|市))", remaining)
    if district_match:
        district = district_match.group(1)
        result["district"] = district
        remaining = remaining[len(district) :]

    road_match = re.search(r"([^0-9号]{1,20}(?:大道|大街|路|街道|街|道))", remaining)
    if road_match:
        result["road"] = road_match.group(1)

    house_match = re.search(r"(\d+号)", remaining)
    if house_match:
        result["house_no"] = house_match.group(1)

    building_match = re.search(r"(\d+栋)", remaining)
    if building_match:
        result["building"] = building_match.group(1)

    unit_match = re.search(r"(\d+单元)", remaining)
    if unit_match:
        result["unit"] = unit_match.group(1)

    room_match = re.search(r"(\d+室)", remaining)
    if room_match:
        result["room"] = room_match.group(1)

    return result
