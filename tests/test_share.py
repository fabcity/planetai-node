"""SHARE_LEVEL, and the two leaks it closes. No network, no database.

The static half reads app/main.py and asserts on it, the shape test_shipped.py uses — because the thing that recurs
here is structural. `SELECT *` in /sensors published every column added to the table on the day it landed (A7), so a
test that only checked today's redaction would pass the day someone adds `sensors.wifi_ssid`.

The request half drives FastAPI's TestClient with the database stubbed out. TestClient's peer address is
"testclient", which is not loopback, so by default every request here is exactly the case that matters: a stranger
on the house WiFi. Loopback is asked for explicitly where it is the subject.

Run: PYTHONPATH=app python3 tests/test_share.py
"""
import ast
import os
import re

SRC = open("app/main.py").read()
SETTINGS = open("app/settings.py").read()
ENV = open(".env.example").read()
GUI = open("app/static/index.html").read()

# ---------------------------------------------------------------- the structural half
tree = ast.parse(SRC)
funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

# A7 · the star is the bug, not just the meta filter. Name the columns and a new one stays private until it is named.
# The docstring is stripped first: it explains why the star is gone, and naming it there must not read as using it.
def code_of(name):
    fn = funcs[name]
    stmts = fn.body[1:] if ast.get_docstring(fn) else fn.body
    return "\n".join(ast.get_source_segment(SRC, st) for st in stmts)
body = code_of("sensors_")
assert "SELECT *" not in body, "/sensors is back on SELECT *: every column added to `sensors` now publishes itself"
assert "FROM sensors" in body and "sensor_id" in body, "/sensors must name its columns"
for k in ("host", "firmware", "mesh_node", "gateway", "channel", "root_topic", "topic"):
    assert f'"{k}"' not in body, f"/sensors names {k} — the allowlist is what to keep, not a denylist of what to drop"
print("sensors: columns named, not SELECT *")

# F11 · every numeric query parameter in every route carries bounds. This walk found exactly one that did not.
unguarded = []
for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    if not any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") in ("get", "post", "put") for d in node.decorator_list):
        continue
    args = node.args.args[len(node.args.args) - len(node.args.defaults):]
    for a, d in zip(args, node.args.defaults):
        if getattr(a.annotation, "id", "") not in ("int", "float"):
            continue
        kw = {k.arg for k in d.keywords} if isinstance(d, ast.Call) and getattr(d.func, "id", "") == "Query" else set()
        if not {"ge", "le"} <= kw:
            unguarded.append(f"{node.name}({a.arg})")
assert not unguarded, f"numeric route parameters with no ge=/le= bounds: {unguarded}"
print("routes: every numeric parameter is bounded")

# A12 · /health rounds for every caller, at every level.
assert re.search(r'"lat": round\(float\(os\.getenv\("NODE_LAT".*?\), 3\)', SRC), "/health must round lat to 3 decimals"
assert re.search(r'"lon": round\(float\(os\.getenv\("NODE_LON".*?\), 3\)', SRC), "/health must round lon to 3 decimals"
assert '"node": NODE' in SRC, "/health keeps the node name: /export publishes it by design and the dashboard prints it in five places"

# The two paths that are on no allowlist at any level, and the one the middleware must not decide twice.
mw = ast.get_source_segment(SRC, funcs["_share_level"])
allow = SRC[SRC.index("_SHARE_OFF = ("):SRC.index("_SHARE = {")]
for p in ("place/geojson", "settings/raw", "backups", "actions", "aggregates", "test-alert"):
    assert f'"/{p}"' not in allow, f"/{p} is on a SHARE_LEVEL allowlist and must never be"
assert 'startswith("/mcp")' in mw, "the middleware must pass /mcp through: _mcp_auth has already decided it"
assert "_bearer_ok" in mw, "the middleware must reuse _bearer_ok, which is constant-time"
assert "headers" not in code_of("_is_local"), \
    "_is_local reads a header: X-Forwarded-For would make the loopback bypass a one-line spoof. Use request.client only."
print("allowlists: the plan, the raw settings and every write are off them")

# The setting itself, and the reserved names that are refused rather than silently accepted.
assert '"SHARE_LEVEL"' in SETTINGS and '"ACT_TOKEN"' in SETTINGS, "settings.py: both new keys"
assert '"SHARE_LEVEL":   ("off", "open")' in SETTINGS, "settings.py: SHARE_LEVEL must refuse anything but off and open"
assert '"SHARE_LEVEL"}' in SETTINGS or '"SHARE_LEVEL",' in SETTINGS, "settings.py: SHARE_LEVEL must be PUBLIC"
for word in ("cell", "means"):
    assert word in SETTINGS.split('"SHARE_LEVEL":        (')[1][:1200], f"settings.py: {word} must be named in SHARE_LEVEL's help as reserved"
assert re.search(r"^SHARE_LEVEL=off", ENV, re.M) and re.search(r"^ACT_TOKEN=", ENV, re.M), ".env.example: both new keys"
assert "planetai_act" in GUI and "acttok" in GUI, "the dashboard's Unlock panel needs the second token field"
assert "e===403" in GUI, "the plan card must say why it is empty rather than going blank"
print("setting: declared, bounded, documented, and in the dashboard")

import settings as S
assert "cell" not in S.CHOICES["SHARE_LEVEL"] and "means" not in S.CHOICES["SHARE_LEVEL"]
try:
    S.set("SHARE_LEVEL", "cell"); raise AssertionError("SHARE_LEVEL=cell must be refused: it would do nothing")
except ValueError as e:
    assert "cell" in str(e), "the refusal must quote the help text, which says what cell will mean"
print("reserved levels refused")

# ---------------------------------------------------------------- the request half
try:
    from fastapi.testclient import TestClient
except ImportError:
    print("share: request checks skipped (pip install -r app/requirements.txt)")
    raise SystemExit(0)

import logging
import time
logging.disable(logging.WARNING)      # main.py logs a failed bootstrap connect on import; that is the point of the stub
os.environ.update(ADMIN_TOKEN="admin-tok", ACT_TOKEN="act-tok", NODE_LAT="-8.6478291", NODE_LON="115.1385412",
                  NODE_NAME="bayu-2", DATABASE_URL="postgresql://unused/never-connected")
import settings                                    # noqa: F811 — the same module; the stub below is what matters
settings._cache = {"at": time.time() + 1e9, "rows": {}}     # never touch a database: get() falls through to the environment
import main

# One sensor row shaped like the AirGradient on the clean node: a hostname on the WiFi, a room name, 7 decimals.
ROW = {"sensor_id": "ag-84fce6", "source": "airgradient", "name": "Kitchen, upstairs", "lat": -8.6478291,
       "lon": 115.1385412, "indoor": True, "local": True, "kind": "sensor", "scale": "community", "cadence": "PT5M",
       "meta": {"host": "airgradient_84fce6.local", "model": "I-9PSL", "firmware": "3.1.9", "licence": "CC BY 4.0",
                "mesh_node": "!8f491db0", "gateway": "gw-1", "channel": "0", "root_topic": "msh", "topic": "msh/x"}}
main.q = lambda sql, *a: [dict(ROW, meta=dict(ROW["meta"]))] if "FROM sensors" in sql else []
main.db = lambda: (_ for _ in ()).throw(RuntimeError("no database in this test"))

def level(v):
    settings._cache["rows"]["SHARE_LEVEL"] = v

lan = TestClient(main.app)                                   # peer "testclient": a stranger on the WiFi
local = TestClient(main.app, client=("127.0.0.1", 51000))    # the machine the node runs on
ADMIN, ACT = {"Authorization": "Bearer admin-tok"}, {"Authorization": "Bearer act-tok"}

def dp(x):
    return len(str(float(x)).split(".")[1].rstrip("0"))

level("off")
assert lan.get("/sensors").status_code == 403, "off: an unauthenticated /sensors from the WiFi must be refused"
assert "SHARE_LEVEL" in lan.get("/sensors").json()["error"], "the 403 must name the setting"
assert lan.get("/sensors", headers=ADMIN).status_code == 200, "off: the admin token still reads /sensors"
assert lan.get("/sensors", headers=ADMIN).json()[0]["meta"]["host"], "a token reads the unredacted row"
assert local.get("/sensors").status_code == 200, "off: this machine still reads everything"
assert lan.get("/health").status_code == 200 and lan.get("/").status_code == 200, "off: the shell stays readable"
assert lan.get("/export").status_code != 403, "off: backup.sh fetches /export over the published port to write the daily file"
print("off: /sensors refused from the WiFi, answered to a token and to this machine")

for lv in ("off", "open"):
    level(lv)
    h = lan.get("/health").json()
    assert dp(h["lat"]) <= 3 and dp(h["lon"]) <= 3, f"{lv}: /health hands out {h['lat']},{h['lon']}"
    assert h["node"] == "bayu-2", f"{lv}: /health keeps the node name"
    assert lan.get("/place/geojson").status_code == 403, f"{lv}: the building's shape needs a token"
    assert lan.get("/settings/raw").status_code == 403, f"{lv}: the unmasked keys need a token"
print("every level: 3 decimals in /health, the plan and the raw settings refused")

level("open")
r = lan.get("/sensors")
assert r.status_code == 200, "open: a wall screen with no token reads the sensors"
s0 = r.json()[0]
for k in ("host", "firmware", "mesh_node", "gateway", "channel", "root_topic", "topic"):
    assert k not in s0["meta"], f"open: /sensors still hands out meta.{k}"
assert s0["meta"]["licence"] == "CC BY 4.0", "open: provenance must survive the filter — it is what makes a reading citable"
assert dp(s0["lat"]) <= 3 and dp(s0["lon"]) <= 3, f"open: /sensors hands out {s0['lat']},{s0['lon']}"
assert s0["name"] == "Kitchen, upstairs", "open: the sensor's name is on the dashboard and stays"
print("open: sensors readable, hostnames and firmware gone, position at 110 m")

# F10 · closing a loop. The middleware refuses the anonymous case; the route refuses a read-only token.
level("open")
assert lan.post("/actions", json={"alert_id": 1, "stage": "acted"}).status_code == 403, "open: an anonymous action must be refused"
assert lan.post("/actions", json={"alert_id": 1, "stage": "bad"}, headers=ACT).status_code == 400, "open: ACT_TOKEN gets past the gate and reaches the route"
level("off")
assert local.post("/actions", json={"alert_id": 1, "stage": "bad"}).status_code == 400, "off: this machine records an action with no token"
assert lan.post("/actions", json={"alert_id": 1, "stage": "acted"}).status_code == 403, "off: an action from the WiFi must be refused"
print("actions: open on this machine, ACT_TOKEN from anywhere else")

# The reduced settings read: the layout, because every screen in the house needs it, and the level, so a screen can say why.
level("off")
d = {r["key"]: r for r in lan.get("/settings").json()["runtime"]}
assert d["SHARE_LEVEL"]["value"] == "off", "off: a refused screen must be able to read what is refusing it"
assert d["UI_LAYOUT"]["value"] == "" or d["UI_LAYOUT"]["value"] is not None, "off: the layout read must keep working"
assert d["ALERT_LEVEL"]["value"] == "" or "••" in d["ALERT_LEVEL"]["value"], "off: everything else is masked"
assert d["TELEGRAM_BOT_TOKEN"]["value"] in ("", "•••• set"), "a secret is masked at every level"
level("open")
assert lan.get("/settings").json()["runtime"], "open: /settings still answers"
print("settings: at off, the layout and the level and nothing else")
print("all share-level checks passed")
