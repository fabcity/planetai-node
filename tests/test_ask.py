"""The ask pane: what the model is told, what it may do, and what is kept. No model, no database, no network.

  · privacy: the context built on node #1's 21 Sep capture carries none of the node's position to three
    decimals, no sensor or station name, no sensor id and no `meta`; and a tool result is scrubbed the same way
  · a request to turn MAP_TILES on is a `proposal` card and no setting changes
  · nothing is stored: after a request the log holds no word that was asked or answered, and the database was
    never opened
  · /ask/status is 404 with no loop set up, and says `running: false` with the tag when Ollama is down
  · /docs/search answers from the build's copy of docs/site, with no model
  · the three routes follow SHARE_LEVEL like every other read

Run: PACKS_DIR=packs PYTHONPATH=app python3 tests/test_ask.py
"""
import asyncio
import io
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("PACKS_DIR", "packs")
sys.path.insert(0, str(ROOT / "app"))

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("ask: skipped (pip install -r app/requirements.txt)")
    raise SystemExit(0)

logging.disable(logging.WARNING)
os.environ.update(ADMIN_TOKEN="admin-tok", NODE_NAME="bayu-2", DATABASE_URL="postgresql://unused/never-connected",
                  COMPOSE_PROFILES="mqtt,agent", OLLAMA_URL="http://127.0.0.1:9", AGENT_MODEL="qwen3.5:4b")
import settings                                     # noqa: E402
settings._cache = {"at": time.time() + 1e9, "rows": {}}
import main                                         # noqa: E402
import ask                                          # noqa: E402
import agent_loop                                   # noqa: E402
import issues as I                                  # noqa: E402
from issues import engine                           # noqa: E402
from issues import api as issues_api                # noqa: E402

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


class S(dict):
    def get(self, k, d=""):
        return super().get(k, d)

    def num(self, k, d):
        return d


FIX = json.loads((ROOT / "app/issues/fixtures/node1-2026-09-21d.json").read_text())
DOC = engine.replay(FIX, S(NODE_ISSUES="air,heat,land,coast"), I.load())
LAT, LON = FIX["health"]["lat"], FIX["health"]["lon"]
NAMES = sorted({s["name"] for s in FIX["sensors"] if s.get("name")} | {s["name"] for s in DOC["stations"] if s.get("name")})
IDS = sorted({s["sensor_id"] for s in FIX["sensors"]})
check(NAMES and IDS and any(n.lower() in json.dumps(DOC, ensure_ascii=False).lower() for n in NAMES),
      "the capture has no sensor name in its bundle, so the privacy test below would prove nothing")


def leaks(text: str) -> list[str]:
    found = [f"{v:.3f}" for v in (LAT, LON) if f"{v:.3f}" in text]
    found += [n for n in NAMES if len(n) >= 3 and n.lower() in text.lower()]
    found += [i for i in IDS if i in text]
    found += [f'"{k}"' for k in ("meta", "lat", "lon", "sensor_id") if f'"{k}"' in text]
    return found


# ---------------------------------------------------------------- privacy
learn = json.loads((ROOT / "app/static/learn.json").read_text())
scrub = ask.scrub_for(DOC, [s.get("name") for s in FIX["sensors"]], LAT, LON)
ctx = json.dumps(scrub.value(ask.context(DOC, "en", "now", "advanced", "lead", learn, "v0.73")), ensure_ascii=False)
check(not leaks(ctx), f"the pane's context carries {leaks(ctx)}")
check("focus" in ctx and "The first thing on Now" in ctx, "the context lost the learn entry for the part in focus")
check(json.loads(ctx)["open_alerts"], "the context lost the open alerts, so the privacy test is scrubbing nothing")
for name in ("sensors", "stations"):
    raw = json.dumps(FIX["sensors"] if name == "sensors" else DOC["stations"], ensure_ascii=False)
    check(leaks(raw) and not leaks(scrub(raw)), f"a {name} tool result reaches the model with {leaks(scrub(raw))}")
print("  privacy: the context and a tool result carry no position, name, id or meta")

# ---------------------------------------------------------------- the stubs every request below uses
LOG = io.StringIO()
logging.disable(logging.NOTSET)
handler = logging.StreamHandler(LOG)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)

opened = []
main.db = lambda: opened.append("db") or (_ for _ in ()).throw(RuntimeError("no database in this test"))
main.q = lambda sql, *a: [{"name": s.get("name")} for s in FIX["sensors"]] if "FROM sensors" in sql else []
issues_api.issues_now = lambda: DOC
written = []
settings.set = lambda *a, **k: written.append(("settings.set", a, k))

ASKED = "Could you please turn the satellite map on for me"
ANSWER = "I have put the satellite map on a card for you to press"


class Tool:
    def __init__(self, name):
        self.name, self.description, self.inputSchema = name, name, {"type": "object", "properties": {}}


class Session:
    def __init__(self):
        self.called = []

    async def call_tool(self, name, args):
        self.called.append(name)
        return type("R", (), {"content": [type("C", (), {"text": json.dumps(FIX["sensors"])})()]})()


SESSION = Session()


@asynccontextmanager
async def fake_session(hc, url=None, keep=None):
    listed = [Tool(n) for n in ("status", "sensors", "settings_get", "settings_set", "act", "run_pack_script")]
    yield SESSION, keep(listed)


SCRIPT = []


async def fake_chat(hc, rung, messages, tools, final=False, system=None):
    SCRIPT.append({"tools": [t["function"]["name"] for t in tools or []], "system": system,
                   "seen": json.dumps([m.get("content") for m in messages if m.get("role") == "tool"], ensure_ascii=False)})
    if len(SCRIPT) == 1:
        return {"role": "assistant", "content": "", "tool_calls": [
            {"id": "a", "function": {"name": "sensors", "arguments": "{}"}},
            {"id": "b", "function": {"name": "settings_set", "arguments": json.dumps({"changes": {"MAP_TILES": "on"}})}},
            {"id": "c", "function": {"name": "act", "arguments": json.dumps({"alert_id": 367, "note": "I opened the windows"})}}]}
    return {"role": "assistant", "content": ANSWER}


agent_loop.node_session = fake_session
agent_loop.chat = fake_chat
lan = TestClient(main.app)
local = TestClient(main.app, client=("127.0.0.1", 51000))


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(l.split(": ", 1) for l in block.split("\n") if ": " in l)
        if "event" in lines:
            out.append((lines["event"], json.loads(lines["data"])))
    return out


# ---------------------------------------------------------------- a request that asks for a change
settings._cache["rows"]["MAP_TILES"] = "off"
r = local.post("/ask", json={"messages": [{"role": "user", "content": ASKED}], "view": "now", "mode": "simple"})
check(r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream"), f"/ask answered {r.status_code}")
ev = events(r.text)
kinds = [e for e, _ in ev]
prop = next((d for e, d in ev if e == "proposal"), None)
check(ask._proposal({"tool": "settings_set", "args": {"changes": {"MAP_TILES": "1"}}}, "en")["proposed"] is None,
      "a value the key would refuse must not be proposed")
check(prop and prop["setting"] == "MAP_TILES" and prop["current"] == "off" and prop["proposed"] == "on",
      f"MAP_TILES did not become a proposal card: {prop}")
check(prop and "tile server" in prop["leaves"]["en"] and "Set up" in prop["undo"]["en"],
      f"the card does not say what leaves and how to undo it: {prop}")
check("settings_set" not in SESSION.called and "sensors" in SESSION.called,
      f"the loop ran {SESSION.called}: an admin tool was executed, or a read was not")
check(not written and settings._cache["rows"]["MAP_TILES"] == "off", f"a setting changed: {written}")
actp = next((d for e, d in ev if e == "proposal" and d["tool"] == "act"), None)
check(actp and actp["args"] == {"alert_id": 367} and "opened the windows" not in r.text,
      f"an act card must carry the alert and never the model's words for what the person did: {actp}")
check("act" not in SESSION.called, "the loop ran act")
check(kinds[-1] == "done" and "tools" in kinds and "token" in kinds, f"the stream was {kinds}")
check("".join(d["text"] for e, d in ev if e == "token").strip() == ANSWER, "the answer did not arrive as tokens")
menu = SCRIPT[0]["tools"]
check("settings_get" not in menu and "status" in menu and "settings_set" in menu and "act" in menu,
      f"the pane's menu is {menu}")
check(not leaks(SCRIPT[0]["system"]), f"the system prompt carries {leaks(SCRIPT[0]['system'])}")
check(len(SCRIPT) > 1 and "sensor" in SCRIPT[1]["seen"] and not leaks(SCRIPT[1]["seen"]),
      f"the sensors result reached the model carrying {leaks(SCRIPT[-1]['seen'])}")
print("  proposal: MAP_TILES on is a card with its current value, what leaves and the way back; nothing changed")

# ---------------------------------------------------------------- the shape a live node hands it
# A capture's timestamps are strings; the live engine's are datetimes straight from Postgres. v0.75 was
# tested on captures only and answered every question on node #1 with a 500 (datetime is not JSON
# serializable). The same request, on the live shape.
import copy                                          # noqa: E402
LIVE = copy.deepcopy(DOC)
for _v in LIVE["issues"].values():
    for _a in _v.get("open_asks") or []:
        _a["ts"] = datetime.fromisoformat(_a["ts"])
check(any(isinstance(a["ts"], datetime) for v in LIVE["issues"].values() for a in v.get("open_asks") or []),
      "the live-shaped bundle has no datetime in it, so this proves nothing")
issues_api.issues_now = lambda: LIVE
SCRIPT.clear()
r2 = local.post("/ask", json={"messages": [{"role": "user", "content": "how is it"}]})
check(r2.status_code == 200 and [e for e, _ in events(r2.text)][-1] == "done",
      f"on a live node's bundle /ask answered {r2.status_code}: {r2.text[:200]}")
issues_api.issues_now = lambda: DOC
print("  live shape: datetimes from Postgres reach the model as ISO strings, not a 500")

# ---------------------------------------------------------------- nothing is stored
logged = LOG.getvalue()
check(ASKED not in logged and ANSWER not in logged and "satellite map" not in logged,
      "a word somebody asked or the model answered is in the log")
check("[pane] tool sensors" in logged, "the log should still say which tool ran and how long it took")
check(not opened, "the pane opened the database")
check(not list((ROOT / "out").glob("*ask*")) if (ROOT / "out").exists() else True, "the pane wrote a file under out/")
print("  nothing kept: the log names the tool and its time, never a word; no database, no file")
logging.getLogger().removeHandler(handler)
logging.disable(logging.WARNING)

# ---------------------------------------------------------------- status
os.environ["COMPOSE_PROFILES"] = "mqtt"
_nf = local.get("/ask/status")
check(_nf.status_code == 404 and _nf.json()["detail"]["recommend"]["pull"].startswith("planetai agent local pull ")
      and _nf.json()["detail"]["mcp"] == "/mcp", f"the 404 must carry what to pull and the other way in: {_nf.text}")
check(local.post("/ask", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 404,
      "with no agent profile /ask must be 404")
os.environ["COMPOSE_PROFILES"] = "mqtt,agent"
st = local.get("/ask/status").json()
check(st["running"] is False and st["model"] == "qwen3.5:4b" and st["stored"] is False and "not answering" in st["why"],
      f"Ollama down should read running:false with the tag: {st}")
check({t["class"] for t in st["tools"]} == {"read", "act", "admin"} and "settings_get" not in {t["name"] for t in st["tools"]},
      f"/ask/status lists {st['tools']}")
print("  status: 404 with no loop, running:false with the tag when Ollama is down")

# ---------------------------------------------------------------- docs search, and the share level
hits = local.get("/docs/search", params={"q": "map_tiles"}).json()
check(hits and all({"page", "anchor", "title", "snippet"} <= set(h) for h in hits)
      and any("MAP_TILES" in h["snippet"] for h in hits), f"/docs/search found {hits[:2]}")
check(local.get("/docs/search", params={"q": "x"}).status_code == 422, "a one-letter search should be refused")
settings._cache["rows"]["SHARE_LEVEL"] = "off"
check(all(lan.get(p, params={"q": "air"}).status_code == 403 for p in ("/ask/status", "/docs/search")),
      "at SHARE_LEVEL=off the pane's routes must need a token from the WiFi")
settings._cache["rows"]["SHARE_LEVEL"] = "open"
check(lan.get("/docs/search", params={"q": "air"}).status_code == 200, "at open the WiFi may search the docs")
print("  docs: searched with no model; the routes follow SHARE_LEVEL")

print("\n".join(f"  x {f}" for f in fails) or "  ask: private context, proposals not changes, nothing kept")
sys.exit(1 if fails else 0)
