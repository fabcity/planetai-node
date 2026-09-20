"""The network's source registry, as the node carries it. Domain-blind.

    load()    -> (entries, version)   the vendored snapshot of awesome-fabcity-data
    find()    -> entries, filtered

`data/sources/` is a pinned copy of the registry (tools/sync_registry.sh), mounted read-only. It is
what the network has decided can be measured at each pillar and scale — 209 rows at the time of
writing, against the fourteen sources a node actually reads.

That gap is the point. `index.cells()` can only emit rows this node can compute, so the cell nobody
has an adapter for is simply absent from `/cells`, and until now absent meant unanswerable. The
registry answers it: `GET /sources?cell=Social|City` says what is filed for that cell, and
`wired_in_planetai` says which of it anything reads yet.

This module names no metric, no source and no pillar. It loads, filters and serves; every word of
vocabulary in it came out of the registry's own schema. Adding a source is still a PR upstream and a
re-pin (docs/SOURCES.md), never a change here.

Reads index.json, not the YAML beside it: the same one file `bin/planetai` reads, with the standard
library, because a node's Python has no PyYAML.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger("planetai.registry")
SOURCES_DIR = Path(os.getenv("SOURCES_DIR", "/app/data/sources"))

_cache: dict = {"mtime": None, "entries": [], "version": {}}


def load() -> tuple[list[dict], dict]:
    """(entries, version). Cached on index.json's mtime, so a re-pin applied by `planetai update`
    is picked up without a restart and a hot path does not re-read 209 entries every request."""
    index = SOURCES_DIR / "index.json"
    if not index.is_file():
        return [], {}
    mtime = index.stat().st_mtime
    if _cache["mtime"] != mtime:
        try:
            entries = json.loads(index.read_text())
            ver = {}
            vp = SOURCES_DIR / "REGISTRY_VERSION"
            if vp.is_file():
                ver = dict(l.split("=", 1) for l in vp.read_text().split() if "=" in l)
            ver["entries"] = len(entries)
            _cache.update(mtime=mtime, entries=entries, version=ver)
        except Exception as e:  # noqa: BLE001
            log.warning("source registry at %s did not load: %s", index, e)
            return [], {}
    return _cache["entries"], _cache["version"]


def find(pillar: str = "", scale: str = "", pilot: str = "", cell: str = "",
         wired: bool | None = None) -> list[dict]:
    """Every filter is AND, and an empty one matches everything.

    `pilot` is the exception worth knowing: an entry relevant to `global` is relevant to every pilot,
    so asking for Bali returns Bali's sources AND the planet-wide ones. A node asking what it could
    measure wants both, and the registry's own `pilot_relevance` is where that word comes from."""
    entries, _ = load()
    out = []
    for e in entries:
        if pillar and e.get("pillar") != pillar:
            continue
        if scale and e.get("scale") != scale:
            continue
        if cell and e.get("cell") != cell:
            continue
        if wired is not None and bool(e.get("wired_in_planetai")) is not wired:
            continue
        if pilot:
            rel = e.get("pilot_relevance") or []
            if pilot not in rel and "global" not in rel:
                continue
        out.append(e)
    return out


def one(slug: str) -> dict | None:
    entries, _ = load()
    return next((e for e in entries if e.get("slug") == slug), None)


def counts_by_cell() -> dict[str, tuple[int, bool]]:
    """{cell: (how many registered, does anything read any of them)} — what index.py puts on a row."""
    out: dict[str, tuple[int, bool]] = {}
    entries, _ = load()
    for e in entries:
        n, wired = out.get(e.get("cell", ""), (0, False))
        out[e.get("cell", "")] = (n + 1, wired or bool(e.get("wired_in_planetai")))
    return out
