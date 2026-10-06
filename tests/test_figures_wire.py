"""The wire part of docs/SPEC_dashboard_figures.md §3: the usual day, an open event's rooms, the stations that
stopped, and GET /issues/days. No database: a capture and hand-made rows.
Run: PACKS_DIR=packs PYTHONPATH=app python3 tests/test_figures_wire.py
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("PACKS_DIR", "packs")
os.environ.setdefault("DATABASE_URL", "postgresql://x:x@127.0.0.1:1/x")
sys.path.insert(0, str(ROOT / "app"))
import issues as I                # noqa: E402
from issues import engine          # noqa: E402


class Settings:
    def get(self, key, default=""):
        return default

    def num(self, key, default):
        return default


SNAP = json.loads((ROOT / "app/issues/fixtures/node1-2026-10-06-events.json").read_text())
DECL = I.load()


def fresh():
    return json.loads(json.dumps(SNAP))


# --- §3.1 the usual day --------------------------------------------------------------------------
ROWS = [{"sensor_id": "a", "metric": "apparent", "hour": 7, "median": 30.0, "p90": 31.0},
        {"sensor_id": "b", "metric": "apparent", "hour": 7, "median": 32.0, "p90": 35.0},
        {"sensor_id": "b", "metric": "temp", "hour": 7, "median": 99.0, "p90": 99.0},       # another metric
        {"sensor_id": "c", "metric": "apparent", "hour": 7, "median": 99.0, "p90": 99.0}]   # another distance
heat = {"metric": "apparent"}
block, why = engine._usual(heat, "room", {"sensors": ["a", "b"]}, ROWS)
assert why is None and block["window_days"] == 14 and block["distance"] == "room", (block, why)
assert len(block["hours"]) == 24 and [h["hour"] for h in block["hours"]] == list(range(24))
assert block["hours"][7] == {"hour": 7, "median": 31.0, "p90": 33.0}, block["hours"][7]
assert block["hours"][8] == {"hour": 8, "median": None, "p90": None}, "an hour with no history is null, not zero"
assert engine._usual(heat, "room", {"sensors": ["a"]}, None) == (None, "unread")
assert engine._usual(heat, "room", None, ROWS) == (None, "no_source")
assert engine._usual(heat, "room", {"sensors": ["z"]}, ROWS) == (None, "no_history")
print("  usual: the mean over the hero distance's sensors of each hour's median and p90, the issue's own metric")

rep = engine.replay(fresh(), Settings(), DECL)
for k, v in rep["issues"].items():
    assert "usual" in v and "usual_absent" in v, k
    if v.get("watched"):
        assert v["usual"] is None and v["usual_absent"] == "unread", (k, v["usual_absent"])
snap = fresh()
carried = {"window_days": 14, "distance": "room", "hours": [{"hour": h, "median": 30.0, "p90": 31.0} for h in range(24)]}
snap["issues"]["issues"]["heat"]["usual"], snap["issues"]["issues"]["heat"]["usual_absent"] = carried, None
assert engine.replay(snap, Settings(), DECL)["issues"]["heat"]["usual"] == carried, "a capture's usual replays verbatim"
print("  usual: a capture without it replays as unread; a capture with it replays it verbatim")

class Tx:
    """A connection.transaction() that records it was entered and left, as psycopg's savepoint does."""
    def __init__(self):
        self.entered = self.exited = False

    def __enter__(self):
        self.entered = True

    def __exit__(self, *exc):
        self.exited = True
        return False


class LiveCur:
    def __init__(self, fail):
        self.fail, self.tx = fail, Tx()
        self.connection = type("Conn", (), {"transaction": lambda _s: self.tx})()

    def execute(self, sql, args=()):
        if self.fail:
            raise RuntimeError("materialized view has not been populated")

    def fetchall(self):
        return [{"sensor_id": "a", "metric": "apparent", "hour": 7, "median": 30.0, "p90": 31.0}]


bad = LiveCur(True)
assert engine._optional(bad, engine.USUAL_SQL) is None and bad.tx.entered and bad.tx.exited, "a failing read is None, inside a savepoint"
good = LiveCur(False)
assert engine._optional(good, engine.USUAL_SQL) == good.fetchall() and good.tx.entered and good.tx.exited, "a good read is its rows, inside a savepoint"
print("  usual: the read runs in a savepoint of its own; an unpopulated view is None, not a failed /issues")

print("figures_wire: the usual day")
