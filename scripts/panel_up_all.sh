#!/usr/bin/env bash
set -euo pipefail

FACTORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDR_ROOT="/Users/huda/Code/si-factory-public-security-address"
URBAN_ROOT="/Users/huda/Code/si-factory-urban-governance"

"$FACTORY_ROOT/scripts/panel_up.sh"
"$ADDR_ROOT/scripts/panel_up.sh"
"$URBAN_ROOT/scripts/panel_up.sh"

sleep 1

echo "--- panel status ---"
printf "factory: "
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8877/
printf "addr: "
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8787/
printf "urban: "
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8788/

echo "factory => http://127.0.0.1:8877"
echo "addr    => http://127.0.0.1:8787"
echo "urban   => http://127.0.0.1:8788"
