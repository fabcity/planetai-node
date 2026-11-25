#!/usr/bin/env bash
# `planetai reticulum` writes the [[Fab City hub]] block into the household's own config/reticulum/config, or takes it
# out (docs/SPEC_hub.md §4, §6). Only that block may change, and saying yes twice is saying it once. Runs the real
# reticulum_hub() and hub_up() lifted out of bin/planetai.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
{ grep -E '^RETICULUM_HUB=' bin/planetai
  sed -n '/^reticulum_hub_on() {/p;/^reticulum_hub() {/,/^}$/p;/^hub_up() {/p;/^json() {/,/^\$1"; }$/p;/^reticulum_is_hub() {/p;/^presence_on() {/p;/^reticulum_see() {/,/^}$/p' bin/planetai; } > "$d/fn.sh"
grep -q 'awk -v on=' "$d/fn.sh" && grep -q '^hub_up()' "$d/fn.sh" && grep -q '^reticulum_see()' "$d/fn.sh" || { echo "  FAIL could not lift reticulum_hub() and reticulum_see() out of bin/planetai"; exit 1; }
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
check 'grep -qx "    command = openssl s_client -quiet -verify_return_error -verify_hostname fabalabbali.tail71245c.ts.net -connect fabalabbali.tail71245c.ts.net:443 -servername fabalabbali.tail71245c.ts.net" "$d/c"' \
                                                                            "dialling node #1 through Funnel, its certificate checked by name"
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

# a block someone edited by hand: a comment and a blank line inside it, a commented section after it
cat > "$d/hand" <<'EOF2'
[interfaces]
  [[TCP Server]]
    type = TCPServerInterface
    listen_port = 4242

  [[Fab City hub]]
    type = PipeInterface
    # turned off by hand, 3 Dec

    enabled = no
    command = openssl s_client -quiet -connect fabalabbali.tail71245c.ts.net:443

  # [[RNode LoRa]]
  #   type = RNodeInterface
EOF2
printf '[interfaces]\n  [[TCP Server]]\n    type = TCPServerInterface\n    listen_port = 4242\n\n  # [[RNode LoRa]]\n  #   type = RNodeInterface\n' > "$d/hand.want"
reticulum_hub off "$d/hand"
check 'cmp -s "$d/hand" "$d/hand.want"'                                     "no takes out a hand-edited block whole, and the commented section after it stays"
check '! grep -q "PipeInterface\|enabled = no" "$d/hand"'                    "so no hub line is left under [[TCP Server]]"

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

# "Let other PLANETAI nodes see this node?" (docs/SPEC_hub.md §8): yes dials the hub and turns presence on, no does
# neither, and a node that is a hub itself only announces. The node's settings are a file here.
api() { [[ "$1" == /presence ]] && { [[ "$(cat "$d/presence")" == 1 ]] && echo '{"enabled": true}' || echo '{"enabled": false}'; }; }
config_set() { echo "$1=$2" >> "$d/sets"; [[ "$1" == RETICULUM_PRESENCE ]] && echo "$2" > "$d/presence"; }
see() { cp "$d/tpl" "$d/s"; echo "$1" > "$d/presence"; : > "$d/sets"; reticulum_see "$d/s" "$2"; }
see 0 y
check 'reticulum_hub_on "$d/s" && [ "$(cat "$d/sets")" = "RETICULUM_PRESENCE=1" ]'        "yes dials the hub and turns presence on"
reticulum_see "$d/s" y
check '[ "$(grep -c "^  \[\[Fab City hub\]\]" "$d/s")" = 1 ] && [ "$(cat "$d/sets")" = "RETICULUM_PRESENCE=1" ]' "yes again changes nothing"
reticulum_see "$d/s" n
check '! reticulum_hub_on "$d/s" && cmp -s "$d/s" "$d/tpl" && [ "$(cat "$d/presence")" = 0 ]' "no takes the block out and turns presence off"
see 0 n
check '[ ! -s "$d/sets" ] && cmp -s "$d/s" "$d/tpl"'                                       "no on a node not seen changes nothing"
sed 's/enable_transport = No/enable_transport = Yes/' "$d/tpl" > "$d/hubcfg"; echo 0 > "$d/presence"; : > "$d/sets"
reticulum_see "$d/hubcfg" y
check '! reticulum_hub_on "$d/hubcfg" && [ "$(cat "$d/sets")" = "RETICULUM_PRESENCE=1" ]'  "a hub says yes by announcing, and never dials itself"

[[ $fail -eq 0 ]] && echo "reticulum hub: ok"
exit $fail
