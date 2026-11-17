"""The Place report's reading: what kind of place this is, and what is worth doing here (docs/SPEC_place_report.md §11).

Four things live here, in the order each rests on the one before:

  facts(cur)            every figure the reading may rest on, as one JSON-able document, at the precision of a
                        report that leaves the house: nothing closer than the res-8 cell, no name, no point
  rules(doc)            the node's own reading, deterministic: five sections, at least four avenues, and what it
                        cannot see. This is what every node gets, with no model anywhere
  accept(answer, doc)   a model's fuller text, kept only if its numbers are the node's
  the two routes        GET /place/reading and POST /place/reading, for this machine or a token

The facts are the only place a number may come from, as report.bundle is for the hourly report.
"""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta

log = logging.getLogger("planetai.reading")

# The frame for an avenue (the Fab City Full Stack's seven layers, as "Mapping agents", DRS2026, words them; the
# Implementation Guide's three key actions; the paper's three signals). A text that names anything else is refused.
LAYERS = ("Infrastructure", "Learning", "Value-generating projects", "Communities", "Place-based interventions",
          "Bioregional strategies", "Global networks")
ACTIONS = ("Map and research", "Experiment", "Rethink")
SIGNALS = ("socio-spatial", "bioregional", "asset")
SECTIONS = (("region", "The region it belongs to"), ("land", "What the land allows"), ("needs", "What people here need"),
            ("system", "How the place behaves"), ("street", "The life of the street"))

STALE_DAYS = 400      # a figure older than this counts as not held
AIR_MIN_DAYS = 30     # measured days before the node states its air figure
WHO_DAY = 15          # µg/m³, the WHO 24-hour guideline for PM2.5 (2021)

# metric in `readings` -> (fact, form). A distance from the node's point becomes whole kilometres here, because the
# report leaves the house (SPEC_place_report §6); the place pack's counts and shares cover 1 km round the point.
READ = {
    "buildings": ("buildings", "n"), "sat_buildings": ("sat_buildings", "n"), "osm_building_coverage": ("osm_coverage", "share"),
    "built_share": ("built_share", "share"), "green_share": ("green_share", "share"), "commercial_share": ("commercial_share", "share"),
    "businesses_per_km2": ("businesses_km2", "n"), "roads_km": ("roads_km", "n"),
    "poi_food": ("poi_food", "n"), "poi_retail": ("poi_retail", "n"), "poi_education": ("poi_education", "n"),
    "poi_health": ("poi_health", "n"), "poi_worship": ("poi_worship", "n"), "poi_lodging": ("poi_lodging", "n"),
    "poi_services": ("poi_services", "n"),
    "nearest_school_m": ("school_km", "km"), "nearest_health_m": ("clinic_km", "km"), "nearest_market_m": ("market_km", "km"),
    "lst_delta": ("heat_delta_c", "d1"), "terrain_upslope_ha": ("upslope_ha", "d1"),
    "tree_frac": ("tree_share", "share"), "crop_frac": ("crop_share", "share"),
}
# the facts that do not come from one reading, and how each is said
FORM = {**{k: f for k, f in READ.values()},
        "buildings_then": "n", "buildings_then_year": "n", "buildings_now": "n",
        "river_km": "n", "basin_km2": "n", "bioregion_km2": "n",
        "grid": "s", "fossil_low_pct": "n", "fossil_high_pct": "n",
        "index_place": "s", "index_label": "s", "index_measured": "n", "index_cells": "n",
        "labs_50km": "n", "lab_km": "n", "air_days_over": "n", "air_days": "n", "cells_held": "n"}
SHARES = frozenset(k for k, f in FORM.items() if f == "share")

_PLACE = "turn on the place pack in Set up › Packs"
FILL = {**{k: _PLACE for k, _ in READ.values()},
        "buildings_then": _PLACE, "buildings_then_year": _PLACE, "buildings_now": _PLACE,
        "heat_delta_c": "turn on the surface-heat pack in Set up › Packs",
        "upslope_ha": "planetai run terrain fetch",
        "tree_share": "turn on the earth-engine pack in Set up › Packs", "crop_share": "turn on the earth-engine pack in Set up › Packs",
        "river_km": "planetai run hydro fetch", "basin_km2": "planetai run hydro fetch", "bioregion_km2": "planetai run hydro fetch",
        "grid": "planetai run energy fetch", "fossil_low_pct": "planetai run energy fetch", "fossil_high_pct": "planetai run energy fetch",
        "index_place": "planetai place", "index_label": "planetai place", "index_measured": "planetai place", "index_cells": "planetai place",
        "labs_50km": "set MAKE_ENABLED=1, then planetai restart", "lab_km": "set MAKE_ENABLED=1, then planetai restart",
        "air_days_over": "an outdoor sensor of your own, measuring for 30 days", "air_days": "an outdoor sensor of your own, measuring for 30 days",
        "cells_held": "planetai update"}


def say(key: str, v) -> str:
    """A fact as text. The rules and the check on a model's numbers both go through here, so they cannot disagree."""
    form = FORM[key]
    if form == "s":
        return str(v)
    if form == "share":
        return f"{round(v * 100)}%"
    if form == "d1":
        return f"{v:.1f}"
    return str(round(v))


def _d(x) -> dict:
    return x if isinstance(x, dict) else {}


def shape(latest: dict, hydro: dict | None, energy: dict | None, index: dict | None, labs: list, air: tuple | None,
          held: int | None, yearly: list, today: date) -> dict:
    """The facts document, from what the node read. Pure: the I/O is facts(), below.

    `latest` is metric -> (value, "YYYY-MM-DD"); `labs` the labs' distances in km; `air` (days over, days measured);
    `yearly` [(year, buildings the satellite counted)]. A figure the node does not hold is None and named in `fill`."""
    day, floor = today.isoformat(), (today - timedelta(days=STALE_DAYS)).isoformat()
    F: dict = dict.fromkeys(FORM)

    def put(key, v, at=day):
        if v is None or at < floor:
            return
        form = FORM[key]
        F[key] = {"v": str(v) if form == "s" else round(float(v), 3) if form == "share" else round(float(v), 1) if form == "d1"
                  else int(round(float(v))), "at": at[:10]}

    for metric, (key, form) in READ.items():
        if metric in latest:
            v, at = latest[metric]
            put(key, v / 1000.0 if form == "km" else v, at)
    years = sorted((int(y), float(n)) for y, n in yearly or [])
    if len(years) >= 3:
        put("buildings_then", years[0][1]); put("buildings_then_year", years[0][0]); put("buildings_now", years[-1][1])
    h, b = _d(hydro), _d(_d(hydro).get("basin"))
    if _d(h.get("nearest")).get("dist_m") is not None:
        put("river_km", h["nearest"]["dist_m"] / 1000.0)
    put("basin_km2", _d(b.get("level12")).get("up_area"))
    put("bioregion_km2", _d(b.get("level4")).get("sub_area"))
    e, sh = _d(energy), _d(_d(energy).get("share"))
    if e.get("grid") and sh.get("low") is not None and sh.get("high") is not None:
        put("grid", str(e["grid"]).replace("-", " ").title()); put("fossil_low_pct", sh["low"] * 100); put("fossil_high_pct", sh["high"] * 100)
    i, sc = _d(index), _d(_d(index).get("score"))
    if _d(i.get("read")).get("ok") and _d(i.get("place")).get("name") and sc.get("cells_total"):
        put("index_place", i["place"]["name"]); put("index_label", sc.get("status_label")); put("index_measured", sc.get("cells_measured") or 0)
        put("index_cells", sc["cells_total"])
    near = sorted(float(k) for k in labs or [] if k is not None and float(k) <= 50)
    if labs is not None and (near or labs):
        put("labs_50km", len(near))
        if near:
            put("lab_km", near[0])
    if air and air[1] >= AIR_MIN_DAYS:
        put("air_days_over", air[0]); put("air_days", air[1])
    put("cells_held", held)
    return {"at": day, "facts": F, "fill": {k: FILL[k] for k, v in F.items() if v is None}}


def _self(path: str):
    """One of this node's own routes, read on the loopback with the node's own token: the shapes the page already reads."""
    import httpx  # noqa: PLC0415
    try:
        r = httpx.get(f"http://127.0.0.1:{os.getenv('PORT', '8080')}{path}", timeout=10,
                      headers={"Authorization": f"Bearer {os.getenv('ADMIN_TOKEN', '')}"})
        return r.json() if r.status_code == 200 else None
    except Exception as e:  # noqa: BLE001 — a read that fails leaves its facts out
        log.info("reading: %s did not answer (%s)", path, type(e).__name__)
        return None


def facts(cur, get=_self, today: date | None = None) -> dict:
    """Every figure the reading may rest on. `cur` is a dict-row cursor; `get` reads one of the node's own routes."""
    import packs  # noqa: PLC0415 — the loader reads PACKS_DIR at import

    pub = packs.public_sql("r")
    cur.execute(f"SELECT DISTINCT ON (r.metric) r.metric, r.value, r.ts FROM readings r WHERE r.metric = ANY(%s) AND {pub} "
                "ORDER BY r.metric, r.ts DESC", (list(READ),))
    latest = {r["metric"]: (r["value"], r["ts"].date().isoformat()) for r in cur.fetchall()}
    cur.execute(f"SELECT r.ts, r.value FROM readings r WHERE r.sensor_id = 'place-point' AND r.metric = 'sat_buildings_yearly' AND {pub} ORDER BY r.ts")
    yearly = [(r["ts"].year, r["value"]) for r in cur.fetchall()]
    cur.execute("SELECT (meta->>'distance_km')::float AS km FROM sensors WHERE kind = 'facility' AND meta ? 'distance_km'")
    labs = [r["km"] for r in cur.fetchall()]
    # days on which this node's own outdoor sensors gave 18 hourly means or more, and how many of them were over the guideline
    cur.execute(f"""SELECT count(*) FILTER (WHERE m > %s) AS over, count(*) AS days FROM (
                      SELECT avg(r.mean) AS m FROM readings_1h r JOIN sensors s ON s.sensor_id = r.sensor_id
                      WHERE r.metric = 'pm25' AND r.bucket > now() - interval '365 days' AND s.local AND NOT s.indoor AND s.kind = 'sensor' AND {pub}
                      GROUP BY date_trunc('day', r.bucket) HAVING count(DISTINCT r.bucket) >= 18) d""", (WHO_DAY,))
    a = cur.fetchone() or {}
    cells = _d(get("/place/cells"))
    return shape(latest, get("/hydro"), get("/energy"), get("/index/place"), labs if os.getenv("MAKE_ENABLED", "") == "1" or labs else None,
                 (a.get("over") or 0, a.get("days") or 0), cells.get("held"), yearly, today or date.today())
