#!/usr/bin/env bash
# Two checks about the libraries the image carries:
#   1. app/requirements.txt resolves on python:3.12-slim, so a pin that contradicts a dependency fails here and
#      not in `planetai update` on a node. Skips when no python3.12 or no network.
#   2. every pack script that imports something from its own pack.yaml `pip:` list says how to install it.
#      `planetai update` ships a pack's code but NOT its libraries — app/requirements-packs.txt is written by
#      `planetai packs install` and is gitignored. Node #1 hit this: `planetai run earth fetch` downloaded 9 MB
#      of tile index and then printed ModuleNotFoundError once per year, nine times, naming no remedy.
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

python3 - <<'PY' || exit 1
import glob, os, re, sys
# pip name -> the module a script actually imports, where they differ
MODULE = {"earthengine-api": "ee", "pillow": "PIL", "beautifulsoup4": "bs4"}
errs = []
for manifest in sorted(glob.glob("packs/*/pack.yaml")):
    pack = os.path.basename(os.path.dirname(manifest))
    text = open(manifest).read()
    m = re.search(r"^pip:\s*\[([^\]]*)\]", text, re.M) or re.search(r"^pip:\s*\n((?:\s*-.*\n)+)", text, re.M)
    if not m:
        continue
    pips = [x.strip().strip("\"'-  ") for x in re.split(r"[,\n]", m.group(1)) if x.strip().strip("\"'-  ")]
    mods = {MODULE.get(p, p.replace("-", "_")) for p in pips}
    for script in sorted(glob.glob(f"packs/{pack}/*.py")):
        if os.path.basename(script) == "adapter.py":
            continue                      # the adapter runs in the poll loop; docs/PACKS.md already requires it to idle
        body = open(script).read()
        used = {mod for mod in mods if re.search(rf"^\s*(?:import|from)\s+{re.escape(mod)}\b", body, re.M)}
        if not used:
            continue
        says = ("ImportError" in body or "ModuleNotFoundError" in body
                or re.search(r"\brequire\(", body) or "packs install" in body)
        if not says:
            errs.append(f"{script} imports {', '.join(sorted(used))} but never says `planetai packs install`; "
                        f"a node that ran `planetai update` gets ModuleNotFoundError and no remedy")
print("\n".join(f"  x {e}" for e in errs) or "  every pack script that needs a pack library says how to install it")
sys.exit(1 if errs else 0)
PY
