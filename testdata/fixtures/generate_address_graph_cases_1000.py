#!/usr/bin/env python3
"""生成符合新图谱结构的1000条地址测试用例。"""

import json
import random
from datetime import datetime
from pathlib import Path

random.seed(20260212)

DISTRICTS = [
    "黄浦区", "浦东新区", "徐汇区", "静安区", "虹口区", "杨浦区", "闵行区", "宝山区", "嘉定区", "青浦区"
]

ROADS = [
    "中山东一路", "中山东二路", "南京东路", "南京西路", "淮海中路", "四川北路", "陆家嘴环路", "世纪大道", "延安中路", "衡山路"
]

COMMUNITIES = [
    "世纪花园小区", "海景苑小区", "锦绣家园小区", "翠湖天地小区", "静安华府小区", "陆家嘴壹号院小区"
]

INVALID_SAMPLES = [
    "", "abc123", "@@@###", "中山东一路", "黄浦区100号", "北京市朝阳区建国路88号", "深圳南山区科技园100号", "None", "NULL"
]


def make_valid_case(idx: int, pattern: str):
    district = random.choice(DISTRICTS)
    road = random.choice(ROADS)
    house = f"{random.randint(1, 2999)}号"
    source = f"seed_{(idx % 12) + 1}"

    components = {
        "city": "上海市",
        "district": district,
        "road": road,
        "community": "",
        "house_number": house,
        "unit": "",
        "room": "",
    }

    raw = f"上海市{district}{road}{house}"
    required_nodes = ["city", "district", "road", "building"]

    if pattern in ("road_community_building", "road_community_building_unit_room"):
        community = random.choice(COMMUNITIES)
        components["community"] = community
        raw = f"上海市{district}{road}{community}{house}"
        required_nodes.append("community")

    if pattern == "road_community_building_unit_room":
        unit = f"{random.randint(1, 8)}单元"
        room = f"{random.randint(1, 30)}{random.randint(1, 2)}{random.randint(1, 9)}室"
        components["unit"] = unit
        components["room"] = room
        raw = f"{raw}{unit}{room}"
        required_nodes.extend(["unit", "room"])

    input_field = "raw" if idx % 2 == 0 else "address"
    aliases = [raw.replace("上海市", "上海")]

    return {
        "case_id": f"G-{idx:04d}",
        "category": "valid",
        "graph_pattern": pattern,
        "input": {
            input_field: raw,
            "source": source,
        },
        "expected": {
            "cleaning_pass": True,
            "required_node_types": required_nodes,
            "forbidden_node_types": ["address", "alias"],
            "aliases_as_properties": True,
            "graph_nodes_min": len(required_nodes),
            "graph_relationships_min": max(3, len(required_nodes) - 1),
            "components_hint": components,
            "aliases_hint": aliases,
        },
    }


def make_invalid_case(idx: int):
    sample = random.choice(INVALID_SAMPLES)
    return {
        "case_id": f"G-{idx:04d}",
        "category": "invalid",
        "graph_pattern": "invalid",
        "input": {
            "raw": sample,
            "source": f"seed_{(idx % 12) + 1}",
        },
        "expected": {
            "cleaning_pass": False,
            "forbidden_node_types": ["address", "alias"],
            "error": "CLEANING_INVALID_OUTPUT",
        },
    }


def main():
    # 1000条：350 + 300 + 200 + 150
    counts = [
        ("road_building", 350),
        ("road_community_building", 300),
        ("road_community_building_unit_room", 200),
        ("invalid", 150),
    ]

    cases = []
    i = 1
    for pattern, n in counts:
        for _ in range(n):
            if pattern == "invalid":
                cases.append(make_invalid_case(i))
            else:
                cases.append(make_valid_case(i, pattern))
            i += 1

    output = {
        "meta": {
            "name": "address-graph-cases-1000",
            "version": "2026-02-12",
            "generated_at": datetime.now().isoformat(),
            "description": "基于新图谱结构（Road->Community/Building->Unit->Room，address/alias为属性）的大规模测试数据",
            "total_cases": len(cases),
            "distribution": {
                "road_building": 350,
                "road_community_building": 300,
                "road_community_building_unit_room": 200,
                "invalid": 150,
            },
        },
        "cases": cases,
    }

    out = Path(__file__).resolve().parent / "address-graph-cases-1000-2026-02-12.json"
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated: {out}")


if __name__ == "__main__":
    main()
