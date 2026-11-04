# Place light GIS, PR 1: drawing and maps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw on Place (markers, lines, areas, notes, with colour, label, note, image), keep drawings in named maps,
download them as PNG/GeoJSON/KML/DXF, share a map upstream with a warning, record the work in the ledger and as
private daily readings, tie a drawing to an open issue as its acted step; satellite on by default, then-and-now in the
lower band, drone pins, folding sides.

**Architecture:** Two core PostGIS tables and a new `app/maps.py` router (CRUD, exports, ledger rows, the issue tie,
the upstream push and its receiving route). A new pure-function companion `app/static/doors-draw.js` (geodesic math,
the drawing state machine, the readout) wired into `doors-placemap.js` (keys on the screen, rendering, editing) and
`doors-place.js` (your maps, the lower band, dialogs).

**Tech Stack:** FastAPI, psycopg, PostGIS 3.4 (`imresamu/postgis:16-3.4-alpine`), plain browser JS, MapLibre 5.24 and
deck.gl as vendored, node for JS tests.

**Spec:** `docs/superpowers/specs/2026-11-04-place-light-gis-design.md` (§4, §5, §8, §10, §13 item 1). Layout
authority: `docs/superpowers/specs/2026-11-04-place-light-gis-mockup.html`. PRs 2 (cells, OSM) and 3 (tools, agents)
are out of scope: no OSM key, no cell fetch, no Run panel, no MCP tools here.

## Global Constraints

- One token: every new household route is token-only at every `SHARE_LEVEL` by staying off `_SHARE_OFF`/`_SHARE_OPEN`
  in `app/auth.py`; the page adds `place\/maps|place\/marks` to `DOORS_LOCKED` in `app/static/doors-load.js`.
- No new front-end or Python dependency. No build step. DXF is hand-written ASCII R12; KML from `ST_AsKML`.
- The stored `length_m`/`area_m2` are PostGIS's, from `geom::geography`, written on every insert and update.
- GeoJSON contract: collection carries `map`, `owner`, `node`, `schema: "planetai.place.map/v0"`; each Feature's
  `properties` are `kind`, `label`, `note`, `colour` (1–6), `colour_hex`, `length_m`, `area_m2`, `image` (capture id,
  never a file), `drawn_by`, `updated_at`. WGS84.
- Colours are numbers 1–6; the server holds the palette (hex + DXF ACI) and serves it with `GET /place/maps`. None is
  the satellite's orange (`#F5A623`-ish) or the cells' blue (`PAL.dark` cells); each reads on satellite and on black.
- Drawing needs no drag: taps add points; Enter adds at the map centre; points move by tap-then-tap or arrows.
- 44 px targets on the screen; keys are `<button>` with `aria-label` and `aria-pressed`; the readout's finished figure
  is `aria-live="polite"`.
- Drawing colours appear on the screen only, never as page chrome.
- `actions` gains stage `place`; GIS rows are coalesced: same actor, verb and drawing within 60 s is one row.
- Copy is plain, in Tomas's voice; no AI patterns (run the avoid-ai-writing pass on user-facing copy before the PR).
- Tests: each suite ends in `sys.exit()`; a new suite needs its `tests/all` line and the count in `tests/all` bumped;
  a suite that skips without Postgres is listed in `EXPECTED_SKIPS`.
- Node #1 runs the branch for a real cycle before merge, CI green first.

## Review Focus

1. A node in the southern hemisphere (node #1 is at −8.8°): DXF must use EPSG 327xx, not 326xx. → Task 3 test.
2. A self-intersecting area, a line with one point, an area with two: refused with a sentence (422), never stored. →
   Task 2 test.
3. A label or note holding `<`, `&`, quotes or a newline: escaped in the page, valid XML in KML, one line in DXF TEXT.
   → Task 3 and Task 7 tests.
4. A screen without a token: no keys, no maps list contents, the section says how to unlock; `GET /place/maps` without
   a token from off-machine is refused. → Task 2 and Task 7 tests.
5. Sharing with no `PARENT`, or a parent that answers 404: the switch stays off or the row says the node upstream does
   not take maps yet; nothing retries faster than hourly after a failure. → Task 4 test.

---

### Task 1: Schema, PostGIS in core, CI database

**Files:**
- Modify: `init.sql` (append a dated block), `.github/workflows/lint.yml:30`, `config/channels.yml`
- Create: `tests/test_maps_pg.py`
- Modify: `tests/all` (line + count 105 → 106, add `test_maps_pg` to `EXPECTED_SKIPS`)

**Interfaces:**
- Produces: tables `place_maps(id, name, owner, agent, shared, shared_at, share_error, pushed_at, push_tried_at,
  created_at, updated_at, from_node, remote_id)` with `UNIQUE (from_node, remote_id)`, and `place_marks(id, map_id,
  kind, geom, colour, label, note, capture_id, length_m, area_m2, drawn_by, run_id, alert_id, event_id, created_at,
  updated_at)` as §5; `actions_stage_check` including `'place'`; channel roles `{source: place, metric: marks |
  marked_area_m2, role: private}`.

- [ ] **Step 1: Write the failing test** `tests/test_maps_pg.py` (skips with the line
  `  - maps on a real database skipped (set RHO_PG_URL to a Postgres with init.sql applied)` when `RHO_PG_URL` unset):

```python
# on a fresh DB with init.sql applied twice
assert table_exists("place_maps") and table_exists("place_marks")
cur.execute("INSERT INTO place_maps (name) VALUES ('t') RETURNING id"); mid = cur.fetchone()["id"]
cur.execute("""INSERT INTO place_marks (map_id, kind, geom) VALUES
  (%s, 'area', ST_GeomFromText('POLYGON((115.167 -8.819,115.168 -8.819,115.168 -8.818,115.167 -8.819))',4326))""", (mid,))
cur.execute("INSERT INTO actions (stage, actor, note, choice) VALUES ('place','t','x','drew')")   # check allows it
for bad in ("INSERT INTO place_marks (map_id, kind, geom) VALUES (%s,'circle',ST_Point(0,0,4326))",
            "INSERT INTO place_marks (map_id, kind, geom, colour) VALUES (%s,'marker',ST_Point(0,0,4326),7)"):
    assert raises(bad, mid)          # kind and colour CHECKs hold
cur.execute("DELETE FROM place_maps WHERE id=%s", (mid,)); assert count("place_marks") == 0   # cascade
```

- [ ] **Step 2: Run it.** `RHO_PG_URL=… python3 tests/test_maps_pg.py` → FAIL (no table). Use a scratch PostGIS
  (`docker run … imresamu/postgis:16-3.4-alpine`, see memory "pg suites skip locally").

- [ ] **Step 3: Implement.** In `init.sql`, ahead of the tables, a `DO $$ … $$` block that runs `CREATE EXTENSION IF
  NOT EXISTS postgis` and on failure `RAISE EXCEPTION 'PostGIS is not in this database: Place maps need the
  imresamu/postgis image docker-compose.yml names. Run planetai update after the db image is current.'`. Then the two
  tables (`CREATE TABLE IF NOT EXISTS`), the GIST index on `place_marks.geom`, an index on `place_marks(map_id)`,
  and the widened `actions_stage_check` (drop and re-add, as at `init.sql:186-187`, keeping every existing stage).
  `lint.yml`: `postgres:16-alpine` → `imresamu/postgis:16-3.4-alpine`. `config/channels.yml`: the two `place` rows,
  `role: private`, units `count` and `m²`.

- [ ] **Step 4: Run it** twice against a fresh DB (`psql -v ON_ERROR_STOP=1 < init.sql` ×2), then the suite → PASS.
  Run against plain `postgres:16-alpine` once and confirm `planetai`'s update would stop with that sentence.

- [ ] **Step 5: Commit** `schema: place maps in core, PostGIS enabled by init.sql, CI on the PostGIS image`.

### Task 2: `app/maps.py`: maps, drawings, the ledger, the issue tie

**Files:**
- Create: `app/maps.py`, `tests/test_maps.py`
- Modify: `app/main.py` (include the router next to `geo.router`, `:1565`), `tests/all` (line, count → 107),
  `tests/test_maps_pg.py` (route-level cases against the DB)

**Interfaces:**
- Consumes: Task 1 tables; `db()` from `app/db.py`; `actor` from the request body (`planetai_actor` on the page).
- Produces:
  - `router = APIRouter()` with `GET/POST /place/maps`, `PATCH/DELETE /place/maps/{id}`, `POST
    /place/maps/{id}/marks`, `PATCH/DELETE /place/marks/{id}`.
  - `PALETTE: dict[int, tuple[str, int]]` (colour → hex, DXF ACI); `GET /place/maps` returns `{maps: [...],
    palette: {"1": "#…", …}}`, each map `{id, name, owner, agent, shared, share_error, from_node, marks, updated_at}`.
  - `check_feature(feature: dict) -> str | None` — the refusal sentence, or None.
  - `ledger(cur, actor: str, verb: str, note: str, key: str) -> None` — insert or, for the same `(actor, verb, key)`
    within 60 s, update `ts` and `note` on the existing `stage='place'` row. `key` is e.g. `mark:12`; it is kept in
    `choice` as `<verb>` only and in the note's tail `(mark 12)` so the ledger groups it.
  - `tie(cur, mark_id: int, issue: dict | None, words: str, actor: str) -> None` — §8's acted row.

- [ ] **Step 1: Write the failing tests.** `tests/test_maps.py` (no DB, pure functions):

```python
assert check_feature({"type":"Feature","properties":{"kind":"line"},"geometry":{"type":"LineString","coordinates":[[115.1,-8.8]]}}) == "A line needs two points or more."
assert check_feature(area([[0,0],[1,1],[1,0],[0,1],[0,0]])) == "That area crosses itself. Draw its corners in order around it."
assert check_feature(area([[0,0],[1,0],[0,0]])) == "An area needs three corners or more."
assert check_feature(marker(115.167,-8.819)) is None
assert check_feature({"type":"Feature","properties":{"kind":"marker"},"geometry":{"type":"LineString","coordinates":[[0,0],[1,1]]}}) == "A marker is one point."
assert set(PALETTE) == {1,2,3,4,5,6} and all(h.startswith("#") and 1 <= aci <= 255 for h, aci in PALETTE.values())
```

  `tests/test_maps_pg.py` gains, through FastAPI's `TestClient` with `ADMIN_TOKEN` set:
  - create map → add an area → its `area_m2` is within 1 % of `ST_Area(geom::geography)`;
  - the same drawing changed twice inside 60 s → one `stage='place'` row with `choice='changed'`;
  - `GET /place/maps` from a non-local client with no token → 401/403;
  - `PATCH /place/marks/{id}` with `{"issue": {"alert_id": A}, "words": ""}` → 422 "Say what you did, in your own words.";
    with words → one `actions` row `stage='acted', alert_id=A, choice='place.mark:<id>'`; with `{"issue": null}` →
    that row deleted; deleting the drawing after tying keeps the acted row;
  - tying to an issue the Done button would refuse (decision required first) → the same status and sentence
    `POST /actions` gives for it.

- [ ] **Step 2: Run** both → FAIL.

- [ ] **Step 3: Implement** `app/maps.py`. `check_feature` validates kind↔geometry type, point counts, and an area's
  ring with a pure segment-intersection test (no shapely; O(n²) is fine at hand-drawn sizes,
  `# ponytail: O(n²) crossing check, fine below a few hundred corners`). Inserts/updates compute `length_m` (line:
  `ST_Length(geom::geography)`) and `area_m2` (area: `ST_Area(geom::geography)`) in the same statement. `DELETE
  /place/maps/{id}` needs `?confirm=<name>` matching the map's name, else 409 with "Deleting needs the map's name.".
  Agent maps (`agent` set) are refused for household edits in this PR (403 "This is <agent>'s map.") so PR 3 only adds
  writers. `tie` writes the row directly (not through `POST /actions`); it reads the issue's mode the way the Done
  button's row carries it (`alert_id` or `event_id`) and reuses the decision-required check from `app/main.py`'s
  `/actions` handler by extracting it into a small function both call. Every write calls `ledger()` with verbs `drew`,
  `changed`, `deleted`, `downloaded:<fmt>` (Task 3), `shared`/`unshared` (Task 4).

- [ ] **Step 4: Run** → PASS; `make lint` → ok (`app imports, N routes` rises by the new routes).

- [ ] **Step 5: Commit** `maps: named maps and drawings on the node, in the ledger, and as an issue's acted step`.

### Task 3: Downloads: GeoJSON, KML, DXF

**Files:**
- Modify: `app/maps.py`, `tests/test_maps.py`, `tests/test_maps_pg.py`

**Interfaces:**
- Consumes: Task 2's tables and `PALETTE`.
- Produces: `feature_collection(map_row: dict, marks: list[dict], node: str) -> dict`; `to_kml(fc: dict) -> str`;
  `utm_epsg(lon: float, lat: float) -> int`; `to_dxf(features_xy: list[dict], epsg: int) -> str` where each item is
  `{kind, label, note, colour, xy}` and `xy` is the geometry's coordinates already in metres; routes `GET
  /place/maps/{id}.geojson|.kml|.dxf`, each served with `Content-Disposition: attachment;
  filename="<node>-<map-slug>-<YYYY-MM-DD>.<ext>"`, each writing a `downloaded:<ext>` ledger row.

- [ ] **Step 1: Write the failing tests** (pure, in `tests/test_maps.py`):

```python
assert utm_epsg(115.167, -8.819) == 32750 and utm_epsg(2.17, 41.39) == 32631 and utm_epsg(-179.9, 10) == 32601
fc = feature_collection({"id":3,"name":"Garden plan","owner":"Tomas"}, [mark_row(kind="area", label='Rain <garden> & "pond"', colour=3)], "bayu-ungasan")
assert fc["schema"] == "planetai.place.map/v0" and fc["map"] == "Garden plan" and fc["node"] == "bayu-ungasan"
p = fc["features"][0]["properties"]; assert set(p) == {"kind","label","note","colour","colour_hex","length_m","area_m2","image","drawn_by","updated_at"}
assert p["colour_hex"] == PALETTE[3][0]
k = to_kml(fc); ET.fromstring(k)                      # valid XML with the hostile label
assert "Rain &lt;garden&gt; &amp;" in k
d = to_dxf([{"kind":"area","label":"two\nlines","note":"","colour":3,"xy":[[500000,9025000],[500010,9025000],[500010,9025010],[500000,9025000]]}], 32750)
assert d.startswith("999\nEPSG:32750") and "\nAREAS\n" in d and "two lines" in d and d.rstrip().endswith("EOF")
assert d.count("\nPOLYLINE\n") == 1 and d.count("\nVERTEX\n") == 4
```

  And in `tests/test_maps_pg.py`: `.dxf` of a map at the node's point returns coordinates near `(500000±10000,
  9.02e6±0.05e6)` for node #1's `NODE_LAT/NODE_LON`; `.kml` and `.geojson` round-trip the feature count.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement.** `utm_epsg`: zone `int((lon + 180) // 6) + 1` clamped to 1–60, `32600 + zone` north,
  `32700 + zone` south. The `.dxf` route queries `ST_AsGeoJSON(ST_Transform(geom, %s))` with that EPSG from the
  node's own `NODE_LON/NODE_LAT`. `to_dxf` writes R12 sections HEADER (with a `999` comment `EPSG:<code>, metres`),
  TABLES (LAYER entries `MARKERS`, `LINES`, `AREAS`, `NOTES`), ENTITIES (`POINT`; `POLYLINE`+`VERTEX`+`SEQEND`, flag
  1 for areas; `TEXT` at the first vertex for labels and notes, newlines collapsed to spaces), `EOF`. `to_kml` builds
  with `xml.etree.ElementTree` and embeds each geometry from `ST_AsKML(geom)`. `image` is the capture id only.

- [ ] **Step 4: Run** → PASS.

- [ ] **Step 5: Commit** `maps: GeoJSON, KML and DXF in the node's UTM metres`.

### Task 4: Sharing upstream

**Files:**
- Modify: `app/maps.py`, `app/auth.py:86` (`_CHILD_WRITES`), `app/main.py` (schedule `maps.push_maps`), tests

**Interfaces:**
- Consumes: `PARENT()`, `PARENT_TOKEN()`, `AGG_TOKEN`, `NODE` from `app/main.py`/`app/auth.py`; Task 3's
  `feature_collection`.
- Produces: `PATCH /place/maps/{id}` with `{"shared": true, "confirm": "exact"}`; `push_maps() -> None` run every 60 s;
  `POST /place/maps/received` (child writes); received maps listed read-only by `GET /place/maps` with `from_node`.

- [ ] **Step 1: Write the failing tests** (`tests/test_maps_pg.py`, with `httpx` posts monkeypatched to a recorder):
  - `PATCH {"shared": true}` without `confirm` → 409 with the warning sentence (exact copy):
    "Sharing sends every drawing in this map, at its exact place, with its labels, notes and measures, to the node
    upstream, where the people holding its token can see it. Press Share again to send it.";
  - with `PARENT` unset → 409 "There is no node upstream to share with. Set PARENT in Set up first.";
  - shared + changed twice in 30 s → one `put` sent at the next `push_maps()`; unshare → one `delete`;
  - recorder answers 404 → `share_error = "The node upstream does not take maps yet."`, `shared` stays true, no resend
    until `push_tried_at` is an hour old;
  - `POST /place/maps/received` with the parent's `AGG_TOKEN`: `put` creates `from_node='kid', remote_id=7` with its
    features; a second `put` replaces them; `delete` removes the map; a household token is refused; a household
    `PATCH` on a received map → 403 "This map came from kid; it is read-only here.";
  - a drawing added to a shared map inside the house's own res-10 cell (the cell `captures.at_home` uses) holds the
    map: the response carries `warn` "This drawing sits on the house. Press Share again to send the map with it.",
    `share_error` holds that sentence, and `push_maps()` sends nothing for that map until a `PATCH {"shared": true,
    "confirm": "exact"}`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** `push_maps` sends maps where `shared AND (pushed_at IS NULL OR updated_at > pushed_at)`
  and (`share_error IS NULL OR push_tried_at < now() - interval '1 hour'`), and pending deletes (a small
  `place_maps_unshared(map_id, at)` table or a `shared=false AND pushed_at IS NOT NULL` state; builder's choice, test
  pins behaviour). Body `{schema, node, map_id, op, geojson}`. `main.py`: `loop(maps.push_maps, 60, delay=140)`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `maps: a shared map goes to the node upstream, exactly, after a plain warning`.

### Task 5: The daily readings

**Files:**
- Modify: `app/maps.py`, `app/main.py` (schedule), `tests/test_maps_pg.py`

**Interfaces:**
- Produces: `daily_readings() -> None`, run hourly, writing once per local day for sensor `place-gis` (source
  `place`, local, outdoor, kind as core's own derived sensors) the metrics `marks` (count in household maps) and
  `marked_area_m2` (sum of `area_m2` in household maps). PRs 2 and 3 add `cells_fetched` and `tool_runs`.

- [ ] **Step 1: Failing test:** after two drawings, `daily_readings()` twice → one reading per metric for today;
  the values are 2 and the area sum; `packs.public_sql` excludes both (they are `private`), checked by selecting
  through it.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement**, registering the sensor the way `app/bootstrap.py:94` does.
  `main.py`: `loop(maps.daily_readings, 3600, delay=200)`. **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `maps: a private daily count of what was drawn`.

### Task 6: `doors-draw.js`: the geodesic math, the drawing state, the readout

**Files:**
- Create: `app/static/doors-draw.js`, `tests/test_doors_draw.py`
- Modify: `app/main.py` `COMPANIONS` (`:1891`), `app/static/doors.html` (script tag after `doors-cake.js`),
  `tests/all` (line, count → 108)

**Interfaces:**
- Produces, on `window` and `module.exports`:
  - `lengthM(coords: [lon,lat][]) -> number`, `areaM2(ring: [lon,lat][]) -> number`, `perimeterM(ring) -> number`
    (spherical, R = 6371008.8 m);
  - `fmtLen(m) -> string` ("58 m", "1.24 km"), `fmtArea(m2) -> string` ("312 m² · 0.03 ha", "2.4 ha" past 10,000 m²);
  - `drawState(kind: 'marker'|'line'|'area'|'note') -> {kind, pts: []}`; `addPt(s, pt) -> s`; `backPt(s) -> s`;
    `canFinish(s) -> boolean`; `toFeature(s, props) -> GeoJSON Feature | null` (area ring closed);
  - `figure(s, hover?) -> {value: string, unit: string, hint: string}` with the hints of the mockup's `READ` table;
  - `KEYS = [['select','V'],['marker','M'],['line','L'],['area','A'],['note','N'],['image','I']]`.

- [ ] **Step 1: Failing tests** (run the file under node from Python, as `tests/test_doors.py:857` does):

```python
assert abs(lengthM([[115.167,-8.819],[115.168,-8.819]]) - 110.0) < 1.0
assert abs(areaM2([[0,0],[0.001,0],[0.001,0.001],[0,0.001],[0,0]]) - 12364) < 60     # ~111.2 m square at the equator
assert fmtArea(312) == "312 m² · 0.03 ha" and fmtLen(1240) == "1.24 km" and fmtLen(58.4) == "58 m"
s = addPt(addPt(drawState('area'),[0,0]),[0.001,0]); assert not canFinish(s) and toFeature(s, {}) is None
s = addPt(s,[0.001,0.001]); f = toFeature(s, {"label":"x"}); assert f["geometry"]["coordinates"][0][0] == f["geometry"]["coordinates"][0][-1]
assert backPt(s)["pts"] == [[0,0],[0.001,0]]
assert figure(drawState('line'))["hint"].startswith("Press to add a point")
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (pure; no DOM). **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `place: the drawing's math and state, as pure functions`.

### Task 7: Drawing on the screen, and your maps

**Files:**
- Modify: `app/static/doors-placemap.js` (`tools()` at `:493`, `redraw()`, map click/keys handlers),
  `app/static/doors-place.js`, `app/static/doors.html`, `app/static/doors-load.js` (`DOORS_LOCKED`),
  `tests/test_doors.py`

**Interfaces:**
- Consumes: Task 6 exports; Task 2–4 routes; `planetai_actor` from `localStorage` (try/catch).
- Produces: `PM.draw` (`{map, state, sel, colour}`); `window.placeMaps()` re-reads `GET /place/maps` and redraws the
  left column's **your maps** and the lower band's table.

- [ ] **Step 1: Failing tests** in `tests/test_doors.py` (string and node-run checks, the file's existing style):
  - the screen's key column has six keys with `aria-label`s "Select", "Marker", "Line, with distance", "Area, with
    surface", "Note", "Image" and an "Undo", each `aria-pressed`; the old `['inspect'…'png']` list is gone; "From the
    house" is in `#ptools`;
  - `DOORS_LOCKED.test('/place/maps')` and `.test('/place/marks/3')` are true;
  - `#cake` renders **your maps** above `results` with a square dot class `ly map`, then a "New map" button;
  - with no token, the section reads "Your maps are kept on this node. Unlock this screen in Set up to draw." and no
    key is drawn;
  - a label `<img src=x onerror=1>` from `GET /place/maps` renders escaped in the lower band table and the map label;
  - the readout element has `aria-live="polite"`;
  - focus on a key or a drawing is visible on the black screen (the cells' blue outline, as the hour pill uses);
  - the Data door's ledger, given a `stage: 'place'` action, offers a **place** stage filter and renders the row.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**, following the mockup:
  - keys on the screen's left edge (44 px, letter in the corner), the readout beside them (tool, open map, the figure
    from `figure()`, six swatches from the palette, the hint); keyboard shortcuts V M L A N I, ⌘Z/Ctrl+Z, Enter adds
    at the map centre or finishes, Backspace removes the last point, Esc cancels, arrows pan;
  - drawings render as deck.gl layers in the same overlay (so the PNG holds them): area fill at .28 and 2 px stroke,
    dashed lines with per-segment metres, pins, note labels; corners as small squares while drawing or selected;
  - select: tap a drawing → the form under the readout (label, note, colour, image, issue + "what you did"); a corner
    moves with tap-on-corner then tap-on-place, or arrows while selected; save on change via `PATCH`;
  - image key: picker listing captures (`GET /captures?limit=200`) or a new photo through the existing Add-an-image
    dialog posting `POST /captures` with the drawing's point, then `PATCH` the drawing's `capture_id`;
  - your maps: rows switch maps on/off, a row's name opens rename/owner/share/delete; New map prompts a name; the open
    map is the last one drawn in, remembered per browser;
  - delete asks with the map's name and count, typing nothing more than pressing Delete again, and sends `?confirm=`;
  - share: first press shows the exact warning sentence from Task 4 in the row; a second press sends `confirm:"exact"`;
  - lower band left: the open map's table (colour, label, kind, measure, note, image thumbnail, issue); a row selects
    its drawing.
- [ ] **Step 4: Run** `python3 tests/test_doors.py` → PASS; `bash tests/visual/gate.sh` (see memory "run the visual
  gate locally") → exit 0.
- [ ] **Step 5: Commit** `place: draw on the screen, keep it in named maps`.

### Task 8: Download menu, satellite by default, then-and-now below, drone pins

**Files:**
- Modify: `app/static/doors-placemap.js`, `app/static/doors-place.js`, `app/static/doors.html`, `tests/test_doors.py`

- [ ] **Step 1: Failing tests:**
  - the screen's right column holds, in order, "Map only", "Full screen", "Back to this node’s cell", "Download";
  - the download menu lists "Image of the screen · PNG", "For upstream and QGIS · GeoJSON", "For Google Earth, phones
    · KML", "For CAD, in metres · DXF", "Everything on the screen"; the PNG path still reads the canvas;
  - `LAYERS.find(l => l.id === 'imagery')` turns on in `groundRows()` when `G.imagery` (and stays off without it);
  - `.altc` and `#mapalt` are gone from `doors.html`; the lower band's right holds `what changed, year on year` with
    the then-and-now pair, the year arrows and the AlphaEarth hectares line with its `model` word, and bars from
    `place_yearly` (`D` already carries it, or the builder adds it to `buildD`);
  - below zoom 13 a `drone-pins` layer exists with one pin per `PM.meta.layers.drone.mosaics` item at its bbox centre,
    labelled "drone, <gsd> cm, <Mon YYYY>"; pressing one flies to its bbox at zoom 16.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** "Everything on the screen" downloads the PNG and each visible
  map's three files as separate downloads (no zip library: design §11 allows it). A small base switch (satellite ·
  streets · drone) sits bottom right, drone only where `G.drone`. **Step 4: Run** → PASS, gate exit 0.
- [ ] **Step 5: Commit** `place: downloads in four formats, the satellite first, the years below the map, drone pins`.

### Task 9: Folding sides, map only, full screen, the phone

**Files:**
- Modify: `app/static/doors.html` (CSS, markup), `app/static/doors-place.js`, `tests/test_doors.py`,
  `tests/visual/measure.mjs`

- [ ] **Step 1: Failing tests:**
  - each side has a fold button (`aria-expanded`, `aria-label` "Hide the layers"/"Show the layers", "…tools"); a
    folded side is a 36 px strip with its name;
  - `[`, `]`, `\` and `F` toggle left, right, both, full screen (not while typing in an input);
  - the fold state is read and written in `localStorage` inside try/catch (grep: no bare `localStorage.` in the new
    code outside try);
  - full screen calls `requestFullscreen` on the screen element and the key is not drawn when
    `document.fullscreenEnabled` is false;
  - at 760 px and below the keys run as a row along the screen's bottom edge with the readout above them;
  - `measure.mjs` gains panes `place-folded` at 1440 (both folded: the screen is at least 1300 px wide) and checks 390
    keeps the bottom sheet with **your maps** first.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (grid columns on `.bench`; map-only lets the screen take `100vh`
  less the header; `PM.map.resize()` after each fold). **Step 4: Run** → PASS, gate exit 0.
- [ ] **Step 5: Commit** `place: the sides fold, the map takes the window`.

### Task 10: Docs, changelog, design log, node #1

**Files:**
- Modify: `docs/site/dashboard.md` (`## Place`), `CHANGELOG.md` (Unreleased), `tools/build_learn.py` +
  `app/static/learn.json` + `data/docs_site.json` (rebuilt), `README.md` if the docs index lists specs
- External (separate PR, Tomas's yes): `planetai-design/decisions/design-log.md` line for the drawing colours and keys

- [ ] **Step 1:** Write the Place docs section in Tomas's voice: how to draw, keep a map, download it, share it, tie a
  drawing to an issue. Run the avoid-ai-writing pass twice. Rebuild learn/docs (`python3 tools/build_learn.py`).
- [ ] **Step 2:** `make lint` and `bash tests/all` → all green, 108 suites; visual gate exit 0.
- [ ] **Step 3: Commit** `docs: Place drawing and maps`.
- [ ] **Step 4 (needs Tomas's yes):** push, PR, CI green; node #1 on the branch: `planetai update` to a log file
  (never piped), check the schema landed (`\d place_marks`), PACKS_ENABLED/.env/crontab unchanged, then on Place with
  the token at 1440 and 390: satellite on, nothing over the screen, one drawing per key, all four downloads (DXF opened
  in a CAD program at the right size, GeoJSON in QGIS), a drawing tied to an open issue shows as acted in the ledger,
  drone pin where node #1 has a mosaic, sides folded and remembered after reload; one real cycle; `tested: node 1`.
