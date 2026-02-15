#!/usr/bin/env bash
# Ручной дамп PostgreSQL. Использование:
#   DATABASE_URL='postgresql://...' ./scripts/backup_db.sh
# или
#   export DATABASE_URL="..."
#   ./scripts/backup_db.sh
#
# Создаёт файл db_backup_YYYYMMDD_HHMMSS.dump в текущей директории (custom format pg_dump).

set -e
if [ -z "${DATABASE_URL}" ]; then
  echo "Ошибка: задайте DATABASE_URL (например export DATABASE_URL='postgresql://...')" >&2
  exit 1
fi
DATE=$(date +%Y%m%d_%H%M%S)
OUT="db_backup_${DATE}.dump"
pg_dump "$DATABASE_URL" -Fc -f "$OUT"
echo "Создан дамп: $OUT"
