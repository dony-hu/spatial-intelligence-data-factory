#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


def parse_catalog(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    datasets = []
    current = None
    section = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        item_match = re.match(r"^\s*-\s+id:\s*(\S+)\s*$", line)
        if item_match:
            if current:
                datasets.append(current)
            current = {"id": item_match.group(1), "storage": {}, "checksum": {}}
            section = None
            continue

        if current is None:
            continue

        section_match = re.match(r"^\s{4}(storage|checksum):\s*$", line)
        if section_match:
            section = section_match.group(1)
            continue

        top_match = re.match(r"^\s{4}([a-z_]+):\s*(.+)\s*$", line)
        if top_match:
            key, value = top_match.groups()
            current[key] = value.strip().strip('"')
            section = None
            continue

        nested_match = re.match(r"^\s{6}([a-z_]+):\s*(.+)\s*$", line)
        if nested_match and section in ("storage", "checksum"):
            key, value = nested_match.groups()
            current[section][key] = value.strip().strip('"')

    if current:
        datasets.append(current)
    return datasets


def main():
    parser = argparse.ArgumentParser(description="Read test data catalog.")
    parser.add_argument("--catalog", default="testdata/catalog/catalog.yaml")
    parser.add_argument("--dataset-id")
    parser.add_argument("--format", choices=["json", "shell"], default="json")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(f"catalog not found: {catalog_path}", file=sys.stderr)
        return 1

    datasets = parse_catalog(catalog_path)
    if args.dataset_id:
        datasets = [d for d in datasets if d.get("id") == args.dataset_id]
        if not datasets:
            print(f"dataset not found: {args.dataset_id}", file=sys.stderr)
            return 1

    if args.format == "json":
        print(json.dumps(datasets, ensure_ascii=False, indent=2))
        return 0

    for d in datasets:
        print(f"id={d.get('id','')}")
        print(f"local_path={d.get('local_path','')}")
        print(f"storage_type={d.get('storage',{}).get('type','')}")
        print(f"storage_uri={d.get('storage',{}).get('uri','')}")
        print(f"checksum_algo={d.get('checksum',{}).get('algo','')}")
        print(f"checksum_value={d.get('checksum',{}).get('value','')}")
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

