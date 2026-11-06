"""The index pack's place list and the nearest-place suggestion.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_index_pack.py
What is checked is what fails silently: a list that lost a place, a centre in the wrong order (the registry's are
[lat, lng]; swap them and Bali lands in the Indian Ocean without an error), a node in Menorca told it is in
Barcelona, and the two command-line entry points the `planetai place` command calls instead of redoing the sums.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packs", "index"))
import place as PL  # noqa: E402

PY = os.path.join(ROOT, "packs", "index", "place.py")
P = PL.load()

# ---- the list: the registry's 61, each with a centre.
assert len(P) == 61, len(P)
assert [p["slug"] for p in P] == sorted(p["slug"] for p in P)
assert all(set(p) == {"slug", "name", "country", "lat", "lon"} for p in P)
assert sum(1 for p in P if p["lat"] is not None) == 61

# ---- nearest, by where the place is rather than by which list it is in.
assert PL.nearest(41.39, 2.17, P)["slug"] == "barcelona"
assert PL.nearest(-8.8271, 115.15709, P)["slug"] == "bali"        # node #1: 66 km from Bali's centre
# Menorca is 240 km from Barcelona and has no place of its own: a suggestion that far would be a guess.
assert PL.nearest(39.89, 4.26, P) is None
# a place with no centre can never be the nearest, and a list of only those is None, not an error
blank = [{"slug": "x", "name": "X", "country": "Y", "lat": None, "lon": None}]
assert PL.nearest(0, 0, blank) is None
assert PL.nearest(41.39, 2.17, blank + P)["slug"] == "barcelona"
# the antimeridian: Fiji-side longitudes must not read as the far side of the world
wrap = [{"slug": "w", "name": "W", "country": "Z", "lat": 0.0, "lon": -179.9}]
assert PL.nearest(0.0, 179.9, wrap)["slug"] == "w"

# ---- known
assert PL.known("barcelona", P) and not PL.known("barcelone", P) and not PL.known("", P)

# ---- the entry points `planetai place` calls
def run(*a):
    return subprocess.run([sys.executable, PY, *a], capture_output=True, text=True)

r = run("--nearest", "41.39", "2.17")
assert r.returncode == 0 and json.loads(r.stdout)["slug"] == "barcelona", (r.stdout, r.stderr)
assert len(r.stdout.strip().splitlines()) == 1
r = run("--nearest", "39.89", "4.26")
assert r.returncode == 0 and r.stdout.strip() == "null", r.stdout
assert run("--known", "bali").returncode == 0
assert run("--known", "bali-ish").returncode == 2
assert run().returncode not in (0, 2)

# ---- the daily read (adapter.py). The fixtures are Barcelona and Accra as index.fab.city served them on 6 Nov
# 2026 and the registry's index.json at the commit the Barcelona file names, saved whole.
import datetime as dt  # noqa: E402
import copy  # noqa: E402
import adapter as A  # noqa: E402


def fixture(n):
    with open(os.path.join(ROOT, "tests/data", n)) as f:
        return json.load(f)


BCN = fixture("index_place_barcelona_2026-11-06.json")
ACC = fixture("index_place_accra_2026-11-06.json")
REG = fixture("registry_index_8099744.json")
SHA = BCN["registry_commit"]
NOW = dt.datetime(2026, 11, 6, 8, 0, tzinfo=dt.timezone.utc)


class R:
    def __init__(s, j, headers=None):
        s.j, s.content, s.headers = j, json.dumps(j).encode(), headers or {}
    def raise_for_status(s): pass
    def json(s): return s.j


class HC:
    """Answers by URL and writes down every call. A value that is an Exception is raised instead."""
    def __init__(s, place=BCN, sha=SHA, reg=REG):
        s.calls, s.timeouts, s.place, s.sha, s.reg = [], [], place, sha, reg
    def get(s, url, params=None, headers=None, timeout=None):
        s.calls.append(url); s.timeouts.append(timeout)
        out = (s.sha and {"sha": s.sha}) if "api.github.com" in url else s.reg if url.endswith("/index.json") else s.place
        if isinstance(s.sha, Exception) and "api.github.com" in url:
            raise s.sha
        return R(out)


class Cur:
    """A dict where index_reads would be: the two statements the adapter issues, keyed on their first word."""
    def __init__(s): s.rows, s.one = {}, None
    def execute(s, q, a=()):
        q = q.strip().upper()
        if q.startswith("SELECT"):
            r = s.rows.get(a[0])
            s.one = (r["sha"], r["fetched_at"], r["ok"], r["error"], r["body"]) if r else None
        elif q.startswith("INSERT"):
            what, sha, at, ok, err, body = a
            s.rows[what] = dict(sha=sha, fetched_at=at, ok=ok, error=err, body=None if body is None else json.loads(body))
    def fetchone(s): return s.one


# convert: the upstream dict's entries, in the node's entry shape
E = A.convert(REG)
assert len(E) == 293 and all("slug" in e and "cell" in e and e["reviews"] is not None for e in E), len(E)
ex = next(e for e in E if e["slug"] == "economic/bioregion/exiobase")
assert ex["cell"] == "Economic|Bioregion" and ex["pillar"] == "economic", ex["cell"]
assert ex["id"] == ex["slug"]
assert A.convert({"entries": [{"id": "a/b/c", "pillar": "social", "scale": "city"}]}) == [
    {"slug": "a/b/c", "cell": "Social|City", "id": "a/b/c", "pillar": "social", "scale": "city", "reviews": []}]

# a place that reads: Barcelona is stored whole with its format, and the registry by its sha
cur, hc = Cur(), HC()
assert A.read(hc, cur, "barcelona", NOW) == {"place": True, "registry": True}
pl = cur.rows["place"]
assert pl["ok"] is True and pl["error"] is None and pl["body"]["format"] == "fci-api-v0"
assert pl["body"]["place"] == BCN["place"] and pl["fetched_at"] == NOW
rg = cur.rows["registry"]
assert rg["ok"] and rg["sha"] == SHA and len(rg["body"]) == 293 and rg["body"][0]["slug"]
assert hc.calls[0] == "https://index.fab.city/api/v0/places/barcelona.json", hc.calls
assert all(c.startswith("https://") for c in hc.calls) and len(hc.calls) == 3, hc.calls
assert hc.timeouts == [20, 20, 20], hc.timeouts       # every read has a timeout, and it is 20 s
# the sha has not moved: the registry body is not fetched again, the row is still ok
n = len(hc.calls)
assert A.read(hc, cur, "barcelona", NOW + dt.timedelta(days=1)) == {"place": True, "registry": True}
assert len(hc.calls) == n + 2 and not any(c.endswith("/index.json") for c in hc.calls[n:]), hc.calls[n:]

# an unknown slug is said, and nothing leaves the node
cur, hc = Cur(), HC()
assert A.read(hc, cur, "barcelone", NOW)["place"] is False
assert hc.calls == [], hc.calls
assert cur.rows["place"]["ok"] is False and cur.rows["place"]["error"] == "not an Index place: barcelone"

# GitHub down: the registry keeps what it had, with its sha, and says why; the place is still read
cur, hc = Cur(), HC()
A.read(hc, cur, "barcelona", NOW)
before = copy.deepcopy(cur.rows["registry"])
hc = HC(sha=RuntimeError("github is down"))
assert A.read(hc, cur, "barcelona", NOW + dt.timedelta(days=1)) == {"place": True, "registry": False}
rg = cur.rows["registry"]
assert rg["ok"] is False and "github is down" in rg["error"]
assert rg["body"] == before["body"] and rg["sha"] == before["sha"]
assert cur.rows["place"]["ok"] is True

# a body that is not the Index's format is refused and the last good one stays
cur = Cur()
A.read(HC(), cur, "barcelona", NOW)
good = copy.deepcopy(cur.rows["place"]["body"])
bad = dict(BCN, format="x")
assert A.read(HC(place=bad), cur, "barcelona", NOW + dt.timedelta(days=1))["place"] is False
assert cur.rows["place"]["ok"] is False and "format" in cur.rows["place"]["error"]
assert cur.rows["place"]["body"] == good

# the other place reads the same way (Accra is a different shape of place, same format)
cur = Cur()
assert A.read(HC(place=ACC), cur, "accra", NOW)["place"] is True and cur.rows["place"]["body"]["place"] == ACC["place"]

# a stored place is only kept for the slug it was read for: Barcelona's file is not Accra's, or a typo's
cur = Cur()
A.read(HC(), cur, "barcelona", NOW)
assert A.read(HC(), cur, "barcelone", NOW + dt.timedelta(days=1))["place"] is False
assert cur.rows["place"]["body"] is None and cur.rows["place"]["ok"] is False
assert cur.rows["place"]["error"] == "not an Index place: barcelone"
A.read(HC(), cur, "barcelona", NOW)
assert A.read(HC(place=dict(ACC, format="x")), cur, "accra", NOW)["place"] is False       # a failed read, another place
assert cur.rows["place"]["body"] is None and "format" in cur.rows["place"]["error"]

# a sha that is not a commit sha is an error, and nothing is fetched from raw.githubusercontent
cur, hc = Cur(), HC(sha="main")
assert A.read(hc, cur, "barcelona", NOW) == {"place": True, "registry": False}
assert "not a commit sha" in cur.rows["registry"]["error"] and cur.rows["registry"]["body"] is None
assert not any("raw.githubusercontent" in c for c in hc.calls), hc.calls

# a body over 8 MB is refused before it is parsed
class Big(R):
    def __init__(s): s.j, s.content, s.headers = {}, b"", {"content-length": str(9 * 1024 * 1024)}
cur = Cur()
class HCBig(HC):
    def get(s, url, **k): return Big()
assert A.read(HCBig(), cur, "barcelona", NOW)["place"] is False and "8 MB" in cur.rows["place"]["error"]

# once a day: two fetches an hour apart make one set of calls
os.environ["INDEX_PLACE"] = "barcelona"
os.environ.pop("INDEX_REFRESH_HOURS", None)
store, hc = Cur(), HC()
A._cursor = lambda: __import__("contextlib").nullcontext(store)
A._now = lambda: NOW
assert A.fetch(hc) == ([], [])
n = len(hc.calls)
assert n == 3, n
A._now = lambda: NOW + dt.timedelta(hours=1)
assert A.fetch(hc) == ([], []) and len(hc.calls) == n, hc.calls
A._now = lambda: NOW + dt.timedelta(hours=25)
A.fetch(hc)
assert len(hc.calls) == n + 2, hc.calls
# a blank field in Set up reaches the pack as an empty string: the defaults stand, nothing raises
os.environ["INDEX_REFRESH_HOURS"] = ""
os.environ["INDEX_URL"] = ""
store, hc = Cur(), HC()
A._now = lambda: NOW
assert A.fetch(hc) == ([], []) and hc.calls[0] == "https://index.fab.city/api/v0/places/barcelona.json", hc.calls
n = len(hc.calls)
A._now = lambda: NOW + dt.timedelta(hours=1)
assert A.fetch(hc) == ([], []) and len(hc.calls) == n, "a blank refresh is 24 h"
os.environ["INDEX_PLACE"] = ""
before = len(hc.calls)
A._now = lambda: NOW + dt.timedelta(days=9)
assert A.fetch(hc) == ([], []) and len(hc.calls) == before, "no place named, nothing read"

# ---- GET /index/place (routes.py): what the adapter stored, for the slug the node is set to
os.environ.setdefault("DATABASE_URL", "postgresql://unused/never-connected")
try:
    import importlib.util
    import time
    import settings as ST
except ImportError:
    print("  index route: checks skipped (pip install -r app/requirements.txt)")
else:
    spec = importlib.util.spec_from_file_location("index_routes", os.path.join(ROOT, "packs/index/routes.py"))
    RT = importlib.util.module_from_spec(spec); spec.loader.exec_module(RT)
    ST._cache = {"at": time.time() + 1e9, "rows": {}}

    def serve(cur, chosen="barcelona", pinned=([], {})):
        """The route as the node would answer it, with `cur`'s rows in index_reads and `pinned` for registry.load()."""
        os.environ["INDEX_PLACE"] = chosen
        RT.q = lambda sql, *a: [dict(what=w, **r) for w, r in cur.rows.items()]
        RT.registry.load = lambda: pinned
        return RT.index_place()

    cur = Cur()
    A.read(HC(), cur, "barcelona", NOW)
    o = serve(cur)
    assert o["chosen"] == "barcelona" and o["place"] == BCN["place"] and o["place"]["name"] == "Barcelona", o["place"]
    assert o["read"] == {"at": BCN["generated"], "ok": True, "error": None, "tried": NOW}, o["read"]
    assert o["score"] == BCN["score"] and o["links"] == {"page": BCN["links"]["page"], "report": BCN["links"]["report"]}
    assert len(o["indicators"]) == len(BCN["indicators"]) and o["indicators"][0]["latest"] == {"year": 2022, "value": 91.3}, o["indicators"][0]
    assert set(o["indicators"][0]) == {"label", "unit", "latest", "source"}
    assert o["registry"] == {"sha": SHA, "at": NOW, "from": "live", "filed_here": 35}, o["registry"]
    # a place whose file is Accra's range: no fci, a range, and no indicators to show
    cur = Cur()
    A.read(HC(place=ACC), cur, "accra", NOW)
    o = serve(cur, "accra")
    assert o["score"]["fci"] is None and o["score"]["fci_range"] == [0, 0] and o["indicators"] == [], o["score"]
    # nothing stored: not read, the pinned registry stands in, and the chosen place is still named from the list
    pin = [{"slug": "a", "places": ["barcelona"]}, {"slug": "b", "places": ["bali"]}, {"slug": "c"}]
    o = serve(Cur(), pinned=(pin, {"sha": "abc1234"}))
    assert o["read"]["ok"] is False and o["read"]["at"] is None and o["score"] is None and o["indicators"] == [] and o["links"] is None
    assert o["place"]["name"] == "Barcelona" and o["registry"] == {"sha": "abc1234", "at": None, "from": "pinned", "filed_here": 1}, o
    # a failed read keeps the last body and says why; the date is the body's own, the attempt is later
    cur = Cur()
    A.read(HC(), cur, "barcelona", NOW)
    A.read(HC(place=dict(BCN, format="x")), cur, "barcelona", NOW + dt.timedelta(days=2))
    o = serve(cur)
    assert o["read"]["ok"] is False and "format" in o["read"]["error"] and o["read"]["at"] == BCN["generated"], o["read"]
    assert o["read"]["tried"] == NOW + dt.timedelta(days=2) and o["score"] == BCN["score"]
    # a body for another slug is no body, even before the adapter has cleared it
    cur = Cur()
    A.read(HC(), cur, "barcelona", NOW)
    o = serve(cur, "accra")
    assert o["place"]["slug"] == "accra" and o["score"] is None and o["read"]["at"] is None and o["indicators"] == [], o
    # the table is not there yet (the adapter has not run): no rows, not a 500
    def boom(sql, *a): raise RuntimeError('relation "index_reads" does not exist')
    os.environ["INDEX_PLACE"] = "barcelona"; RT.q = boom
    assert RT.index_place()["read"]["ok"] is False
    print("  ok: GET /index/place")

print("  ok: test_index_pack")
sys.exit(0)
