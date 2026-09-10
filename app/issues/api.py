"""`GET /issues` and `GET /issues/fixtures/{name}`.

Two routes on one prefix, which is the point: `/issues` goes on the `SHARE_LEVEL=open` allowlist and
never on the `off` one, and that single entry covers both. A snapshot carries 15-minute means, alert
texts and sensor names — the household's own data — so a fixture must not be served from `/static/`,
which is readable at `off`.

`app/main.py` learns about this file in exactly two lines: `include_router` and the `/issues` prefix
in `_SHARE_OPEN`. Everything else about issues lives in this package.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Path as PathParam

from . import load
from . import engine

log = logging.getLogger("planetai.issues")
router = APIRouter(prefix="/issues", tags=["issues"])

FIXTURES = Path(__file__).resolve().parent / "fixtures"
# A name, not a path. `{name:path}` would be one `..` away from reading the filesystem, and this port
# answers a household LAN — the same reasoning as COMPANIONS in app/main.py.
NAME = r"^[a-z0-9][a-z0-9._-]{0,63}$"


@router.get("")
@router.get("/")
def issues_now():
    """Every issue this node declares: state, stack, line, attribution, sentence, asks, series.

    The order is `NODE_ISSUES`; an issue the keeper has not declared still appears, marked
    `watched: false`, so a stranger can see what this node could report. `headline` is the issue
    with the highest state, ties going to the declared order.

    The node computes; the page draws. Nothing in the response needs arithmetic to render, and
    nothing in it came from a model.
    """
    import main                    # noqa: PLC0415 — main imports this module at the bottom of itself
    with main.db() as con, con.cursor() as cur:
        return engine.compute(cur, main.settings, load(), earth=_earth())


def _earth():
    """`/earth`'s body, or None. The earth pack's record has exactly one reader in this repo and it
    is `main.earth()`; land's region column asks it rather than opening the pack's files again."""
    import main                    # noqa: PLC0415
    try:
        return main.earth()
    except Exception as e:  # noqa: BLE001
        log.warning("issues: /earth did not answer (%s: %s) — land falls back", type(e).__name__, str(e)[:120])
        return None


@router.get("/fixtures")
def fixtures():
    """Which snapshots this node ships, so a design round does not have to guess a name."""
    return {"fixtures": sorted(p.stem for p in FIXTURES.glob("*.json"))}


@router.get("/fixtures/{name}")
def fixture(name: str = PathParam(pattern=NAME)):
    """One committed snapshot, with its issues computed at the hour it was captured.

    The dashboard reads this with `?fixture=<name>` and renders exactly what it renders from live
    data — same engine, same shape — which is the only way a page reviewed against a fixture tells
    you anything about the page.
    """
    import main                    # noqa: PLC0415
    f = FIXTURES / f"{name}.json"
    if not f.is_file():
        raise HTTPException(404, f"no such fixture; this node ships {fixtures()['fixtures']}")
    snap = json.loads(f.read_text())
    try:
        snap["issues"] = engine.replay(snap, main.settings, load())
    except LookupError as e:        # a snapshot missing a table the engine reads
        snap["issues"] = {"error": str(e)}
    return snap
