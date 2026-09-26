#!/usr/bin/env bash
# Резервная копия PostgreSQL (из контейнера db) и архив каталога media/.
# Запускать из корня проекта на VPS: bash deploy/backup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

: "${DB_USER:?Задайте DB_USER в .env}"
: "${DB_NAME:?Задайте DB_NAME в .env}"

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
mkdir -p "$BACKUP_ROOT"
TS="$(date +%Y%m%d_%H%M%S)"

docker compose exec -T db pg_dump -U "$DB_USER" --clean --if-exists "$DB_NAME" \
  | gzip > "${BACKUP_ROOT}/pg_${TS}.sql.gz"

tar czf "${BACKUP_ROOT}/media_${TS}.tgz" media/

echo "Готово: ${BACKUP_ROOT}/pg_${TS}.sql.gz и media_${TS}.tgz"
