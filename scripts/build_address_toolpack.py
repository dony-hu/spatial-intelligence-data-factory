#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.address_toolpack_builder import AddressToolpackBuilder


def _load_seed_addresses(seed_file: Path) -> List[str]:
    payload: Any = json.loads(seed_file.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [str(x).strip() for x in payload if str(x).strip()]
    if isinstance(payload, dict):
        addresses = payload.get("addresses") or []
        return [str(x).strip() for x in addresses if str(x).strip()]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Build address toolpack from map API observations")
    parser.add_argument("--seed-file", required=True, help="JSON file: list[str] or {addresses:[...]}")
    parser.add_argument("--output-file", required=True, help="Output toolpack file path")
    parser.add_argument("--map-api-url", default=os.getenv("MAP_TOOLPACK_API_URL", ""), help="Map API endpoint")
    parser.add_argument("--map-api-key", default=os.getenv("MAP_TOOLPACK_API_KEY", ""), help="Map API key")
    parser.add_argument("--llm-config", default="config/llm_api.json", help="LLM config path")
    parser.add_argument("--disable-llm", action="store_true", help="Disable LLM refinement")
    args = parser.parse_args()

    seed_file = Path(args.seed_file).resolve()
    output_file = Path(args.output_file).resolve()
    if not seed_file.exists():
        print(f"[ERROR] seed file not found: {seed_file}")
        return 2

    seeds = _load_seed_addresses(seed_file)
    if not seeds:
        print("[ERROR] empty seed addresses")
        return 2

    builder = AddressToolpackBuilder(
        map_api_url=args.map_api_url,
        map_api_key=args.map_api_key,
        llm_config_path=args.llm_config,
        enable_llm_iteration=not args.disable_llm,
    )
    try:
        toolpack = builder.build(seeds)
    except Exception as exc:
        print(f"[ERROR] build failed: {exc}")
        return 1

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(toolpack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[DONE] toolpack written: {output_file}")
    print(f"[DONE] cities={len(toolpack.get('cities') or [])} observations={toolpack.get('observation_count')} llm_refined={toolpack.get('llm_refined')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
