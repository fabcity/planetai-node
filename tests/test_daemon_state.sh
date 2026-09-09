#!/usr/bin/env bash
# "The daemon is not up" and "I cannot reach the daemon" are different sentences. `docker info` fails
# with the same exit code for both, and we read the second as the first: Lucas's installer counted down
# five minutes while his journal said "Active: active (running) … 37min ago", 14 tasks, 24.6M resident.
#
# Drives the real daemon_state() from install.sh with a stubbed docker client.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
ok(){ echo "  ok   $1"; }; bad(){ echo "  FAIL $1"; fails=$((fails+1)); }

fn="$(sed -n '/^daemon_state() {/,/^}/p' install.sh)"
[[ -n "$fn" ]] || { echo "  FAIL could not lift daemon_state() from install.sh"; exit 1; }

# stub: <exit code> <stderr text>; plus whether a socket and an active service are pretended
state() {
  local rc="$1" msg="$2" sock="${3:-0}" active="${4:-0}" d
  d="$(mktemp -d)"
  printf '#!/bin/sh\n[ "$1" = info ] && { printf "%%s\\n" "%s" >&2; exit %s; }\nexit 0\n' "$msg" "$rc" > "$d/docker"
  printf '#!/bin/sh\n[ "$1" = is-active ] && { echo %s; exit 0; }\nexit 0\n' \
    "$([[ "$active" == 1 ]] && echo active || echo inactive)" > "$d/systemctl"
  chmod +x "$d/docker" "$d/systemctl"
  local sockdir="$d/run"; mkdir -p "$sockdir"
  { echo 'need() { command -v "$1" >/dev/null 2>&1; }'
    # /run/docker.sock cannot be faked, so the socket test is driven by a variable in the same shape
    if [[ "$sock" == 1 ]]; then echo 'SOCK_PRESENT=1'; else echo 'SOCK_PRESENT=0'; fi
    sed 's#\[\[ -S /var/run/docker.sock || -S /run/docker.sock \]\]#[[ "$SOCK_PRESENT" == 1 ]]#' <<< "$fn"
    echo 'daemon_state; echo "rc=$?"'
  } > "$d/run.sh"
  PATH="$d:/usr/bin:/bin" bash "$d/run.sh" 2>/dev/null | tail -1
  rm -rf "$d"
}

echo "daemon_state: what the client says vs what is true"
[[ "$(state 0 '' 0 0)" == "rc=0" ]] && ok "usable daemon → 0" || bad "usable daemon did not give 0"
[[ "$(state 1 'Got permission denied while trying to connect to the Docker daemon socket' 0 0)" == "rc=2" ]] \
  && ok "permission denied → 2: it is up, this shell cannot touch it" || bad "permission denied was not read as 2"
[[ "$(state 1 'permission denied' 0 0)" == "rc=2" ]] && ok "the short form too" || bad "short permission-denied missed"
[[ "$(state 1 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?' 1 1)" == "rc=2" ]] \
  && ok "socket present and service active → 2, whatever the client says" || bad "a live service was still read as down"
[[ "$(state 1 'Cannot connect to the Docker daemon' 0 0)" == "rc=1" ]] \
  && ok "no socket, no service → 1, genuinely not up" || bad "a dead daemon was not read as 1"

echo "daemon_state: the caller acts on 2 instead of waiting it out"
grep -q 'wd -eq 2 \]\] && use_docker_group' install.sh && ok "a 2 takes the docker-group path" || bad "a 2 is not acted on"
grep -q 'PLANETAI_SG' install.sh && ok "and cannot re-exec itself in a loop" || bad "no re-exec guard"

[[ $fails -eq 0 ]] && { echo "daemon_state tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
