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
STORAGE_TYPE="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))[0]; print(d.get('storage',{}).get('type',''))" "$TMP_JSON")"
STORAGE_URI="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1]))[0]; print(d.get('storage',{}).get('uri',''))" "$TMP_JSON")"

rm -f "$TMP_JSON"

if [[ -z "$LOCAL_PATH" ]]; then
  echo "local_path is empty for dataset: ${DATASET_ID}"
  exit 1
fi

TARGET="${ROOT_DIR}/${LOCAL_PATH}"
mkdir -p "$(dirname "$TARGET")"

if [[ "$STORAGE_TYPE" == "local" ]]; then
  if [[ -f "$TARGET" ]]; then
    echo "dataset ready (local): $TARGET"
    exit 0
  fi

  SOURCE="${ROOT_DIR}/${STORAGE_URI}"
  if [[ -f "$SOURCE" ]]; then
    cp "$SOURCE" "$TARGET"
    echo "dataset copied: $SOURCE -> $TARGET"
    exit 0
  fi

  echo "local dataset not found: $TARGET"
  exit 1
fi

if [[ "$STORAGE_TYPE" == "s3" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "aws cli not found; cannot pull s3 dataset"
    exit 1
  fi

  aws s3 cp "$STORAGE_URI" "$TARGET"
  echo "dataset downloaded: $STORAGE_URI -> $TARGET"
  exit 0
fi

echo "unsupported storage type: $STORAGE_TYPE"
exit 1

