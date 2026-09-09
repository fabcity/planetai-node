#!/usr/bin/env bash
# `planetai remove` deletes readings nobody else has a copy of. The only thing worth testing about it is
# that it CANNOT do that by accident: it lists first, asks twice, and the second answer must be the
# node's own name typed out.
#
# Run against a throwaway node folder — never a real one, and never with a container runtime reachable.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"; fails=0
ok(){ echo "  ok   $1"; }; bad(){ echo "  FAIL $1"; fails=$((fails+1)); }

# A fake node: the files cmd_remove looks at, and nothing else.
mk() {
  D="$(mktemp -d)/planetai"; mkdir -p "$D/backups" "$D/bin"
  printf 'NODE_NAME=mahon1\nAPP_PORT=8080\n' > "$D/.env"
  printf 'v0.0.0-test\n' > "$D/VERSION"
  cp "$REPO/bin/planetai" "$D/bin/planetai"
  : > "$D/backups/old.sql.gz"
  # no docker on PATH: the same shape as the machine this matters on
  STUB="$(mktemp -d)"; printf '#!/bin/sh\nexit 1\n' > "$STUB/docker"; chmod +x "$STUB/docker"
}

# On a real terminal, because planetai reads every answer from /dev/tty — a pipe drives nothing.
run() { PATH="$STUB:/usr/bin:/bin:/usr/local/bin" PLANETAI_HOME="$D" \
        python3 "$REPO/tests/pty_run.py" "$@" -- bash "$D/bin/planetai" remove 2>&1; }

echo "remove: it cannot happen by accident"

mk; out="$(run n)"
if [[ -d "$D" ]]; then ok "answering no to the first question leaves the folder"; else bad "the folder went on a 'no'"; fi
grep -q "nothing was removed" <<<"$out" && ok "and says so" || bad "no confirmation that nothing happened"

mk; out="$(run y not-the-name)"
if [[ -d "$D" ]]; then ok "a wrong name leaves the folder"; else bad "the folder went on a wrong name"; fi
grep -q 'that is not "mahon1"' <<<"$out" && ok "and names what it wanted" || bad "no message about the wrong name"

mk; out="$(run y mahon1)"
if [[ -d "$D" ]]; then bad "the right name did NOT remove the folder"; else ok "the node's own name, typed out, removes it"; fi

echo "remove: it says what will go, before it goes"
mk; out="$(run n)"
for want in "This will remove" "$D" "readings" "backup(s)"; do
  grep -q -- "$want" <<<"$out" && ok "  lists: $want" || bad "  does not list: $want"
done
grep -q "Copy them out first" <<<"$out" && ok "  and warns the backups go with the folder" || bad "  no warning about the backups"

echo "remove: --keep-data"
mk; out="$(PATH="$STUB:/usr/bin:/bin:/usr/local/bin" PLANETAI_HOME="$D" \
      python3 "$REPO/tests/pty_run.py" n -- bash "$D/bin/planetai" remove --keep-data 2>&1)"
grep -q "kept" <<<"$out" && ok "  says the data is kept" || bad "  does not say the data is kept"
grep -q "deleted" <<<"$out" && bad "  still threatens to delete the readings" || ok "  and does not threaten the readings"

echo "remove: no terminal, no deletion"
mk; out="$(PATH="$STUB:/usr/bin:/bin" PLANETAI_HOME="$D" bash "$D/bin/planetai" remove </dev/null 2>&1)"
if [[ -d "$D" ]]; then ok "with nothing to answer it, the folder stays"; else bad "it deleted with no terminal"; fi

[[ $fails -eq 0 ]] && { echo "remove tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
