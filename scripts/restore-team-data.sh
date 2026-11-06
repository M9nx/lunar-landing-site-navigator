#!/usr/bin/env bash
# Restore archives produced by backup-team-data.sh into Compose volumes.
# Usage: ./scripts/restore-team-data.sh <backup-dir> <timestamp> [compose-project-prefix]
# Example: ./scripts/restore-team-data.sh ./backups 20261105T120000Z
set -euo pipefail
BACKUP_DIR="${1:?backup directory}"
STAMP="${2:?UTC timestamp matching archive names}"
PREFIX="${3:-lunar-landing-site-navigator}"

restore_volume() {
  local vol="$1"
  local archive="$2"
  if [[ ! -f "$archive" ]]; then
    echo "Skip missing $archive" >&2
    return 0
  fi
  docker run --rm \
    -v "${vol}:/volume" \
    -v "${BACKUP_DIR}:/backup:ro" \
    alpine:3.20 \
    sh -c "rm -rf /volume/* /volume/.[!.]* 2>/dev/null; tar -xzf /backup/$(basename "$archive") -C /volume"
  echo "Restored $(basename "$archive") -> $vol"
}

restore_volume "${PREFIX}_api-data" "${BACKUP_DIR}/api-data-${STAMP}.tar.gz"
restore_volume "${PREFIX}_jupyterhub-hub-db" "${BACKUP_DIR}/jupyterhub-hub-db-${STAMP}.tar.gz"

shopt -s nullglob
for archive in "${BACKUP_DIR}/jupyterhub-user-"*"-${STAMP}.tar.gz"; do
  base="$(basename "$archive")"
  vol="${base%-${STAMP}.tar.gz}"
  restore_volume "$vol" "$archive"
done
shopt -u nullglob

if [[ -f "${BACKUP_DIR}/host-data-${STAMP}.tar.gz" ]]; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  tar -xzf "${BACKUP_DIR}/host-data-${STAMP}.tar.gz" -C "$ROOT"
  echo "Restored host data/ under $ROOT"
fi

echo "Restore complete. Restart api and jupyterhub services before verification."
