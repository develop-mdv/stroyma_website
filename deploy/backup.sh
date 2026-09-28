#!/usr/bin/env bash
# Резервная копия PostgreSQL (из контейнера db) и архив каталога media/.
# Запускать из корня проекта на VPS: bash deploy/backup.sh
set -euo pipefail
umask 077

cd "$(dirname "$0")/.."

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
mkdir -p "$BACKUP_ROOT"
TS="$(date +%Y%m%d_%H%M%S)"

docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" --clean --if-exists "$POSTGRES_DB"' \
  | gzip > "${BACKUP_ROOT}/pg_${TS}.sql.gz"

tar czf "${BACKUP_ROOT}/media_${TS}.tgz" media/

echo "Готово: ${BACKUP_ROOT}/pg_${TS}.sql.gz и media_${TS}.tgz"
