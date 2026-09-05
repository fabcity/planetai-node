#!/usr/bin/env bash
# The image installs app/requirements.txt on python:3.12-slim. Resolve it the same way before pushing, so a pin that
# contradicts a dependency fails here and not in `planetai update` on a node. Skips when no python3.12 or no network.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PY="$(command -v python3.12 || ls /opt/homebrew/bin/python3.12 2>/dev/null || true)"
[[ -n "$PY" ]] || { echo "  - requirements resolve skipped (no python3.12 here; CI checks it)"; exit 0; }
V=/tmp/planetai-req-venv
[[ -x "$V/bin/pip" ]] || "$PY" -m venv "$V" >/dev/null 2>&1 || { echo "  - requirements resolve skipped (venv failed)"; exit 0; }
out="$("$V/bin/pip" install --dry-run -q -r app/requirements.txt 2>&1)" ; rc=$?
if [[ $rc -ne 0 ]]; then
  if grep -qi "conflict\|ResolutionImpossible" <<< "$out"; then echo "  x app/requirements.txt does not resolve on python 3.12:"; grep -iE "depends on|requested" <<< "$out" | head -6 | sed 's/^/      /'; exit 1; fi
  echo "  - requirements resolve skipped (pip could not reach the index)"; exit 0
fi
echo "  requirements resolve on python 3.12 ok"
