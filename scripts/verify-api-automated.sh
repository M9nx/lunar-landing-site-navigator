#!/usr/bin/env bash
# Automated API checks (no GitHub OAuth). Usage: ./scripts/verify-api-automated.sh [API_BASE]
set -euo pipefail
API_BASE="${1:-http://127.0.0.1:8000}"
API_BASE="${API_BASE%/}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

echo "=== Health / science gate ==="
health="$(curl -sS "$API_BASE/health")"
echo "$health" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('science_calculations_ready') is False, d; print('science_calculations_ready=false')"
ok "health"

echo "=== Unauthenticated /auth/me ==="
code="$(curl -sS -o /dev/null -w '%{http_code}' "$API_BASE/auth/me")"
[[ "$code" == "401" ]] || fail "/auth/me expected 401 got $code"
ok "/auth/me 401"

echo "=== CORS preflight (loopback origin) ==="
CORS_ORIGIN="http://127.0.0.1:8000"
hdr_file="$(mktemp)"
http_code="$(curl -sS -D "$hdr_file" -o /dev/null -w '%{http_code}' -X OPTIONS "$API_BASE/runs" \
  -H "Origin: $CORS_ORIGIN" \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type,x-csrf-token')"
header_block="$(cat "$hdr_file")"
rm -f "$hdr_file"
echo "$header_block" | grep -qi 'access-control-allow-credentials: true' || fail 'missing Allow-Credentials'
[[ "$http_code" == "200" || "$http_code" == "204" ]] || fail "preflight HTTP $http_code (is $CORS_ORIGIN in ALLOWED_ORIGINS?)"
echo "$header_block" | grep -qi "access-control-allow-origin: $CORS_ORIGIN" || fail "missing exact Allow-Origin for $CORS_ORIGIN"
ok "CORS preflight ($CORS_ORIGIN)"
echo "NOTE: also run preflight manually from each production Pages origin (see docs/GO_LIVE_VERIFICATION.md §6)."

echo "=== Run isolation + CSRF (in api container) ==="
docker compose -f "$ROOT/compose.yaml" exec -T api \
  sh -c 'cd /app && python tools/verify_run_isolation.py --api-base http://127.0.0.1:8000'
ok "run isolation script"

echo "All automated API checks passed."
