#!/usr/bin/env bash
# Nightly pg_dump. Keeps 14 days. Point BACKUP_DIR at a NAS mount so the node dying doesn't take the record with it.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
env_get(){ grep "^$1=" .env | tail -1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//' | tr -d '"'"'"' ' | head -1; }
DIR="$(env_get BACKUP_DIR)"; DIR="${DIR:-./backups}"
mkdir -p "$DIR"
NAME="$(env_get NODE_NAME)"
docker compose exec -T db pg_dump -U planetai planetai | gzip > "$DIR/${NAME:-node}-$(date +%F).sql.gz"
find "$DIR" -name '*.sql.gz' -mtime +14 -delete
echo "backup: $DIR/${NAME:-node}-$(date +%F).sql.gz"
