"""Packs — the community extension point.

A pack is a folder in packs/ with a pack.yaml and any of:
    rules.yml    extra alert rules (SQL + message)      DATA — no code, safe to merge from anyone
    cells.yml    extra Index cells (SQL → fci-cells-v0) DATA — no code
    adapter.py   a source adapter (Python function)     CODE — runs with the node's privileges

Data packs are the default and the point: most useful contributions are a rule and a threshold that
someone learned the hard way in their city. Code packs need review — see docs/PACKS.md.

Loading is deliberately dumb: scan the directory, parse the YAML, import the module. No registry service,
no dependency resolution, no lifecycle hooks. If a pack is broken the node logs it and carries on.
"""
from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path

import yaml

log = logging.getLogger("planetai.packs")
PACKS_DIR = Path(os.getenv("PACKS_DIR", "/app/packs"))


def _allow_code() -> bool:
    import settings
    return settings.get("PACKS_ALLOW_CODE", "0") == "1"


def _enabled() -> list[Path]:
    if not PACKS_DIR.is_dir():
        return []
    import settings
    only = {p for p in settings.get("PACKS_ENABLED", "").replace(" ", "").split(",") if p}
    out = []
    for d in sorted(PACKS_DIR.iterdir()):
        if not (d / "pack.yaml").is_file():
            continue
        if only and d.name not in only:
            continue
        out.append(d)
    return out


def manifests() -> list[dict]:
    out = []
    for d in _enabled():
        try:
            m = yaml.safe_load((d / "pack.yaml").read_text()) or {}
        except Exception as e:  # noqa: BLE001
            log.warning("pack %s: bad pack.yaml (%s)", d.name, e); continue
        m["id"] = m.get("id", d.name)
        m["path"] = str(d)
        m["kind"] = "code" if (d / "adapter.py").is_file() else "data"
        out.append(m)
    return out


def rules() -> list[dict]:
    """Rules contributed by packs, appended after the core rules. Rule ids are namespaced <pack>/<id>."""
    out = []
    for d in _enabled():
        f = d / "rules.yml"
        if not f.is_file():
            continue
        try:
            for r in yaml.safe_load(f.read_text()) or []:
                r["id"] = f"{d.name}/{r['id']}"
                out.append(r)
        except Exception as e:  # noqa: BLE001
            log.warning("pack %s: bad rules.yml (%s)", d.name, e)
    return out


def cells() -> list[dict]:
    """Extra Index cell definitions: {cell, unit, sql, state}. The SQL must return one row with a `value` column."""
    out = []
    for d in _enabled():
        f = d / "cells.yml"
        if not f.is_file():
            continue
        try:
            for c in yaml.safe_load(f.read_text()) or []:
                c["pack"] = d.name
                out.append(c)
        except Exception as e:  # noqa: BLE001
            log.warning("pack %s: bad cells.yml (%s)", d.name, e)
    return out


def adapters(hc):
    """Source adapters from code packs. Off unless PACKS_ALLOW_CODE=1 — a pack's adapter.py runs with this
    node's privileges and network access. Read it before you enable it."""
    out = []
    for d in _enabled():
        f = d / "adapter.py"
        if not f.is_file():
            continue
        if not _allow_code():
            log.warning("pack %s ships code; set PACKS_ALLOW_CODE=1 to run it (read %s first)", d.name, f)
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"planetai_pack_{d.name}", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            out.append((d.name, lambda m=mod: m.fetch(hc)))
        except Exception as e:  # noqa: BLE001
            log.warning("pack %s: adapter failed to load (%s)", d.name, e)
    return out
