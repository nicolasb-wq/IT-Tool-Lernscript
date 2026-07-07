#!/usr/bin/env bash
# Nächtliches Postgres-Backup (pg_dump, gzip), behält die letzten 14 Stände.
# Cron-Beispiel (als root, Pfad anpassen):
#   0 3 * * * /opt/lernscript/scripts/backup.sh >> /var/log/lernscript-backup.log 2>&1
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${APP_DIR}/backups"
KEEP=14

mkdir -p "${BACKUP_DIR}"
STAMP="$(date +%Y-%m-%d_%H%M)"

cd "${APP_DIR}"
docker compose exec -T db pg_dump -U lernscript lernscript \
  | gzip > "${BACKUP_DIR}/lernscript_${STAMP}.sql.gz"

# Alte Backups aufräumen (die neuesten $KEEP behalten)
ls -1t "${BACKUP_DIR}"/lernscript_*.sql.gz | tail -n +$((KEEP + 1)) | xargs -r rm --

echo "[$(date -Is)] Backup OK: lernscript_${STAMP}.sql.gz"
