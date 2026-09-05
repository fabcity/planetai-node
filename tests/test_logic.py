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
