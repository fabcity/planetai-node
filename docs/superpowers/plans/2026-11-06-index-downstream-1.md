# Index downstream, part 1: the place and its daily read — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A node knows its Fab City Index place, reads that place's Index file and the live registry once a day, and
shows the place's Index indicator in the Place door's figures band.

**Architecture:** A new official code pack, `packs/index`, switched on by its own key `INDEX_PLACE` (the Index slug).
Its `adapter.py` does the daily read and stores the two documents in one table; its `routes.py` serves
`GET /index/place`; the Place door's `figures()` draws one row from it. `planetai place` suggests a place from the
node's coordinates and sets the key.

**Tech Stack:** Python 3 stdlib + httpx + psycopg (as other packs), FastAPI APIRouter, vanilla JS, bash.

**Spec:** `docs/superpowers/specs/2026-11-05-index-downstream-design.md`, §4 and §5 (steps 2 and 3 of §10).

## Global Constraints

- The pack's setting is `INDEX_PLACE` (the spec's `NODE_PLACE`, renamed: an official pack's switch is its own key,
  docs/PACKS.md "Code in official packs"). `NODE_CITY` is untouched.
- `INDEX_URL` defaults to `https://index.fab.city`. The place file is `{INDEX_URL}/api/v0/places/<slug>.json`,
  `format` must be `fci-api-v0`.
- Registry: `https://api.github.com/repos/fabcity/awesome-fabcity-data/commits/main` → `sha`; then
  `https://raw.githubusercontent.com/fabcity/awesome-fabcity-data/<sha>/index.json`. Never fetch a branch URL.
- At most one read per 24 h (`INDEX_REFRESH_HOURS=24`); a failed read keeps the last good body and records the error.
- The node never recomputes a score. It shows the Index file's numbers and its label words as they come.
- No request carries the node's coordinates. (The place slug is public; it is the Index's own key.)
- Every outside read: `https`, timeout 20 s, body cap 8 MB.
- Words on the page follow docs/SPEC_language.md; provenance by stroke (`prov()`), never hue.
- New suite → its `tests/all` line and the count 105 → 106.

## Review Focus

1. **A slug the Index does not know** (typo in Set up): the row must say "not an Index place" and name the slug, not
   draw an empty score. → Task 2 test `test_unknown_slug_is_said`.
2. **A simulated place** (55 of 61): `fci` is null and `fci_range` is `[0, dido]`; the row must show the range, never 0.
   → Task 3 test in `tests/test_index_pack.js` cases.
3. **GitHub down or rate-limited, Index up** (60 unauthenticated calls/h): the place still reads, the registry keeps
   its last copy, then the pinned one, and says which. → Task 2 `test_registry_falls_back`.
4. **Node offline from first start**: no row in `index_reads`; the route answers with `read.ok=false` and the
   pinned registry, the page says "not read yet". → Task 2 `test_never_read`.
5. **Pack switched on with `PACKS_ENABLED` set to a list without `index`**: nothing runs. `planetai place` must add
   `index` to the list. → Task 4 test in `tests/test_cli_place.sh`.

---

### Task 1: The pack, its place list, and the suggestion

**Files:**
- Create: `packs/index/pack.yaml`, `packs/index/README.md`, `packs/index/places.json`, `packs/index/place.py`
- Create: `tools/build_index_places.py` (dev only; regenerates places.json)
- Test: `tests/test_index_pack.py`

**Interfaces:**
- Produces: `place.load() -> list[dict]` (each `{slug, name, country, lat|None, lon|None}`);
  `place.nearest(lat: float, lon: float, places: list[dict], max_km: float = 150) -> dict | None`;
  `place.known(slug: str, places: list[dict]) -> bool`.

- [ ] **Step 1: Generate `places.json`.** `tools/build_index_places.py` reads awesome-fabcity-data `places.yaml` at
  `origin/main` (61 slugs) and the `centers` in `../fci-3-prototype/js/map-geo.js` (53). Output:
  `{"generated": "<date>", "from": [<both paths with sha>], "note": "centres are approximate (map-geo v0) and assert no border", "places": [...]}`, sorted by slug. A place with no centre has `lat`/`lon` null.
- [ ] **Step 2: Write the failing tests** in `tests/test_index_pack.py`:
  - `len(load()) == 61`, and `sum(1 for p in load() if p["lat"] is not None) == 53`.
  - `nearest(41.39, 2.17, P)["slug"] == "barcelona"`; `nearest(-8.8271, 115.15709, P)["slug"] == "bali"`.
  - `nearest(39.89, 4.26, P) is None` (Menorca: nothing within 150 km).
  - `known("barcelona", P)` and not `known("barcelone", P)`.
- [ ] **Step 3: Run:** `PYTHONPATH=/tmp/stub:app python3 tests/test_index_pack.py` → fails (no module).
- [ ] **Step 4: Implement `place.py`** (haversine, stdlib) and `pack.yaml`:
  `id: index`, `name: Fab City Index`, `kind: code`, `switch: [INDEX_PLACE]`, `scales: [community]`, `sources: []`,
  `requires: {node: ">=0.91.0"}`, `env:` comment lines plus `INDEX_PLACE=`, `INDEX_URL=https://index.fab.city`,
  `INDEX_REFRESH_HOURS=24`, `attribution: "Fab City Index, CC BY 4.0, Fab City Foundation; awesome-fabcity-data"`.
  README: what it reads, from where, how often, and that it sends no coordinates.
- [ ] **Step 5: Run the test** → PASS. Add `test_index_pack|PYTHONPATH=/tmp/stub:app python3 tests/test_index_pack.py`
  to `tests/all`, count 106. `make lint` → green (it checks pack manifests).
- [ ] **Step 6: Commit** `index pack: the 61 Index places and the nearest one`.

### Task 2: The daily read

**Files:**
- Create: `packs/index/adapter.py`
- Test: `tests/test_index_pack.py` (append before its `sys.exit`, see memory: tests after sys.exit never run)
- Fixtures: `tests/data/index_place_barcelona_2026-11-06.json`, `tests/data/index_place_accra_2026-11-06.json`,
  `tests/data/registry_index_8099744.json` (saved whole from the live hosts)

**Interfaces:**
- Consumes: `place.known`, `place.load` (Task 1).
- Produces: table `index_reads (what text PRIMARY KEY, sha text, fetched_at timestamptz, ok boolean, error text, body jsonb)`
  with rows `what='place'` and `what='registry'`, created by `ensure(cur)` in the adapter as `packs/place` does;
  `convert(upstream: dict) -> list[dict]` (upstream `index.json` → the node's entry shape: `slug=id`,
  `cell="<Pillar>|<Scale>"` capitalised, every other key kept, `reviews` defaulting to `[]`);
  `read(hc, cur, slug, now) -> dict` (does at most the two reads, writes the rows, returns `{"place": ok, "registry": ok}`);
  `fetch(hc) -> ([], [])` (calls `read` when the last `place` row is older than `INDEX_REFRESH_HOURS`).

- [ ] **Step 1: Write the failing tests** with an `HC` stub (as tests/test_forecast.py) and a fake cursor or a dict store:
  - `test_convert`: `convert(fixture)` has 293 entries, the first has `slug`, and `cell == "Economic|Bioregion"` for `economic/bioregion/exiobase`.
  - `test_reads_place`: Barcelona fixture → stored `place` body `format == "fci-api-v0"`, `ok` true.
  - `test_unknown_slug_is_said`: slug `barcelone` → no HTTP call made, `place` row `ok` false, `error == "not an Index place: barcelone"`.
  - `test_registry_falls_back`: GitHub stub raises → `registry` row keeps the previous body and sha, `ok` false, error set; place still `ok`.
  - `test_wrong_format`: a place body with `format: "x"` → `ok` false, previous body kept.
  - `test_once_a_day`: two `fetch` calls 1 h apart make one set of HTTP calls.
- [ ] **Step 2: Run** → fails.
- [ ] **Step 3: Implement** `adapter.py`. The 8 MB cap reads `Content-Length` and the body length; https is asserted on
  every URL built.
- [ ] **Step 4: Run** → PASS; `bash tests/all` green.
- [ ] **Step 5: Commit** `index pack: read the place's Index file and the registry once a day`.

### Task 3: GET /index/place and the row on Place

**Files:**
- Create: `packs/index/routes.py`
- Modify: `app/static/doors-load.js` (`DOORS_ROUTES` gains `index_place: 'index/place'`; `buildD` passes `index_place: A.index_place || null`)
- Modify: `app/static/doors-place.js` `figures()` (one new `.fr` row above "Index cells")
- Test: `tests/test_index_pack.py` (route shape), `tests/test_doors.py` (the row)

**Interfaces:**
- Consumes: `index_reads` (Task 2), `registry.load()` for the pinned fallback.
- Produces: `GET /index/place` →
  `{"chosen": str, "place": {slug,name,country,territory}|null, "read": {"at": iso|null, "ok": bool, "error": str|null},
    "score": <the file's score>|null, "indicators": [{label, unit, latest: {year, value}, source}],
    "links": {page, report}|null, "registry": {"sha": str, "at": iso|null, "from": "live"|"pinned", "filed_here": int}}`.
  `filed_here` counts registry entries whose `places` holds the slug.

- [ ] **Step 1: Failing tests.** Route: with the Barcelona rows stored, `place.name == "Barcelona"`,
  `registry.from == "live"`, `filed_here == 35`; with no rows, `read.ok is False` and `registry.from == "pinned"`.
  Page (test_doors.py's existing JS lift): `figures()` with a Barcelona `index_place` prints "Barcelona",
  "Partial", "0.567"; with Accra prints "Simulated" and "0 – 0" (the range) and never "FCI 0"; with `null` prints
  "Choose this node's Index place" and the command `planetai place`.
- [ ] **Step 2: Run** → fails.
- [ ] **Step 3: Implement.** The row: name and label on the left with `<small>` "Fab City Index · read <date> ·
  N sources filed for <name> in the registry"; on the right the FCI (or its range) with `prov('partial')` for
  partial/simulated and the first three indicators as `num()` lines with year and unit; the place's page as a link.
  A failed read keeps the last values and adds "last read <date>".
- [ ] **Step 4: Run** → PASS; `bash tests/all`; `make lint`.
- [ ] **Step 5: Commit** `Place: the city's Fab City Index row`.

### Task 4: `planetai place`, and init

**Files:**
- Modify: `bin/planetai` (new `place` subcommand; init calls it after the location step; help text)
- Test: `tests/test_cli_place.sh` (or the existing CLI suite if one covers subcommands; check `tests/all`)

**Interfaces:**
- Consumes: `packs/index/places.json`, `place.nearest` logic (re-done in the CLI's inline python, stdlib, as the
  pilot boxes were).
- Produces: `planetai place` (suggest + confirm), `planetai place <slug>` (set), `planetai place none` (clear).
  Setting goes through the runtime config path (`runtime_set INDEX_PLACE`), and adds `index` to `PACKS_ENABLED`
  when that is a list without it (the helper `packs add` uses, bin/planetai ~1377).

- [ ] **Step 1: Failing test:** with NODE_LAT/LON of Barcelona the suggestion line names "Barcelona"; an unknown slug
  exits 2 with "not an Index place"; `none` clears.
- [ ] **Step 2–4:** implement, run, `bash tests/all`.
- [ ] **Step 5: Commit** `planetai place: choose the node's Fab City Index place`.

### Task 5: Docs, changelog, node #1

- [ ] `docs/PACKS.md` (the pack list), the place docs page under `docs/site/` that describes the figures band, and
  `CHANGELOG.md` Unreleased: one bullet each. Regenerate `data/docs_site.json` if `make lint` asks.
- [ ] Push the branch, open the PR, CI green.
- [ ] Node #1 on the branch: `planetai place bali`, wait one poll, `curl -s localhost:8081/index/place` shows
  `place.slug == "bali"`, `registry.from == "live"`; the Place door shows the row. Back to main after.
- [ ] Commit `docs: the Index place`.
