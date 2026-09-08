#!/usr/bin/env bash
# Everything the node needs from a machine, checked before it asks anybody anything.
#
#   curl -fsSL planetai.fab.city/preflight | bash     # nothing installed yet
#   planetai preflight [--json]                        # on a node
#
# Self-contained on purpose: it is fetched and run on its own, before the code is downloaded, so it may not
# assume the repository, .env, docker, python or anything else is there. It reads; it never writes, never
# sudos, never installs and never asks a question.
#
# Exit codes, because two callers depend on them:
#   0  every row passed — go
#   1  something failed that this tester can fix; each ✗ carries the line that fixes it
#   2  no container runtime can be installed on this OS version. Not an error: an answer.
#      The installer prints the verdict and exits 0 on this one.
set -uo pipefail        # not -e: a failing check is the point

JSON=0; [[ "${1:-}" == "--json" ]] && JSON=1
G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; B=$'\033[1m'; N=$'\033[0m'
[[ -t 1 ]] || { G=""; R=""; Y=""; D=""; B=""; N=""; }

rows=""; fails=0; floor=0
# row NAME "value" PASS "fix line"
row() {
  local name="$1" val="$2" pass="$3" fix="${4:-}"
  [[ "$pass" == 1 ]] || fails=$((fails+1))
  if [[ $JSON -eq 1 ]]; then
    rows+="$(printf '{"check":"%s","value":"%s","ok":%s,"fix":%s}' \
      "$name" "$(sed 's/"/\\"/g' <<<"$val")" \
      "$([[ $pass == 1 ]] && echo true || echo false)" \
      "$([[ "$pass" != 1 && -n "$fix" ]] && printf '"%s"' "$(sed 's/"/\\"/g' <<<"$fix")" || echo null)"),"
  else
    printf '  %-13s %-38.38s %s\n' "$name" "$val" "$([[ $pass == 1 ]] && echo "${G}✓${N}" || echo "${R}✗${N}")"
    [[ $pass == 1 || -z "$fix" ]] || printf '                %s%s%s\n' "$D" "$fix" "$N"
  fi
}

# ---------------------------------------------------------------- os and arch
OS="$(uname -s)"; ARCH="$(uname -m)"
case "$ARCH" in x86_64|amd64) ARCH=x86_64;; aarch64|arm64) ARCH=arm64;; esac
MAC_MAJOR=0; MAC_MINOR=0; OSNAME="$OS"; PLATFORM=other

if [[ "$OS" == Darwin ]]; then
  PLATFORM=macos
  VER="$(sw_vers -productVersion 2>/dev/null || echo 0)"
  MAC_MAJOR="${VER%%.*}"; MAC_MINOR="$(cut -d. -f2 <<<"$VER.0")"
  case "$MAC_MAJOR" in 12) CODENAME=Monterey;; 13) CODENAME=Ventura;; 14) CODENAME=Sonoma;; 15) CODENAME=Sequoia;; 26) CODENAME=Tahoe;; *) CODENAME="";; esac
  OSNAME="macOS $VER${CODENAME:+ ($CODENAME)}"
elif [[ "$OS" == Linux ]]; then
  PLATFORM=linux
  OSNAME="$( . /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-Linux}" )"
  grep -qi microsoft /proc/version 2>/dev/null && { PLATFORM=wsl; OSNAME="$OSNAME (WSL2)"; }
fi

# The macOS floor, measured against the three runtimes' own documentation (docs/PLATFORMS.md carries the links):
#   OrbStack       macOS 14.0+
#   Docker Desktop the current and two previous major releases — 14 today, and it moves
#   Colima         macOS 13.0+, and on Intel the vz backend cannot boot a guest below 13.5
# So 13.5 is the floor for a Mac, and below it nothing is installable.
MAC_FLOOR_OK=1
if [[ "$PLATFORM" == macos ]]; then
  if [[ "$MAC_MAJOR" -lt 13 ]] || { [[ "$MAC_MAJOR" -eq 13 ]] && [[ "$MAC_MINOR" -lt 5 ]]; }; then MAC_FLOOR_OK=0; floor=1; fi
fi

[[ $JSON -eq 1 ]] || printf '\n%spreflight%s  %sno questions, no changes, nothing installed%s\n\n' "$B" "$N" "$D" "$N"

if [[ "$PLATFORM" == macos ]]; then
  row os "$OSNAME" "$MAC_FLOOR_OK" "macOS 13.5 or newer is required — see the verdict below"
elif [[ "$PLATFORM" == linux || "$PLATFORM" == wsl ]]; then
  row os "$OSNAME" 1
else
  row os "$OSNAME" 0 "the node runs on macOS, Linux, or Windows through WSL2"
fi

case "$ARCH" in
  x86_64) row arch "x86_64" 1;;
  arm64)  if [[ "$PLATFORM" == macos ]]; then row arch "arm64 (amd64 images emulated)" 1
          else row arch "arm64" 0 "the node's database image (postgis/postgis:16-3.4-alpine) is published for linux/amd64 only. Not a Raspberry Pi yet: docs/PLATFORMS.md"; fi;;
  *)      row arch "$ARCH" 0 "unsupported architecture; a 64-bit x86 or Apple Silicon machine is needed";;
esac

# ---------------------------------------------------------------- memory
MEMB=0
if [[ "$PLATFORM" == macos ]]; then
  # /usr/sbin is not on every PATH, and a check that cannot measure must not report 0 GB and fail —
  # that is the same lie this whole script exists to stop telling.
  MEMB="$(sysctl -n hw.memsize 2>/dev/null || /usr/sbin/sysctl -n hw.memsize 2>/dev/null || echo 0)"
else MEMB=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0) * 1024 )); fi
MEMGB=$(( MEMB / 1073741824 ))
# 4 GB is Docker Desktop's own stated minimum; WSL2's is 8 GB.
MEMNEED=4; [[ "$PLATFORM" == wsl ]] && MEMNEED=8
if [[ $MEMB -eq 0 ]]; then row memory "could not read it" 1
else row memory "${MEMGB} GB" "$([[ $MEMGB -ge $MEMNEED ]] && echo 1 || echo 0)" \
  "${MEMNEED} GB is the container runtime's own minimum; this machine has ${MEMGB} GB"; fi

# ---------------------------------------------------------------- disk
TARGET="${PLANETAI_HOME:-$HOME}"; [[ -d "$TARGET" ]] || TARGET="$HOME"
FREEK="$(df -Pk "$TARGET" 2>/dev/null | awk 'NR==2{print $4}')"; FREEK="${FREEK:-0}"
FREEGB=$(( FREEK / 1048576 ))
MOUNT="$(df -P "$TARGET" 2>/dev/null | awk 'NR==2{print $6}')"
row "disk free" "${FREEGB} GB on ${MOUNT:-/}" "$([[ $FREEGB -ge 3 ]] && echo 1 || echo 0)" \
  "the images and the database need about 3 GB free; ${FREEGB} GB is left on ${MOUNT:-/}"

# ---------------------------------------------------------------- container runtime
have() { command -v "$1" >/dev/null 2>&1; }
APPS="${PLANETAI_APPS:-/Applications}"     # substitutable so a test can present a machine with no runtime
DOCKER_STATIC_URL="https://download.docker.com/mac/static/stable/${ARCH}/docker-27.3.1.tgz"
COLIMA_LINES="curl -fsSL -o /tmp/colima https://github.com/abiosoft/colima/releases/latest/download/colima-Darwin-$(uname -m) && sudo install /tmp/colima /usr/local/bin/colima && colima start --vm-type vz --cpu 2 --memory 4 --disk 20"

runtime_fix() {
  case "$PLATFORM" in
    macos)
      if   [[ "$MAC_MAJOR" -ge 14 ]]; then echo "open https://orbstack.dev/download   (OrbStack, free for personal use; Docker Desktop also works on macOS ${MAC_MAJOR})"
      elif [[ $MAC_FLOOR_OK -eq 1 ]];  then echo "$COLIMA_LINES"
      else echo "nothing is installable on macOS ${MAC_MAJOR}.${MAC_MINOR} — see the verdict below"; fi;;
    wsl)   echo "install Docker Desktop for Windows, turn on 'Use the WSL 2 based engine' and WSL integration for this distro, then run this again";;
    linux) echo "the installer adds Docker itself (curl -fsSL https://get.docker.com | sh). Nothing to do now.";;
    *)     echo "";;
  esac
}

RT_NAME=""; RT_STATE=""
if have docker && docker info >/dev/null 2>&1; then RT_NAME="docker"; RT_STATE=running
elif have docker || have colima || [[ -d "$APPS/OrbStack.app" || -d "$APPS/Docker.app" ]]; then RT_STATE=installed
  if   [[ -d "$APPS/OrbStack.app" ]]; then RT_NAME="OrbStack"
  elif [[ -d "$APPS/Docker.app" ]];   then RT_NAME="Docker Desktop"
  elif have colima;                          then RT_NAME="Colima"
  else RT_NAME="docker"; fi
fi

if [[ "$RT_STATE" == running ]]; then
  row runtime "docker, running" 1
elif [[ "$RT_STATE" == installed ]]; then
  case "$RT_NAME" in
    OrbStack)        START="open -a OrbStack";;
    "Docker Desktop") START="open -a Docker";;
    Colima)          START="colima start";;
    *)               START="start your container runtime (on Linux: sudo systemctl start docker)";;
  esac
  # not a failure the tester has to act on: the installer starts it and waits. Say so.
  row runtime "$RT_NAME, not running" 1
  [[ $JSON -eq 1 ]] || printf '                %sthe install starts it and waits up to 5 minutes (%s)%s\n' "$D" "$START" "$N"
elif [[ "$PLATFORM" == linux ]]; then
  row runtime "none found — the installer adds Docker" 1
else
  row runtime "none found" 0 "$(runtime_fix)"
fi

# ---------------------------------------------------------------- egress
# The four hosts that decide whether an install finishes. Everything else is post-install and belongs to doctor.
# `curl -f` would fail on the 401 the Docker registry answers with and the 404 a bare API root gives, and both
# of those mean the host is reachable. The only real failure is no answer at all, which curl reports as 000.
EG_OK=1; EG_BAD=""
for h in planetai.fab.city/node0/get/SHA256 raw.githubusercontent.com registry-1.docker.io/v2/ api.open-meteo.com; do
  code="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "https://$h" 2>/dev/null || echo 000)"
  [[ "$code" != 000 ]] || { EG_OK=0; EG_BAD="${EG_BAD:+$EG_BAD }${h%%/*}"; }
done
row egress "$([[ $EG_OK == 1 ]] && echo "site, github, registry, open-meteo" || echo "cannot reach: $EG_BAD")" "$EG_OK" \
  "the install needs to reach $EG_BAD. A proxy or a captive portal is in the way."

# ---------------------------------------------------------------- ports
busy=""
for p in 8080 5432; do
  if have lsof; then lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1 && busy="${busy:+$busy, }$p"
  elif have ss;  then ss -ltn "sport = :$p" 2>/dev/null | grep -q LISTEN && busy="${busy:+$busy, }$p"; fi
done
row ports "$([[ -z "$busy" ]] && echo "8080, 5432 free" || echo "$busy in use")" "$([[ -z "$busy" ]] && echo 1 || echo 0)" \
  "set APP_PORT to a free port in .env before installing (8080 is the dashboard; 5432 is the database, bound to localhost)"

# ---------------------------------------------------------------- verdict
if [[ $JSON -eq 1 ]]; then
  verdict=ok; [[ $fails -gt 0 ]] && verdict=fixable; [[ $floor -eq 1 ]] && verdict=below-floor
  printf '{"ok":%s,"verdict":"%s","os":"%s","arch":"%s","checks":[%s]}\n' \
    "$([[ $fails -eq 0 ]] && echo true || echo false)" "$verdict" "$OSNAME" "$ARCH" "${rows%,}"
  [[ $floor -eq 1 ]] && exit 2; [[ $fails -eq 0 ]] && exit 0 || exit 1
fi

echo
if [[ $floor -eq 1 ]]; then
  printf '  %sThis Mac cannot run a node, and no download will change that.%s\n' "$B" "$N"
  printf '  Every container runtime that exists for macOS wants a newer system than %s:\n' "$OSNAME"
  printf '  OrbStack needs 14.0, Docker Desktop needs 14, Colima needs 13.5 on Intel.\n\n'
  printf '  %sTwo ways forward%s\n' "$B" "$N"
  printf '    upgrade this Mac to macOS 13.5 or newer, if it is on Apple'"'"'s list — then run this again\n'
  printf '    or use another machine: any x86 Linux box, or a Mac on 13.5+\n\n'
  printf '  %sNothing was installed and nothing was changed.%s  Sources: docs/PLATFORMS.md\n\n' "$D" "$N"
  exit 2
fi
if [[ $fails -eq 0 ]]; then
  printf '  %sThis machine can run a node.%s\n\n' "$G" "$N"
  exit 0
fi
printf '  %s%d check%s failed.%s Each line above carries the fix. Nothing was installed.\n' "$Y" "$fails" "$([[ $fails -eq 1 ]] || echo s)" "$N"
printf '  Paste this into an issue:  %splanetai preflight --json%s   (or: curl -fsSL planetai.fab.city/preflight | bash -s -- --json)\n\n' "$D" "$N"
exit 1
