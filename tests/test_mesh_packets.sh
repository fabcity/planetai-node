#!/usr/bin/env bash
# The doctor's "mesh packets arriving" right after an update: /health's count starts again at 0 when the app
# restarts, so the last hour's mesh readings in the database answer for it. Runs the real mesh_packets() lifted
# out of bin/planetai, with api and docker stubbed.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
sed -n '/^mesh_packets() {/,/^}$/p;/^json() {/,/^}$/p' bin/planetai > "$d/fn.sh"
grep -q 'interval' "$d/fn.sh" || { echo "  FAIL could not lift mesh_packets() out of bin/planetai"; exit 1; }
run() {  # $1 = what /health says, $2 = what the database says ("" = it does not answer)
  HEALTH="$1" DB="$2" bash -c "source '$d/fn.sh'
api() { [[ -n \"\$HEALTH\" ]] && echo \"\$HEALTH\"; }
docker() { [[ -n \"\$DB\" ]] && printf ' %s\n' \"\$DB\"; }
mesh_packets"
}
fail=0
check() { [[ "$1" == "$2" ]] && echo "  ok  $3" || { echo "  FAIL $3: got '$1', expected '$2'"; fail=1; }; }
check "$(run '{"mesh":{"packets":12}}' 0)"    12  "the app has counted packets: its count"
check "$(run '{"mesh":{"packets":0}}' 142)"   142 "just restarted, the gateway sent in the last hour: the database's count"
check "$(run '{"mesh":{"packets":0}}' 0)"     0   "nothing in the last hour either: 0, and the doctor says so"
check "$(run '' '')"                          0   "the node and the database are down: 0, not an empty string"
[[ $fail -eq 0 ]] && echo "mesh packets: ok"
exit $fail
