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


def _schema() -> str:
    """init.sql with its line comments stripped. `-- rolling stats are for sensors only;` sits inside the `stats`
    view and ends in a semicolon, which silently truncated the view to its SELECT list."""
    sql = open(os.path.join(ROOT, "init.sql")).read()
    return "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())


def _init_sql() -> str:
    sql = _schema()
    out = []
    for t in ("sensors", "readings", "channel_roles"):
        m = re.search(rf"CREATE TABLE IF NOT EXISTS {t} \(.*?\n\);", sql, re.S)
        out.append(m.group(0).replace("JSONB", "JSON"))
    out.append(re.search(r"CREATE VIEW readings_1h AS.*?;", sql, re.S).group(0))
    return "\n".join(out)


def _stats_sql() -> str:
    """The `stats` view verbatim from init.sql. It carries its own now(), so it is rebuilt per instant rather
    than created once — a rolling view frozen at import time would answer every replayed hour identically."""
    sql = _schema()
    # DuckDB merges a USING column, so the view's `r.sensor_id` will not bind in its own GROUP BY. An explicit
    # ON join is the same join; nothing else about the view is touched.
    return (re.search(r"CREATE VIEW stats AS.*?;", sql, re.S).group(0)
            .replace("JOIN sensors s USING (sensor_id)", "JOIN sensors s ON s.sensor_id = r.sensor_id"))


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

    def run(self, rule: dict, at: dt.datetime, lat: float | None = None, lon: float | None = None) -> list[dict]:
        stamp = f"TIMESTAMPTZ '{at.isoformat()}'"
        # `stats` is a 24-hour rolling view over now(), so it has to be rebuilt at the instant being replayed.
        self.con.execute("DROP VIEW IF EXISTS stats")
        self.con.execute(_stats_sql().replace("now()", stamp).replace("CREATE VIEW", "CREATE VIEW"))
        sql = rule["sql"].replace("now()", stamp)
        if lat is not None:
            # the node's coordinates reach a rule through Postgres session settings; DuckDB has none.
            sql = (sql.replace("current_setting('planetai.lat')::float", str(lat))
                      .replace("current_setting('planetai.lon')::float", str(lon)))
        cur = self.con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
