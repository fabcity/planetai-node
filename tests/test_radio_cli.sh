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
