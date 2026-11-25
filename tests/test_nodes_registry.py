"""The nodes the programme lists (docs/SPEC_hello.md step 1): the node reads registry.json on main, keeps only what a
page may see, and serves it at /nodes, open at every share level. UPDATE_CHECK=off reads nothing.

No import of main (it starts a second MQTT client): the functions are lifted whole by AST, as test_agent_buttons does.

    python3 tests/test_nodes_registry.py
"""
import ast
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"REGISTRY_URL", "REGISTRY_EVERY", "REGISTRY_FIELDS", "listed_nodes", "check_registry", "nodes", "_SHARE_OFF"}


class Settings:
    v = {}
    def get(self, k, d=None): return self.v.get(k, d)


class Answer:
    def __init__(self, body, code=200): self.body, self.code = body, code
    def raise_for_status(self):
        if self.code >= 400: raise RuntimeError(self.code)
    def json(self): return json.loads(self.body)


class Client:
    def __init__(self): self.asked, self.answer = 0, None
    def get(self, url, timeout=None):
        self.asked += 1
        if isinstance(self.answer, Exception): raise self.answer
        return self.answer


class App:
    def get(self, *a, **k): return lambda f: f


ns = {"settings": Settings(), "state": {}, "hc": Client(), "time": time, "datetime": datetime, "timezone": timezone,
      "app": App(), "identity": type("Identity", (), {"LISTED": []})(),   # app/identity.py: who pins to a listed id
      "_packs": type("P", (), {"shared": staticmethod(lambda level="open": set())})()}   # auth.py adds the packs' paths
tree = ast.parse((ROOT / "app" / "main.py").read_text() + (ROOT / "app" / "auth.py").read_text())   # _SHARE_OFF is in auth.py
for node in tree.body:
    named = node.name if isinstance(node, ast.FunctionDef) else \
        next((t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)), None)
    if named in NAMES:
        exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
missing = NAMES - set(ns)
assert not missing, f"main.py no longer defines {missing}"

# the repo's own registry.json is what a node will read: it parses and every entry keeps its name
mine = ns["listed_nodes"](json.loads((ROOT / "registry.json").read_text()))
assert mine and all(n["name"] for n in mine), "registry.json lists at least one node"

raw = {"nodes": [
    {"name": "bayu-ungasan", "place": "Ungasan", "cell": "8895a4c843fffff", "lat": -8.816, "lon": 115.164,
     "contact": "someone@example.org", "sources": ["smartcitizen:1"], "scale": "community", "since": "2026-09"},
    {"name": "no-point", "place": "Somewhere"},
    "not a node", {"place": "no name"}]}
rows = ns["listed_nodes"](raw)
assert [r["name"] for r in rows] == ["bayu-ungasan", "no-point"], "a malformed entry is skipped, the rest kept"
assert rows[0]["ll"] == [115.2, -8.8], "another node's point is given to one decimal"
assert rows[1]["ll"] is None, "an entry with no point has none, not 0,0"
assert not any(k in r for r in rows for k in ("contact", "sources", "lat", "lon")), "contact and sources never reach a page"
assert ns["listed_nodes"]("[]") == [] and ns["listed_nodes"]({}) == [], "a file that is not the registry lists nothing"

hc, state, settings = ns["hc"], ns["state"], ns["settings"]
assert ns["nodes"]() == {"read": None, "from": ns["REGISTRY_URL"], "nodes": []}, "nothing read yet says so"

hc.answer = Answer(json.dumps(raw))
ns["check_registry"]()
first = ns["nodes"]()
assert hc.asked == 1 and first["read"] and len(first["nodes"]) == 2 and "error" not in first, "the first check reads"
assert ns["identity"].LISTED == first["nodes"], "the list a parent pins listed names against is the one just read"
ns["check_registry"]()
assert hc.asked == 1, "a second check inside REGISTRY_EVERY asks nothing"

# the second time is a different case: a failed read keeps the last good list and says why
state["registry"]["asked"] -= ns["REGISTRY_EVERY"]
hc.answer = ConnectionError("offline")
ns["check_registry"]()
after = ns["nodes"]()
assert hc.asked == 2 and after["nodes"] == first["nodes"] and after["read"] == first["read"], "a failed read keeps the list"
assert after["error"] == "ConnectionError", "and says why"
ns["check_registry"]()
assert hc.asked == 2, "after a failure it waits an hour, not a minute"

settings.v["UPDATE_CHECK"] = "off"
ns["check_registry"]()
assert hc.asked == 2 and ns["nodes"]()["nodes"] == [], "UPDATE_CHECK=off asks nothing and forgets the list"

assert "/nodes" in ns["_SHARE_OFF"][0], "/nodes is open at every share level"
# Step 2 of docs/SPEC_hub.md: the Node door lists and outlines what this node heard over Reticulum. heardNodes() is lifted
# out of doors-nodegeo.js and run in node. A heard node is matched to a listed one by id, by name only when either side
# has none, so a node that picked a listed node's name but carries another id stays a stranger.
import subprocess  # noqa: E402
prog = r"""
const src = require('fs').readFileSync('./app/static/doors-nodegeo.js', 'utf8');
eval(src.match(/function heardNodes[\s\S]*?\n}\n/)[0]);
const D = {listed: {nodes: [{name: 'bayu-ungasan', id: 'aaaa'}, {name: 'barcelona'}, {name: 'mahon1', id: 'mmmm'}]},
  health: {reticulum: {peers: [
    {node: 'bayu-ungasan', id: 'aaaa', cell: '8395a4fffffffff', res: 3, km: 0, last: 1},
    {node: 'barcelona', id: 'bbbb', cell: '83394cfffffffff', res: 3, km: 12000, last: 2},
    {node: 'mahon1', id: 'zzzz', cell: '831e5ffffffffff', res: 3, km: 11800, last: 3},
    {node: 'old-node', cell: '83194cfffffffff', res: 3, km: 900, last: 4},
    {cell: 'x', last: 5}]}}};
const H = heardNodes(D);
console.log(JSON.stringify(H.map(h => [h.n, h.listed && h.listed.name, h.cell, h.km])));
console.log(JSON.stringify(heardNodes({listed: null, health: {}})));
"""
out = subprocess.run(["node", "-e", prog], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
rows = json.loads(out[0])
assert rows[0] == ["bayu-ungasan", "bayu-ungasan", "8395a4fffffffff", 0], f"the same id is the listed node: {rows[0]}"
assert rows[1][1] == "barcelona", f"a listed node with no id is matched by name: {rows[1]}"
assert rows[2][1] is None, f"a listed name with another id is a stranger, not mahon1: {rows[2]}"
assert rows[3][1] is None and len(rows) == 4, f"an unlisted node is heard and not listed, and a row with no name is dropped: {rows}"
assert json.loads(out[1]) == [], "a node with no bridge and no list hears nobody"
nodejs = (ROOT / "app/static/doors-node.js").read_text()
assert 'class="h3heard"' in nodejs and ".h3heard{fill:none" in (ROOT / "app/static/doors.html").read_text(), (
    "a heard node is drawn as an outline of its cell, never filled and never a point")
assert "they are not on this map yet" not in nodejs, "the Node door still says heard nodes are not drawn"
# and the Node door draws them: the real around() runs in node with the vendored d3, a fake page and a node that heard one
# stranger, so the globe gets a dashed outline of its cell and the list a row saying where and when it was heard
draw = r"""
const fs = require('fs'), d3 = require('./app/static/d3.min.js');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), geoSrc = fs.readFileSync('./app/static/doors-nodegeo.js', 'utf8'),
      node = fs.readFileSync('./app/static/doors-node.js', 'utf8'), load = fs.readFileSync('./app/static/doors-load.js', 'utf8'),
      wallmap = fs.readFileSync('./app/static/doors-wallmap.js', 'utf8');
const one = (src, n) => src.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0];
const fn = (src, n) => src.match(new RegExp('(async )?function ' + n + '\\b[\\s\\S]*?\\n}\\n'))[0];
const el = { world: { clientWidth: 900, innerHTML: '' }, nodes: { innerHTML: '' } };
const $ = s => el[s.slice(1)];
const geo = async () => ({ type: 'FeatureCollection', features: [] }), hhmm = iso => iso.slice(11, 16);   // the page's zone, as UTC here
const ring = ['833944fffffffff', 41.9, 2.5, 41.2, 2.9, 40.9, 2.4, 41.1, 1.8, 41.8, 1.4, 42.1, 1.9];
eval([one(core, 'esc'), one(core, 'fmt'), one(core, 'ago'), one(core, 'num'), one(geoSrc, 'llRing'), fn(geoSrc, 'heardNodes'), fn(load, 'sendersOf'), one(wallmap, 'notHouse'), fn(node, 'around')].join('\n'));
var KNOWN_NODES = [{ n: 'bayu-ungasan', place: 'Ungasan', ll: [115.17, -8.81], listed: true, reads: 'community', me: true }];
var D = { as_of: '2026-11-25T03:05:00Z', listed: { read: '2026-11-25T02:55:00Z', nodes: [{ name: 'bayu-ungasan' }] },
  health: { reticulum: { announce_s: 1800, relaying: 0, hub: null, peers: [
    { node: 'test-stand-in', id: 'teststandin00000', cell: '833944fffffffff', res: 3, km: 12609, last: Date.parse('2026-11-25T03:01:00Z') / 1000 }] } },
  ngeo: { planet: [], lit: [], dist: {}, heard: { '833944fffffffff': ring } } };
(async () => {
  await around(); const first = { svg: el.world.innerHTML, list: el.nodes.innerHTML.replace(/<[^>]+>/g, ' ') };
  /* a child under a community node names its parent and says when its means went (25 Nov 2026) */
  D.health.parent = { node: 'bayu-ungasan', at: '2026-11-25T03:00:00Z', sensors: 2 }; await around();
  const child = el.nodes.innerHTML.replace(/<[^>]+>/g, ' ');
  /* the community node lists first the nodes that send to it, a stranger reading each as a home nearby */
  D.health = { ...D.health, kind: 'community', parent: undefined };
  D.sensors = [{ sensor_id: 'home-1/outdoor-1', name: 'a home nearby · outdoor 1', kind: 'child' }, { sensor_id: 'home-1/outdoor-2', name: 'a home nearby · outdoor 2', kind: 'child' }];
  D.stats15 = { 'home-1/outdoor-1': { pm25: [5, 30] } }; await around();
  console.log(JSON.stringify({ ...first, child, community: el.nodes.innerHTML.replace(/<[^>]+>/g, ' ') }));
})();
"""
got = json.loads(subprocess.run(["node", "-e", draw], cwd=ROOT, capture_output=True, text=True, check=True).stdout)
got["list"] = re.sub(r"\s+", " ", got["list"])
outline = re.search(r'<path d="([^"]+)" class="h3heard"/>', got["svg"])
assert outline and len(outline.group(1)) > 20, "the heard node's cell is drawn as an outline on the globe"
assert got["svg"].count('class="nd"') == 1, "and no point for it: the only point is this node's own"
assert "1 heard on the hub" in got["list"], got["list"]
assert "test-stand-in" in got["list"] and "heard on the hub, 4 min ago, about 12609 km away" in got["list"], got["list"]
got["child"] = re.sub(r"\s+", " ", got["child"]); got["community"] = re.sub(r"\s+", " ", got["community"])
assert "A community node above it" in got["list"] and "not set" in got["list"], "a private node with no parent says so"
assert "bayu-ungasan the community node it sends to" in got["child"] and "hourly means of 2 sensors" in got["child"] \
    and "sent at 03:00" in got["child"] and "A community node above it" not in got["child"], got["child"]
assert got["community"].lstrip().startswith("1 node sends to it a home nearby sends to this node hourly means of 2 sensors, the last 30 min ago"), \
    got["community"][:200]
assert "A community node above it" not in got["community"] and "ungasan" not in got["community"].split("listed")[0], got["community"]
print("heard nodes: matched by id, by name only when either side has none, outlined and listed")
print("links: a child names its parent and when its means went; a community node lists its senders first, as a home nearby")
print("nodes: registry.json read, trimmed to what a page may see, kept through a failed read, off with UPDATE_CHECK")
