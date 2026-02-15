from __future__ import annotations

import re


_ALIASES = {
    "大道": "路",
    "大街": "路",
    "號": "号",
    "號楼": "号楼",
}


def normalize_text(raw_text: str) -> str:
    text = raw_text.strip().replace("　", " ")
    text = re.sub(r"\s+", "", text)
    for key, value in _ALIASES.items():
        text = text.replace(key, value)
    text = text.replace("（", "(").replace("）", ")")
    return text
