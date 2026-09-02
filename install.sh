#!/usr/bin/env bash
# planetai-node installer. Idempotent — re-run any time.
#   ./install.sh [--name bayu-2] [--sc 19880] [--lat -8.8271 --lon 115.15709]
# Tested targets: macOS (Apple Silicon/Intel, needs OrbStack or Docker Desktop), Debian/Ubuntu/Raspberry Pi OS 64-bit, Arch, Fedora.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

say()  { printf '\033[1;32m>>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1; }

NAME=""; SC=""; LAT=""; LON=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2;; --sc) SC="$2"; shift 2;; --lat) LAT="$2"; shift 2;; --lon) LON="$2"; shift 2;;
    -h|--help) sed -n '2,5p' "$0"; exit 0;; *) die "unknown flag $1";;
  esac
done

# ---- platform
OS="$(uname -s)"; ARCH="$(uname -m)"
case "$ARCH" in x86_64|amd64) ARCH=amd64;; aarch64|arm64) ARCH=arm64;; *) die "unsupported arch $ARCH (32-bit ARM? use a 64-bit OS)";; esac
if [[ "$OS" == "Darwin" ]]; then PLATFORM=macos
elif [[ "$OS" == "Linux" ]]; then . /etc/os-release 2>/dev/null || true
  case "${ID:-}" in debian|ubuntu|raspbian|linuxmint|pop) PLATFORM=debian;; arch|manjaro|cachyos|endeavouros) PLATFORM=arch;; fedora|rhel|rocky|almalinux) PLATFORM=fedora;; *) PLATFORM=linux;; esac
else die "unsupported OS $OS"; fi
say "platform ${PLATFORM}/${ARCH}"

# ---- docker
if [[ "$PLATFORM" == "macos" ]]; then
  need docker && docker info >/dev/null 2>&1 || die "Docker isn't running. Install OrbStack (https://orbstack.dev, recommended) or Docker Desktop, start it, re-run."
elif ! need docker; then
  say "installing docker"
  case "$PLATFORM" in
    arch) sudo pacman -Sy --noconfirm docker docker-compose && sudo systemctl enable --now docker;;
    *)    curl -fsSL https://get.docker.com | sh;;
  esac
  sudo usermod -aG docker "$USER" || true
  warn "added you to the docker group — if 'docker ps' fails, log out/in and re-run."
fi
docker compose version >/dev/null 2>&1 || die "docker compose plugin missing"

# ---- .env
if [[ ! -f .env ]]; then cp .env.example .env; chmod 600 .env; say "created .env from .env.example"; fi
setenv() { local k="$1" v="$2"; if grep -q "^${k}=" .env; then
  if [[ "$PLATFORM" == macos ]]; then sed -i '' "s|^${k}=.*|${k}=${v}|" .env; else sed -i "s|^${k}=.*|${k}=${v}|" .env; fi
  else echo "${k}=${v}" >> .env; fi; }
[[ -n "$NAME" ]] && setenv NODE_NAME "$NAME"
[[ -n "$SC"   ]] && setenv SC_DEVICES "$SC"
[[ -n "$LAT"  ]] && setenv NODE_LAT "$LAT"
[[ -n "$LON"  ]] && setenv NODE_LON "$LON"
grep -q '^POSTGRES_PASSWORD=change-me' .env && setenv POSTGRES_PASSWORD "$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"

# ---- up
say "building and starting"
docker compose pull db 2>/dev/null || true
docker compose up -d --build

# ---- doctor
sleep 8
ok=1
chk() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1"; ok=0; fi; }
echo "doctor:"
chk "db healthy"      "docker compose exec -T db pg_isready -U planetai"
chk "app answering"   "curl -sf localhost:8080/health"
chk "telegram set"    "grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env"
[[ $ok -eq 1 ]] || warn "something's off: docker compose logs -f app"
grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env || warn "alerts go to the log only until TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS are set in .env (then: docker compose up -d)"

# ---- backup cron (best effort; skip silently if no crontab)
if need crontab && ! crontab -l 2>/dev/null | grep -q planetai-backup; then
  ( crontab -l 2>/dev/null; echo "17 3 * * * cd $(pwd) && ./backup.sh >/dev/null 2>&1 # planetai-backup" ) | crontab - 2>/dev/null && say "nightly backup scheduled (03:17)"
fi

echo
say "done. First reading lands within $(grep '^POLL_SECONDS' .env | cut -d= -f2 || echo 300)s."
echo "   curl -s localhost:8080/health | python3 -m json.tool"
echo "   curl -s localhost:8080/stats  | python3 -m json.tool"
echo "   docker compose logs -f app"
