#!/usr/bin/env bash
# The whole machine matrix, from fixtures, without owning twelve Macs.
#
# Every fact preflight uses comes from a probe an environment variable can replace, so a machine is one
# line here. The one that matters is Lucas's: MacBookPro11,5 on macOS 12.7.6, taken from that machine's
# own System Information — 4 cores, 16 GB, 428 GB free.
#
# Runs the real tools/preflight.sh. Never a copy typed into the test.
set -uo pipefail
cd "$(dirname "$0")/.."
PF="$PWD/tools/preflight.sh"
[[ -r "$PF" ]] || { echo "no tools/preflight.sh"; exit 1; }
fails=0

# Nothing installed, a clean network, free ports — unless a case says otherwise.
BASE=(PF_HAVE= PF_DOCKER_RUNNING=0 PF_APPS=/nonexistent PF_EGRESS_OK=1 PF_PORTS_BUSY=
      PF_MEM_BYTES=17179869184 PF_DISK_FREE_KB=448790528 PF_DISK_MOUNT=/ PF_CORES=4)
MAC_LUCAS=(PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro11,5)
# The .dmg Lucas downloaded the day before, which cannot launch on Monterey.
ORB=/tmp/pf-apps-orbstack; mkdir -p "$ORB/OrbStack.app"

OUT=""; RC=0
run()  { OUT="$(env "${BASE[@]}" "$@" bash "$PF" 2>&1)"; RC=$?; }
ok()   { if [[ "$2" == "$3" ]]; then echo "  ok   $1"; else echo "  FAIL $1: got $2, want $3"; fails=$((fails+1)); fi; }
has()  { if grep -qi -- "$2" <<<"$OUT"; then echo "  ok   $1"; else echo "  FAIL $1 — expected: $2"; fails=$((fails+1)); fi; }
hasnt(){ if grep -qi -- "$2" <<<"$OUT"; then echo "  FAIL $1 — found: $2"; fails=$((fails+1)); else echo "  ok   $1"; fi; }

echo "1. below every floor — Lucas's MacBookPro11,5 on Monterey"
run "${MAC_LUCAS[@]}"
ok    "exit 2: a verdict, not a crash"            "$RC" 2
has   "  says no runtime can be installed"        "No container runtime can be installed"
hasnt "  never says something went wrong"         "Something went wrong"
has   "  reports his real memory"                 "16 GB"
has   "  reports his real free disk"              "428 GB"

echo "2. a runtime on the disk that cannot launch on this OS — the false pass"
run "${MAC_LUCAS[@]}" PF_APPS="$ORB"
has   "  named, with the version it needs"        "requires macOS 14.0"
hasnt "  no start-and-wait promise"               "waits up to 5 minutes"
hasnt "  and no green tick for it"                "OrbStack, not running"
ok    "  still below the floor overall"           "$RC" 2

echo "3. the verdict says what the machine IS, and ends in commands"
run "${MAC_LUCAS[@]}"
has   "  names the hardware before the blocker"   "capable node — 4 cores, 16 GB, 428 GB free"
has   "  and that the OS is the only blocker"     "OS is the only blocker"
hasnt "  never 'use another machine' with no command" "use another machine"
has   "  a UTM download command"                  "curl -fL -o ~/Downloads/UTM.dmg"
has   "  an Ubuntu Server iso command"            "live-server-amd64.iso"
has   "  and the metal route"                     "docs/REVIVE_A_LAPTOP.md"
hasnt "  not Multipass, whose floor is 14"        "multipass"
hasnt "  not VirtualBox, whose floor is 13"       "virtualbox"

echo "4. the ceiling: three sentences, never a guess"
run "${MAC_LUCAS[@]}"
has   "  a 2015 model cannot upgrade"             "cannot go past macOS 12.7.6"
run PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro14,3
has   "  a 2017 model can — Ventura clears 13.5"  "can run macOS 13.7.6 — upgrade"
run PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=SomeFutureMac99,9
has   "  an unknown model is not guessed at"      "will not guess"
has   "  and is pointed at Apple's own list"      "support.apple.com"

echo "5. above every floor, nothing installed"
run PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro18,1
ok    "  exit 1: fixable"                         "$RC" 1
has   "  offers Colima as a command"              "colima start"
hasnt "  and is not called below the floor"       "No container runtime can be installed"

echo "6. runtime installed and stopped, above the floor"
run PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro18,1 PF_APPS="$ORB"
has   "  says it is not running"                  "not running"
has   "  and promises the wait"                   "waits up to 5 minutes"

echo "7. Apple Silicon on 13.2 — Colima supports it; the hard-coded 13.5 did not"
run PF_OS=Darwin PF_OS_VERSION=13.2 PF_ARCH=arm64 PF_HW_MODEL=Mac14,2
hasnt "  not turned away"                         "No container runtime can be installed"
ok    "  exit 1: fixable"                         "$RC" 1

echo "8. Intel on 13.2 — vz cannot boot the guest kernel, so it IS below the floor"
run PF_OS=Darwin PF_OS_VERSION=13.2 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro16,1
ok    "  exit 2: below the floor"                 "$RC" 2

echo "9. Linux amd64"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 22.04.5 LTS" PF_ARCH=x86_64
hasnt "  no macOS verdict"                        "No container runtime can be installed"
has   "  the installer adds Docker"               "installer adds Dock"

echo "10. Linux arm64 — the database image is amd64-only"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 24.04 LTS" PF_ARCH=arm64
has   "  the arch row fails"                      "amd64"
ok    "  exit 1"                                  "$RC" 1

echo "11. WSL2"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 22.04.5 LTS" PF_ARCH=x86_64 PF_IS_WSL=1 PF_MEM_BYTES=4294967296
has   "  detected as WSL2"                        "WSL2"
has   "  and held to 8 GB"                        "8 GB is the container"

echo "12. --json parses on every shape"
for args in "PF_OS=Darwin PF_OS_VERSION=12.7.6 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro11,5" \
            "PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro18,1" \
            "PF_OS=Linux PF_OS_PRETTY=Ubuntu PF_ARCH=arm64"; do
  # shellcheck disable=SC2086
  j="$(env "${BASE[@]}" $args bash "$PF" --json 2>&1)"
  if python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d['checks'] and 'verdict' in d" "$j" 2>/dev/null
  then echo "  ok   parses: ${args%% *}…"
  else echo "  FAIL --json did not parse: $args"; sed 's/^/       /' <<<"$j" | head -3; fails=$((fails+1)); fi
done

echo "13. it changes nothing, and never runs sudo"
before="$(ls -A . | sort)"; run "${MAC_LUCAS[@]}"; after="$(ls -A . | sort)"
ok "  no file appeared or vanished" "$before" "$after"
if grep -nE '^[[:space:]]*sudo\b' "$PF" | grep -q .; then
  echo "  FAIL the script runs sudo"; fails=$((fails+1))
else echo "  ok   never runs sudo (fix lines quote one; nothing executes it)"; fi

echo "14. laptop notes: only when true, never in the verdict"
run "${MAC_LUCAS[@]}" PF_IS_LAPTOP=1 PF_HAS_ETHERNET=0
has   "  says it is a laptop"                     "This is a laptop"
has   "  the sleep fix, as a command"             "pmset -a disablesleep 1"
has   "  the battery command"                     "Cycle Count"
has   "  and the missing wired port"              "no wired port here"
has   "  labelled not-a-failure"                  "none of them failures"
run "${MAC_LUCAS[@]}" PF_IS_LAPTOP=0
hasnt "  silent on a desktop"                     "This is a laptop"
run "${MAC_LUCAS[@]}" PF_IS_LAPTOP=1 PF_HAS_ETHERNET=1
hasnt "  and silent about ethernet when there is a port" "no wired port here"

echo "15. python3, which the CLI needs and preflight does not"
run PF_OS=Linux PF_OS_PRETTY="Arch Linux" PF_ARCH=x86_64 PF_HAVE="docker" PF_DOCKER_RUNNING=1
has   "  missing python3 fails the row"           "python3       not installed"
has   "  with pacman on Arch and Omarchy"         "pacman -S --noconfirm python"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 22.04.5 LTS" PF_ARCH=x86_64 PF_HAVE="docker" PF_DOCKER_RUNNING=1
has   "  and apt-get on Ubuntu"                   "apt-get install -y python3"
run PF_OS=Linux PF_OS_PRETTY="Ubuntu 22.04.5 LTS" PF_ARCH=x86_64 PF_HAVE="docker python3" PF_DOCKER_RUNNING=1
has   "  and passes when it is there"             "python3       present"

echo "16. Linux first: two named distros, and a word to an Intel Mac that works"
run "${MAC_LUCAS[@]}" PF_HAVE=python3
has   "  Ubuntu Server, for a box nobody uses"    "Ubuntu Server — nobody uses it"
has   "  Omarchy, for a laptop somebody uses"     "a laptop somebody uses AND a node"
has   "  and the Omarchy iso as a command"        "omarchy.org/omarchy-4.0.3.iso"
run PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=x86_64 PF_HW_MODEL=MacBookPro16,1 PF_HAVE="docker python3" PF_DOCKER_RUNNING=1
ok    "  a working Intel Mac still passes"        "$RC" 0
has   "  and is told about the treadmill"         "this is an Intel Mac"
run PF_OS=Darwin PF_OS_VERSION=15.6.1 PF_ARCH=arm64 PF_HW_MODEL=Mac14,2 PF_HAVE="docker python3" PF_DOCKER_RUNNING=1
ok    "  Apple Silicon passes too"                "$RC" 0
hasnt "  and is NOT told to switch"               "this is an Intel Mac"

echo "17. it fits 80 columns"
run "${MAC_LUCAS[@]}"
wide="$(awk '{ n=length($0); if (n>m) m=n } END { print m+0 }' <<<"$(sed -n '/preflight/,/ports/p' <<<"$OUT")")"
if [[ "$wide" -le 80 ]]; then echo "  ok   the table is $wide columns"
else echo "  FAIL the table is $wide columns"; fails=$((fails+1)); fi

[[ $fails -eq 0 ]] && { echo "preflight fixture matrix passes"; exit 0; } || { echo "$fails preflight test(s) failed"; exit 1; }
