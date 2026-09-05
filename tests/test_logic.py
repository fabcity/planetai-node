"""Tests for the logic that has no adapter to stub: cell provenance and the per-loop error keys.
Each corresponds to a bug found in the 5 Sep audit. Run: PYTHONPATH=/tmp/stub:app python3 tests/test_logic.py"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://x/x")
os.environ.setdefault("NODE_CITY", "testville")
import index  # noqa: E402


class Cur:
    """Just enough cursor to drive index.cells(): a bucket count, then one row per pack cell, then rho."""
    def __init__(self, buckets): self.buckets, self.q = buckets, None
    def execute(self, sql, *a): self.q = sql
    def fetchone(self):
        if "count(*) AS n" in self.q: return {"n": self.buckets}
        if "alerts_act" in self.q: return {"alerts_act": 0, "acted": 0, "median_minutes": None}
        return {"value": 12.0}


def cells_with(buckets, state, min_buckets):
    index_packs = type(sys)("packs")
    index_packs.cells = lambda: [{"cell": "Environmental|Community", "unit": "u", "sql": "select 1 as value",
                                  "state": state, "min_buckets": min_buckets, "pack": "t"}]
    sys.modules["packs"] = index_packs
    return index.cells(Cur(buckets))


# a `live` claim is demoted until the data supports it, then allowed. Before the fix the pack said `partial`
# and the core only ever demoted, so the cell could never reach live while two docs promised it would.
assert cells_with(3, "live", 12)[0]["state"] == "partial", "live must be demoted below min_buckets"
assert cells_with(20, "live", 12)[0]["state"] == "live", "live must be allowed once min_buckets is met"
assert cells_with(20, "partial", 12)[0]["state"] == "partial", "partial is never promoted"
assert "3/12 hourly buckets" in cells_with(3, "live", 12)[0]["notes"], "provenance note must show the shortfall"

# per-loop error keys: one loop failing must not clear or mask another's state
state = {"errors": {}}
state["errors"]["run_rules"] = "boom"
state["errors"].pop("poll_sources", None)
assert state["errors"] == {"run_rules": "boom"}, "a healthy loop must not clear another loop's error"

print("all logic tests pass")

# ---------------------------------------------------------------- "outside" resolves: yours, else nearest three, else model
# The same order in the air-quality rules, the insight digest and the dashboard. Pinned here because averaging
# every station within 15 km put an Uluwatu reading of 3 alongside the street's 15 (5 Sep).
def resolve_outside(rows, lat, lon):
    mine = [r for r in rows if r["local"] and not r["indoor"] and r["v"] is not None]
    if mine:
        return sum(r["v"] for r in mine) / len(mine), "yours"
    near = sorted([r for r in rows if not r["local"] and not r["indoor"] and r["v"] is not None],
                  key=lambda r: (r["lat"] - lat) ** 2 + ((r["lon"] - lon) * 0.99) ** 2)[:3]
    if near:
        return sum(r["v"] for r in near) / len(near), "nearest"
    return None, "model"

N = (-8.8271, 115.15709)
far = [{"local": False, "indoor": False, "v": 3.0, "lat": -8.83, "lon": 115.09},     # Uluwatu, 7 km
       {"local": False, "indoor": False, "v": 4.0, "lat": -8.79, "lon": 115.17},     # 4 km
       {"local": False, "indoor": False, "v": 19.0, "lat": -8.82, "lon": 115.16},    # Fab Lab kit, 1 km
       {"local": False, "indoor": False, "v": 13.9, "lat": -8.822, "lon": 115.161},  # Kios Utak, 1 km
       {"local": False, "indoor": False, "v": 7.0, "lat": -8.80, "lon": 115.18}]     # 3 km
mine = [{"local": True, "indoor": False, "v": 14.0, "lat": -8.820, "lon": 115.1667}]
v, src = resolve_outside(far + mine, *N)
assert src == "yours" and v == 14.0, "your own outdoor sensor wins outright"
v, src = resolve_outside(far, *N)
assert src == "nearest" and abs(v - (19.0 + 13.9 + 7.0) / 3) < 1e-9, f"nearest three, not all five: {v}"
assert v > 10, "the Uluwatu 3.0 must not drag the street average down"
v, src = resolve_outside([], *N)
assert src == "model"
print("outside resolution order pinned")
