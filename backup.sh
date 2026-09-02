#!/usr/bin/env bash
# Nightly pg_dump. Keeps 14 days. Point BACKUP_DIR at a NAS mount so the node dying doesn't take the record with it.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
DIR="$(grep '^BACKUP_DIR=' .env | cut -d= -f2- | tr -d '"')"; DIR="${DIR:-./backups}"
mkdir -p "$DIR"
NAME="$(grep '^NODE_NAME=' .env | cut -d= -f2-)"
docker compose exec -T db pg_dump -U planetai planetai | gzip > "$DIR/${NAME:-node}-$(date +%F).sql.gz"
find "$DIR" -name '*.sql.gz' -mtime +14 -delete
echo "backup: $DIR/${NAME:-node}-$(date +%F).sql.gz"
