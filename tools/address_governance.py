"""
Address Governance Module for Shanghai Public Security
Implements address standardization, entity mapping, and data fusion
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json
import re
from enum import Enum


class AddressLevel(Enum):
    """Address hierarchy levels"""

    PROVINCE = 1
    CITY = 2
    DISTRICT = 3
    STREET = 4
    LANE = 5
    BUILDING = 6
    UNIT = 7
    FLOOR = 8
    ROOM = 9


class AddressComponent:
    """Represents a single address component"""

    def __init__(
        self,
        component_type="",
        value="",
        level=0,
        standardized_value=None,
        confidence=0.0,
    ):
        self.component_type = component_type
        self.value = value
        self.level = level
        self.standardized_value = standardized_value
        self.confidence = confidence


class ParsedAddress:
    """Result of address parsing"""

    def __init__(
        self,
        raw_address="",
        components=None,
        parsing_method="",
        confidence_score=0.0,
        component_confidences=None,
        parsing_errors=None,
    ):
        self.raw_address = raw_address
        self.components = components or {}
        self.parsing_method = parsing_method
        self.confidence_score = confidence_score
        self.component_confidences = component_confidences or {}
        self.parsing_errors = parsing_errors or []


class StandardizedAddress:
    """Standardized address representation"""

    def __init__(
        self,
        standard_full_address="",
        province="",
        city="",
        district="",
        street=None,
        lane=None,
        building=None,
        unit=None,
        floor=None,
        room=None,
        latitude=None,
        longitude=None,
        confidence_score=0.0,
        rules_applied=None,
    ):
        self.standard_full_address = standard_full_address
        self.province = province
        self.city = city
        self.district = district
        self.street = street
        self.lane = lane
        self.building = building
        self.unit = unit
        self.floor = floor
        self.room = room
        self.latitude = latitude
        self.longitude = longitude
        self.confidence_score = confidence_score
        self.rules_applied = rules_applied or []


class AddressStandardizer:
    """Standardizes raw addresses into canonical form"""

    # Mapping of common abbreviations to full names
    ABBREVIATION_MAP = {
        "北": "北京市",
        "上": "上海市",
        "广": "广东省",
        "深": "深圳市",
        "苏": "江苏省",
        "浙": "浙江省",
        "杭": "杭州市",
        "南京": "南京市",
        "苏州": "苏州市",
        "无锡": "无锡市",
        "常州": "常州市",
        "南通": "南通市",
        "泰州": "泰州市",
        "镇江": "镇江市",
        "黄浦": "黄浦区",
        "浦东": "浦东新区",
        "奉贤": "奉贤区",
        "金山": "金山区",
    }

    # Province to city mapping for Shanghai
    SHANGHAI_DISTRICTS = {
        "黄浦区": "310101",
        "浦东新区": "310115",
        "静安区": "310106",
        "徐汇区": "310104",
        "虹口区": "310109",
        "杨浦区": "310110",
        "闵行区": "310112",
        "宝山区": "310113",
        "嘉定区": "310114",
        "奉贤区": "310120",
        "金山区": "310116",
        "松江区": "310117",
        "青浦区": "310118",
        "崇明区": "310151",
    }

    def standardize(self, parsed_address):
        """
        Standardize a parsed address

        Args:
            parsed_address: ParsedAddress object with components

        Returns:
            StandardizedAddress with standardized values
        """
        components = parsed_address.components
        rules_applied = []

        # Standardize province
        province = self._standardize_province(
            components.get("province", ""), rules_applied
        )

        # Standardize city
        city = self._standardize_city(components.get("city", ""), rules_applied)

        # Standardize district
        district = self._standardize_district(
            components.get("district", ""), rules_applied
        )

        # Standardize street name
        street = components.get("street", "").strip()
        street = self._standardize_street(street, rules_applied)

        # Build full standard address
        full_address = self._build_full_address(
            province,
            city,
            district,
            street,
            components.get("building", ""),
            components.get("unit", ""),
            components.get("floor", ""),
            components.get("room", ""),
        )

        return StandardizedAddress(
            standard_full_address=full_address,
            province=province,
            city=city,
            district=district,
            street=street,
            lane=components.get("lane", "").strip() or None,
            building=components.get("building", "").strip() or None,
            unit=components.get("unit", "").strip() or None,
            floor=components.get("floor", "").strip() or None,
            room=components.get("room", "").strip() or None,
            confidence_score=parsed_address.confidence_score
            * 0.95,  # Reduce confidence slightly
            rules_applied=rules_applied,
        )

    def _standardize_province(self, province, rules_applied):
        """Standardize province name"""
        province = province.strip()

        if province in self.ABBREVIATION_MAP:
            rules_applied.append("abbreviation_expansion_province")
            return self.ABBREVIATION_MAP[province]

        if province.endswith("省"):
            return province
        elif province in ["北京", "上海", "天津", "重庆"]:
            rules_applied.append("municipality_standardization")
            return f"{province}市"

        return province

    def _standardize_city(self, city, rules_applied):
        """Standardize city name"""
        city = city.strip()

        if city in self.ABBREVIATION_MAP:
            rules_applied.append("abbreviation_expansion_city")
            return self.ABBREVIATION_MAP[city]

        if not city.endswith("市"):
            rules_applied.append("city_suffix_addition")
            return f"{city}市"

        return city

    def _standardize_district(self, district, rules_applied):
        """Standardize district name"""
        district = district.strip()

        if district in self.SHANGHAI_DISTRICTS:
            return district

        if not district.endswith("区"):
            rules_applied.append("district_suffix_addition")
            return f"{district}区"

        return district

    def _standardize_street(self, street, rules_applied):
        """Standardize street name"""
        street = street.strip()

        if not street:
            return ""

        # Remove trailing "路/街/道/弄" if it appears in the middle
        if any(x in street[:-1] for x in ["路", "街", "道", "弄"]):
            rules_applied.append("street_name_cleanup")

        return street

    def _build_full_address(
        self, province, city, district, street, building, unit, floor, room
    ):
        """Build full standardized address string"""
        parts = [province, city, district]

        if street:
            parts.append(street)
        if building:
            parts.append(building)
        if unit:
            parts.append(f"{unit}单元")
        if floor:
            parts.append(f"{floor}层")
        if room:
            parts.append(room + "室" if not room.endswith("室") else room)

        return "".join(parts)


class AddressParser:
    """Parses raw addresses into components"""

    # Regex patterns for parsing
    PATTERNS = {
        "province": r"^(北京|上海|天津|重庆|河北|山西|辽宁|吉林|黑龙江|江苏|浙江|安徽|福建|江西|山东|河南|湖北|湖南|广东|广西|海南|四川|贵州|云南|西藏|陕西|甘肃|青海|宁夏|新疆)(?:省|市)?",
        "city": r"(北京市|上海市|[^省市\s]{2,4}市)",
        "district": r"([^区\s]+区)",
        "street": r"((?:北|中山|南|东|西|西北|东北|西南|东南)[^路街道弄\s]+(?:路|街|道|弄))",
        "building": r"(\d+号(?:[甲乙丙丁])?)",
        "unit": r"(\d+单元)",
        "floor": r"([0-9顶十百千]+(?:楼|层))",
        "room": r"(\d{3,4}室?)",
    }

    def parse(self, raw_address, parsing_method="regex"):
        """
        Parse raw address into components

        Args:
            raw_address: Raw address string
            parsing_method: Parsing method to use (regex, ml_model, etc)

        Returns:
            ParsedAddress with extracted components
        """
        if parsing_method == "regex":
            return self._parse_regex(raw_address)
        elif parsing_method == "ml_model":
            return self._parse_ml_model(raw_address)
        else:
            return self._parse_regex(raw_address)

    def _parse_regex(self, raw_address):
        """Parse using regex patterns"""
        components = {}
        component_confidences = {}

        # Remove common prefixes
        clean_address = raw_address.replace("中华人民共和国", "").replace("上海市", "")

        # Extract components
        for component_type, pattern in self.PATTERNS.items():
            match = re.search(pattern, clean_address)
            if match:
                components[component_type] = match.group(0)
                component_confidences[component_type] = (
                    0.85 + (len(match.group(0)) / 10) * 0.1
                )
            else:
                components[component_type] = ""
                component_confidences[component_type] = 0.0

        # Calculate overall confidence
        valid_components = sum(1 for v in components.values() if v)
        overall_confidence = valid_components / len(components)

        return ParsedAddress(
            raw_address=raw_address,
            components=components,
            parsing_method="regex",
            confidence_score=overall_confidence,
            component_confidences=component_confidences,
        )

    def _parse_ml_model(self, raw_address):
        """Parse using ML model (stub for future implementation)"""
        # This would integrate with an actual ML model
        return self._parse_regex(raw_address)


class EntityMapper:
    """Maps standardized addresses to entities (POI, buildings, etc)"""

    def __init__(self):
        self.entity_database = self._load_entity_database()

    def _load_entity_database(self):
        """Load entity reference database (stub)"""
        return {"poi": [], "building": [], "landmark": []}

    def map_to_entity(self, standardized_address):
        """
        Map standardized address to entity

        Args:
            standardized_address: StandardizedAddress object

        Returns:
            Mapping result with entity_id, type, confidence
        """
        # Fuzzy matching against entity database
        best_match = self._fuzzy_match(standardized_address)

        return {
            "entity_id": best_match.get("id") if best_match else None,
            "entity_type": best_match.get("type") if best_match else None,
            "entity_name": best_match.get("name") if best_match else None,
            "similarity_score": best_match.get("similarity") if best_match else 0.0,
            "mapping_method": "fuzzy_match",
            "match_confidence": best_match.get("confidence", 0.0)
            if best_match
            else 0.0,
        }

    def _fuzzy_match(self, standardized_address):
        """Perform fuzzy matching against entity database"""
        # Implementation would use fuzzy string matching algorithms
        # For now, return None as stub
        return None

    def merge_multi_source(self, entities):
        """
        Merge multiple source entities into canonical form

        Args:
            entities: List of entities from different sources

        Returns:
            Merged canonical entity
        """
        if not entities:
            return {}

        # Take first entity as base and merge metadata from others
        canonical = entities[0].copy()
        canonical["sources"] = [e.get("source") for e in entities]
        canonical["merged_metadata"] = {}

        for entity in entities[1:]:
            for key, value in entity.items():
                if key not in canonical:
                    canonical["merged_metadata"][key] = value

        return canonical


class AddressGovernanceSystem:
    """Main system orchestrating address governance"""

    def __init__(self, region="Shanghai"):
        self.region = region
        self.parser = AddressParser()
        self.standardizer = AddressStandardizer()
        self.mapper = EntityMapper()
        self.quality_rules = self._load_quality_rules()

    def _load_quality_rules(self):
        """Load quality assurance rules"""
        return {
            "completeness_threshold": 0.8,
            "accuracy_threshold": 0.85,
            "consistency_threshold": 0.9,
        }

    def process_address(self, raw_address):
        """
        Complete address processing pipeline

        Args:
            raw_address: Raw address input

        Returns:
            Processing result with all stages
        """
        # Stage 1: Parse
        parsed = self.parser.parse(raw_address)

        # Stage 2: Standardize
        standardized = self.standardizer.standardize(parsed)

        # Stage 3: Map to entity
        entity_mapping = self.mapper.map_to_entity(standardized)

        # Stage 4: Validate quality
        quality_score = self._assess_quality(parsed, standardized, entity_mapping)

        return {
            "raw_address": raw_address,
            "parsed": parsed.__dict__,
            "standardized": standardized.__dict__,
            "entity_mapping": entity_mapping,
            "quality_score": quality_score,
            "processing_region": self.region,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _assess_quality(self, parsed, standardized, mapping):
        """Assess quality of address processing"""
        if mapping is None:
            mapping = {}
        factors = [
            parsed.confidence_score,
            standardized.confidence_score,
            mapping.get("match_confidence", 0.0) if mapping.get("entity_id") else 0.7,
        ]

        return sum(factors) / len(factors)
