#!/usr/bin/env bash
# Update a running node in place. Safe to re-run. Backs up first, migrates the schema, rebuilds, checks.
#   ./update.sh              update to whatever is in this folder / on this branch
#   ./update.sh --no-pull    skip git pull (use when you unpacked a tarball over the folder)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

say()  { printf '\033[1;32m>>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f .env ]] || die "no .env here — is this a node folder?"
set -a; . ./.env; set +a
PORT="${APP_PORT:-8080}"
PULL=1; [[ "${1:-}" == "--no-pull" ]] && PULL=0

# 1. back up before touching anything. If this fails, stop.
say "backing up the database first"
./backup.sh || die "backup failed — not updating. Fix the backup, then re-run."

FROM="$(docker compose exec -T db psql -U planetai -tAc "SELECT max(version) FROM schema_version" planetai 2>/dev/null || echo "pre-0.4")"
say "current schema: ${FROM}"

# 2. keep local edits from being silently clobbered
for f in config/rules.yml .env; do
  [[ -f "$f" ]] && cp "$f" "$f.before-update"
done

# 3. get the new code
if [[ $PULL -eq 1 ]] && [[ -d .git ]]; then
  say "pulling"
  git stash list >/dev/null 2>&1
  if ! git pull --ff-only; then
    warn "git pull failed (local changes?). Commit or stash them, or re-run with --no-pull after unpacking manually."
    exit 1
  fi
fi

# 4. apply the schema to the EXISTING database. init.sql only runs on a fresh volume; this is the other half.
say "applying schema (idempotent)"
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U planetai planetai < init.sql >/dev/null \
  || die "schema failed to apply — your data is untouched and the backup is in ${BACKUP_DIR:-./backups}"

# 5. new settings keys, without overwriting anything you set
say "checking .env for new settings"
NEW=0
while IFS= read -r line; do
  k="${line%%=*}"
  [[ "$k" =~ ^[A-Z_]+$ ]] || continue
  grep -q "^${k}=" .env || { echo "$line" >> .env; echo "   + ${k}"; NEW=$((NEW+1)); }
done < .env.example
[[ $NEW -eq 0 ]] && echo "   nothing new" || warn "${NEW} new setting(s) added with defaults — review .env"

# 6. rebuild and restart
say "rebuilding"
docker compose up -d --build

# 7. verify
sleep 8
TO="$(docker compose exec -T db psql -U planetai -tAc "SELECT max(version) FROM schema_version" planetai 2>/dev/null || echo "?")"
ok=1
chk(){ if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1"; ok=0; fi; }
echo "doctor:"
chk "all modules in image" "[ \"\$(ls app/*.py | wc -l)\" -eq \"\$(docker compose exec -T app sh -c 'ls /app/*.py | wc -l')\" ]"
chk "db healthy"        "docker compose exec -T db pg_isready -U planetai"
chk "app answering"     "curl -sf localhost:${PORT}/health"
chk "readings intact"   "[ \$(docker compose exec -T db psql -U planetai -tAc 'SELECT count(*) FROM readings' planetai) -gt 0 ]"
chk "views rebuilt"     "curl -sf localhost:${PORT}/stats"
chk "packs loaded"      "curl -sf localhost:${PORT}/packs"
echo
if docker compose logs app 2>/dev/null | grep -qE 'api\.telegram\.org/bot[0-9]+:'; then
  warn "a Telegram bot token is visible in this node's container logs (logged by versions before v0.4.3)."
  warn "Revoke it via @BotFather /revoke, update .env, then: docker compose down && docker compose up -d"
fi
say "schema ${FROM} → ${TO}"
if [[ -f config/rules.yml.before-update ]] && ! diff -q config/rules.yml config/rules.yml.before-update >/dev/null 2>&1; then
  warn "config/rules.yml changed in this update. Your previous copy: config/rules.yml.before-update"
  warn "If you had edited thresholds, re-apply them — or better, move them into a pack (docs/PACKS.md)."
fi
[[ $ok -eq 1 ]] || die "something is off: docker compose logs app | tail -40"
say "updated. Nothing was lost: $(docker compose exec -T db psql -U planetai -tAc 'SELECT count(*) FROM readings' planetai | tr -d ' ') readings, $(docker compose exec -T db psql -U planetai -tAc 'SELECT count(*) FROM alerts' planetai | tr -d ' ') alerts, $(docker compose exec -T db psql -U planetai -tAc 'SELECT count(*) FROM actions' planetai | tr -d ' ') actions."
