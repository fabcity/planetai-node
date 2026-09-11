#!/usr/bin/env python3
"""Hold the node's copy of the frozen layer to the design repo it was copied from.

    python3 tools/check_theme.py                 # in `make lint`, and it FAILS

Three files under `app/static/` are not this repo's to edit: `planetai-theme.css` is generated from
planetai-design/references/planetai-layer.md, and `signs.svg` and `kilometre-cells.json` are that
repo's assets. They were copied here because a node serves its dashboard on a LAN that may have no
route out, and a copy with no guard drifts — a colour edited on this side reaches every screen in
the house on the next reload with nothing having said what moved. This is the guard.

**One line is allowed to differ, and it is named.** `planetai-theme.css` declares the mono at
`fonts/jetbrains-mono-latin.woff2`. `GET /static/{name}` takes a NAME and not a path, deliberately,
on a port that answers a household LAN, so that request 404s — a cost of one request, paid on
purpose, because the alternative is a path parameter reaching the filesystem. `dashboard.css`
declares the same family at the flat name the node does serve, which is the declaration that
resolves. So a `src:` line whose two sides name the same FILE by different paths is reported and
forgiven. Anything else — a second such line, a different file, a changed token, a moved brace —
fails, and the fix is to copy the file again rather than to widen this.

The design repo is a sibling checkout on a laptop and is absent on a node and in CI, where this
prints one line and exits 0. Point it somewhere else with PLANETAI_DESIGN_REPO.
"""
from __future__ import annotations

import difflib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = Path(os.environ.get("PLANETAI_DESIGN_REPO", ROOT.parent / "planetai-design"))

# node copy -> its original in the design repo. Copied verbatim; neither side is edited here.
FROZEN = {
    "app/static/planetai-theme.css": "planetai-theme.css",
    "app/static/signs.svg": "assets/signs/signs.svg",
    "app/static/kilometre-cells.json": "assets/h3/kilometre-cells.json",
}

SRC_LINE = re.compile(r"^(\s*src:\s*url\(['\"]?)([^'\")]+)(.*)$")


def forgiven(ours: str, theirs: str) -> str | None:
    """The one difference this project has decided to live with, or None.

    Both sides must be a `src: url(...)` naming the same file by a different path, and nothing else
    on the line may move. A basename comparison is the normalisation: `fonts/x.woff2` and `x.woff2`
    are the same file reached two ways, `x.woff2` and `y.woff2` are two files.
    """
    a, b = SRC_LINE.match(ours), SRC_LINE.match(theirs)
    if not (a and b):
        return None
    if (a.group(1), a.group(3)) != (b.group(1), b.group(3)):
        return None
    if a.group(2) == b.group(2) or a.group(2).rsplit("/", 1)[-1] != b.group(2).rsplit("/", 1)[-1]:
        return None
    return f"{b.group(2)} -> {a.group(2)}"


def check(rel: str, sub: str, errs: list[str], notes: list[str]) -> None:
    ours_p, theirs_p = ROOT / rel, DESIGN / sub
    if not theirs_p.exists():
        errs.append(f"{rel}: {theirs_p} is missing from the design repo — nothing to hold it to")
        return
    ours, theirs = ours_p.read_text().splitlines(), theirs_p.read_text().splitlines()
    if len(ours) != len(theirs):
        errs.append(f"{rel}: {len(ours)} lines here, {len(theirs)} in the design repo. Copy it again.")
        return
    bad = []
    for i, (o, t) in enumerate(zip(ours, theirs), 1):
        if o == t:
            continue
        note = forgiven(o, t)
        if note:
            notes.append(f"{rel}:{i} the mono, flattened by decision: {note}")
        else:
            bad.append(i)
    if bad:
        errs.append(f"{rel}: {len(bad)} line(s) differ from the design repo, at {', '.join(map(str, bad))}:\n"
                    + "".join(difflib.unified_diff([ours[i - 1] + "\n" for i in bad],
                                                   [theirs[i - 1] + "\n" for i in bad],
                                                   fromfile=rel, tofile=str(theirs_p), n=0)).rstrip())


def main() -> int:
    if not DESIGN.exists():
        print(f"  - theme check skipped ({DESIGN} is not here; it is a sibling checkout, not a dependency)")
        return 0
    errs: list[str] = []
    notes: list[str] = []
    for rel, sub in FROZEN.items():
        check(rel, sub, errs, notes)
    for n in notes:
        print(f"  ~ {n}")
    if errs:
        print("\n".join(f"  x {e}" for e in errs))
        print("\n  The frozen layer belongs to planetai-design. Change it there, then copy it here —\n"
              "  and if a second line has to differ, it needs a decision, not an exception in this file.")
        return 1
    print(f"  {len(FROZEN)} frozen files match {DESIGN.name}"
          + (f", with {len(notes)} line forgiven by decision" if notes else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
