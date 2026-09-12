"""Index brick. Domain-blind.

  cells()  -> fci-cells-v0 rows this node can honestly compute, each with its provenance state
  rho()    -> action latency: how fast an alert became a human action, from the actions ledger

The core knows nothing about what a node measures. Two things are always computable:
  · Governance|<scale> — rho, because every node has alerts and an actions ledger
  · whatever domain packs contribute via cells.yml (docs/PACKS.md)

The cell key is 'Pillar|Scale' (canonical, FCI Observations base). State is live | partial | mock and is
never upgraded here or downstream.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

log = logging.getLogger("planetai.index")
CITY = os.getenv("NODE_CITY", "unknown")
SCALE = os.getenv("NODE_SCALE", "community").capitalize()


_ro = {"missing": False}


def run_ro(cur, sql: str, params=None) -> list:
    """Run one pack statement as planetai_ro (init.sql ≥ 0.21): SELECT on every table but settings, no writes. The role
    switch lives inside a transaction so it ends with the statement, whatever happens to it. On a database that has
    not been updated yet the role is missing: say so once and run as the owner, rather than silence every rule."""
    if not _ro["missing"]:
        try:
            with cur.connection.transaction():
                cur.execute("SET LOCAL ROLE planetai_ro")
                cur.execute(sql, params)
                return cur.fetchall()
        except Exception as e:  # noqa: BLE001
            if "planetai_ro" in str(e) and "does not exist" in str(e):
                _ro["missing"] = True
                log.warning("role planetai_ro is missing (schema before 0.21): pack SQL runs as the database owner until planetai update")
            else:
                raise
    cur.execute(sql, params)
    return cur.fetchall()


def _row(cell: str, value, unit: str, source: str, state: str, note: str = "") -> dict:
    return {"city": CITY, "cell": cell, "value": None if value is None else round(float(value), 3), "unit": unit,
            "source": source, "observed_at": datetime.now(timezone.utc).isoformat(), "state": state, "notes": note}


def _buckets(cur) -> dict:
    """The core's honesty check for a pack cell that wants to claim `live`: how much in-custody data exists in
    the last 24h, counted three ways.

    In CUSTODY, not local. `local` is this node's own instrument, here; custody is `local OR kind='child'`, so a
    child's hourly means count and a peer's sensor across the street does not, whatever its coordinates. Before
    this the count was `WHERE s.local`, and a community node aggregating ten homes counted zero — the roll-up
    path was built and could never say `live`. The predicate itself lives in `init.sql` as a generated column,
    so it is one word here and cannot drift from the fifteen other places that ask the question.

    `sensors` and `children` are for `min_sensors` (see `cells`): one child reporting is one household's
    kitchen, and a cell that says `live` off one kitchen is the same lie as a model claiming it.
    """
    cur.execute("""SELECT count(*) AS n, count(DISTINCT r.sensor_id) AS sensors,
                          count(DISTINCT split_part(r.sensor_id, '/', 1))
                            FILTER (WHERE s.kind = 'child') AS children
                   FROM readings_1h r JOIN sensors s USING (sensor_id)
                   WHERE s.custody AND r.bucket > now() - interval '24 hours'""")
    row = cur.fetchone() or {}
    return {"buckets": int(row.get("n") or 0), "sensors": int(row.get("sensors") or 0),
            "children": int(row.get("children") or 0)}


def cells(cur) -> list[dict]:
    out: list[dict] = []

    # ---- domain cells, contributed by packs. The core evaluates the SQL and polices the provenance.
    try:
        import packs
        defs = packs.cells()
    except Exception as e:  # noqa: BLE001
        log.warning("packs unavailable: %s", e); defs = []
    counts = _buckets(cur) if defs else {"buckets": 0, "sensors": 0, "children": 0}
    have = counts["buckets"]
    # A node that aggregates may not say `live` off one instrument. Two in-custody sensors from two different
    # children is the smallest thing that is a place rather than a room — decided 12 September 2026, see
    # docs/decisions/2026-09-10-custody.md. A home node with one kit is a home node and is left alone: it
    # describes one address and its `unit` string says so.
    need_sensors = 2 if (counts["children"] or SCALE.lower() != "community") else 1
    thin = bool(counts["sensors"] < need_sensors or 0 < counts["children"] < 2)
    for c in defs:
        try:
            rows = run_ro(cur, c["sql"])
            row = rows[0] if rows else None
        except Exception as e:  # noqa: BLE001
            log.warning("pack cell %s failed: %s", c.get("cell"), e); continue
        if not row or row.get("value") is None:
            continue
        state = c.get("state", "partial")
        need = int(c.get("min_buckets", 0))
        if state == "live" and need and have < need:
            state = "partial"          # a pack may not claim live before the data supports it
        if state == "live" and thin:
            state = "partial"          # nor off too few instruments, however many hours they have filled
        note = c.get("notes", "")
        if need:
            note = (note + f" · {have}/{need} hourly buckets").strip(" ·")
        if counts["children"]:
            note = (note + f" · {counts['sensors']} sensors across {counts['children']} children").strip(" ·")
        out.append(_row(c["cell"], row["value"], c.get("unit", ""), f"planetai-node · pack:{c['pack']}", state, note))

    # ---- Governance|<scale>: is anyone acting on what this node says. Always computable, any domain.
    rr = rho(cur)
    if rr["alerts_act"]:
        out.append(_row(f"Governance|{SCALE}", rr["rho"],
                        "rho — share of act-level alerts answered within 24h (30d)",
                        "planetai-node actions ledger", "partial" if rr["acted"] < 5 else "live",
                        f"{rr['acted']}/{rr['alerts_act']} acted; median detect-to-act {rr['median_minutes']} min"))
    return out


def rho(cur, days_ago: int = 0) -> dict:
    """rho over the last 30 days: share of level='act' alerts that got an 'acknowledged' or 'acted' row within 24h,
    plus median detect-to-act latency in minutes. The address-scale instrument for H0-A.

    THIS NODE'S ALERTS AND ITS CHILDREN'S TOGETHER. A child pushes one row per alert it raised, as timestamps
    and nothing else (main.py::push_events), and they pool here: an aggregator measures the action latency of
    the district it aggregates, not only of the alerts it happened to raise itself. A node with no children
    reads an empty `events` table and gets exactly the number it got before.

    The child never sends a ratio — a mean of ten ratios is not the ratio of the pooled counts. It sends the
    two timestamps and the definition of rho stays here, which is why a change to this query reaches every
    child's history at once with nothing to re-push.

    days_ago moves the whole 30-day window back, so the report can say whether the number moved this week without
    keeping a second copy of this query anywhere."""
    cur.execute("""WITH ref AS (SELECT now() - make_interval(days => %(back)s) AS t),
                        a AS (SELECT ('self/' || id) AS id, ts FROM alerts, ref
                              WHERE level='act' AND ts > ref.t - interval '30 days' AND ts <= ref.t
                              UNION ALL
                              SELECT (e.child || '/' || e.alert_id), e.raised_at FROM events e, ref
                              WHERE e.level='act' AND e.raised_at > ref.t - interval '30 days' AND e.raised_at <= ref.t),
                        f AS (SELECT ('self/' || alert_id) AS id, min(ts) AS t FROM actions
                              WHERE stage IN ('acknowledged','acted') GROUP BY alert_id
                              UNION ALL
                              SELECT (child || '/' || alert_id), least(responded_at, acted_at) FROM events
                              WHERE responded_at IS NOT NULL OR acted_at IS NOT NULL)
                   SELECT count(a.id) AS alerts_act,
                          count(f.id) FILTER (WHERE f.t - a.ts < interval '24 hours') AS acted,
                          percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM f.t - a.ts)/60)
                            FILTER (WHERE f.t - a.ts < interval '24 hours') AS median_minutes
                   FROM a LEFT JOIN f ON f.id = a.id""", {"back": days_ago})
    r = cur.fetchone() or {}
    n, acted = int(r.get("alerts_act") or 0), int(r.get("acted") or 0)
    return {"window_days": 30, "days_ago": days_ago, "alerts_act": n, "acted": acted, "rho": round(acted / n, 3) if n else None,
            "median_minutes": round(float(r["median_minutes"])) if r.get("median_minutes") is not None else None}
