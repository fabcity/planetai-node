"""The thingdata pack against a stub ThingData server.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_thingdata.py

There is no deployment to record fixtures from, so the payloads here are the shapes
`reuse-city/thingdata-server` v0.1.3 returns from its own `to_dict()`. What is checked is what fails
silently: a total that stopped at page one, a percentage over a truncated catalogue, and a thing
counted as documented because a relationship pointed the other way.
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packs", "thingdata"))
import adapter as A  # noqa: E402

# relative, so the suite does not start failing one quarter after it was written
_n = dt.datetime.now(dt.timezone.utc)
NOW = (_n - dt.timedelta(days=3)).replace(tzinfo=None).isoformat()
OLD = (_n - dt.timedelta(days=400)).replace(tzinfo=None).isoformat()


class Stub:
    """Serves four collections with ThingData's skip/limit paging."""

    def __init__(self, coll):
        self.coll = coll
        self.calls = 0

    def get(self, url, params=None):
        self.calls += 1
        rows = self.coll[url.rsplit("/", 1)[1]]
        page = rows[params["skip"]:params["skip"] + params["limit"]]
        return type("R", (), {"json": lambda self, p=page: p, "raise_for_status": lambda self: None})()


def run(coll, **env):
    os.environ.update({"THINGDATA_INSTANCES": "td=https://td.example.org", "THINGDATA_SCALE": "city",
                       "THINGDATA_MAX": "5000", **env})
    hc = Stub(coll)
    sensors, readings = A.fetch(hc)
    return sensors, {m: v for _, _, m, v in readings}, hc


fails = []

# --- one thing of four documented, one guide of two fresh ------------------------------------------
things = [{"id": f"t{i}"} for i in range(4)]
coll = {
    "things": things,
    "guides": [{"id": "g1", "thing_id": "t1", "created_at": NOW, "updated_at": None},
               {"id": "g2", "thing_id": None, "created_at": OLD, "updated_at": OLD}],
    "stories": [],
    # a relationship pointing AT a guide from a thing is not documentation of that thing
    "relationships": [{"source_type": "thing", "source_id": "t2", "target_type": "guide", "target_id": "g2"}],
}
s, m, _ = run(coll)
if m["things_total"] != 4 or m["guides_total"] != 2:
    fails.append(f"counts: {m}")
if m["things_documented_pct"] != 25.0:
    fails.append(f"one thing of four is documented, got {m['things_documented_pct']}")
if m["knowledge_fresh_90d_pct"] != 50.0:
    fails.append(f"one guide of two is fresh, got {m['knowledge_fresh_90d_pct']}")
if s[0]["kind"] != "portal" or s[0]["local"] or s[0]["lat"] is not None:
    fails.append("a catalogue is not a local measurement: kind must be portal, never local, no coordinates")

# --- a relationship from a guide does document the thing -------------------------------------------
coll2 = dict(coll, relationships=[{"source_type": "guide", "source_id": "g2",
                                   "target_type": "thing", "target_id": "t2"}])
_, m2, _ = run(coll2)
if m2["things_documented_pct"] != 50.0:
    fails.append(f"a guide→thing relationship documents it, got {m2['things_documented_pct']}")

# --- paging: a catalogue bigger than one page is counted whole -------------------------------------
big = {"things": [{"id": f"t{i}"} for i in range(250)], "guides": [], "stories": [], "relationships": []}
_, m3, hc = run(big)
if m3["things_total"] != 250:
    fails.append(f"paging stopped early: {m3['things_total']} of 250")

# --- and above the cap it refuses rather than report a page as a total -----------------------------
try:
    run(big, THINGDATA_MAX="100")
    fails.append("counted a catalogue larger than THINGDATA_MAX instead of refusing")
except RuntimeError as e:
    if "THINGDATA_MAX" not in str(e):
        fails.append(f"the refusal must name the setting that lifts it: {e}")

# --- nothing configured: idle, never an exception --------------------------------------------------
os.environ["THINGDATA_INSTANCES"] = ""
if A.fetch(Stub(coll)) != ([], []):
    fails.append("an unconfigured pack must return nothing, not raise")

print("\n".join(f"  ✗ {f}" for f in fails) or
      "thingdata: counts page to the end, a percentage is never taken over a truncated catalogue, "
      "relationships only count in the direction that documents a thing, and it idles unconfigured")
sys.exit(1 if fails else 0)
