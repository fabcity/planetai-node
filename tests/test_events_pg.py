"""events_pg without a database: rule rows become Candidates, and settings become a Policy.
Run: PYTHONPATH=app python3 tests/test_events_pg.py
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@127.0.0.1:1/x")
import events_pg as P  # noqa: E402

rule = {"id": "heat/heat_sustained", "kind": "sustained", "issue": "heat", "level": "act"}
rows = [{"sensor_id": "sc-1", "name": "K ROOM", "value": 36.1, "line": 35, "over": True},
        {"sensor_id": "sc-2", "name": "L ROOM", "value": 34.5, "line": 35, "over": False}]
cs = P.candidates(rule, rows)
assert [(c.room, c.over) for c in cs] == [("K ROOM", True), ("L ROOM", False)], cs
assert cs[0].issue == "heat" and cs[0].kind == "sustained" and cs[0].where == "inside"
assert P.candidates({"id": "air-quality/x", "level": "act"}, rows) == [], "a rule without kind: is report-only"
print("  rows of a kinded rule become candidates; a rule without kind: gives none")

rule2 = {"id": "air-quality/air_spike", "kind": "spike", "level": "warn"}
c2 = P.candidates(rule2, [{"sensor_id": "o", "name": "OUT", "value": 40, "line": 12, "over": True, "where": "outside"}])
assert c2[0].issue == "air" and c2[0].where == "outside", "issue defaults from the pack's domain; where passes through"
print("  issue defaults from the pack (air-quality -> air); where passes through")

os.environ.update(QUIET_HOURS="1", QUIET_FROM="22", QUIET_TO="6", ALERT_MAX_PER_DAY="4", ALERT_LEVEL="warn")
pol = P.policy()
assert pol.quiet == (22, 6) and pol.max_per_day == 4 and pol.alert_level == "warn", pol
os.environ["QUIET_HOURS"] = "0"
assert P.policy().quiet is None
print("events_pg: candidates from kinded rules, a Policy from settings")
