#!/usr/bin/env bash
# Copy the repo tunnel template to a private host path (no credentials in git).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST_DIR="${HOME}/.config/lunar-navigator"
DEST="${DEST_DIR}/cloudflare-tunnel.yml"
mkdir -p "$DEST_DIR"
if [[ -f "$DEST" ]]; then
  echo "Already exists: $DEST (not overwritten)"
  exit 0
fi
cp "$ROOT/docs/examples/cloudflare-tunnel.example.yml" "$DEST"
echo "Created $DEST — edit tunnel UUID and credentials-file, then run:"
echo "  cloudflared tunnel --config $DEST run <TUNNEL_UUID>"
