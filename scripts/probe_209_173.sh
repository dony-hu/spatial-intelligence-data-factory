#!/usr/bin/env bash
set -euo pipefail

AK_TEST2='0748238c55024ea88a61815232a53714'
AK_TEST='a0ece06a144a42228cd074e527a4f14f'

run() {
  local name="$1"
  shift
  echo "=== ${name} ==="
  curl -sS "$@" -w "\nHTTP:%{http_code}\n"
  echo
}

run '209/header/full' \
  --get 'https://gis-apis.sf-express.com/iad/api' \
  -H "ak: ${AK_TEST2}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'province=广东省' \
  --data-urlencode 'city=深圳市' \
  --data-urlencode 'county=南山区' \
  --data-urlencode 'town=南山街道'

run '209/query-ak/min' \
  --get 'https://gis-apis.sf-express.com/iad/api' \
  --data-urlencode "ak=${AK_TEST2}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦'

run '173/header/755/aoi' \
  --get 'https://gis-apis.sf-express.com/atype/api' \
  -H "ak: ${AK_TEST}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'citycode=755' \
  --data-urlencode 'opt=aoi'

run '173/header/7551/aoi' \
  --get 'https://gis-apis.sf-express.com/atype/api' \
  -H "ak: ${AK_TEST}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'citycode=7551' \
  --data-urlencode 'opt=aoi'

run '173/query-ak/755/aoi' \
  --get 'https://gis-apis.sf-express.com/atype/api' \
  --data-urlencode "ak=${AK_TEST}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'citycode=755' \
  --data-urlencode 'opt=aoi'

run '173/query-ak/755/defaultopt' \
  --get 'https://gis-apis.sf-express.com/atype/api' \
  --data-urlencode "ak=${AK_TEST}" \
  --data-urlencode 'address=深圳市南山区前海顺丰总部大厦' \
  --data-urlencode 'citycode=755'
