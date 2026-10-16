#!/usr/bin/env bash
# `planetai radio` runs through the ~/.local/bin symlink on every node. It once looked for tools/radio.py next to
# the link (~/.local/tools/), so the command failed on node #1 after its packages were installed (17 Oct 2026).
set -euo pipefail
cd "$(dirname "$0")/.."
t="$(mktemp -d)"; trap 'rm -rf "$t"' EXIT
ln -s "$PWD/bin/planetai" "$t/planetai"; mkdir "$t/py"
# a python3 that has the packages and reports which file it was asked to run
printf '#!/bin/sh\ncase "$*" in *"import meshtastic"*) exit 0;; esac\n[ -f "$1" ] && echo "radio.py at $1" || echo "missing: $1"\n' > "$t/py/python3"
chmod +x "$t/py/python3"
out="$(PATH="$t/py:$PATH" "$t/planetai" radio --help)"
[[ "$out" == "radio.py at $PWD/tools/radio.py" ]] || { echo "  x planetai radio through a symlink ran: $out"; exit 1; }
echo "  ok   planetai radio, run through a symlink, finds the node's tools/radio.py"
grep -q 'python3 -m pip install --user' bin/planetai || { echo "  x the hint must install for the python3 that runs radio.py"; exit 1; }
echo "  ok   its install hint is python3 -m pip, for the same interpreter"
# The region comes from NODE_CITY in .env, whose shipped line carries a comment. radio.py once read the comment as
# part of the city, found no region and fell back to EU_868: an 868 MHz fleet for node #1 in Bali (17 Oct 2026).
r="$t/root"; mkdir -p "$r"
printf 'NODE_NAME=testnode\nNODE_CITY=bali                         # pilot key used in Index cells: bali | barcelona\n' > "$r/.env"
PLANETAI_ROOT="$r" python3 tools/radio.py init >/dev/null
grep -q 'SG_923' "$r/config/radio/fleet.yaml" || { echo "  x a commented NODE_CITY=bali did not give SG_923"; exit 1; }
echo "  ok   NODE_CITY=bali with its shipped comment gives SG_923, Indonesia's band"
printf 'NODE_NAME=testnode\nNODE_CITY=atlantis\n' > "$r/.env"; rm -rf "$r/config"
if PLANETAI_ROOT="$r" python3 tools/radio.py init >/dev/null 2>"$t/err"; then echo "  x an unknown city got a region"; exit 1; fi
grep -q 'no radio region' "$t/err" || { echo "  x an unknown city must say to pass --region"; cat "$t/err"; exit 1; }
echo "  ok   a city with no known region refuses and asks for --region, never guesses"
