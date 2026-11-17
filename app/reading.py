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

import json
import logging
import os
import re
import threading
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

import cells

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
        "buildings_then": "n", "buildings_then_year": "y", "buildings_now": "n",
        "river_km": "n", "basin_km2": "n", "bioregion_km2": "n",
        "grid": "s", "fossil_low_pct": "n", "fossil_high_pct": "n",
        "index_place": "s", "index_label": "s", "index_measured": "n", "index_cells": "n",
        "labs_50km": "n", "lab_km": "n", "air_days_over": "n", "air_days": "n", "cells_held": "n"}
SHARES = frozenset(k for k, f in FORM.items() if f == "share")

_PLACE = "turn on the place pack in Set up › Packs"
FILL = {**{k: _PLACE for k, _ in READ.values()},
        "buildings_then": _PLACE, "buildings_then_year": _PLACE, "buildings_now": _PLACE,
        "school_km": "draw it on openstreetmap.org, where the place pack reads it", "clinic_km": "draw it on openstreetmap.org, where the place pack reads it",
        "market_km": "draw it on openstreetmap.org, where the place pack reads it",
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
    if form == "y":
        return str(int(v))
    return f"{round(v):,}" if round(v) >= 10000 else str(round(v))


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
                  else int(round(float(v))), "at": at[:10]}   # "n", "km" and "y" are whole numbers

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


# ---------------------------------------------------------------- the rules: the node's own reading
NOTHING = "The node holds nothing yet that speaks to this."
THIN = 0.6            # under this share of the satellite's buildings on the public map, an OpenStreetMap count is said to be thin

# What is missing, said for a person, in the order the gaps become avenues. (what, the facts it covers, an avenue to map it)
GAPS = (
    ("the rivers and basins round this place", ("river_km", "basin_km2", "bioregion_km2"),
     ("Find where this place's water goes", "Bioregional strategies", "bioregional")),
    ("where the grid's power comes from", ("grid", "fossil_low_pct", "fossil_high_pct"),
     ("Find where the power comes from", "Infrastructure", "asset")),
    ("what stands within a kilometre: buildings, roads, shops, green", ("buildings", "sat_buildings", "osm_coverage", "built_share", "green_share",
     "commercial_share", "businesses_km2", "roads_km", "poi_food", "poi_retail", "poi_education", "poi_health", "poi_worship", "poi_lodging",
     "poi_services", "buildings_then", "buildings_then_year", "buildings_now"),
     ("Count what stands here", "Place-based interventions", "socio-spatial")),
    ("this place on the Fab City Index", ("index_place", "index_label", "index_measured", "index_cells"),
     ("Choose this node's place on the Fab City Index", "Global networks", "asset")),
    ("the air outside over a year", ("air_days_over", "air_days"),
     ("Measure the air outside for a month", "Learning", "socio-spatial")),
    ("where rain runs across the ground", ("upslope_ha",), ("See where the rain runs", "Place-based interventions", "bioregional")),
    ("the nearest place to make and fix things", ("labs_50km", "lab_km"), ("Look for the nearest place to make and fix", "Infrastructure", "asset")),
    ("how hot the ground gets", ("heat_delta_c",), None),
    ("trees and farmed land from the satellite", ("tree_share", "crop_share"), None),
    ("the nearest school, clinic and market", ("school_km", "clinic_km", "market_km"), None),
    ("which of its seven cells the node holds", ("cells_held",), None),
)


def rules(doc: dict) -> dict:
    """The node's own reading of its place. Pure: the same facts give the same text.

    Every sentence carries its figure, a rule whose facts are missing does not fire, and an avenue that rests on a
    held figure cites it. Where fewer than four avenues fire, the gaps supply the rest as things to map."""
    F = doc["facts"]
    v = lambda k: F[k]["v"] if F.get(k) else None            # noqa: E731
    has = lambda *ks: all(F.get(k) is not None for k in ks)  # noqa: E731
    t = lambda k: say(k, v(k))                               # noqa: E731
    near = lambda k: "within a kilometre" if v(k) == 0 else f"about {t(k)} km away"   # noqa: E731
    thin = has("osm_coverage") and v("osm_coverage") < THIN
    osm = lambda text: text[:-1] + ", as far as the public map goes." if thin else text   # noqa: E731
    lines: dict = {i: [] for i, _ in SECTIONS}
    found: list = []                                         # (figures it rests on, avenue)
    lab = f"the lab {near('lab_km')}" if has("lab_km") else None

    def avenue(rests, title, why, first, layer, action, signal):
        found.append((len(rests), {"title": title, "why": why, "first_step": first, "layer": layer, "action": action, "signal": signal,
                                   "with": lab if action == "Experiment" else None}))

    # --- the region it belongs to
    if has("basin_km2", "bioregion_km2"):
        lines["region"].append(f"Rain that falls here leaves by a basin of {t('basin_km2')} km², inside a bioregion of {t('bioregion_km2')} km².")
        avenue(("basin_km2", "bioregion_km2"), "Walk the water from here to the sea, and mark what enters it",
               f"This place drains through a basin of {t('basin_km2')} km². What leaves the ground here reaches the coast.",
               "Follow the nearest river downstream for a morning with the neighbours, and photograph every drain and outfall on the way.",
               "Bioregional strategies", "Map and research", "bioregional")
    if has("river_km"):
        lines["region"].append("A river runs within a kilometre." if v("river_km") == 0 else f"The nearest river is about {t('river_km')} km away.")
    if has("grid", "fossil_low_pct", "fossil_high_pct"):
        span = f"{t('fossil_low_pct')}%" if v("fossil_low_pct") == v("fossil_high_pct") else f"Between {t('fossil_low_pct')}% and {t('fossil_high_pct')}%"
        lines["region"].append(f"{span} of the electricity here is burned, on the {t('grid')} grid.")
        if v("fossil_low_pct") >= 60:
            avenue(("fossil_low_pct", "fossil_high_pct", "grid"), "Count the roofs that could carry panels, then share one array among neighbours",
                   f"At least {t('fossil_low_pct')}% of the power on the {t('grid')} grid comes from coal and gas.",
                   "List ten roofs on the street that face the sun, and ask who would share the cost of one array.",
                   "Infrastructure", "Experiment", "asset")
    if has("index_place", "index_label", "index_measured", "index_cells"):
        lines["region"].append(f"{t('index_place')} is on the Fab City Index as {t('index_label')}, with {t('index_measured')} of {t('index_cells')} cells measured.")
        if v("index_measured") < v("index_cells"):
            avenue(("index_measured", "index_cells"), "Fill one cell of the city's Index from this node",
                   f"{t('index_measured')} of the {t('index_cells')} cells of {t('index_place')} on the Fab City Index is measured. A node that measures here can fill another.",
                   f"Open index.fab.city, find a cell of {t('index_place')} with no source, and see whether this node already holds the figure.",
                   "Global networks", "Map and research", "asset")
    if has("lab_km", "labs_50km"):
        lines["region"].append(f"The nearest place to make or fix something is {near('lab_km')}, one of {t('labs_50km')} within 50 km.")
    elif has("labs_50km") and v("labs_50km") == 0:
        lines["region"].append("No fab lab is listed within 50 km.")
        avenue(("labs_50km",), "Start a shared bench before a lab", "No fab lab is listed within 50 km of here.",
               "Put tools and a table in one room, one evening a week, and see who comes.", "Infrastructure", "Experiment", "socio-spatial")

    # --- what the land allows
    if has("green_share", "built_share"):
        lines["land"].append(f"{t('green_share')} of the ground within a kilometre is green, and {t('built_share')} is built on.")
    if has("heat_delta_c"):
        hot = v("heat_delta_c") > 0.5
        lines["land"].append(f"The surface here runs {t('heat_delta_c')} °C hotter than the land around it." if hot
                             else "The surface here is no hotter than the land around it.")
        if hot:
            avenue(("heat_delta_c",) + (("green_share",) if has("green_share") else ()), "Shade and soak the hardest ground",
                   f"The surface runs {t('heat_delta_c')} °C hotter than the land around it" + (f", with {t('green_share')} of the ground green." if has("green_share") else "."),
                   "Pick the hottest stretch of street, and plant or shade twenty metres of it before the next dry season.",
                   "Place-based interventions", "Experiment", "bioregional")
    if has("upslope_ha"):
        if v("upslope_ha") >= 1:
            lines["land"].append(f"Water from {t('upslope_ha')} ha of higher ground passes this point.")
            avenue(("upslope_ha",), "Slow the water where it gathers", f"Rain from {t('upslope_ha')} ha of higher ground runs past this point.",
                   "After the next heavy rain, mark where water stands, and dig one soakaway there.", "Place-based interventions", "Experiment", "bioregional")
        else:
            lines["land"].append(f"Little water arrives from above: {t('upslope_ha')} ha of higher ground drains past this point.")
    if has("tree_share", "crop_share"):
        lines["land"].append(f"{t('tree_share')} of the land is under trees, and {t('crop_share')} is farmed.")
    if has("sat_buildings", "roads_km"):
        lines["land"].append(f"The satellite counts {t('sat_buildings')} buildings within a kilometre, along {t('roads_km')} km of road.")

    # --- what people here need
    if has("air_days_over", "air_days"):
        lines["needs"].append(f"On {t('air_days_over')} of the {t('air_days')} days the node measured, the air outside was over the WHO guideline for a day."
                              if v("air_days_over") else f"On none of the {t('air_days')} days the node measured was the air outside over the WHO guideline for a day.")
        if v("air_days_over") * 10 >= v("air_days"):
            avenue(("air_days_over", "air_days"), "Build sensors with the neighbours, and agree what to do on a bad day",
                   f"The air outside was over the WHO guideline on {t('air_days_over')} of the {t('air_days')} days the node measured.",
                   "Hold one evening to assemble two kits, and write down who closes which window when the figure passes the guideline.",
                   "Learning", "Experiment", "socio-spatial")
    for key, what in (("clinic_km", "clinic"), ("school_km", "school"), ("market_km", "market")):
        if has(key):
            lines["needs"].append(osm(f"A {what} is drawn within a kilometre." if v(key) == 0 else f"The nearest {what} drawn is about {t(key)} km away."))
            if v(key) >= 2:
                avenue((key,), f"Ask who walks to the {what}, and what would shorten the way", f"The nearest {what} drawn is about {t(key)} km away.",
                       "Ask ten households how they get there and what it costs them, and take the answers to the banjar.", "Communities", "Rethink", "socio-spatial")
    if has("lab_km", "labs_50km"):
        lines["needs"].append(f"What breaks here can be mended {near('lab_km')}.")
        avenue(("lab_km", "labs_50km"), "Hold a repair evening", f"A place to make and fix things is {near('lab_km')}, one of {t('labs_50km')} within 50 km.",
               "Bring five broken things to one table, and see which can be mended with what is at hand.", "Learning", "Experiment", "asset")

    # --- how the place behaves
    if has("buildings_then", "buildings_then_year", "buildings_now"):
        up = v("buildings_now") > v("buildings_then")
        lines["system"].append(f"The satellite counts {t('buildings_now')} buildings here, {'up from' if up else 'against'} {t('buildings_then')} in {t('buildings_then_year')}."
                               + (" More roofs, less soak, more heat: each feeds the next." if up and (has("green_share") or has("heat_delta_c")) else ""))
        if up:
            avenue(("buildings_then", "buildings_then_year", "buildings_now"), "Agree a rule for new ground",
                   f"{t('buildings_then')} buildings in {t('buildings_then_year')}, {t('buildings_now')} now.",
                   "Write one line the banjar can hold a builder to: what each new roof gives back in shade, or in ground that soaks.",
                   "Bioregional strategies", "Rethink", "bioregional")
    if has("osm_coverage"):
        lines["system"].append(f"{t('osm_coverage')} of the buildings the satellite sees are on the public map." + (" What is not drawn is not planned for." if thin else ""))
        if thin:
            avenue(("osm_coverage",), "Map the missing buildings and paths together", f"Only {t('osm_coverage')} of the buildings the satellite sees are on the public map.",
                   "Spend two hours on openstreetmap.org with a neighbour, and draw the buildings of one street.", "Communities", "Map and research", "asset")
    if has("fossil_low_pct") and v("fossil_low_pct") >= 60:
        lines["system"].append(f"At least {t('fossil_low_pct')}% of the power used here is burned somewhere else, so nobody here sees the smoke their use makes.")
    if has("cells_held"):
        lines["system"].append(f"The node measures in {t('cells_held')} of its 7 cells." + (" What happens in the others reaches nobody." if v("cells_held") < 7 else ""))
        if v("cells_held") < 3:
            avenue(("cells_held",), "Lend a kit to a neighbour in a cell nobody measures", f"The node measures in {t('cells_held')} of its 7 cells.",
                   "Open Place at Cell scale, pick an open cell, and ask one household in it to keep a sensor for a month.", "Communities", "Experiment", "asset")

    # --- the life of the street
    count = lambda k, one, many: f"{t(k)} {one if v(k) == 1 else many}"   # noqa: E731
    kinds = [(k, one, many) for k, one, many in (("poi_food", "to eat", "to eat"), ("poi_lodging", "to stay", "to stay"), ("poi_retail", "shop", "shops"),
                                                 ("poi_services", "service", "services"), ("poi_education", "school", "schools"),
                                                 ("poi_health", "clinic", "clinics"), ("poi_worship", "place of worship", "places of worship")) if has(k)]
    if kinds:
        drawn = [(k, one, many) for k, one, many in kinds if v(k) > 0]
        if drawn:
            lines["street"].append(osm(f"{len(drawn)} kind{'s' if len(drawn) > 1 else ''} of place {'are' if len(drawn) > 1 else 'is'} drawn within a kilometre: "
                                       + ", ".join(count(*d) for d in drawn) + "."))
        else:
            lines["street"].append(osm("No shop, café or service is drawn within a kilometre."))
        if has("poi_lodging", "poi_retail", "poi_services") and v("poi_lodging") > 0 and v("poi_lodging") >= v("poi_retail") + v("poi_services"):
            lines["street"].append("More places house visitors than sell what a household needs from day to day.")
            avenue(("poi_lodging", "poi_retail", "poi_services"), "Give one ground floor a second use that serves the people who live here",
                   f"{count('poi_lodging', 'place', 'places')} to stay within a kilometre, against {count('poi_retail', 'shop', 'shops')} and {count('poi_services', 'service', 'services')}.",
                   "Find one ground floor that is closed most of the day, and ask its owner for two mornings a week.",
                   "Value-generating projects", "Experiment", "socio-spatial")
    if has("businesses_km2", "roads_km"):
        lines["street"].append(osm(f"{t('businesses_km2')} businesses a square kilometre, along {t('roads_km')} km of road."))
        if v("businesses_km2") < 10:
            avenue(("businesses_km2", "roads_km"), "Open one shared space for a season, and see who comes",
                   f"{t('businesses_km2')} businesses a square kilometre along {t('roads_km')} km of road leave few places to meet by chance.",
                   "Ask the banjar for one unused ground floor or yard for three months, with a table, shade and a notice board.",
                   "Place-based interventions", "Experiment", "socio-spatial")
    if has("commercial_share"):
        lines["street"].append(osm(f"{t('commercial_share')} of the buildings are shops or workplaces." if v("commercial_share") > 0
                                   else "No building within a kilometre is drawn as a shop or a workplace."))

    blind = [{"what": what, "command": FILL[next(k for k in keys if F.get(k) is None)], "facts": [k for k in keys if F.get(k) is None]}
             for what, keys, _ in GAPS if any(F.get(k) is None for k in keys)]
    avenues = [a for _, a in sorted(found, key=lambda x: -x[0])][:6]         # sorted is stable: the order above breaks a tie
    for what, keys, gap in GAPS:
        if len(avenues) >= 4:
            break
        if gap and all(F.get(k) is None for k in keys):
            command = FILL[keys[0]]
            avenues.append({"title": gap[0], "why": f"The node does not hold {what} yet.", "first_step": f"On the node: {command}. Then open Place again.",
                            "layer": gap[1], "action": "Map and research", "signal": gap[2], "with": None})
    return {"sections": [{"id": i, "heading": h, "lines": lines[i] or [NOTHING]} for i, h in SECTIONS], "avenues": avenues, "blind": blind}


# ---------------------------------------------------------------- the fuller text: a model's, kept only if it holds
# The manner each section is read in. The names steer the model and stop here: a text that carries one is refused,
# and no page, button, doc or answer of the node says them (Tomas, 17 Nov 2026: "do not mention the names of experts").
MANNER = (("region", "the region as the unit, its limits and its balance, the way Lewis Mumford read a city in its region"),
          ("land", "what the land is fit for against what it is used for, as Ian McHarg would lay it out"),
          ("needs", "real needs before wants, met with local means, as Victor Papanek asked of design"),
          ("system", "stocks, flows, loops and delays, and where a small push counts, as Donella Meadows would trace them"),
          ("street", "the mix of uses, short blocks and eyes on the street, as Jane Jacobs watched them"))
PERSON = re.compile(r"mumford|mcharg|papanek|meadows|jacobs", re.I)
UNITS = re.compile(r"\b(?:PM2\.5|PM10|PM1|CO2|NO2|O3)\b", re.I)    # a unit's own digits are not a figure
ALWAYS = (1, 2, 3, 4, 5, 6, 7, 50, WHO_DAY)                        # small counts, the labs' radius, the guideline


def prompt(doc: dict, ruled: dict) -> str:
    """What the model is handed: the frame, the manner, the facts, the node's own reading, and the shape to answer in."""
    head = dict(SECTIONS)
    held = {k: f["v"] for k, f in doc["facts"].items() if f}
    return (
        "You are writing two pages of a report about one place, for the people who live there and for whoever they hand it to: "
        "neighbours, a village council, a funder. Read the place five ways, one paragraph each, in this order:\n"
        + "".join(f"- {i} · {head[i]}: {how}.\n" for i, how in MANNER)
        + "Write in their manner and name no person: not them, not anyone. Plain words, no headings, no lists, 60 to 120 words a section. "
        "Say what the figures mean for the people here, beyond the figures themselves.\n"
        "Use only numbers that are in FACTS, written as THE NODE'S OWN READING writes them. No dates, no coordinates, no other figure.\n"
        "A count or a share that comes from the public map covers one kilometre round the place, never 'this cell'.\n\n"
        "Then give four to six ways to improve the place. You may keep, sharpen or replace the node's own. Each has:\n"
        "- title: a plain imperative;\n- why: one or two sentences with the figures it rests on;\n"
        "- first_step: something a household, a village council or a lab can start this month;\n"
        f"- layer: one of {json.dumps(LAYERS)};\n- action: one of {json.dumps(ACTIONS)};\n- signal: one of {json.dumps(SIGNALS)}.\n\n"
        'Answer with JSON only: {"sections": {"region": "...", "land": "...", "needs": "...", "system": "...", "street": "..."}, '
        '"avenues": [{"title": "...", "why": "...", "first_step": "...", "layer": "...", "action": "...", "signal": "..."}]}\n\n'
        f"FACTS\n{json.dumps(held, ensure_ascii=False)}\n\nTHE NODE'S OWN READING\n"
        + json.dumps({"sections": {s["id"]: " ".join(s["lines"]) for s in ruled["sections"]},
                      "avenues": [{k: a[k] for k in ("title", "why", "first_step", "layer", "action", "signal")} for a in ruled["avenues"]]},
                     ensure_ascii=False))


def stray_numbers(text: str, doc: dict) -> list[str]:
    """The numbers in `text` that are not the node's. A share may be said as a percentage or as a fraction."""
    allowed = set(float(n) for n in ALWAYS)
    for k, f in doc["facts"].items():
        if not f or FORM[k] == "s":
            continue
        v = f["v"]
        allowed.add(float(say(k, v).replace(",", "").rstrip("%")))
        if k in SHARES:
            allowed.update((round(v, 2), round(v, 3), round(v * 100, 1)))
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", UNITS.sub("", text))
    return [n for n in re.findall(r"\d+(?:\.\d+)?", text) if float(n) not in allowed]


def accept(answer: str, doc: dict) -> tuple[dict | None, str]:
    """A model's answer, as (written, "") when it holds and (None, why) when it does not. Never raises."""
    try:
        got = json.loads(answer[answer.index("{"):answer.rindex("}") + 1])
    except (ValueError, TypeError, AttributeError):
        return None, "not the JSON it was asked for"
    sec, av = (got.get("sections"), got.get("avenues")) if isinstance(got, dict) else (None, None)
    ids = [i for i, _ in SECTIONS]
    if not isinstance(sec, dict) or sorted(sec) != sorted(ids):
        return None, f"sections: the five of the frame were asked for, and it gave {sorted(sec) if isinstance(sec, dict) else 'none'}"
    for i in ids:
        if not isinstance(sec[i], str) or not sec[i].strip():
            return None, f"section {i} is empty"
    if not isinstance(av, list) or not 4 <= len(av) <= 6:
        return None, f"avenues: four to six were asked for, and it gave {len(av) if isinstance(av, list) else 'none'}"
    out = []
    for n, a in enumerate(av, 1):
        if not isinstance(a, dict) or not all(isinstance(a.get(k), str) and a[k].strip() for k in ("title", "why", "first_step")):
            return None, f"avenue {n} lacks its title, its why or its first step"
        for key, frame in (("layer", LAYERS), ("action", ACTIONS), ("signal", SIGNALS)):
            if a.get(key) not in frame:
                return None, f"avenue {n}: its {key} is not one of the frame's ({str(a.get(key))[:40]!r})"
        out.append({**{k: a[k].strip() for k in ("title", "why", "first_step")}, "layer": a["layer"], "action": a["action"], "signal": a["signal"], "with": None})
    text = "\n".join([sec[i] for i in ids] + [f"{a['title']} {a['why']} {a['first_step']}" for a in out])
    if PERSON.search(text):
        return None, "it names a person"
    stray = stray_numbers(text, doc)
    if stray:
        return None, "numbers the node does not hold: " + ", ".join(dict.fromkeys(stray))
    return {"sections": {i: sec[i].strip() for i in ids}, "avenues": out}, ""


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


def facts(cur, get=None, today: date | None = None) -> dict:
    """Every figure the reading may rest on. `cur` is a dict-row cursor; `get` reads one of the node's own routes."""
    import packs  # noqa: PLC0415 — the loader reads PACKS_DIR at import
    get = get or _self

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


# ---------------------------------------------------------------- the routes: GET and POST /place/reading
# The household's alone at every SHARE_LEVEL, as /place/cells and /hydro are: on no allowlist in app/auth.py, so this
# machine or a token. One facts document for one kind of reader keeps a model's text safe to show to all of them.
# Reading it takes the admin or the act token; asking a model for the fuller text takes the admin token.
NO_MODEL = "No model on this house's network can write this. The reading above is the node's own."
WRITING_MAX = timedelta(minutes=10)     # a `writing` row older than this failed: a restart must not leave the button stuck
router = APIRouter(dependencies=[Depends(cells._household)])
_lock = threading.Lock()


def _db():
    from db import db  # noqa: PLC0415 — db.py needs DATABASE_URL at import
    return db()


def _rungs() -> list:
    import ask  # noqa: PLC0415 — the same ladder and AGENT_PREFER the pane reads
    return ask.rungs()


def _spawn(fn, *args) -> None:
    threading.Thread(target=fn, args=args, daemon=True, name="place-reading").start()


def pick(rungs: list):
    """The model that may write: the first that is neither small nor off the house's network, whatever AGENT_PREFER
    lets the pane use. The facts stay at home. The local rung is always `small` in the ladder today, so a node whose
    only strong model is its local one has no writer yet."""
    return next((r for r in rungs if not r.small and not r.leaves), None)


def _ask(rung, system: str) -> str:
    """One answer from one rung, with ten minutes to give it. No tools, so chat() runs it without thinking."""
    import asyncio  # noqa: PLC0415
    import httpx  # noqa: PLC0415
    import agent_loop  # noqa: PLC0415

    async def go():
        async with httpx.AsyncClient(timeout=WRITING_MAX.total_seconds()) as hc:
            m = await agent_loop.chat(hc, rung, [{"role": "system", "content": system}, {"role": "user", "content": "Write the reading."}], None, final=True)
            return m.get("content") or ""
    return asyncio.run(go())


def write(rid: int, rung, doc: dict, ruled: dict) -> None:
    """Ask the model, check what it wrote, and keep it or the reason it was refused. Runs off the request."""
    from psycopg.types.json import Jsonb  # noqa: PLC0415
    try:
        written, why = accept(_ask(rung, prompt(doc, ruled)), doc)
    except Exception as e:  # noqa: BLE001 — whatever went wrong, the row must leave `writing`
        written, why = None, f"the model did not answer ({type(e).__name__})"
    log.info("reading %d: %s", rid, "written" if written else f"refused, {why}")
    with _db() as con, con.transaction(), con.cursor() as cur:
        cur.execute("UPDATE place_readings SET state = %s, text = %s, refused = %s WHERE id = %s",
                    ("written" if written else "refused", Jsonb(written) if written else None, why or None, rid))


def _rows(cur) -> list:
    cur.execute("SELECT id, ts, state, model, wherefrom, text, refused FROM place_readings ORDER BY id DESC LIMIT 20")
    return list(cur.fetchall())


def _stale(row) -> bool:
    return row["state"] == "writing" and datetime.now(timezone.utc) - row["ts"] > WRITING_MAX


@router.get("/place/reading")
def place_reading(authorization: str = Header("")):
    """The node's own reading of its place, the fuller text if a model wrote one that held, and whether this caller
    may ask for one."""
    from auth import _bearer_ok  # noqa: PLC0415
    with _db() as con, con.transaction(), con.cursor() as cur:
        doc = facts(cur)
        rows = _rows(cur)
    last = rows[0] if rows else None
    kept = next((r for r in rows if r["state"] == "written"), None)
    state, refused = (("refused", "took too long") if _stale(last) else (last["state"], last["refused"])) if last else ("none", None)
    return {"facts_at": doc["at"], "rules": rules(doc), "written": kept["text"] if kept else None,
            "written_at": kept["ts"].isoformat() if kept else None, "by": {"model": kept["model"], "where": kept["wherefrom"]} if kept else "node",
            "state": state, "refused": refused,
            "can_write": _bearer_ok(authorization, os.getenv("ADMIN_TOKEN", "").strip()) and pick(_rungs()) is not None}


@router.post("/place/reading", status_code=202)
def write_reading(authorization: str = Header("")):
    """Ask a model on the house's network for the fuller text. 202 at once; GET says when it is written or refused."""
    from psycopg.types.json import Jsonb  # noqa: PLC0415
    import agent_loop  # noqa: PLC0415
    from auth import _admin  # noqa: PLC0415
    _admin(authorization)
    rung = pick(_rungs())
    if rung is None:
        raise HTTPException(409, NO_MODEL)
    with _lock, _db() as con, con.transaction(), con.cursor() as cur:      # one writing at a time: a second press joins the first
        rows = _rows(cur)
        if rows and rows[0]["state"] == "writing" and not _stale(rows[0]):
            return {"state": "writing", "id": rows[0]["id"]}
        doc = facts(cur)
        cur.execute("INSERT INTO place_readings (state, rung, model, wherefrom, facts) VALUES ('writing', %s, %s, %s, %s) RETURNING id",
                    (rung.name, rung.model, agent_loop.where_of(rung)["where"], Jsonb(doc)))
        rid = cur.fetchone()["id"]
    _spawn(write, rid, rung, doc, rules(doc))
    return {"state": "writing", "id": rid}
