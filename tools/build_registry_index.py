#!/usr/bin/env python3
"""Fold the vendored registry YAML into one `data/sources/index.json`.

    python3 tools/build_registry_index.py            # rewrite the index
    python3 tools/build_registry_index.py --check    # print what would change, exit 1 if anything

Dev machine only: it needs PyYAML, which a node's Python does not have. That is the whole reason the
index exists — `bin/planetai` and `app/registry.py` read the JSON with the standard library, and the
YAML beside it is there for people and for anyone who wants to read the entry as it was filed.

Each entry is the YAML's own fields plus two the path already knows:
    slug   pillar/scale/slug, the id a pack's `sources:` names
    cell   "Environmental|City" — the Index's key spelling for that pillar and scale, which is a
           capitalise-and-join of the registry's own words and needs no mapping table. If that ever
           stops being true, the table belongs here and nowhere else.
Sorted by slug with a stable two-space indent, so a re-sync is a readable diff rather than a reflow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"


def build(sources: Path = SOURCES) -> list[dict]:
    out = []
    for p in sorted((sources / "data").rglob("*.yaml")):
        rel = p.relative_to(sources / "data")
        pillar, scale, slug = rel.parts[0], rel.parts[1], rel.stem
        e = yaml.safe_load(p.read_text()) or {}
        e["slug"] = f"{pillar}/{scale}/{slug}"
        e["cell"] = f"{pillar.capitalize()}|{scale.capitalize()}"
        out.append(e)
    return sorted(out, key=lambda e: e["slug"])


def render(entries: list[dict]) -> str:
    # `default=str` is for `added:`/`updated:`, which PyYAML hands back as datetime.date. An ISO string
    # is what the schema calls them and what every reader here wants.
    return json.dumps(entries, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n"


def main(argv: list[str]) -> int:
    target = SOURCES / "index.json"
    text = render(build())
    if "--check" in argv:
        have = target.read_text() if target.is_file() else ""
        if have == text:
            print(f"  index.json matches the {len(build())} vendored YAML entries")
            return 0
        print("  x data/sources/index.json is not what the YAML produces — it was hand-edited, or a sync was")
        print("    left half-done. Regenerate it: python3 tools/build_registry_index.py")
        return 1
    target.write_text(text)
    print(f"  wrote {target.relative_to(ROOT)} — {len(json.loads(text))} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
