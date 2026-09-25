"""The dashboard's ask pane: `GET /ask/status`, `POST /ask`, `GET /docs/search`.

A person reading the page asks the node's own model, on this machine, about what the page shows. The loop is
`agent_loop.pane`: it reads, and anything else it reaches for comes back as a proposal the person presses.

THREE PROMISES, EACH HELD BY A TEST IN tests/test_ask.py:

  · The context carries no coordinate, no room or sensor name, no sensor id and no `meta`. It is built here from
    the /issues bundle the page already has, and every tool result passes through the same `scrub` before the
    model reads it. A local model is on the machine those facts describe; the rule holds anyway, because a pane
    open on a wall is read by whoever walks past, and what the model is never told it cannot repeat.
  · Nothing is stored. No transcript on disk, no row, no log line with a word anybody typed. The thread lives in
    the browser tab and dies with it.
  · Nothing is changed. An `act` or an admin tool is a `proposal` event; the page presses it with its own token.

`/docs/search` needs no model: a case-insensitive substring over learn.json and data/docs_site.json, which
`make learn` cuts out of docs/site at build time, because the container never sees docs/.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import agent_loop
import settings
from tool_classes import TOOL_CLASS

log = logging.getLogger("planetai.ask")
router = APIRouter(tags=["ask"])
HERE = Path(__file__).resolve().parent
LEARN = HERE / "static" / "learn.json"
# `./data` is mounted at /app/data in the container, and sits beside app/ in a checkout.
DOCS_COPY = next((p for p in (HERE / "data" / "docs_site.json", HERE.parent / "data" / "docs_site.json")
                  if p.exists()), HERE / "data" / "docs_site.json")
LOCALES = ("en", "id", "es")

# Keys that name a place, a device or a household's own words about its kit. Dropped wherever they occur.
DROP = frozenset({"lat", "lon", "latitude", "longitude", "centroid", "center", "position", "sensor_id", "sensor_ids",
                  "sensors", "name", "source", "meta", "stations", "geometry", "host", "hostname", "mesh_node",
                  "gateway", "topic", "root_topic", "actor", "note", "provenance", "series", "buckets"})


class Scrub:
    """What the model may never be told: this node's position and the names and ids of the things in it.

    Built once per request from what the node knows about itself, so a sensor renamed this morning is
    scrubbed this afternoon. Keys in DROP are removed at any depth; in every string left, each known name and
    id becomes "a sensor", and the node's own coordinates, to two decimals or finer, become "here".
    """

    def __init__(self, names=(), lat=None, lon=None):
        pats = sorted({str(n).strip() for n in names if n and len(str(n).strip()) >= 3}, key=len, reverse=True)
        self.names = re.compile("|".join(re.escape(n) for n in pats), re.I) if pats else None
        coords = []
        for v in (lat, lon):
            if v:
                head = f"{float(v):.2f}"
                coords.append(re.escape(head) + r"\d*")
        self.coords = re.compile("|".join(coords)) if coords else None

    def text(self, s: str) -> str:
        if self.names:
            s = self.names.sub("a sensor", s)
        if self.coords:
            s = self.coords.sub("here", s)
        return s

    def value(self, v):
        if isinstance(v, dict):
            return {k: self.value(x) for k, x in v.items() if k not in DROP}
        if isinstance(v, list):
            return [self.value(x) for x in v]
        if isinstance(v, str):
            return self.text(v)
        return v

    def __call__(self, text: str) -> str:
        """A tool's result, which arrives as JSON text; anything that is not JSON is scrubbed as a string."""
        try:
            return json.dumps(self.value(json.loads(text)), ensure_ascii=False)
        except (TypeError, ValueError):
            return self.text(str(text))


def scrub_for(doc: dict, sensor_names=(), lat=None, lon=None) -> Scrub:
    names = list(sensor_names)
    ids = []
    for s in doc.get("stations") or []:
        names.append(s.get("name")); ids.append(s.get("sensor_id"))
    for iss in (doc.get("issues") or {}).values():
        for cell in (iss.get("stack") or {}).values():
            if cell:
                ids += cell.get("sensors") or []
                if cell.get("source") and not re.fullmatch(r"\d+ sensors", str(cell["source"])):
                    names.append(cell["source"])
    return Scrub(names + ids, lat, lon)


def context(doc: dict, loc: str, view: str, mode: str, focus: str | None = None, learn: dict | None = None,
            version: str = "") -> dict:
    """What the model is told the page shows. Everything is the node's own words and figures from /issues."""
    loc = loc if loc in LOCALES else "en"

    def L(d):
        return (d.get(loc) or d.get("en") or "") if isinstance(d, dict) else (d or "")
    iss = doc.get("issues") or {}
    lead = (doc.get("lead") or {}).get("issue")
    h = (iss.get(lead) or {}).get("hero") or {}
    out = {
        "view": view, "mode": mode, "node_version": version,
        "lead": {"issue": lead, "picked_by": (doc.get("lead") or {}).get("by"),
                 "value": h.get("value"), "unit": h.get("unit"), "stamp": L(h.get("stamp")),
                 "sentence": L(h.get("sentence")), "plain": L(h.get("plain")), "rule": h.get("rule")},
        "digest": {k: L(v) for k, v in (doc.get("digest") or {}).items()},
        "issues": [{"issue": k, "name": L(v.get("name")), "state": v.get("state"), "why": L(v.get("reason_text")),
                    "unit": v.get("unit"), "line": (v.get("line") or {}).get("value"),
                    "at": {d: c.get("value") for d, c in (v.get("stack") or {}).items() if c}}
                   for k, v in iss.items() if v.get("watched") is not False],
        "open_alerts": [{"id": a.get("id"), "issue": k, "at": a.get("ts"), "says": str(a.get("text") or "").split("\n")[0]}
                        for k, v in iss.items() for a in (v.get("open_asks") or [])][:12],
    }
    if focus and learn:
        m = (learn.get("marks") or {}).get(focus)
        if m:
            out["focus"] = {"part": m.get("title"), "quote": m.get("quote"), "more": m.get("more"),
                            "from": f"{m.get('page_title')} · {m.get('section') or ''}".strip(" ·")}
    return out


def configured() -> bool:
    """A loop is configured when the agent profile is on: `planetai agent local` adds it."""
    return "agent" in (os.getenv("COMPOSE_PROFILES") or "").replace(" ", "").split(",")


def _probe(model: str) -> tuple[bool, str]:
    url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    try:
        tags = httpx.get(url + "/api/tags", timeout=3).json().get("models") or []
    except (httpx.HTTPError, ValueError):
        return False, "Ollama is installed and not answering"
    names = {t.get("name") for t in tags} | {str(t.get("name", "")).removesuffix(":latest") for t in tags}
    return (True, "") if model in names else (False, f"{model} is not on this machine yet")


@router.get("/ask/status")
def ask_status():
    """Which model the pane would ask, whether it is running, and what it may do. 404 when no loop is set up."""
    if not configured():
        raise HTTPException(404, "no model is set up on this node; `planetai agent local` sets one up")
    rung = agent_loop.local_rung()
    running, why = _probe(rung.model)
    return {"model": rung.model, "rung": rung.name, "running": running, "why": why or None,
            "tools": [{"name": n, "class": TOOL_CLASS[n]} for n in sorted(agent_loop.PANE_TOOLS)],
            "stored": False}


class Msg(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class AskBody(BaseModel):
    messages: list[Msg] = Field(min_length=1, max_length=24)
    view: str = Field("now", max_length=20)
    mode: str = Field("advanced", max_length=20)
    focus: str | None = Field(None, max_length=40)


def _proposal(p: dict, loc: str) -> dict:
    """Add a setting's own words to a proposal: its current value, what would leave, how to undo it."""
    out = dict(p, setting=None, current=None, proposed=None, group=None, leaves=None, undo=None)
    if p.get("tool") == "settings_set":
        changes = (p.get("args") or {}).get("changes") or {}
        key = next(iter(changes), None)
        row = next((r for r in settings.describe()["runtime"] if r["key"] == key), None)
        if row:
            out.update(setting=key, proposed=str(changes[key]), current=row["value"], group=row["group"],
                       leaves={l: row["help"] for l in LOCALES},
                       undo={l: UNDO[l].format(key=key, value=row["value"] or "blank", group=row["group"])
                             for l in LOCALES})
    return out


# A proposal's way back, in the household's language. The id and es strings want a native reader.
UNDO = {"en": "Set {key} back to {value} under Set up → {group}.",
        "id": "Kembalikan {key} ke {value} di Set up → {group}.",
        "es": "Vuelve a poner {key} en {value} en Set up → {group}."}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/ask")
async def ask(body: AskBody):
    """One answer, streamed as server-sent events: token · tools · proposal · done · error. Nothing is kept."""
    if not configured():
        raise HTTPException(404, "no model is set up on this node; `planetai agent local` sets one up")
    import main                                    # noqa: PLC0415 — main includes this router at the bottom of itself
    from issues import api as issues_api           # noqa: PLC0415
    doc = await asyncio.to_thread(issues_api.issues_now)
    try:
        names = [r["name"] for r in await asyncio.to_thread(main.q, "SELECT name FROM sensors") if r.get("name")]
    except Exception:  # noqa: BLE001 — a read failing must not put names back in; it only means fewer to look for
        names = []
    scrub = scrub_for(doc, names, os.getenv("NODE_LAT"), os.getenv("NODE_LON"))
    loc = settings.get("ALERT_LOCALE", "en") or "en"
    learn = json.loads(LEARN.read_text()) if body.focus and LEARN.exists() else None
    ctx = scrub.value(context(doc, loc, body.view, body.mode, body.focus, learn, os.getenv("NODE_VERSION", "")))
    system = agent_loop.PANE_SYSTEM.format(node=os.getenv("NODE_NAME", "node"),
                                           lang=agent_loop.LANG_NAME, context=json.dumps(ctx, ensure_ascii=False))
    hc = httpx.AsyncClient(headers={"Authorization": f"Bearer {os.getenv('ADMIN_TOKEN', '')}",
                                    "X-Agent": agent_loop.AUDIT_PANE}, timeout=60)
    url = f"http://127.0.0.1:{os.getenv('PORT', '8080')}/mcp"

    async def stream():
        try:
            async with agent_loop.node_session(hc, url, keep=agent_loop.pane_tools) as (session, tools):
                async def call(name, args):
                    res = await session.call_tool(name, args)
                    return "\n".join(getattr(x, "text", "") for x in res.content)
                async for event, data in agent_loop.pane([m.model_dump() for m in body.messages], system, tools,
                                                         call, scrub):
                    yield _sse(event, _proposal(data, loc) if event == "proposal" else data)
        except Exception as e:  # noqa: BLE001
            log.warning("ask: %s", type(e).__name__)                  # the kind of failure, never the words
            yield _sse("error", {"message": f"the node could not answer ({type(e).__name__})"})
        finally:
            await hc.aclose()
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


def _docs() -> list[dict]:
    rows = []
    try:
        rows += json.loads(DOCS_COPY.read_text())
    except (OSError, ValueError):
        pass
    try:
        for m in (json.loads(LEARN.read_text()).get("marks") or {}).values():
            rows.append({"page": m.get("page"), "anchor": m.get("anchor"), "title": m.get("title"),
                         "text": f"{m.get('quote', '')} {m.get('more', '')}"})
    except (OSError, ValueError):
        pass
    return rows


@router.get("/docs/search")
def docs_search(q: str = Query(..., min_length=2, max_length=80)):
    """This node's documentation, searched without a model: a substring, case-insensitive, twenty hits at most."""
    needle = q.lower()
    hits = []
    for r in _docs():
        text = str(r.get("text") or "")
        i = (str(r.get("title") or "") + " " + text).lower().find(needle)
        if i < 0:
            continue
        j = max(0, text.lower().find(needle))
        snippet = text[max(0, j - 80): j + 160].strip()
        hits.append({"page": r.get("page"), "anchor": r.get("anchor"), "title": r.get("title"), "snippet": snippet})
        if len(hits) >= 20:
            break
    return hits
