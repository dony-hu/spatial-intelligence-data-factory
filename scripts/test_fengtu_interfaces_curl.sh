#!/usr/bin/env bash
set -euo pipefail

if [[ "${ALLOW_DEMO_SCRIPTS:-0}" != "1" ]]; then
  echo "[blocked] scripts/test_fengtu_interfaces_curl.sh 已默认禁用（probe/mock流程）"
  echo "如需强制运行请设置: ALLOW_DEMO_SCRIPTS=1"
  echo "建议使用真实最小链路: ./scripts/run_governance_e2e_minimal.sh"
  exit 2
fi

AK_TEST='a0ece06a144a42228cd074e527a4f14f'
AK_TEST2='0748238c55024ea88a61815232a53714'

run_case() {
  local name="$1"
  shift
  echo "=== ${name} ==="
  curl -sS "$@" -w "\nHTTP_STATUS:%{http_code}\n"
  echo
}

run_case "209_address_level_judge" \
  --get 'https://gis-apis.sf-express.com/iad/api' \
  --data-urlencode "ak=${AK_TEST2}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦'

run_case "182_address_real_check" \
  --get 'https://gis-apis.sf-express.com/opquery/addressRealCheck' \
  -H "ak: ${AK_TEST2}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'province=广东省' \
  --data-urlencode 'city=深圳市' \
  --data-urlencode 'county=南山区'

run_case "173_address_type_identify" \
  --get 'https://gis-apis.sf-express.com/atype/api' \
  --data-urlencode "ak=${AK_TEST}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'citycode=755' \
  --data-urlencode 'opt=aoi'

run_case "183_address_resolve_l5" \
  -X POST 'https://gis-apis.sf-express.com/opquery/addressResolve' \
  -H "ak: ${AK_TEST2}" \
  -H 'Content-Type: application/json' \
  -d '{"address":"深圳市南山区前海顺丰总部大厦","province":"广东省","city":"深圳市","county":"南山区","town":"南山街道"}'

run_case "184_address_standardize" \
  -X POST 'https://gis-apis.sf-express.com/opquery/stdAddr/api' \
  -H "ak: ${AK_TEST}" \
  -H 'Content-Type: application/json' \
  -d '{"address":"深圳市南山区前海顺丰总部大厦","full":1}'

run_case "185_address_aoi_keyword" \
  -X POST 'https://gis-apis.sf-express.com/opquery/keyword' \
  -H "ak: ${AK_TEST}" \
  -H 'Content-Type: application/json' \
  -d '{"address":"深圳市南山区前海顺丰总部大厦","province":"广东省","city":"深圳市","county":"南山区","company":"顺丰"}'
