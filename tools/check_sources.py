#!/usr/bin/env python3
"""Hold every `sources:` id in a pack.yaml to an entry that exists in the registry.

    python3 tools/check_sources.py               # in `make lint`, and it FAILS

`sources:` names where a pack's data comes from, as ids in `awesome-fabcity-data`, whose files are
`data/<pillar>/<scale>/<slug>.yaml`. Nothing read that key until this, so nothing noticed when a
slug moved or when a pack named an id that was never filed — which is how a registry becomes a
bibliography.

**It reads the registry's `origin/main`, not the files on the disk.** The first version of this read
the working tree and reported six broken ids; four of those six were filed on main and the sibling
checkout here was eight days behind on a harvest branch. What a pack may name is what the registry
has published, and a laptop's branch is not that. `--worktree` reads the files instead, for someone
adding a source and a pack in the same sitting.

The registry is a sibling checkout on a laptop and is absent on a node and in CI, where this prints
one line and exits 0. Point it somewhere else with PLANETAI_REGISTRY_REPO.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path(os.environ.get("PLANETAI_REGISTRY_REPO", ROOT.parent / "awesome-fabcity-data"))
REF = "origin/main"

ID = re.compile(r"^([a-z]+)/([a-z]+)/([a-z0-9-]+)$")


def declared() -> list[tuple[Path, str]]:
    """Every (pack.yaml, id) pair. Parsed with a regex rather than yaml, because this runs in the
    same lint that already checks the yaml parses and a second dependency here buys nothing."""
    out = []
    for p in sorted(ROOT.glob("packs/*/pack.yaml")):
        m = re.search(r"^sources:\s*\[(.*?)\]", p.read_text(), re.M | re.S)
        if m:
            out += [(p, s.strip()) for s in m.group(1).split(",") if s.strip()]
    return out


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REGISTRY), *args], capture_output=True, text=True, timeout=10)


def filed(worktree: bool) -> tuple[set[str], str]:
    """Every id the registry carries, and a word saying which registry that was."""
    if not worktree:
        r = git("ls-tree", "-r", "--name-only", REF, "data")
        if r.returncode == 0 and r.stdout.strip():
            at = git("log", "-1", "--format=%h %cs", REF).stdout.strip()
            ids = {n[len("data/"):-len(".yaml")] for n in r.stdout.split() if n.endswith(".yaml")}
            return ids, f"{REF} @ {at}"
    ids = {str(q.relative_to(REGISTRY / "data"))[:-len(".yaml")]
           for q in (REGISTRY / "data").rglob("*.yaml")}
    at = git("log", "-1", "--format=%h %cs (%D)").stdout.strip() or "no git"
    return ids, f"working tree @ {at}"


def main(argv: list[str]) -> int:
    pairs = declared()
    if not (REGISTRY / "data").is_dir():
        print(f"  - source check skipped ({REGISTRY} is not here; it is a sibling checkout, not a dependency)")
        return 0

    ids, at = filed("--worktree" in argv)
    bad = []
    for path, sid in pairs:
        if not ID.match(sid):
            bad.append((path, sid, "not a <pillar>/<scale>/<slug> id"))
        elif sid not in ids:
            slug = sid.rsplit("/", 1)[1]
            near = sorted(i for i in ids if slug in i or i.rsplit("/", 1)[1] in slug)
            bad.append((path, sid, f"did you mean {near[0]}?" if near else "no entry in the registry"))

    if bad:
        print(f"  x {len(bad)} of {len(pairs)} source ids do not resolve in {REGISTRY.name} ({at})")
        for path, sid, why in bad:
            print(f"      {path.relative_to(ROOT)}: {sid} — {why}")
        print("    Either the id is wrong here, or the source belongs in the registry and is not filed yet:")
        print("    add it there first (its CONTRIBUTING.md), then name it here.")
        return 1

    print(f"  {len(pairs)} source ids resolve in {REGISTRY.name} ({at})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
