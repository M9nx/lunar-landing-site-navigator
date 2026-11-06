#!/usr/bin/env bash
# B7: repeat GET /health and GET /v1/benchmark/status; write JSON for review (infrastructure only).
# Does not authenticate; does not call POST /v1/compare.
set -euo pipefail
API_BASE="${1:-http://127.0.0.1:8000}"
ITERATIONS="${2:-30}"
OUT_JSON="${3:-research-results/b7_api_benchmark_sample.json}"
API_BASE="${API_BASE%/}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_ABS="${OUT_JSON}"
case "$OUT_ABS" in
  /*) ;;
  *) OUT_ABS="$ROOT/$OUT_JSON" ;;
esac
mkdir -p "$(dirname "$OUT_ABS")"

python3 - "$API_BASE" "$ITERATIONS" "$OUT_ABS" <<'PY'
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

base, iterations_s, out_path = sys.argv[1:4]
iterations = max(1, int(iterations_s))

def curl_json(url):
    r = subprocess.run(
        ["curl", "-sS", "-w", "\n%{http_code}", url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        return {"error": "curl_failed", "stderr": r.stderr}
    lines = r.stdout.strip().split("\n")
    code = lines[-1]
    body = "\n".join(lines[:-1])
    if not body:
        return {"http_code": int(code), "error": "empty_body"}
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"http_code": int(code), "raw": body[:500]}
    if isinstance(data, dict):
        data = dict(data)
        data["http_code"] = int(code)
    return data

health_times = []
bench_times = []
health_payloads = []
bench_payloads = []

for i in range(iterations):
    t0 = time.perf_counter()
    h = curl_json(f"{base}/health")
    health_times.append((time.perf_counter() - t0) * 1000.0)
    health_payloads.append(h)

    t0 = time.perf_counter()
    b = curl_json(f"{base}/v1/benchmark/status")
    bench_times.append((time.perf_counter() - t0) * 1000.0)
    bench_payloads.append(b)

def stats(xs):
    if not xs:
        return None
    xs = sorted(xs)
    return {
        "n": len(xs),
        "min_ms": round(min(xs), 3),
        "median_ms": round(xs[len(xs) // 2], 3),
        "max_ms": round(max(xs), 3),
        "mean_ms": round(sum(xs) / len(xs), 3),
    }

payload = {
    "collection_utc": datetime.now(timezone.utc).isoformat(),
    "api_base": base,
    "iterations": iterations,
    "interpretation": (
        "Round-trip client time for curl+JSON parse only; "
        "not a substitute for server-only benchmark/status sqlite_ping_ms."
    ),
    "curl_total_ms": {
        "health": stats(health_times),
        "v1_benchmark_status": stats(bench_times),
    },
    "last_health": health_payloads[-1] if health_payloads else None,
    "last_benchmark_status": bench_payloads[-1] if bench_payloads else None,
}

if isinstance(payload["last_benchmark_status"], dict):
    pings = [
        p.get("sqlite_ping_ms")
        for p in bench_payloads
        if isinstance(p, dict) and p.get("sqlite_ping_ms") is not None
    ]
    if pings:
        payload["sqlite_ping_ms_from_json"] = {
            "n": len(pings),
            "min": min(pings),
            "median": sorted(pings)[len(pings) // 2],
            "max": max(pings),
        }

os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
print("Wrote:", out_path)
PY
