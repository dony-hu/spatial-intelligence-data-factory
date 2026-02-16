from __future__ import annotations

import re


_ALIASES = {
    "號": "号",
    "號楼": "号楼",
    "幢": "栋",
}

_CITY_PROVINCE_PREFIX = {
    "深圳市": "广东省",
    "苏州市": "江苏省",
    "武汉市": "湖北省",
    "随州市": "湖北省",
}

_MUNICIPALITIES = ("北京市", "上海市", "天津市", "重庆市")


def normalize_text(raw_text: str) -> str:
    text = raw_text.strip().replace("　", " ")
    text = re.sub(r"\s+", "", text)
    for key, value in _ALIASES.items():
        text = text.replace(key, value)
    text = text.replace("（", "(").replace("）", ")")
    text = _normalize_prefix(text)
    return text


def _normalize_prefix(text: str) -> str:
    # Municipalities may appear once in raw text; normalize to province+city form.
    for city in _MUNICIPALITIES:
        if text.startswith(city):
            if text.startswith(f"{city}{city}"):
                return text
            return f"{city}{text}"

    # For non-municipality city-leading inputs, prepend province when missing.
    for city, province in _CITY_PROVINCE_PREFIX.items():
        if text.startswith(city):
            return f"{province}{text}"
    return text
