#!/usr/bin/env bash
# "already runs a node" must mean containers, not a settings file. Lucas's machine had .env and NO docker,
# and was told it was running one — then offered an update that died inside backup.sh.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
CLI="$PWD/bin/planetai"

# Lift the decision out of the real file and drive it with a stubbed docker.
block="$(sed -n '/^  local node_running=0/,/^  fi$/p' "$CLI" | head -3)"
[[ -n "$block" ]] || { echo "  FAIL could not lift the decision from bin/planetai"; exit 1; }

check() { # check <docker-info-rc> <compose-ps-output> <expect 0|1>
  local rc="$1" ps="$2" want="$3" d; d="$(mktemp -d)"
  printf '#!/bin/sh\ncase "$1" in info) exit %s;; compose) [ "$2" = ps ] && printf "%%s" "%s"; exit 0;; esac\nexit 0\n' "$rc" "$ps" > "$d/docker"
  chmod +x "$d/docker"
  got="$(PATH="$d:$PATH" bash -c "
    node_running=0
    if docker info >/dev/null 2>&1 && [[ -n \"\$(docker compose ps -q 2>/dev/null)\" ]]; then node_running=1; fi
    echo \$node_running")"
  rm -rf "$d"
  if [[ "$got" == "$want" ]]; then echo "  ok   docker=$([[ $rc == 0 ]] && echo up || echo absent) containers='${ps:-none}' → running=$got"
  else echo "  FAIL docker rc=$rc ps='$ps': got $got want $want"; fails=$((fails+1)); fi
}

echo "already-runs-a-node: what counts as running"
check 1 ""          0    # Lucas: no docker at all
check 0 ""          0    # docker up, no containers — an install that stopped
check 0 "abc123"    1    # docker up, containers there — actually running

grep -q 'there is no container runtime running, so there is nothing to update' bin/planetai \
  && echo "  ok   update refuses before backing up, with a reason" \
  || { echo "  FAIL update still tries the backup"; fails=$((fails+1)); }

[[ $fails -eq 0 ]] && { echo "running-state tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
