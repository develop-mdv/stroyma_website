#!/usr/bin/env bash
# Восстановление из архива pg_*.sql.gz (gunzip | psql).
# Использование: bash deploy/restore.sh backups/pg_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail

cd "$(dirname "$0")/.."

DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Укажите путь к pg_*.sql.gz: bash deploy/restore.sh backups/pg_....sql.gz"
  exit 1
fi

echo "Восстановление БД из $DUMP (остановите сайт при необходимости)..."
gunzip -c "$DUMP" | docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Готово."
