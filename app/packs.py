"""Packs — the extension point. Core packs ship in packs/ with the release; wild packs are added by whoever runs
the node (`planetai packs add`, docs/decisions/2026-10-01-packs.md).

A pack is a folder in packs/ with a pack.yaml and any of:
    rules.yml    extra alert rules (SQL + message)      DATA — no code, safe to merge from anyone
    cells.yml    extra Index cells (SQL → fci-cells-v0) DATA — no code
    adapter.py   a source adapter (Python function)     CODE — runs with the node's privileges
    hooks.py     on_readings / on_alert, called by emit()  CODE — the same

Data packs are the default and the point: most useful contributions are a rule and a threshold that
someone learned the hard way in their city. Code packs need review — see docs/PACKS.md.

Loading is deliberately dumb: scan the directory, parse the YAML, import the module. No registry service,
no dependency resolution, no lifecycle hooks. If a pack is broken the node logs it and carries on.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import time
from pathlib import Path

import yaml

log = logging.getLogger("planetai.packs")
PACKS_DIR = Path(os.getenv("PACKS_DIR", "/app/packs"))
CORE_CHANNELS = Path(os.getenv("CHANNELS_PATH", "/app/config/channels.yml"))


def _allow_code() -> bool:
    import settings
    return settings.get("PACKS_ALLOW_CODE", "0") == "1"


# Packs this node will not load because their `requires:` rules it out, and why: what `planetai packs` reads back.
REFUSED: dict[str, str] = {}


def _enabled() -> list[Path]:
    if not PACKS_DIR.is_dir():
        return []
    import requires
    import settings
    only = {p for p in settings.get("PACKS_ENABLED", "").replace(" ", "").split(",") if p}
    here = os.getenv("NODE_VERSION", "")
    out = []
    for d in sorted(PACKS_DIR.iterdir()):
        if not (d / "pack.yaml").is_file():
            continue
        if only and d.name not in only:
            continue
        # A pack written for a newer node may read a column, a route or a setting this one does not have. It is
        # refused whole, rules and adapter alike, with one line in the log, and not half-loaded.
        try:
            spec = ((yaml.safe_load((d / "pack.yaml").read_text()) or {}).get("requires") or {}).get("node")
        except Exception:  # noqa: BLE001 — a pack.yaml that does not parse is reported where it is read
            spec = None
        why = requires.check(spec, here)
        if why:
            if REFUSED.get(d.name) != why:
                log.warning("pack %s not loaded: %s", d.name, why)
            REFUSED[d.name] = why
            continue
        REFUSED.pop(d.name, None)
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
        m["kind"] = "code" if (d / "adapter.py").is_file() or (d / "hooks.py").is_file() else "data"
        out.append(m)
    return out


# What a `contributes:` rule may contribute to. A rule with one of these is not an alert: it has no message, it
# is never sent, and its SQL is run where the thing it contributes to is built.
CONTRIBUTES = ("report",)


CORE_RULES = Path(os.getenv("RULES_PATH", "/app/config/rules.yml"))


def load_rules() -> list[dict]:
    """Every rule this node evaluates, core plus packs. Lives here rather than in main because two callers need it and
    they must not disagree: main runs them, and index asks which rule ids are still alive when it derives whether an
    alert's condition stopped being true. A rule that has been renamed or deleted can never fire again, so counting
    its silence as a cleared condition would turn every retired rule into a success."""
    try:
        core = yaml.safe_load(CORE_RULES.read_text()) or []
    except FileNotFoundError:
        core = []
    return core + alerts()            # a pack rule with `contributes:` is part of the report, not an alert


def module(pack: str, name: str = "adapter"):
    """A pack's own module, imported from PACKS_DIR, or None if it is not on this node.

    `packs` in app/ is this LOADER, not a package: the pack directories live under PACKS_DIR and
    `import packs.make.adapter` fails with "packs is not a package". Two callers worked around that
    by inserting a path and importing bare — `app/issues/engine.py::_where_to_go` and
    `app/report.py` — and both defaulted PACKS_DIR to "../packs", which is not where a node keeps
    them. It is /app/packs in the image, and PACKS_DIR is unset there, so both imports failed on
    every node: `asks.where` was null with the pack on and a lab 3.3 km away, and the report's
    `make` line never appeared. Neither said anything, because both swallow the failure by design.

    One place knows this path, and it is the one that already reads every pack. This also stops
    mutating sys.path on each call, which the two workarounds did once per request."""
    d = PACKS_DIR / pack
    f = d / f"{name}.py"
    if not f.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(f"pai_pack_{pack}_{name}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:  # noqa: BLE001 — a broken pack must not break the caller
        log.warning("pack %s: %s.py did not import (%s)", pack, name, e)
        return None


def rules() -> list[dict]:
    """Every rule a pack ships, alerts and contributors alike. Rule ids are namespaced <pack>/<id>."""
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


def alerts() -> list[dict]:
    """The rules that can reach a household. A rule with `contributes:` is not one: it has nothing to say on its
    own, and sending a rule with no message once printed the raw template, braces and all."""
    return [r for r in rules() if not r.get("contributes")]


def contributors(to: str = "report") -> list[dict]:
    """The rules whose SQL is run where `to` is built, rather than sent. See docs/PACKS.md."""
    return [r for r in rules() if r.get("contributes") == to]


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


ROLES = ("ambient", "enclosure", "device_health", "derived", "index", "private")


def public_sql(alias: str = "r") -> str:
    """SQL: this row of readings (or readings_1h, or the stats view) is not `private`. The one predicate every road
    out of the house is written with (docs/decisions/2026-10-03-pack-design.md, point 2 (A)): a private reading is
    used here by readouts, sections, rules and cells, and is left out of the daily export, the aggregates a parent
    receives, the report bundle, and every read an agent or a reader without the admin token makes."""
    return (f"NOT EXISTS (SELECT 1 FROM sensors ps JOIN channel_roles pc ON pc.source = ps.source "
            f"WHERE ps.sensor_id = {alias}.sensor_id AND pc.metric = {alias}.metric AND pc.role = 'private')")


def channels() -> list[dict]:
    """Channel role declarations: core's own, then every enabled pack's. A pack may not redeclare a pair core has
    already claimed; the first declaration wins and the duplicate is logged, so a merged pack cannot quietly
    relabel PM2.5 as a vendor index."""
    out, seen = [], set()
    files = [(CORE_CHANNELS, "core")] + [(d / "channels.yml", d.name) for d in _enabled()]
    for f, who in files:
        if not f.exists():
            continue
        try:
            decls = yaml.safe_load(f.read_text()) or []
        except Exception as e:  # noqa: BLE001
            log.warning("channels.yml in %s did not parse: %s", who, e); continue
        for c in decls:
            key = (c.get("source"), c.get("metric"))
            if not all(key) or c.get("role") not in ROLES:
                log.warning("%s: skipping channel declaration %r", who, c); continue
            if key in seen:
                log.warning("%s: %s/%s is already declared; keeping the first", who, *key); continue
            seen.add(key)
            out.append({"source": key[0], "metric": key[1], "role": c["role"],
                        "comparable": bool(c.get("comparable", False)), "unit": c.get("unit"),
                        "reference": c.get("reference"), "declared_by": who})
    return out


def agent_scripts() -> list[str]:
    """`<pack>/<script>` for every pack script an agent may run through `run_pack_script`. A core pack's scripts are
    all reachable, as they always were. A wild pack's are reachable only when its pack.yaml names them under
    `agent_scripts:`, because a wild script can print what its pack keeps off the readings (a camera pack's motion
    log, a photo of the home) and the node's own terminal is the only place that should see it. `planetai run`
    still runs every script."""
    out = []
    for f in sorted(PACKS_DIR.glob("*/*.py")):
        d, name = f.parent, f.stem
        if name in ("adapter", "hooks") or not (d / "pack.yaml").is_file():     # the node calls these; nobody runs them
            continue
        # ponytail: wild means `.wild` beside pack.yaml, written by `planetai packs add`; a pack copied in by hand
        # counts as core. A list of core ids shipped with the release would close that, if hand-copied packs spread.
        if (d / ".wild").is_file():
            try:
                listed = (yaml.safe_load((d / "pack.yaml").read_text()) or {}).get("agent_scripts")
            except Exception:  # noqa: BLE001 — a pack.yaml that does not parse lists nothing
                listed = None
            if not (isinstance(listed, list) and name in listed):
                continue
        out.append(f"{d.name}/{name}")
    return out


def _manifest(d: Path) -> dict:
    try:
        return yaml.safe_load((d / "pack.yaml").read_text()) or {}
    except Exception:  # noqa: BLE001 — a pack.yaml that does not parse is reported where manifests() reads it
        return {}


def _official_on(d: Path) -> bool:
    """An official pack (shipped and signed with the release, so no `.wild`) that names its own `switch:` runs its
    code when that switch is 1, without PACKS_ALLOW_CODE: decision A of the sensors spec (PR #262), for the packs that
    can be switched off by themselves. An official pack without a switch still waits for the flag, because turning
    the flag's meaning over for all of them at once would start forecast, place and surface-heat on every node."""
    import settings
    sw = _manifest(d).get("switch")
    return not (d / ".wild").is_file() and isinstance(sw, str) and settings.get(sw, "0") == "1"


def stations() -> list[dict]:
    """The enabled packs that read public stations around the node (pack.yaml `stations:`), each with its pack id,
    name, `switch` and whether that switch is on. What "Air stations nearby", GET /nearby and the ring's footprint
    read, so none of them names a network."""
    import settings
    out = []
    for m in manifests():
        s, sw = m.get("stations"), m.get("switch")
        if isinstance(s, dict) and s.get("source"):
            out.append({**s, "pack": m["id"], "name": m.get("name") or m["id"], "switch": sw,
                        "on": isinstance(sw, str) and settings.get(sw, "0") == "1"})
    return out


# Hooks: a code pack's `hooks.py` hears what the node does, at two points. `on_readings(sensors, readings)` after every
# batch the node stores (a poll, an MQTT message), and `on_alert(level, text, alert_id)` with every alert it sends.
# Gated like an adapter: PACKS_ALLOW_CODE, or an official pack's own switch. Each pack's module is loaded once per
# process, so what it keeps (packs/home-assistant: the entities it has announced) lasts; which packs are on is read
# again every minute, because emit runs on every MQTT message.
_HOOKS: dict = {"at": 0.0, "on": []}
_HOOK_MODULES: dict = {}


def _hook_modules() -> list:
    if time.time() - _HOOKS["at"] < 60:
        return _HOOKS["on"]
    on = []
    for d in _enabled():
        f = d / "hooks.py"
        if not f.is_file() or not (_allow_code() or _official_on(d)):
            continue
        if f not in _HOOK_MODULES:
            try:
                spec = importlib.util.spec_from_file_location(f"planetai_pack_{d.name}_hooks", f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                _HOOK_MODULES[f] = mod
            except Exception as e:  # noqa: BLE001
                log.warning("pack %s: hooks.py failed to load (%s)", d.name, e)
                continue
        on.append((d.name, _HOOK_MODULES[f]))
    _HOOKS.update(at=time.time(), on=on)
    return on


def emit(name: str, *args) -> None:
    """Call `name` in every pack that has it. A pack that fails is logged and never stops the node's own work."""
    for pack, mod in _hook_modules():
        fn = getattr(mod, name, None)
        if callable(fn):
            try:
                fn(*args)
            except Exception as e:  # noqa: BLE001
                log.warning("pack %s: %s failed (%s)", pack, name, type(e).__name__)


def adapters(hc):
    """Source adapters from code packs. Off unless PACKS_ALLOW_CODE=1, or an official pack's own switch is on — a
    pack's adapter.py runs with this node's privileges and network access. Read it before you enable it."""
    out = []
    for d in _enabled():
        f = d / "adapter.py"
        if not f.is_file():
            continue
        if not (_allow_code() or _official_on(d)):
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
