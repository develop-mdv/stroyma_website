#!/usr/bin/env bash
# Восстановление из архива pg_*.sql.gz (gunzip | psql).
# Использование: bash deploy/restore.sh backups/pg_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a && source .env && set +a
fi

: "${DB_USER:?Задайте DB_USER в .env}"
: "${DB_NAME:?Задайте DB_NAME в .env}"

DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Укажите путь к pg_*.sql.gz: bash deploy/restore.sh backups/pg_....sql.gz"
  exit 1
fi

echo "Восстановление БД из $DUMP (остановите сайт при необходимости)..."
gunzip -c "$DUMP" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"

echo "Готово."
