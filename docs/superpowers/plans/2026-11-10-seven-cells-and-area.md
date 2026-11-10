# Plan: seven cells and the area pull

Spec: `docs/superpowers/specs/2026-11-10-seven-cells-and-area-design.md`. Branch `cells-area-2026-11-10`.
Gemini builds Tasks 1–8, one per run. Task 9 (docs, in Tomas's voice) and Task 10 (node #1, PR) stay with Claude and Tomas.

## Global constraints

- CI runs Python 3.12, this Mac 3.14: quote annotations naming a type defined later in the file.
- A test suite is stdlib `check()` calls ending in `sys.exit()`; nothing below that line runs. A new suite needs its
  line in `tests/all` and the count sentence there goes up by one.
- Postgres suites skip locally without a database. Any SQL you write also gets a pure test of the Python around it.
- JS tests pass JSON to node through a temp file, never argv (128 KB cap on Linux CI).
- No new dependencies. `h3` (v4 API), PostGIS, httpx are already there. Every httpx client has a timeout.
- Schema: `init.sql` rules at its top (CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS). Next version is the
  first free one after the last `INSERT INTO schema_version` in the file; check, don't assume.
- A missing number stays missing: no 0, no default, no guess.
- `make lint` and `bash tests/all` green before a task is done.

## Review focus (what Claude checks hardest)

- `held` derived on read, never stored; it must not be possible to get `held` without a reading in the last 24 h.
- No sensor on a node that was local yesterday stops being local after upgrade (adoption, Task 2).
- `/place/cells` and `/area` are on no SHARE_LEVEL allowlist.
- Tests that pass by bending the fixture to the code (padding data, loosening a check) are a failed task.

---

## Task 1 · `app/cells.py`, pure

**Interfaces**

```python
RES = 8
STATES = ("home", "held", "claimed", "open")

def home(lat: float, lon: float) -> str                      # h3.latlng_to_cell(lat, lon, RES)
def ring(home_cell: str) -> list[str]                        # sorted grid_disk(home_cell, 1), home first
def own(home_cell: str, claims: set[str]) -> set[str]        # {home} | (claims ∩ neighbours); claims elsewhere ignored
def cell_of(lat: float | None, lon: float | None) -> str | None
def states(home_cell: str, claims: set[str], seen: set[str]) -> list[dict]
    # one row per ring cell: {"cell", "state", "ring": geo._row(cell)}; seen = res-8 cells with an own reading in 24 h
    # home -> "home"; claimed and in seen -> "held"; claimed -> "claimed"; else "open"
def held_count(rows: list[dict]) -> int                      # home counts as held: "N of 7"
def adoptable(home_cell: str, local_points: list[tuple[float, float]]) -> set[str]
    # neighbour cells (never home) that contain one of the points
```

Steps: write `tests/test_cells.py` against node #1's cell `8895a4c843fffff` (ring of 7, 3 of 6 neighbours outside
parent `8795a4c84ffffff`: assert it), a claim outside the ring is ignored, each state reached, `adoptable` never
returns home. See it fail, implement, see it pass. Add to `tests/all`.

## Task 2 · schema, `stamp_local`, adoption

**Interfaces**

```sql
CREATE TABLE IF NOT EXISTS node_cells (
  cell       TEXT PRIMARY KEY,
  claimed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  claimed_by TEXT NOT NULL          -- 'home' | 'adopted' | 'keeper' | 'agent:<name>'
);
```

```python
# app/sources.py
def stamp_local(sensors: list[dict], own_cells: set[str] | None) -> list[dict]
    # None (node has no coordinates) leaves every claim alone, as today. A sensor with no point keeps its claim.
    # Otherwise local stays True only when cells.cell_of(lat, lon) in own_cells.

# app/cells.py
def load(cur, home_cell: str) -> set[str]       # own(home_cell, claims), adopting first if no 'home' row for home_cell
def adopt(cur, home_cell: str, radius_m: float = 500) -> set[str]
    # inserts (home_cell,'home') and, for every sensor with local AND kind='sensor' AND a point within radius_m of the
    # node, its neighbour cell as 'adopted'. Returns what it claimed. Runs once per home cell.
```

Both callers in `app/main.py` (`poll_once`, `_store`) pass `cells.load(cur, cells.home(lat, lon))`, or None without
coordinates. Load once per poll, not per sensor.

Tests: `stamp_local` table cases (in own cells, in an open neighbour, no point, node without coordinates);
`adopt` with a fake cursor; a pg test for the table if the suite style allows. Existing `stamp_local` tests change
with the signature; do not delete a case, port it.

## Task 3 · `LOCAL_RADIUS_M` out

Every reader of `LOCAL_RADIUS_M` (grep app, packs, tools, docs, .env.example, tests). The "The street" claim in
`app/issues/geometry.py` declares the own cells: footprint = sum of `h3.cell_area` over own cells, `declared` names
the cells count, `where` = "node_cells". The setting leaves `app/settings.py` and `.env.example`. A node whose `.env`
still sets it must start and ignore it (check how `settings.py` treats an unknown key; if it refuses, stop and report).
`docs/` text that explains the radius: list the files in the report, don't rewrite prose (Task 9 is Claude's).

## Task 4 · routes

**Interfaces**

```
GET    /place/cells               -> {"home": id, "res": 8, "cells": states(...), "held": n, "of": 7, "community_ready": n >= 4}
POST   /place/cells/{cell}/claim  -> 200 the same body | 400 not a neighbour | 409 already claimed
DELETE /place/cells/{cell}/claim  -> 200 the same body | 400 home cannot be released | 404 not claimed
```

`GET /cells` already exists: it is the Index contract (fci-cells-v0, `cells_()` in app/main.py) and must not change.
In `app/cells.py` as `router`, included in `app/main.py` beside `geo.router`. On no SHARE_LEVEL allowlist (read how
`geo.py` and `maps.py` are gated and do the same). `seen` comes from one query: res-8 cells of custody `kind='sensor'`
sensors with a reading in the last 24 h (compute the cell in Python; sensors are few). Each claim and release writes
an `actions` row with stage `place` (read how `maps.py` writes them; same columns).

Tests: route tests in the style of the existing route suites, including 400/404/409 and that the answer to a
caller with no token is refused.

## Task 5 · Place map shows the seven

`app/static/doors-placemap.js`: at the Cell zoom, a PolygonLayer of the seven from `GET /place/cells`, coloured by state from
the existing theme tokens (no new colour; ask in the report if none fits). Inspector on a neighbour gets Claim or
Release, calling the routes. A line under the map: "N of 7 cells held". Read
`docs/` design notes the file points to before changing it.

Run the visual gate locally (`docs/DEVELOPING.md` says how); paste its last lines. The rig has no WebGL, so also say
in the report that the map itself was not seen.

## Task 6 · `app/area.py`, selection and own/peers

**Interfaces**

```python
AREA_CAP = 500

def cover(sel: dict) -> list[str]
    # sel has exactly one of: {"cells": [...]} res 5..10 | {"polygon": GeoJSON geometry} | {"mark_id": int}
    # mark_id is resolved by the route (geometry from place_marks via ST_AsGeoJSON), not here
    # returns sorted res-8 cells; ValueError past AREA_CAP (estimated before covering), on bad ids or bad geometry
def bbox(cells: list[str]) -> tuple[float, float, float, float]   # west, south, east, north
def summarise(rows: list[dict]) -> dict
    # rows: {metric, ts, value}; per metric {"latest", "latest_at", "mean_24h", "n"}
def own(sensors, readings, selection: set[str], own_cells: set[str]) -> dict
def peers(sensors, readings, selection: set[str]) -> dict          # {"metrics": ..., "sensors": n, "unplaced": n}
```

`own` only counts sensors whose cell is in `selection & own_cells`; it also returns `children_unplaced`.

Tests pure, with fixtures built in the test. A selection with no own cells gives an empty own block that says so.

## Task 7 · the `area` hook and three packs

`app/packs.py`: no change needed if `collect("area", cells, bbox)` works as is; confirm and say so. Each pack adds
`area(cells, bbox)` to its `hooks.py` (create the file if the pack has none), returning the shape in the spec §2.

- `packs/hydro`: clip the kept result to bbox. No network.
- `packs/eyes`: reuse `_cell_wkt` and `OTHERS_LICENCES`; one GBIF call per selection (union the cells' polygons or
  send a MULTIPOLYGON; check GBIF's geometry length limit and say what you chose); cache a day keyed by the sorted cells.
- `packs/forecast`: one Open-Meteo call at the centroid, cached an hour.

Tests mock the network (follow how existing pack tests do it). No live calls in tests.

## Task 8 · `POST /area` and the Pull tool

Route in `app/area.py`, included like Task 4, same gate. Body is the selection; answer
`{"cells": n, "res": 8, "own": ..., "peers": ..., "open": [...]}`. 400 on a bad selection with the ValueError's
sentence, 404 on an unknown mark.

Place Tools menu gets **Pull**: tap cells or choose a drawn area, then the three blocks in the side panel, each with
source and age. Visual gate as Task 5.

## Task 9 · docs (Claude)

Docs page in Tomas's voice, CHANGELOG under Unreleased, the SPEC_eyes §7 step 4 line, the radius text Task 3 listed.

## Task 10 · node #1 (Claude + Tomas)

Node #1 on the branch: before/after `SELECT sensor_id, local FROM sensors` must match; `GET /place/cells` shows the
adopted cells; one Pull over the seven and one over a drawn area. Then PR, `tested: node 1` label on Tomas's word.
