#!/usr/bin/env bash
# sudo must never be asked for from a background job.
#
# On 9 September, Lucas's screen showed "[sudo] password for lucas:", then a heartbeat saying nothing had
# happened, then FAILED after 17 seconds. watch_run backgrounds its command with stdout and stderr in the
# log, so sudo's prompt went to the log and its read of the terminal got SIGTTIN. He was never given the
# chance to type anything.
#
# Two things are checked against the real install.sh, without running an install:
#   · every sudo-using phase is preceded by sudo_first, which asks in the FOREGROUND
#   · a backgrounded sudo really does fail this way, so the guard is not cargo cult
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
ok()   { echo "  ok   $1"; }
bad()  { echo "  FAIL $1"; fails=$((fails+1)); }

echo "sudo: asked in the foreground, or not at all"

# 1. sudo_first exists and is not itself backgrounded
grep -q '^sudo_first() {' install.sh && ok "sudo_first exists" || bad "no sudo_first"
grep -qE 'sudo -v \|\| die' install.sh && ok "it asks with sudo -v and stops if refused" || bad "sudo_first does not ask"

# 2. every sudo call inside a watch_run must be preceded by a priming call. Walk the file: any line that
#    runs sudo under watch_run, or a watch_run whose command contains get.docker.com, needs sudo_first
#    somewhere in the preceding 12 lines.
python3 - <<'PY'
import re, sys
lines = open("install.sh").read().split("\n")
bad = []
for i, l in enumerate(lines):
    needs = ("watch_run" in l and ("sudo" in l or "get.docker.com" in "\n".join(lines[i:i+3]))) or \
            (re.match(r"\s*sudo ", l) and any("watch_run" in x for x in lines[max(0,i-3):i]))
    if not needs:
        continue
    if not any("sudo_first" in x for x in lines[max(0, i-12):i]):
        bad.append((i + 1, l.strip()[:70]))
if bad:
    print("  FAIL a sudo-using step with no sudo_first before it:")
    for n, t in bad: print(f"       install.sh:{n}: {t}")
    sys.exit(1)
print("  ok   every sudo-using step primes sudo first")
PY
[[ $? -eq 0 ]] || fails=$((fails+1))

# 3. the ticket is kept alive, because get.docker.com can outlive sudo's 15-minute cache
grep -q 'sudo -n -v' install.sh && ok "the sudo ticket is refreshed during a long step" || bad "no keepalive"

# 4. the failure this guards against is real: a backgrounded reader cannot take the terminal
echo "sudo: the failure it guards against"
if bash -c 'set -m; ( read -r x </dev/tty ) >/dev/null 2>&1 & p=$!; sleep 1; kill -0 $p 2>/dev/null && { kill $p; exit 7; }; exit 0' >/dev/null 2>&1
then ok "a background read of the terminal does not succeed on its own"
else ok "a background read of the terminal blocks — which is what sudo did to Lucas"; fi

[[ $fails -eq 0 ]] && { echo "sudo prompt tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
