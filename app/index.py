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


def _row(cell: str, value, unit: str, source: str, state: str, note: str = "") -> dict:
    return {"city": CITY, "cell": cell, "value": None if value is None else round(float(value), 3), "unit": unit,
            "source": source, "observed_at": datetime.now(timezone.utc).isoformat(), "state": state, "notes": note}


def _buckets(cur) -> int:
    """How many hourly buckets of local data exist in the last 24h — the core's honesty check for a pack cell
    that wants to claim `live`."""
    cur.execute("""SELECT count(*) AS n FROM readings_1h r JOIN sensors s USING (sensor_id)
                   WHERE s.local AND r.bucket > now() - interval '24 hours'""")
    row = cur.fetchone()
    return int((row or {}).get("n") or 0)


def cells(cur) -> list[dict]:
    out: list[dict] = []

    # ---- domain cells, contributed by packs. The core evaluates the SQL and polices the provenance.
    try:
        import packs
        defs = packs.cells()
    except Exception as e:  # noqa: BLE001
        log.warning("packs unavailable: %s", e); defs = []
    have = _buckets(cur) if defs else 0
    for c in defs:
        try:
            cur.execute(c["sql"])
            row = cur.fetchone()
        except Exception as e:  # noqa: BLE001
            log.warning("pack cell %s failed: %s", c.get("cell"), e); continue
        if not row or row.get("value") is None:
            continue
        state = c.get("state", "partial")
        need = int(c.get("min_buckets", 0))
        if state == "live" and need and have < need:
            state = "partial"          # a pack may not claim live before the data supports it
        note = c.get("notes", "")
        if need:
            note = (note + f" · {have}/{need} hourly buckets").strip(" ·")
        out.append(_row(c["cell"], row["value"], c.get("unit", ""), f"planetai-node · pack:{c['pack']}", state, note))

    # ---- Governance|<scale>: is anyone acting on what this node says. Always computable, any domain.
    rr = rho(cur)
    if rr["alerts_act"]:
        out.append(_row(f"Governance|{SCALE}", rr["rho"],
                        "rho — share of act-level alerts answered within 24h (30d)",
                        "planetai-node actions ledger", "partial" if rr["acted"] < 5 else "live",
                        f"{rr['acted']}/{rr['alerts_act']} acted; median detect-to-act {rr['median_minutes']} min"))
    return out


def rho(cur) -> dict:
    """rho over the last 30 days: share of level='act' alerts that got an 'acknowledged' or 'acted' row within 24h,
    plus median detect-to-act latency in minutes. The address-scale instrument for H0-A."""
    cur.execute("""WITH a AS (SELECT id, ts FROM alerts WHERE level='act' AND ts > now() - interval '30 days'),
                        f AS (SELECT alert_id, min(ts) AS t FROM actions WHERE stage IN ('acknowledged','acted') GROUP BY alert_id)
                   SELECT count(a.id) AS alerts_act,
                          count(f.alert_id) FILTER (WHERE f.t - a.ts < interval '24 hours') AS acted,
                          percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM f.t - a.ts)/60) AS median_minutes
                   FROM a LEFT JOIN f ON f.alert_id = a.id""")
    r = cur.fetchone() or {}
    n, acted = int(r.get("alerts_act") or 0), int(r.get("acted") or 0)
    return {"window_days": 30, "alerts_act": n, "acted": acted, "rho": round(acted / n, 3) if n else None,
            "median_minutes": round(float(r["median_minutes"])) if r.get("median_minutes") is not None else None}
