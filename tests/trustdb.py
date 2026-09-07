"""Run a trust-pack rule over node #1's own readings, in DuckDB.

The rules are Postgres and `make test` has no Postgres, so DuckDB runs the rule text as it ships: the only edit is
`now()`, replaced with the instant the test wants to stand at, so one series can be swept hour by hour. The schema
comes from init.sql (the `readings_1h` view verbatim), the channel roles from config/channels.yml, and the readings
from tests/data/node1-*.tsv — the real series out of node #1's 7 September dump, not numbers typed into a test.

Needs duckdb, dev only: pip install duckdb. A test that cannot import it says so and skips.
"""
from __future__ import annotations

import datetime as dt
import os
import re

import duckdb
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTC = dt.timezone.utc
# the last reading in tests/data/node1-readings.tsv: 7 September 2026, 13:14:22 UTC = 21:14 WITA, three minutes
# before the trust pack sent its three wrong warnings.
FIXTURE_NOW = dt.datetime(2026, 9, 7, 13, 14, 22, tzinfo=UTC)


def _init_sql() -> str:
    sql = open(os.path.join(ROOT, "init.sql")).read()
    out = []
    for t in ("sensors", "readings", "channel_roles"):
        m = re.search(rf"CREATE TABLE IF NOT EXISTS {t} \(.*?\n\);", sql, re.S)
        out.append(m.group(0).replace("JSONB", "JSON"))
    out.append(re.search(r"CREATE VIEW readings_1h AS.*?;", sql, re.S).group(0))
    return "\n".join(out)


def rules(pack: str = "trust") -> dict:
    """The pack's rules as shipped, by id."""
    with open(os.path.join(ROOT, "packs", pack, "rules.yml")) as f:
        return {r["id"]: r for r in yaml.safe_load(f)}


def readings(sensor: str | None = None, metric: str | None = None) -> list[tuple]:
    rows = []
    with open(os.path.join(ROOT, "tests/data/node1-readings.tsv")) as f:
        for line in f:
            ts, sid, met, val = line.rstrip("\n").split("\t")
            if (sensor and sid != sensor) or (metric and met != metric):
                continue
            rows.append((dt.datetime.fromisoformat(ts), sid, met, float(val)))
    return rows


def sensors() -> list[tuple]:
    """The five kits as node #1 held them. `local` is TRUE for all five: the live node had Ungasan Kit and BAYU NEW
    ENCLOSURE local when it named them at 21:17, though the 21:43 dump has them FALSE — docs/HANDOFF_trust.md (c)."""
    rows = []
    with open(os.path.join(ROOT, "tests/data/node1-sensors.tsv")) as f:
        for line in f:
            sid, source, name, lat, lon, indoor, local, kind = line.rstrip("\n").split("\t")
            rows.append((sid, source, name, float(lat), float(lon), indoor == "t", local == "t", kind))
    return rows


def day(rows: list[tuple], end: dt.datetime = FIXTURE_NOW) -> list[tuple]:
    """The last real 24 hours of a series."""
    return [r for r in rows if r[0] > end - dt.timedelta(hours=24)]


def week(rows: list[tuple], at: dt.datetime, days: int = 8) -> list[tuple]:
    """The series' last real day, replayed over the `days` days before `at`.

    The rules now ask for a week and node #1's kits are two days old, so a real week of any of them does not exist
    yet. Replaying one real day preserves that day's values, hourly means and diurnal shape exactly — every number
    here was measured — and gives the sensor the age and the hourly coverage the rule requires. What is synthetic
    is the calendar, and only the calendar.
    """
    d, shift = day(rows), at - FIXTURE_NOW
    return [(ts + shift - dt.timedelta(days=k), sid, m, v) for k in range(days) for ts, sid, m, v in d]


def flat(sensor: str, metric: str, value: float, hours: int, at: dt.datetime, every_min: int = 5) -> list[tuple]:
    """A synthetic channel stuck on one number for `hours` — the failure channel_dead exists to catch."""
    return [(at - dt.timedelta(minutes=m), sensor, metric, value)
            for m in range(0, hours * 60, every_min)]


class Node:
    """A node holding one set of readings, which a rule can be run against at any instant."""

    def __init__(self, rows: list[tuple], who: list[tuple] | None = None):
        self.con = duckdb.connect()
        self.con.execute(_init_sql())
        self.con.executemany(
            "INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind) VALUES (?,?,?,?,?,?,?,?)",
            who if who is not None else sensors())
        seen = set()
        self.con.executemany("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (?,?,?,?)",
                             [r for r in rows if not (r[:3] in seen or seen.add(r[:3]))])
        with open(os.path.join(ROOT, "config/channels.yml")) as f:
            for c in yaml.safe_load(f):
                self.con.execute(
                    "INSERT INTO channel_roles (source, metric, role, comparable, declared_by) VALUES (?,?,?,?,'core')",
                    (c["source"], c["metric"], c["role"], bool(c.get("comparable", False))))

    def run(self, rule: dict, at: dt.datetime) -> list[dict]:
        sql = rule["sql"].replace("now()", f"TIMESTAMPTZ '{at.isoformat()}'")
        cur = self.con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
