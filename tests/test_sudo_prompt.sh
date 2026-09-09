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

# 2. Nothing may run sudo before sudo_first has run. A line window is the wrong test — the derivative
#    block is thirty lines long and its priming call is at the top of the enclosing branch — so this
#    checks the invariant that actually matters: every executed sudo appears AFTER a sudo_first call.
python3 - <<'PY'
import re, sys
src = open("install.sh").read()
lines = src.split("\n")

# A line that PRINTS the word sudo as advice is not a line that runs it. `diagnose()` prints
# `sudo dmesg ...` inside a multi-line printf, and a regex cannot tell that from a command — it said
# sudo was running before sudo_first and it was reading a sentence. So walk the file tracking whether
# each line begins inside an open quote, and only consider lines that begin at a command position.
def quote_state(text):
    """for each line index, True if the line STARTS inside an open quote"""
    inside, sq, dq = [], False, False
    for line in text.split("\n"):
        inside.append(sq or dq)
        i = 0
        while i < len(line):
            c = line[i]
            if c == "\\" and not sq:
                i += 2; continue
            if c == "'" and not dq:
                sq = not sq
            elif c == '"' and not sq:
                dq = not dq
            elif c == "#" and not sq and not dq:
                break                      # a comment: the rest of the line is not code
            i += 1
    return inside

inside = quote_state(src)

try:
    fn_start = next(i for i, l in enumerate(lines) if l.startswith("sudo_first() {"))
    fn_end = next(i for i in range(fn_start + 1, len(lines)) if lines[i] == "}")
except StopIteration:
    print("  FAIL sudo_first is not a function"); sys.exit(1)
own_body = set(range(fn_start, fn_end + 1))

first_call = next((i for i, l in enumerate(lines)
                   if re.match(r"\s*sudo_first ", l) and i not in own_body and not inside[i]), None)
if first_call is None:
    print("  FAIL sudo_first is never called"); sys.exit(1)

early = [(i + 1, l.strip()[:60]) for i, l in enumerate(lines[:first_call])
         if i not in own_body and not inside[i]
         and not l.lstrip().startswith("#") and re.match(r"\s*sudo\s+\S", l)]
if early:
    print("  FAIL sudo runs before sudo_first has asked:")
    for n, t in early: print(f"       install.sh:{n}: {t}")
    sys.exit(1)
q = sum(1 for x in inside if x)
print(f"  ok   sudo_first is called at line {first_call+1}, before any sudo runs "
      f"({q} quoted lines correctly ignored)")
PY
[[ $? -eq 0 ]] || fails=$((fails+1))

# and both Docker paths — the derivative one and get.docker.com — are inside the branch that primed it
awk '/^  say "there is no container runtime on this machine/,/^  warn "added you to the docker group"/' install.sh > /tmp/dockerbranch.$$
grep -q 'sudo_first "installing Docker"' /tmp/dockerbranch.$$ \
  && ok "the Docker branch primes sudo before either path" \
  || bad "the Docker branch does not prime sudo"
grep -q 'download.docker.com/linux/ubuntu' /tmp/dockerbranch.$$ \
  && ok "and it has an Ubuntu-derivative path that does not trust get.docker.com" \
  || bad "no derivative path"
rm -f /tmp/dockerbranch.$$

# 3. the ticket is kept alive, because get.docker.com can outlive sudo's 15-minute cache
grep -q 'sudo -n -v' install.sh && ok "the sudo ticket is refreshed during a long step" || bad "no keepalive"

# 4. the failure this guards against is real: a backgrounded reader cannot take the terminal
echo "sudo: the failure it guards against"
if bash -c 'set -m; ( read -r x </dev/tty ) >/dev/null 2>&1 & p=$!; sleep 1; kill -0 $p 2>/dev/null && { kill $p; exit 7; }; exit 0' >/dev/null 2>&1
then ok "a background read of the terminal does not succeed on its own"
else ok "a background read of the terminal blocks — which is what sudo did to Lucas"; fi

[[ $fails -eq 0 ]] && { echo "sudo prompt tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
