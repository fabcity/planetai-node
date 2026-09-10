#!/usr/bin/env python3
"""Report the diff between the dashboard's :root token block and the committed copy in docs/design/planetai-theme.css.

**Report-only. It prints and exits 0, and it is not in `make lint`.** It exists so that when a token changes, the
change is visible as a diff in a review rather than discovered on a wall screen: the dashboard is one file with no
build step, so a colour edited in `app/static/index.html` reaches every screen in the house on the next reload with
nothing having said what moved.

The .css file is a committed fixture, not a stylesheet anything loads. `app/static/index.html` remains the only
source of these values.

Turning this into a failing gate — and deciding which direction is authoritative when the two disagree — is the
design session's call, not this script's. It reports; somebody who owns the tokens decides.

    python3 tools/check_theme.py
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "app/static/index.html"
CSS = ROOT / "docs/design/planetai-theme.css"


def root_block(text: str) -> str:
    """The `:root{ ... }` block, verbatim. Non-greedy to the first `}`, which is correct here because the block holds
    no nested braces — a nested rule would need this to count them, and would also mean the block stopped being a
    flat list of tokens, which is the thing worth keeping legible."""
    m = re.search(r"^:root\{.*?^\}", text, re.S | re.M)
    return m.group(0) if m else ""


def main() -> int:
    html = root_block(HTML.read_text())
    if not html:
        print(f"check_theme: no :root block found in {HTML.relative_to(ROOT)} — the extractor needs updating, not the CSS.")
        return 0
    if not CSS.exists():
        print(f"check_theme: {CSS.relative_to(ROOT)} does not exist. To create it:\n"
              f"  python3 tools/check_theme.py --write")
        return 0
    css = root_block(CSS.read_text())
    if html == css:
        n = len(re.findall(r"--[a-z0-9-]+:", html))
        print(f"check_theme: {n} tokens, identical in the dashboard and docs/design/planetai-theme.css.")
        return 0
    print("check_theme: the dashboard's tokens and the committed copy differ. Nothing is broken by this; it is here so\n"
          "the change is reviewable. Either the design session moved a token (update the .css with --write) or the\n"
          "dashboard drifted (put it back).\n")
    sys.stdout.writelines(difflib.unified_diff(
        css.splitlines(keepends=True), html.splitlines(keepends=True),
        fromfile="docs/design/planetai-theme.css", tofile="app/static/index.html", n=2))
    print()
    return 0            # report-only, on purpose. See the docstring.


HEADER = """/* The dashboard's :root token block, extracted verbatim from app/static/index.html.

   A committed fixture, not a stylesheet: nothing loads this file, and no build step reads it. app/static/index.html
   stays the only source of these values. `python3 tools/check_theme.py` reports when the two have drifted apart, so
   that a changed token shows up as a diff in a review instead of on a wall screen. Regenerate with
   `python3 tools/check_theme.py --write`. */
"""


def write() -> int:
    CSS.write_text(HEADER + root_block(HTML.read_text()) + "\n")
    print(f"wrote {CSS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(write() if "--write" in sys.argv else main())
