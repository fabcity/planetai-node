#!/usr/bin/env bash
# The floor, and what the installer does at it. Runs the real tools/preflight.sh, never a copy.
#
# The machine under test is stubbed on PATH — sw_vers, uname, curl, lsof — because the one case that matters
# is a machine none of us has: an Intel Mac on Monterey. Exit codes are the contract two callers depend on:
#   0 go · 1 the tester can fix it · 2 below the floor, and the installer must exit 0 on this one.
set -uo pipefail
cd "$(dirname "$0")/.."
PF="$PWD/tools/preflight.sh"
[[ -r "$PF" ]] || { echo "no tools/preflight.sh"; exit 1; }

fails=0
OUT=""; RC=0
run() {  # run <macos-version> <arch>  -> sets $RC and $OUT. Not in a subshell: $OUT has to survive.
  local ver="$1" arch="$2" d; d="$(mktemp -d)"
  printf '#!/bin/sh\n[ "$1" = -productVersion ] && echo %s || echo macOS\n' "$ver" > "$d/sw_vers"
  printf '#!/bin/sh\ncase "$1" in -m) echo %s;; *) echo Darwin;; esac\n' "$arch" > "$d/uname"
  printf '#!/bin/sh\necho 200\n' > "$d/curl"          # every host reachable; this test is offline
  printf '#!/bin/sh\nexit 1\n' > "$d/lsof"            # no port in use
  chmod +x "$d"/*; mkdir -p "$d/apps"
  # a bare machine: only the stubs and the base system on PATH, and an empty /Applications
  OUT="$(PATH="$d:/usr/bin:/bin" PLANETAI_APPS="$d/apps" bash "$PF" 2>&1)"; RC=$?
  rm -rf "$d"
}
ok() { if [[ "$2" == "$3" ]]; then echo "  ok   $1"; else echo "  FAIL $1: got $2, want $3"; fails=$((fails+1)); fi; }
has() { if grep -q "$2" <<<"$OUT"; then echo "  ok   $1"; else echo "  FAIL $1: not in output"; fails=$((fails+1)); fi; }
hasnt() { if grep -q "$2" <<<"$OUT"; then echo "  FAIL $1: '$2' is in the output"; fails=$((fails+1)); else echo "  ok   $1"; fi; }

echo "preflight: the macOS floor"
run 12.7.6 x86_64; ok "Monterey 12.7.6 Intel is below the floor" "$RC" 2
has "  and it says so in a sentence" "cannot run a node"
has "  and names the upgrade"        "13.5"
hasnt "  and never says something went wrong" "Something went wrong"
hasnt "  and never names software the machine cannot run" "orbstack.dev/download"

run 13.4 x86_64;  ok "Ventura 13.4 Intel is below it too (vz cannot boot a guest)" "$RC" 2
run 13.5 x86_64;  [[ "$RC" == 2 ]] && { echo "  FAIL Ventura 13.5 Intel should pass the floor"; fails=$((fails+1)); } || echo "  ok   Ventura 13.5 Intel passes the floor"
has "  and is offered Colima, not OrbStack" "colima"
run 14.0 x86_64;  [[ "$RC" == 2 ]] && { echo "  FAIL Sonoma 14.0 should pass the floor"; fails=$((fails+1)); } || echo "  ok   Sonoma 14.0 passes the floor"
run 26.6.2 arm64; [[ "$RC" == 2 ]] && { echo "  FAIL Tahoe arm64 should pass the floor"; fails=$((fails+1)); } || echo "  ok   Tahoe arm64 passes the floor"

echo "preflight: it changes nothing"
before="$(cd "$(dirname "$PF")/.." && ls -A | sort)"
run 12.7.6 x86_64
after="$(cd "$(dirname "$PF")/.." && ls -A | sort)"
ok "no file appeared or vanished" "$before" "$after"
if grep -nE '^[[:space:]]*sudo\b' "$PF" | grep -q .; then
  echo "  FAIL the script runs sudo"; fails=$((fails+1))
else echo "  ok   it never runs sudo (the fix lines quote one; nothing here executes it)"; fi

echo "preflight: --json"
d="$(mktemp -d)"; printf '#!/bin/sh\n[ "$1" = -productVersion ] && echo 12.7.6 || echo macOS\n' > "$d/sw_vers"
printf '#!/bin/sh\ncase "$1" in -m) echo x86_64;; *) echo Darwin;; esac\n' > "$d/uname"
printf '#!/bin/sh\necho 200\n' > "$d/curl"; printf '#!/bin/sh\nexit 1\n' > "$d/lsof"; chmod +x "$d"/*
mkdir -p "$d/apps"; j="$(PATH="$d:/usr/bin:/bin" PLANETAI_APPS="$d/apps" bash "$PF" --json 2>&1)"; rm -rf "$d"
python3 -c "
import json,sys
d=json.loads(sys.argv[1])
assert d['verdict']=='below-floor', d['verdict']
assert d['ok'] is False
assert [c for c in d['checks'] if c['check']=='os'][0]['ok'] is False
assert all(c['fix'] is None for c in d['checks'] if c['ok']), 'a passing row carries a fix line'
print('  ok   parses, verdict below-floor, no fix on a passing row')
" "$j" || { echo "  FAIL --json"; fails=$((fails+1)); }

[[ $fails -eq 0 ]] && { echo "preflight tests pass"; exit 0; } || { echo "$fails preflight test(s) failed"; exit 1; }
