#!/usr/bin/env bash
# The whole machine matrix, from fixtures, without owning twelve Macs.
#
# Every fact preflight uses comes from a probe an environment variable can replace, so a machine is a
# line of env vars here. The one that matters is Lucas's: MacBookPro11,5 on macOS 12.7.6, confirmed from
# that machine's own System Information — 4 cores, 16 GB, 428 GB free.
#
# Runs the real tools/preflight.sh. Never a copy typed into the test.
set -uo pipefail
cd "$(dirname "$0")/.."
PF="$PWD/tools/preflight.sh"
[[ -r "$PF" ]] || { echo "no tools/preflight.sh"; exit 1; }
fails=0

# A machine with nothing installed and a clean network, unless a case says otherwise.
BASE=(PF_HAVE= PF_DOCKER_RUNNING=0 PF_APPS=/nonexistent PF_EGRESS_OK=1 PF_PORTS_BUSY= PF_MEM_BYTES=17179869184 PF_DISK_FREE_KB=448790528 PF_DISK_MOUNT=/)

OUT=""; RC=0
run() { OUT="$(env "${BASE[@]}" "$@" bash "$PF" 2>&1)"; RC=$?; }
runj(){ OUT="$(env "${BASE[@]}" "$@" bash "$PF" --json 2>&1)"; RC=$?; }
ok()   { if [[ "$2" == "$3" ]]; then echo "  ok   $1"; else echo "  FAIL $1: got $2, want $3"; fails=$((fails+1)); fi; }
has()  { if grep -qi -- "$2" <<<"$OUT"; then echo "  ok   $1"; else echo "  FAIL $1"; sed 's/^/       /' <<<"$OUT" | head -14; fails=$((fails+1)); fi; }
hasnt(){ if grep -qi -- "$2" <<<"$OUT"; then echo "  FAIL $1: '$2' is in the output"; sed 's/^/       /' <<<"$OUT" | head -14; fails=$((fails+1)); else echo "  ok   $1"; fi; }
row()  { grep -E "^  $1 " <<<"$OUT" | head -1; }

MAC_LUCAS=(PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro11,5)

echo "1. below every floor — Lucas's MacBookPro11,5 on Monterey"
run "${MAC_LUCAS[@]}"
ok    "exit 2, a verdict not a crash" "$RC" 2
has   "  says it cannot"              "cannot run a node"
hasnt "  never says something went wrong" "Something went wrong"
has   "  reports the real memory"     "16 GB"
has   "  reports the real free disk"  "428 GB"

echo "2. a runtime on the disk that cannot launch on this OS — the false pass"
# OrbStack.app was on Lucas's disk because he downloaded the .dmg the day before. It cannot start on
# Monterey. Preflight read the folder, ticked the row green, and promised to start it and wait.
run "${MAC_LUCAS[@]}" PF_APPS=/tmp/pf-apps-orbstack
has   "  named, with the version it needs" "requires macOS 14.0"
hasnt "  no start-and-wait promise for something that cannot start" "waits up to 5 minutes"
hasnt "  and no green tick for it"    "OrbStack, not running"
ok    "  still below the floor overall" "$RC" 2

echo "4. above every floor, no runtime installed"
run PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro18,1
ok    "exit 1, fixable"               "$RC" 1
has   "  offers Colima by command"    "colima start"
hasnt "  and does not call it below the floor" "cannot run a node"

echo "4. runtime installed and stopped, above the floor"
run PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro18,1 PF_APPS=/tmp/pf-apps-orbstack
has   "  says it is not running"      "not running"
has   "  and promises the wait"       "waits up to 5 minutes"

echo "5. Apple Silicon on 13.2 — Colima supports it; the old hard-coded 13.5 did not"
run PF_OS=Darwin PF_OS_VERSION=13.2 PF_ARCH=arm64 PF_HW_MODEL=Mac14,2
hasnt "  not turned away"             "cannot run a node"
ok    "  exit 1, fixable"             "$RC" 1

echo "6. Intel on 13.2 — vz cannot boot the guest kernel, so it IS below the floor"
run PF_OS=Darwin PF_OS_VERSION=13.2 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro16,1
ok    "  exit 2, below the floor"     "$RC" 2

echo "7. Linux amd64"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 22.04.5 LTS" PF_ARCH=x86_64
hasnt "  no macOS verdict"            "cannot run a node"
has   "  the installer adds Docker"   "installer adds Dock"

echo "8. Linux arm64 — the database image is amd64-only"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 24.04 LTS" PF_ARCH=arm64
has   "  the arch row fails"          "amd64"
ok    "  exit 1"                      "$RC" 1

echo "9. WSL2"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 22.04.5 LTS" PF_ARCH=x86_64 PF_IS_WSL=1 PF_MEM_BYTES=4294967296
has   "  detected as WSL2"            "WSL2"
has   "  and holds it to 8 GB"        "8 GB is the container"

echo "10. unknown Mac model — never guess"
run PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=SomeFutureMac99,9
ok    "  still exits 2"               "$RC" 2

echo "11. --json parses on every case above"
for args in "PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro11,5" \
            "PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro18,1" \
            "PF_OS=Linux PF_OS_PRETTY=Ubuntu PF_ARCH=arm64"; do
  # shellcheck disable=SC2086
  runj $args
  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d['checks'] and 'verdict' in d" "$OUT" 2>/dev/null; then
    echo "  ok   parses: $args"
  else echo "  FAIL --json did not parse: $args"; sed 's/^/       /' <<<"$OUT" | head -3; fails=$((fails+1)); fi
done

echo "12. it changes nothing"
before="$(ls -A . | sort)"; run "${MAC_LUCAS[@]}"; after="$(ls -A . | sort)"
ok "  no file appeared or vanished" "$before" "$after"
if grep -nE '^[[:space:]]*sudo\b' "$PF" | grep -q .; then
  echo "  FAIL the script runs sudo"; fails=$((fails+1))
else echo "  ok   it never runs sudo (the fix lines quote one; nothing here executes it)"; fi

[[ $fails -eq 0 ]] && { echo "preflight fixture matrix passes"; exit 0; } || { echo "$fails preflight test(s) failed"; exit 1; }
