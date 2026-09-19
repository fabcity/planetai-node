"""The record: the ring's last week against its own preceding two months.

Replayed over tests/data/bad_ring_daily_2026-09-16.json — Bali Air Dispatch's daily record for the 16 stations
within 15 km of node #1, as the archive published it on 16 September 2026, not numbers typed into a test. The
rules ship as Postgres and `make test` has no Postgres, so trustdb runs the rule text as it ships, in DuckDB,
with now() replaced by the instant being replayed.

A daily mean enters the node as one reading on that day: the rule takes a per-station daily average, so one
reading a day reproduces the archive's own day means exactly. What is synthetic is the sampling, not a value.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_season.py
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))

with open(os.path.join(ROOT, "tests/data/bad_ring_daily_2026-09-16.json")) as f:
    FIX = json.load(f)

try:
    import trustdb
except ImportError:
    print("  - season replay skipped (pip install duckdb)")
    sys.exit(0)

RULES = trustdb.rules("season")
UTC = dt.timezone.utc

WHO = [(f"bad-{sid}", "baliairdispatch", s["name"], s["latitude"], s["longitude"], False, False, "sensor")
       for sid, s in FIX["stations"].items()]
ROWS = [(dt.datetime.fromisoformat(d).replace(hour=12, tzinfo=UTC), f"bad-{sid}", "pm25", float(v))
        for sid, d, v in FIX["daily"]]


def run(rule, at):
    """The rule at one instant, over only what the node could have known by then."""
    return trustdb.Node([r for r in ROWS if r[0] <= at], WHO).run(RULES[rule], at)


def at(day, hour=23):
    return dt.datetime.fromisoformat(day).replace(hour=hour, tzinfo=UTC)


# ---- the episode. 1-3 June 2026: six paired stations at 21 ug/m3 against a baseline of 12.
hit = run("turning", at("2026-06-03"))
assert hit, "the ring stepped up ~9 ug/m3 over its own two months at the start of June 2026; that is the rule"
assert hit[0]["stations"] >= 3 and float(hit[0]["step"]) >= 8 and float(hit[0]["week"]) >= 20, hit

# ---- and it is quiet the rest of the year. A seasonal rule that speaks every week is a weather report.
days = sorted({d for _, d, _ in FIX["daily"]})
fired = [d for d in days if d >= "2026-01-01" and run("turning", at(d))]
assert fired == ["2026-05-31", "2026-06-01", "2026-06-02", "2026-06-03"], \
    f"one episode in 2026, the end of May into June, and nothing else: {fired}"
# four days, but one alert: `turning` holds a three-day cooldown precisely so an episode is not four messages.

# ---- the floor for the week itself. The same +9 step in clean air changes nobody's afternoon, and the
# archive's own quiet weeks on this ring sit near 10 ug/m3, so the step alone would have fired on them.
clean = [(ts, sid, m, v / 3) for ts, sid, m, v in ROWS]
assert trustdb.Node([r for r in clean if r[0] <= at("2026-06-03")], WHO).run(RULES["turning"], at("2026-06-03")) == [], \
    "a step of 9 on a week reading 7 ug/m3 is not the season turning"

# ---- two stations is a coincidence with a witness.
pair = [r for r in ROWS if r[1] in {w[0] for w in WHO[:2]}]
assert trustdb.Node([r for r in pair if r[0] <= at("2026-06-03")], WHO[:2]).run(RULES["turning"], at("2026-06-03")) == [], \
    "under three paired stations the rule says nothing"

# ---- the report line. It reports whatever the week is, but only once something actually pairs.
rec = run("record", at("2026-09-15"))
assert rec and rec[0]["stations"] >= 3 and rec[0]["baseline_days"] >= 20, rec
assert run("record", at("2026-05-10")) == [], \
    "before this ring had 68 days of record, `record` reports nothing rather than a number built on four days"

print(f"season: the June 2026 episode fires, {len(fired)} days in the year do, and the report line needs a record")
