#!/usr/bin/env bash
# Update a running node in place. Safe to re-run. Backs up first, migrates the schema, rebuilds, checks.
#   ./update.sh              update to whatever is in this folder / on this branch
#   ./update.sh --no-pull    skip git pull (use when you unpacked a tarball over the folder)
set -euo pipefail

# Bash reads a script as it runs. This script pulls new code, which rewrites the file bash is reading, and
# from that point it executes from a byte offset in a different file: steps skipped, steps garbled. So on first
# entry, copy to a temp file and run from there; the copy is immune to the pull.
if [[ -z "${PLANETAI_UPDATE_COPY:-}" ]]; then
  NODE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"          # the node folder, resolved BEFORE we leave it
  tmp="$(mktemp -t planetai-update.XXXXXX)"; cp "${BASH_SOURCE[0]}" "$tmp"
  PLANETAI_UPDATE_COPY="$NODE_DIR" exec bash "$tmp" "$@"
fi
trap 'rm -f "${BASH_SOURCE[0]}"' EXIT      # the temp copy
cd "$PLANETAI_UPDATE_COPY"                 # back into the node folder; the copy lives in /tmp

say()  { printf '\033[1;32m>>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

[[ -f .env ]] || die "no .env here — is this a node folder?"
# `.env` is sourced below, so a stray space after `=` makes the shell try to run the value as a command.
# Catch it here and name the line, rather than failing with "command not found".
bad="$(grep -nE '^[A-Z_]+=[[:space:]]+[^[:space:]#]' .env || true)"
if [[ -n "$bad" ]]; then
  printf '\033[1;31mxx .env has a space after `=`, which the shell reads as a command:\033[0m\n' >&2
  printf '   %s\n' "$bad" >&2
  printf '   Remove the spaces so it reads NAME=value, then run this again.\n' >&2
  exit 1
fi
set -a; . ./.env; set +a
# nodes installed before v0.14 have no admin token; the GUI needs one to change settings
rand_hex() { openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
# judge the VALUE, not the line: a line like `ADMIN_TOKEN=   # comment` has text after = and no value
envval() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//' | tr -d '" '; }
if [[ -z "$(envval ADMIN_TOKEN)" ]]; then
  tok="$(rand_hex)"; [[ -n "$tok" ]] || die "could not generate a random token (no openssl, no /dev/urandom?)"
  if grep -q "^ADMIN_TOKEN=" .env; then sed -i.bak "s|^ADMIN_TOKEN=.*|ADMIN_TOKEN=${tok}|" .env && rm -f .env.bak; else echo "ADMIN_TOKEN=${tok}" >> .env; fi
  echo "   + ADMIN_TOKEN (for the GUI; planetai ui shows it)"
fi
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
if [[ $PULL -eq 1 ]] && [[ ! -d .git ]] && [[ -f VERSION ]]; then
  # installed from the tarball (no repository access): fetch the current one and unpack over this folder
  say "updating from ${PLANETAI_SITE:-https://planetai.fab.city/node0}"
  tmp="$(mktemp -d)"
  if curl -fsSL "${PLANETAI_SITE:-https://planetai.fab.city/node0}/get/planetai-node.tar.gz" -o "$tmp/n.tar.gz"; then
    tar xzf "$tmp/n.tar.gz" -C "$tmp" && ( cd "$tmp/planetai-node" && tar cf - . ) | tar xf - --exclude=.env
    say "now $(cat VERSION 2>/dev/null || echo '?')"
  else
    warn "could not reach the site; keeping the version you have"
  fi
  rm -rf "$tmp"
elif [[ $PULL -eq 1 ]] && [[ -d .git ]]; then
  say "pulling"
  # name the remote and branch explicitly: a clone repaired by hand may have no upstream set
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
  git branch --set-upstream-to="origin/$branch" "$branch" >/dev/null 2>&1 || true
  git fetch -q --tags origin 2>/dev/null || true      # pulling a named branch skips tags; version stamps need them
  if ! git pull --ff-only origin "$branch"; then
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
NEW=0; HDR=0
while IFS= read -r line; do
  k="${line%%=*}"
  [[ "$k" =~ ^[A-Z_]+$ ]] || continue
  if ! grep -q "^${k}=" .env; then
    # new keys go under their own dated marker, not silently under whatever heading happens to be last
    [[ $HDR -eq 0 ]] && { printf '\n# ---- added by update on %s (see .env.example for what each does) ----\n' "$(date +%F)" >> .env; HDR=1; }
    echo "$line" >> .env; echo "   + ${k}"; NEW=$((NEW+1))
  fi
done < .env.example
[[ $NEW -eq 0 ]] && echo "   nothing new" || warn "${NEW} new setting(s) added with defaults — review .env"

# 6. rebuild and restart
# stamp the version the node is about to run, from git, so /health and planetai status report it
if grep -q "^NODE_VERSION=" .env; then sed -i.bak "s|^NODE_VERSION=.*|NODE_VERSION=$(git describe --tags --always 2>/dev/null || echo dev)|" .env && rm -f .env.bak; else echo "NODE_VERSION=$(git describe --tags --always 2>/dev/null || echo dev)" >> .env; fi
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
