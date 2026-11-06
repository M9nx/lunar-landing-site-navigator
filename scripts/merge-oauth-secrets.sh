#!/usr/bin/env bash
# Merge GitHub OAuth secrets from a private file into .env (never commit secrets file).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS="${1:-$ROOT/.env.oauth.secrets}"
# Template: docs/examples/oauth-secrets.env.example
ENV="$ROOT/.env"

if [[ ! -f "$SECRETS" ]]; then
  cat >&2 <<EOF
Missing $SECRETS

Create it with (paste values from GitHub OAuth app pages only on this host):

  API_GITHUB_CLIENT_SECRET=...
  HUB_GITHUB_CLIENT_ID=...
  HUB_GITHUB_CLIENT_SECRET=...

Hub Client ID must start with letter O if GitHub shows Ov23… (not zero 0v23).
EOF
  exit 1
fi

python3 <<PY
from pathlib import Path
secrets = {}
for line in Path("$SECRETS").read_text().splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    secrets[k.strip()] = v.strip()
allowed = {
    "API_GITHUB_CLIENT_SECRET",
    "HUB_GITHUB_CLIENT_ID",
    "HUB_GITHUB_CLIENT_SECRET",
}
lines = Path("$ENV").read_text().splitlines()
out = []
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        k = line.split("=", 1)[0].strip()
        if k in allowed and k in secrets and secrets[k]:
            line = f"{k}={secrets[k]}"
    out.append(line)
Path("$ENV").write_text("\\n".join(out) + "\\n")
print("Merged OAuth secrets into .env (keys:", ", ".join(sorted(secrets.keys() & allowed)), ")")
PY
