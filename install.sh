#!/usr/bin/env bash
# planetai-node installer. Idempotent — re-run any time.
#   ./install.sh --name <node> [--preset bali|barcelona|boston|santiago] [--lat <lat> --lon <lon>]
#                [--sc 19880] [--airgradient host,host] [--purpleair ip] [--indoor] [--no-bad] [--no-bootstrap]
#   A node needs coordinates. Sensors are optional: with none, it still bootstraps 92 days of CAMS air quality
#   and NASA POWER climatology for its location — free, no key, anywhere on earth.
#   pick at least one sensor flag. --indoor marks LAN sensors as indoor. --no-bad disables the Bali Air Dispatch reference (outside Bali).
# Targets: macOS (Apple Silicon/Intel; OrbStack or Docker Desktop), Debian/Ubuntu/Raspberry Pi OS 64-bit, Arch, Fedora, Windows via WSL2 (Ubuntu).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# ---------------------------------------------------------------- feedback, because run 1 had none
# On 7 September this script printed ONE line — "writing settings, pulling images, building the node" —
# for a phase of several minutes, and then died inside it. The tester could not tell what had been tried,
# what had succeeded, or how long to wait. So: named steps, elapsed seconds on start and finish, a
# heartbeat every 10 s carrying the last interesting line, and on failure the step's NAME first.
#
# No cursor tricks, no spinner, no colour dependence, nothing wider than 80 columns: this has to read the
# same in a terminal, in a pipe, and in a log a tester pastes into an issue.
LOG_FILE="${PLANETAI_INSTALL_LOG:-$PWD/.planetai-install.log}"
STEP_T0=$SECONDS
STEP_N=0; STEP_TOTAL=0; STEP_NAME=""; RUN_T0=$SECONDS
: > "$LOG_FILE"

hb_line() {           # the last thing worth showing: which layer, which image, which build step
  # compose and buildkit redraw with carriage returns, so one "line" of the log holds many frames.
  # Split on \r, keep the frames that name something, take the newest, squeeze the spacing.
  # `|| true` is not decoration: this runs under `set -euo pipefail`, and for the first ten seconds the
  # log is empty, so grep exits 1, the pipeline fails, and the assignment that calls this kills the whole
  # install — silently, before any heartbeat prints. That is exactly what it did.
  { tr '\r' '\n' < "$LOG_FILE" 2>/dev/null \
    | grep -aE 'Downloading|Extracting|Pull complete|Download complete|Verifying|Waiting|Pulling from|Creating|Created|Starting|Started|Healthy|^#[0-9]+ ' \
    | tail -1 | sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/  */ /g' -e 's/^ *//' | cut -c1-62; } 2>/dev/null || true
}
step() {              # step "name"  — announce and start the clock
  STEP_N=$((STEP_N+1)); STEP_NAME="$1"; STEP_T0=$SECONDS
  printf '[%d/%d] %s\n' "$STEP_N" "$STEP_TOTAL" "$1"
}
step_ok()   { printf '        done in %ds\n' $((SECONDS-STEP_T0)); }
step_fail() {         # step_fail "why"
  printf '\n'
  printf 'FAILED: %s\n' "$STEP_NAME"
  printf '  after   %ds\n' $((SECONDS-STEP_T0))
  printf '  reason  %s\n' "${1:-see the log}"
  local l; l="$( { grep -aE 'ERROR|error:|Error|failed|cannot|denied|refused' "$LOG_FILE" 2>/dev/null | tail -1 | cut -c1-70; } || true)"
  [[ -n "$l" ]] && printf '  log     %s\n          %s\n' "$LOG_FILE" "$l" || printf '  log     %s\n' "$LOG_FILE"
  printf '  resume  planetai setup      (your answers are saved; it will not ask them again)\n'
  printf '\ninstall FAILED at step %d/%d "%s" after %ds — %s\n' "$STEP_N" "$STEP_TOTAL" "$STEP_NAME" $((SECONDS-RUN_T0)) "$LOG_FILE"
  exit 1
}
watch_run() {         # watch_run "why it failed" cmd...  — run it, heartbeat every 10s, never go quiet
  local why="$1"; shift
  "$@" >>"$LOG_FILE" 2>&1 &
  local pid=$! last=$SECONDS h
  while kill -0 "$pid" 2>/dev/null; do
    sleep 2
    if (( SECONDS - last >= 10 )); then
      last=$SECONDS; h="$(hb_line || true)"
      printf '        %4ds  %s\n' $((SECONDS-STEP_T0)) "${h:-still working — the tool has printed nothing new yet}"
    fi
  done
  wait "$pid" || step_fail "$why"
}

say()  { printf '\033[1;32m>>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
# Every exit goes through the reporter. `die` predates it and there are a dozen calls: the old-database
# guard, the missing coordinates, the port clash. Each one used to print a bare xx line with no step
# name, no elapsed time and no way back — the shape the tester met on 7 September. Now they all carry
# their step, and the summary line is printed once whichever path exits.
die()  {
  printf '\033[1;31mxx\033[0m %s\n' "$*" >&2
  if [[ -n "${STEP_NAME:-}" ]]; then
    printf '\nFAILED: %s\n' "$STEP_NAME" >&2
    printf '  after   %ds\n' $((SECONDS-STEP_T0)) >&2
    printf '  reason  %s\n' "$*" >&2
    printf '  log     %s\n' "${LOG_FILE:-none yet}" >&2
    printf '  resume  planetai setup      (your answers are saved; it will not ask them again)\n' >&2
    printf '\ninstall FAILED at step %d/%d "%s" after %ds\n' "${STEP_N:-0}" "${STEP_TOTAL:-0}" "$STEP_NAME" $((SECONDS-RUN_T0)) >&2
  else
    printf '\ninstall FAILED before the first step: %s\n' "$*" >&2
  fi
  exit 1
}
need() { command -v "$1" >/dev/null 2>&1; }

ARGS=("$@")                 # kept whole: the docker-group re-exec below needs them after the loop has shifted them away
NAME=""; SC=""; AG=""; PA=""; LAT=""; LON=""; INDOOR=""; NOBAD=""; PRESET=""; NOBOOT=""
SCUSER=""; KIND=""; TZ_=""; YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2;; --sc) SC="$2"; shift 2;; --airgradient) AG="$2"; shift 2;; --purpleair) PA="$2"; shift 2;;
    --lat) LAT="$2"; shift 2;; --lon) LON="$2"; shift 2;; --indoor) INDOOR=1; shift;; --no-bad) NOBAD=1; shift;;
    --preset) PRESET="$2"; shift 2;; --no-bootstrap) NOBOOT=1; shift;;
    --sc-user) SCUSER="$2"; shift 2;; --kind) KIND="$2"; shift 2;; --tz) TZ_="$2"; shift 2;; --yes) YES=1; shift;;
    -h|--help) sed -n '2,6p' "$0"; exit 0;; *) die "unknown flag $1";;
  esac
done

# ---- platform
OS="$(uname -s)"; ARCH="$(uname -m)"
case "$ARCH" in x86_64|amd64) ARCH=amd64;; aarch64|arm64) ARCH=arm64;; *) die "unsupported arch $ARCH (32-bit ARM? use a 64-bit OS)";; esac
if [[ "$OS" == "Darwin" ]]; then PLATFORM=macos
elif [[ "$OS" == "Linux" ]]; then
  # read ID in a subshell: os-release also defines NAME, which would overwrite the --name flag (every Linux node was called "Ubuntu")
  ID="$( . /etc/os-release 2>/dev/null && echo "${ID:-}" )"
  case "${ID:-}" in debian|ubuntu|raspbian|linuxmint|pop) PLATFORM=debian;; arch|manjaro|cachyos|endeavouros) PLATFORM=arch;; fedora|rhel|rocky|almalinux) PLATFORM=fedora;; *) PLATFORM=linux;; esac
else die "unsupported OS $OS"; fi
grep -qi microsoft /proc/version 2>/dev/null && { PLATFORM="wsl-${PLATFORM}"; say "Windows (WSL2) detected"; }
say "platform ${PLATFORM}/${ARCH}"

if [[ "$PLATFORM" != macos ]]; then
  for t in curl make; do need "$t" || {
    # Every sudo this script runs says on the line before what it will do and why. Silence is how an
    # installer ends up looking like something that took liberties with a machine.
    say "$t is missing and the node needs it. This asks for your password to install just that package:"
    case "$PLATFORM" in
      *debian*) echo "     sudo apt-get update && sudo apt-get install -y $t"; sudo apt-get update -qq && sudo apt-get install -y -qq "$t";;
      *arch*)   echo "     sudo pacman -Sy --noconfirm $t";               sudo pacman -Sy --noconfirm "$t";;
      *fedora*) echo "     sudo dnf install -y $t";                       sudo dnf install -y "$t";;
      *)        die "$t is missing and I do not recognise this distribution's package manager. Install $t, then run this again.";;
    esac; }
  done
fi

# ---- the plan, BEFORE the container runtime, not after it. On a fresh Linux box `get.docker.com`
# is the single biggest download of the whole install — hundreds of megabytes of packages — and it
# used to run above the first named step, inside the outer spinner, saying nothing. A tester in
# Menorca watched "writing settings, pulling images, building the node" for twenty minutes on
# 8 September while Docker installed invisibly behind it. Step 1 is the runtime now.
STEP_TOTAL=7
printf '\n%s\n' "Installing a node. Seven steps. Two to six minutes if Docker is already here,"
printf '%s\n' "up to twenty on a fresh Linux box, because Docker itself is a large download."
printf '%s\n' "Progress below. Full log:"
printf '%s\n\n' "  $LOG_FILE"

# ---- docker
# An installed-but-not-running runtime is not a reason to stop: it is a reason to wait. Every tester who hit
# "Docker isn't running" had Docker on the machine and had simply not opened it since the last reboot.
runtime_app() {                     # what is installed here, and the line that starts it
  if   [[ -d /Applications/OrbStack.app ]]; then echo "OrbStack|open -a OrbStack"
  elif [[ -d /Applications/Docker.app   ]]; then echo "Docker Desktop|open -a Docker"
  elif need colima;                           then echo "Colima|colima start"
  elif need systemctl && systemctl list-unit-files docker.service >/dev/null 2>&1; then echo "Docker|sudo systemctl start docker"
  else echo "|"; fi
}
wait_for_daemon() {                 # up to 5 minutes, with the clock visible
  local deadline=$((SECONDS + 300))
  while (( SECONDS < deadline )); do
    docker info >/dev/null 2>&1 && { [[ -t 1 ]] && printf '\r\033[K'; say "container runtime is up"; return 0; }
    [[ -t 1 ]] && printf '\r  waiting for the container runtime … %d:%02d left\033[K' $(( (deadline-SECONDS)/60 )) $(( (deadline-SECONDS)%60 ))
    sleep 2
  done
  [[ -t 1 ]] && printf '\r\033[K'
  return 1
}
step "making sure a container runtime is running"
if ! docker info >/dev/null 2>&1; then
  IFS='|' read -r rt_name rt_start <<< "$(runtime_app)"
  if [[ -n "$rt_name" ]]; then
    say "$rt_name is installed but not running. Starting it — this takes up to a minute on a cold boot."
    case "$rt_start" in
      "sudo systemctl start docker") say "this one needs sudo: it starts the system docker service, nothing else"; $rt_start || true;;
      *) $rt_start >/dev/null 2>&1 || true;;
    esac
    wait_for_daemon || die "$rt_name did not come up within 5 minutes. Open it by hand, wait for it to say it is ready, then:
   planetai setup      (your answers are saved; it will not ask them again)"
  fi
fi
if [[ "$PLATFORM" == "macos" ]]; then
  docker info >/dev/null 2>&1 || die "no container runtime on this Mac. Run 'planetai preflight' — it names the one that installs on this macOS version."
elif [[ "$PLATFORM" == wsl-* ]] && ! need docker; then
  die "Docker not visible inside WSL. Install Docker Desktop for Windows, enable 'Use the WSL 2 based engine' and turn on WSL integration for this distro (Settings → Resources → WSL integration), then re-run."
elif ! need docker; then
  say "there is no container runtime on this machine, and the node is two containers. Installing Docker."
  case "$PLATFORM" in
    *arch*) echo "     sudo pacman -Sy --noconfirm docker docker-compose   (the packages)"
            echo "     sudo systemctl enable --now docker                  (so it starts with the machine)"
            watch_run "pacman could not install docker — check the network and the mirrors" \
              sudo pacman -Sy --noconfirm docker docker-compose
            sudo systemctl enable --now docker || true;;
    *)      echo "     curl -fsSL https://get.docker.com | sh              (Docker's own installer; it uses sudo itself)"
            echo "     the big one: several hundred MB of packages, and it says little while it works"
            watch_run "Docker's own installer failed — its output is in the log" \
              bash -c 'curl -fsSL https://get.docker.com | sh';;
  esac
  say "and one more, so you can use Docker without sudo every time — it adds your user to the docker group:"
  echo "     sudo usermod -aG docker $USER"
  sudo usermod -aG docker "$USER" || true
  warn "added you to the docker group"
fi
# the new group is not in this shell yet: continue under it now (sg), rather than dying with "permission denied
# while trying to connect to the docker API" and asking the person to log out and in
if ! docker info >/dev/null 2>&1 && grep -qw docker <<< "$(id -nG "$USER")" && [[ -z "${PLANETAI_SG:-}" ]] && command -v sg >/dev/null; then
  say "docker group applied for this run (new terminals have it automatically)"
  exec sg docker -c "PLANETAI_SG=1 $(printf '%q ' "$0" "${ARGS[@]}")"
fi
docker info >/dev/null 2>&1 || die "Docker is installed but this user cannot reach it. Log out and back in (the docker group is new), then run the same line again."
docker compose version >/dev/null 2>&1 || die "docker compose plugin missing"
step_ok

# ---- .env
step "writing settings to .env"
if [[ ! -f .env ]]; then cp .env.example .env; chmod 600 .env; fi
setenv() { local k="$1" v="$2"; if grep -q "^${k}=" .env; then
  if [[ "$PLATFORM" == macos ]]; then sed -i '' "s|^${k}=.*|${k}=${v}|" .env; else sed -i "s|^${k}=.*|${k}=${v}|" .env; fi
  else echo "${k}=${v}" >> .env; fi; }
if [[ -n "$PRESET" ]]; then
  [[ -f "presets/${PRESET}.env" ]] || die "no preset '${PRESET}'. Available: $(ls presets/*.env 2>/dev/null | xargs -n1 basename | sed 's/.env//' | tr '\n' ' ')"
  say "applying preset: ${PRESET}"
  while IFS='=' read -r k v; do [[ "$k" =~ ^[A-Z_]+$ ]] && setenv "$k" "$v"; done < "presets/${PRESET}.env"
fi
[[ -n "$NOBOOT" ]] && setenv BOOTSTRAP 0
[[ -n "$NAME" ]] && setenv NODE_NAME "$NAME"
[[ -n "$SC"   ]] && setenv SC_DEVICES "$SC"
[[ -n "${SCUSER:-}" ]] && setenv SC_USER "$SCUSER"
[[ -n "${KIND:-}" ]] && setenv NODE_KIND "$KIND"
[[ -n "${TZ_:-}" ]] && setenv NODE_TZ "$TZ_"
[[ -n "$AG"   ]] && setenv AIRGRADIENT_HOSTS "$AG"
[[ -n "$PA"   ]] && setenv PURPLEAIR_HOSTS "$PA"
[[ -n "$INDOOR" ]] && setenv SENSOR_INDOOR 1
[[ -n "$NOBAD"  ]] && setenv BAD_ENABLED 0
grep -qE '^NODE_LAT=-?[0-9]' .env || die "this node needs coordinates: pass --lat and --lon, or --preset <site>"
if ! grep -qE '^(SC_DEVICES|SC_USER|AIRGRADIENT_HOSTS|PURPLEAIR_HOSTS)=.+' .env; then
  warn "no sensor configured — that is fine. On first start this node will pull 92 days of CAMS air quality"
  warn "and NASA POWER climatology for its coordinates, so it has something true to say before hardware arrives."
  warn "Add a sensor later with --sc / --airgradient / --purpleair, or edit .env."
fi
[[ -n "$LAT"  ]] && setenv NODE_LAT "$LAT"
[[ -n "$LON"  ]] && setenv NODE_LON "$LON"
# from git in a clone, from the VERSION file the tarball carries otherwise. Testers install from the tarball,
# where git describe has nothing to read, and every one of them reported their version as "dev".
setenv NODE_VERSION "$(git describe --tags --always 2>/dev/null || cat VERSION 2>/dev/null || echo dev)"
NEWPW=0
grep -q '^POSTGRES_PASSWORD=change-me' .env && { setenv POSTGRES_PASSWORD "$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"; NEWPW=1; }
# A new .env means a new database password, and a database from an earlier node may still be on this machine (the
# tester deleted the folder to "start over" but Docker kept the volume). The app would then fail to log in on every
# call while pg_isready and the install's own doctor say the database is fine. Refuse now and say which way out.
if [[ $NEWPW -eq 1 ]]; then
  DATA_DIR_SET="$(grep '^DATA_DIR=' .env | cut -d= -f2 | sed 's/[[:space:]]*#.*$//' | tr -d ' ')"
  if { [[ -z "$DATA_DIR_SET" ]] && docker volume inspect planetai_db >/dev/null 2>&1; } || { [[ -n "$DATA_DIR_SET" && -f "$DATA_DIR_SET/PG_VERSION" ]]; }; then
    warn "a database from an earlier node is still on this machine (${DATA_DIR_SET:-Docker volume planetai_db}), and this is a new .env,"
    warn "so its password cannot match. Two ways out:"
    warn "  keep that data:  put the earlier .env back in this folder, then run this again"
    warn "  start clean:     docker volume rm planetai_db   (this deletes the old node's readings), then run this again"
    die "not starting a node whose app cannot log in to its database"
  fi
fi
  [[ -n "$(grep -E "^ADMIN_TOKEN=" .env | cut -d= -f2- | sed "s/[[:space:]]*#.*//" | tr -d " ")" ]] || setenv ADMIN_TOKEN "$(openssl rand -hex 16)"     # unlocks the GUI's settings pages

step_ok

# ---- port clash check
PORT="$(grep '^APP_PORT=' .env | cut -d= -f2 | sed 's/[[:space:]]*#.*$//' | tr -d ' ')"; PORT="${PORT:-8080}"
if [[ -n "$(docker compose ps -q app 2>/dev/null)" ]]; then :; elif lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  warn "port $PORT is already in use on this machine:"; lsof -nP -iTCP:"$PORT" -sTCP:LISTEN | tail -n +2 | awk '{print "     "$1" (pid "$2")"}' | sort -u
  die "set APP_PORT=8081 (or any free port) in .env and re-run"
fi

# ---- up
step "creating the folders the containers write to"
# create the bind-mounted folders first: on Linux, Docker makes a missing one root-owned, and backup.sh then cannot write
mkdir -p backups exports out
step_ok

# `docker compose pull` prints almost nothing when its output is not a terminal — which is exactly the
# case a tester pastes into an issue, and the reason the heartbeat had nothing to show. `docker pull`
# does print one line per layer, piped or not, so pull the image by name. Same result, visible progress.
DB_IMAGE="$(docker compose config --images 2>/dev/null | grep -E '[a-z0-9._-]+/[a-z0-9._-]+' | head -1)"
DB_IMAGE="${DB_IMAGE:-postgis/postgis:16-3.4-alpine}"
step "downloading the database image ${DB_IMAGE} (about 162 MB)"
watch_run "the database image would not download — check the network, then run the resume command" \
  docker pull "$DB_IMAGE"
step_ok

# BUILDKIT_PROGRESS=plain: the fancy renderer redraws with escape codes and leaves a log nobody can read.
# Plain prints one line per build step, which is what the heartbeat reports and what a tester can paste.
step "building this node's own image and starting both containers"
BUILDKIT_PROGRESS=plain watch_run "the image would not build, or a container would not start" \
  docker compose up -d --build
step_ok

# ---- schema on an existing volume (init.sql only runs when the volume is created)
step "waiting for the database, then applying the schema"
for i in $(seq 30); do
  docker compose exec -T db pg_isready -U planetai >/dev/null 2>&1 && break
  (( i % 5 == 0 )) && printf '        %4ds  waiting for the database to accept connections\n' $((SECONDS-STEP_T0))
  sleep 2
done
if docker compose exec -T db pg_isready -U planetai >/dev/null 2>&1; then
  docker compose exec -T db psql -q -v ON_ERROR_STOP=1 -U planetai planetai < init.sql >>"$LOG_FILE" 2>&1 \
    || printf '        the schema was already there (a fresh volume applies it itself)\n'
else
  printf '        the database did not answer in 60s — the checks below will say so\n'
fi
step_ok

# ---- doctor
step "checking what is running"
sleep 2
ok=1
chk() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1"; ok=0; fi; }
echo "doctor:"
chk "all modules in image" "[ \"\$(ls app/*.py | wc -l)\" -eq \"\$(docker compose exec -T app sh -c 'ls /app/*.py | wc -l')\" ]"
chk "db healthy"      "docker compose exec -T db pg_isready -U planetai"
PORT="$(grep '^APP_PORT=' .env | cut -d= -f2 | sed 's/[[:space:]]*#.*$//' | tr -d ' ')"; PORT="${PORT:-8080}"
chk "app answering"   "curl -sf localhost:${PORT}/health"
chk "telegram set"    "grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env"
[[ -x backup.sh ]] || { chmod +x backup.sh; echo "  ✓ backup.sh made executable"; }
step_ok
[[ $ok -eq 1 ]] || warn "something's off: docker compose logs -f app"
grep -qE '^TELEGRAM_BOT_TOKEN=.+' .env || warn "alerts go to the log only until TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS are set in .env (then: docker compose up -d)"

# ---- backup cron (best effort; skip silently if no crontab)
if need crontab && ! grep -q planetai-backup <<< "$(crontab -l 2>/dev/null)"; then
  ( crontab -l 2>/dev/null; echo "17 3 * * * cd $(pwd) && ./backup.sh >/dev/null 2>&1 # planetai-backup" ) | crontab - 2>/dev/null && say "nightly backup scheduled (03:17)"
fi

echo
if grep -qE 'api\.telegram\.org/bot[0-9]+:' <<< "$(docker compose logs app 2>/dev/null)"; then
  warn "a Telegram bot token is visible in this node's container logs (from a version before v0.4.3)."
  warn "Revoke it: message @BotFather -> /revoke -> pick the bot -> put the new token in .env -> make restart"
  warn "Then clear the old logs: docker compose down && docker compose up -d"
fi
echo
if grep -q '^BOOTSTRAP=1' .env; then
  say "first start pulls ~2,200 rows of history for your location (CAMS 92 days + NASA POWER normals)."
  echo "   watch it:  docker compose logs -f app | grep bootstrap"
fi
# One line, pasteable without editing, success or failure.
NAME_NOW="$(grep '^NODE_NAME=' .env | cut -d= -f2- | sed 's/[[:space:]]*#.*$//' | tr -d ' ')"
printf '\ninstall OK — %s, %d steps in %ds, on localhost:%s\n' "${NAME_NOW:-this node}" "$STEP_TOTAL" $((SECONDS-RUN_T0)) "$PORT"
printf 'log: %s\n' "$LOG_FILE"
say "First reading lands within $(grep '^POLL_SECONDS' .env | cut -d= -f2 || echo 300)s."
echo "   make health     (or: curl -s localhost:${PORT}/health | python3 -m json.tool)"
echo "   make stats"
echo "   docker compose logs -f app"
