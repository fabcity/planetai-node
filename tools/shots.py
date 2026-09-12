#!/usr/bin/env python3
"""Render every fixture this node ships, in a browser, and say what came out.

    python3 tools/shots.py [--out docs/design/shots]

Not in `make lint` and not in `make test`: it needs Chromium, which a node does not have and a
household should never be asked to install. It is the tool a design round is run from.

`--url http://127.0.0.1:8080 --token <admin>` points it at a node that is actually running instead,
and adds one pass with no token at all: at SHARE_LEVEL=off that is what a phone on the house WiFi
gets, and the page is supposed to say so rather than go blank.

Every fixture is computed here exactly as `GET /issues/fixtures/{name}` computes it — same engine,
same `Replay` cursor, same `as_of` — and handed to the page as that route's body. No database, no
app, no port. The browser half is tools/shots.mjs, which needs playwright; playwright lives in the
sibling planetai-design checkout, because a node's tarball has no node_modules in it and is not
going to grow one.

What a fixture does NOT carry, it draws the empty state for, and that is worth a picture too. The
committed 6 September capture predates `planetai snapshot`, so it has no /nearby, /forecast, /trust
or /sensors in it and the three ported cards come out empty here. `planetai snapshot` answers all
twelve; a capture taken with it renders the whole page.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("PACKS_DIR", "packs")
sys.path.insert(0, str(ROOT / "app"))

FIXTURES = ROOT / "app/issues/fixtures"
DESIGN = Path(os.environ.get("PLANETAI_DESIGN_REPO", ROOT.parent / "planetai-design"))


class Settings:
    """`NODE_ISSUES` and nothing else — the only setting the engine reads for a replay."""

    def __init__(self, issues: str):
        self.issues = issues

    def get(self, key, default=""):
        return self.issues if key == "NODE_ISSUES" else default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/design/shots")
    ap.add_argument("--issues", default="air,heat,land,coast", help="NODE_ISSUES for the replay")
    ap.add_argument("--url", help="a node that is running, e.g. http://127.0.0.1:8080, instead of the fixtures")
    ap.add_argument("--token", default=os.environ.get("PAI_TOKEN", ""),
                    help="its admin token, for the passes that are meant to see something")
    args = ap.parse_args()

    node = shutil.which("node")
    modules = DESIGN / "node_modules"
    if not node or not (modules / "playwright").is_dir():
        print(f"  - shots skipped (needs node and playwright; playwright is in {modules})")
        return 0

    if args.url:
        r = subprocess.run([node, str(ROOT / "tools/shots.mjs"), "", args.out, str(ROOT)],
                           env={**os.environ, "PLAYWRIGHT_ENTRY": (modules / "playwright/index.mjs").as_uri(),
                                "NODE_URL": args.url.rstrip("/"), "PAI_TOKEN": args.token})
        return r.returncode

    import issues as I                 # noqa: PLC0415 — after sys.path
    from issues import engine          # noqa: PLC0415

    decl = I.load()
    names = sorted(p.stem for p in FIXTURES.glob("*.json"))
    if not names:
        print("  - shots skipped (this node ships no fixture)")
        return 0

    with tempfile.TemporaryDirectory(prefix="planetai-shots-") as tmp:
        for name in names:
            snap = json.loads((FIXTURES / f"{name}.json").read_text())
            snap["issues"] = engine.replay(snap, Settings(args.issues), decl)
            (Path(tmp) / f"{name}.json").write_text(json.dumps(snap, default=str))
            print(f"  {name}: headline {snap['issues'].get('headline')} · "
                  f"order {snap['issues'].get('order')}")
        r = subprocess.run(
            [node, str(ROOT / "tools/shots.mjs"), tmp, args.out, str(ROOT)],
            env={**os.environ, "PLAYWRIGHT_ENTRY": (modules / "playwright/index.mjs").as_uri()})
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
