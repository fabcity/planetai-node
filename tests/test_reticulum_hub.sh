#!/usr/bin/env bash
# `planetai reticulum` writes the [[Fab City hub]] block into the household's own config/reticulum/config, or takes it
# out (docs/SPEC_hub.md §4, §6). Only that block may change, and saying yes twice is saying it once. Runs the real
# reticulum_hub() and hub_up() lifted out of bin/planetai.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
{ grep -E '^RETICULUM_HUB=' bin/planetai
  sed -n '/^reticulum_hub_on() {/p;/^reticulum_hub() {/,/^}$/p;/^hub_up() {/p;/^json() {/,/^\$1"; }$/p' bin/planetai; } > "$d/fn.sh"
grep -q 'awk -v on=' "$d/fn.sh" && grep -q '^hub_up()' "$d/fn.sh" || { echo "  FAIL could not lift reticulum_hub() out of bin/planetai"; exit 1; }
source "$d/fn.sh"

# the shape of the bridge's config.tpl: the hub block commented, a household's own interface added at the end
cat > "$d/tpl" <<'EOF'
[reticulum]
  enable_transport = No
  share_instance = Yes

[interfaces]
  [[TCP Server]]
    type = TCPServerInterface
    enabled = yes
    listen_port = 4242

  # [[Fab City hub]]
  #   type = PipeInterface
  #   enabled = yes

  [[My LAN friend]]
    type = TCPClientInterface
    target_host = 192.168.1.20
EOF
fail=0
check() { if eval "$1"; then echo "  ok  $2"; else echo "  FAIL $2"; fail=1; fi; }
cp "$d/tpl" "$d/c"

reticulum_hub on "$d/c"
check 'reticulum_hub_on "$d/c"'                                             "yes writes the block"
check '[ "$(grep -c "^  \[\[Fab City hub\]\]" "$d/c")" = 1 ]'                "once, uncommented"
check 'grep -qx "    command = openssl s_client -quiet -verify_return_error -connect fabalabbali.tail71245c.ts.net:443 -servername fabalabbali.tail71245c.ts.net" "$d/c"' \
                                                                            "dialling node #1 through Funnel, with its certificate checked"
check 'awk "/^\[interfaces\]/{i=1} /^  \[\[Fab City hub\]\]/{exit !i}" "$d/c"' "under [interfaces]"
check 'grep -q "^  # \[\[Fab City hub\]\]" "$d/c" && grep -q "My LAN friend" "$d/c"' "the commented copy and the household's own interface stay"
cp "$d/c" "$d/once"; reticulum_hub on "$d/c"
check 'cmp -s "$d/c" "$d/once"'                                             "yes twice is yes once"
reticulum_hub off "$d/c"
check 'cmp -s "$d/c" "$d/tpl"'                                              "no takes it out, and the file is as it was"
reticulum_hub off "$d/c"
check 'cmp -s "$d/c" "$d/tpl"'                                              "no on a file without it changes nothing"
printf '[reticulum]\n  enable_transport = No\n' > "$d/bare"; reticulum_hub on "$d/bare"
check 'grep -q "^\[interfaces\]" "$d/bare" && reticulum_hub_on "$d/bare"'   "a file with no [interfaces] gets one"

# hub_up reads the bridge's /health: 1 only when the hub's interface is up
up() { curl() { printf '%s' "$HEALTH"; [ -n "$HEALTH" ]; }; hub_up; }
HEALTH='{"interfaces":[{"name":"TCP Server","online":true},{"name":"Fab City hub","online":true}]}'
check '[ "$(up)" = 1 ]'                                                     "the hub is up: 1"
HEALTH='{"interfaces":[{"name":"Fab City hub","online":false}]}'
check '[ "$(up)" = 0 ]'                                                     "the hub is down: 0"
HEALTH='{"ok":true,"address":"1b4f"}'
check '[ "$(up)" = 0 ]'                                                     "a bridge too old to say: 0"
HEALTH=''
check '[ "$(up)" = 0 ]'                                                     "no bridge: 0, not an empty string"

[[ $fail -eq 0 ]] && echo "reticulum hub: ok"
exit $fail
