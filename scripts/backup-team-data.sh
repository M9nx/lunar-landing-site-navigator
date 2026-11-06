#!/usr/bin/env bash
# Example tarball backup for team Compose volumes (adjust paths and schedule).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-$ROOT/backups}"
mkdir -p "$DEST"

archive_volume() {
  local vol="$1"
  local out="$2"
  docker run --rm \
    -v "${vol}:/volume:ro" \
    -v "${DEST}:/backup" \
    alpine:3.20 \
    tar -czf "/backup/${out}" -C /volume .
}

PROJECT="${COMPOSE_PROJECT_NAME:-lunar-landing-site-navigator}"

archive_volume "${PROJECT}_api-data" "api-data-${STAMP}.tar.gz"
archive_volume "${PROJECT}_jupyterhub-hub-db" "jupyterhub-hub-db-${STAMP}.tar.gz"

# Per-user notebook homes (DockerSpawner named volumes)
while IFS= read -r vol; do
  [[ -z "$vol" ]] && continue
  archive_volume "$vol" "${vol}-${STAMP}.tar.gz"
done < <(docker volume ls -q --filter "name=^jupyterhub-user-" 2>/dev/null || true)

if [[ -d "$ROOT/data" ]]; then
  tar -czf "${DEST}/host-data-${STAMP}.tar.gz" -C "$ROOT" data
fi

echo "Wrote backups under ${DEST} (timestamp ${STAMP})"
echo "Restore drill: ./scripts/restore-team-data.sh ${DEST} ${STAMP}"
