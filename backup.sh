#!/usr/bin/env bash
# Nightly: back up the database, export yesterday as open data, and copy both wherever you said.
#
#   BACKUP_DIR      where dumps go. Local disk, a NAS mount, a USB drive. Default ./backups
#   BACKUP_KEEP     days of dumps to keep locally (default 30)
#   BACKUP_REMOTE   optional rclone destination, e.g. b2:planetai-bali/bayu-2 or r2:planetai/bayu-2 or nas:planetai
#                   — 40+ backends (S3, B2, R2, Google Drive, Dropbox, SFTP, WebDAV, Nextcloud...). rclone config once.
#   EXPORT_ENABLED  1 (default): write exports/<node>/YYYY-MM-DD.json — hourly means, cells, alerts, rho. Never raw.
#   IPFS_PUBLISH    1: add the export to IPFS (the ipfs compose profile) and record its CID
#
# A mount that is not mounted is the trap: mkdir -p would create a local folder with the NAS's name and back up
# into the node's own disk while claiming otherwise. Anything under /Volumes or /mnt or /media must be a mountpoint.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# a missing key returns empty, never a failure: under set -e a failing grep inside $(...) kills the script silently
env_get(){ { grep "^$1=" .env 2>/dev/null || true; } | tail -1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//' | tr -d '"'"'"' ' | head -1; }
NAME="$(env_get NODE_NAME)"; NAME="${NAME:-node}"
DIR="$(env_get BACKUP_DIR)"; DIR="${DIR:-./backups}"
KEEP="$(env_get BACKUP_KEEP)"; KEEP="${KEEP:-30}"
REMOTE="$(env_get BACKUP_REMOTE)"
EXPORT="$(env_get EXPORT_ENABLED)"; EXPORT="${EXPORT:-1}"
IPFS="$(env_get IPFS_PUBLISH)"; IPFS="${IPFS:-0}"
PORT="$(env_get APP_PORT)"; PORT="${PORT:-8080}"
STAMP="$(date +%F)"
log(){ printf '%s backup: %s\n' "$(date +%H:%M)" "$*"; }
die(){ printf '%s backup FAILED: %s\n' "$(date +%H:%M)" "$*" >&2; exit 1; }

# ---- 1. the destination must be real
case "$DIR" in
  /Volumes/*|/mnt/*|/media/*)
    top="$(echo "$DIR" | cut -d/ -f1-3)"
    if ! mount | grep -q " on ${top} "; then
      die "$top is not mounted. Refusing to create a local folder with its name. Mount the drive, or change BACKUP_DIR."
    fi;;
esac
mkdir -p "$DIR" || die "cannot create $DIR"
[[ -w "$DIR" ]] || die "$DIR is not writable"

# ---- 2. dump, and prove the dump is a database
OUT="$DIR/${NAME}-${STAMP}.sql.gz"
docker compose exec -T db pg_dump -U planetai planetai | gzip > "$OUT.tmp" || die "pg_dump failed"
gzip -t "$OUT.tmp" 2>/dev/null || die "the dump is not a valid gzip"
if ! gunzip -c "$OUT.tmp" | grep -q "CREATE TABLE.*readings" ; then rm -f "$OUT.tmp"; die "the dump has no readings table — refusing to keep it"; fi
mv "$OUT.tmp" "$OUT"
log "$OUT ($(du -h "$OUT" | cut -f1))"
find "$DIR" -name "${NAME}-*.sql.gz" -mtime "+${KEEP}" -delete

# ---- 3. yesterday, as open data (hourly means, cells, alerts, rho — no raw readings, no secrets)
if [[ "$EXPORT" == "1" ]]; then
  EXD="exports/${NAME}"; mkdir -p "$EXD"
  Y="$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)"
  if curl -fsS --max-time 60 "http://localhost:${PORT}/export?day=${Y}" -o "$EXD/${Y}.json.tmp"; then
    python3 -c "import json,sys; d=json.load(open('$EXD/${Y}.json.tmp')); assert 'hourly' in d" 2>/dev/null && mv "$EXD/${Y}.json.tmp" "$EXD/${Y}.json" && log "export $EXD/${Y}.json" || { rm -f "$EXD/${Y}.json.tmp"; log "export skipped: node returned no data for $Y"; }
  else
    rm -f "$EXD/${Y}.json.tmp"; log "export skipped: node not answering on $PORT"
  fi
  # ---- 4. publish to IPFS: content-addressed, public by design — which is why only the export goes, never the dump
  if [[ "$IPFS" == "1" && -f "$EXD/${Y}.json" ]]; then
    if CID="$(docker compose exec -T ipfs ipfs add -Q --pin=true "/export/${NAME}/${Y}.json" 2>/dev/null)"; then
      echo "${Y} ${CID}" >> "$EXD/CIDS.txt"; log "ipfs $CID"
    else log "ipfs skipped: is the ipfs profile running? planetai ipfs"; fi
  fi
fi

# ---- 5. copy off the machine
if [[ -n "$REMOTE" ]]; then
  if command -v rclone >/dev/null; then
    rclone copy --max-age 3d "$DIR" "$REMOTE/backups" 2>&1 | tail -2 || log "rclone: backups copy failed"
    [[ -d "exports/${NAME}" ]] && rclone copy "exports/${NAME}" "$REMOTE/exports" 2>&1 | tail -2 || true
    log "copied to $REMOTE"
  else
    log "BACKUP_REMOTE is set but rclone is not installed (brew install rclone / apt install rclone)"
  fi
fi
date -u +%FT%TZ > "$DIR/LAST_OK"
