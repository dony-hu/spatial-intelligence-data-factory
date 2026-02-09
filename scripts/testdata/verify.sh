#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CATALOG="${ROOT_DIR}/testdata/catalog/catalog.yaml"
TOOL="${ROOT_DIR}/scripts/testdata/catalog_tool.py"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <dataset-id>"
  exit 1
fi

DATASET_ID="$1"
TMP_JSON="$(mktemp)"
python3 "$TOOL" --catalog "$CATALOG" --dataset-id "$DATASET_ID" --format json > "$TMP_JSON"

LOCAL_PATH="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))[0]; print(d.get('local_path',''))" "$TMP_JSON")"
CHECKSUM_ALGO="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))[0]; print(d.get('checksum',{}).get('algo',''))" "$TMP_JSON")"
CHECKSUM_VALUE="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))[0]; print(d.get('checksum',{}).get('value',''))" "$TMP_JSON")"
rm -f "$TMP_JSON"

if [[ -z "$LOCAL_PATH" ]]; then
  echo "local_path is empty for dataset: ${DATASET_ID}"
  exit 1
fi

TARGET="${ROOT_DIR}/${LOCAL_PATH}"
if [[ ! -f "$TARGET" ]]; then
  echo "dataset file not found: $TARGET"
  exit 1
fi

if [[ "$CHECKSUM_ALGO" != "sha256" ]]; then
  echo "unsupported checksum algo: $CHECKSUM_ALGO"
  exit 1
fi

if [[ -z "$CHECKSUM_VALUE" || "$CHECKSUM_VALUE" == "REPLACE_WITH_SHA256" ]]; then
  echo "checksum missing in catalog for dataset: ${DATASET_ID}"
  exit 1
fi

ACTUAL="$(shasum -a 256 "$TARGET" | awk '{print $1}')"
if [[ "$ACTUAL" != "$CHECKSUM_VALUE" ]]; then
  echo "checksum mismatch for ${DATASET_ID}"
  echo "expected: $CHECKSUM_VALUE"
  echo "actual:   $ACTUAL"
  exit 1
fi

echo "checksum ok for ${DATASET_ID}"

