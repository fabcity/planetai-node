# Energy pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A core `energy` pack: the fossil share of the grid behind a node's cells, with its sources and distances, as
an issue on Now (mockup A). It covers Bali (estimated, a range) and Menorca (measured hourly), and live household solar
through Home Assistant.

**Architecture:** `packs/energy/` is a code pack. Pure modules each do one job: `grids.py` (which grid, which ring),
`osm.py` (what's there), `mix.py` (Bali range), `ree.py` (Menorca hourly), `ha.py` (the house) and `today.py` (the
sun). `adapter.fetch()` puts them together into readings, plus one `out/energy/result.json` that `routes.py` serves at
`GET /energy`. Now draws the energy panel from that route. The issue itself is a terrain-shaped context issue.

**Tech Stack:** Python 3.12 in the container (CLI 3.9 stdlib), httpx, FastAPI, Postgres. Plain JS in
`app/static/doors-now.js` and `mobile.js`. Tests are stdlib `check()` scripts registered in `tests/all`.

**Spec:** `docs/superpowers/specs/2026-11-08-energy-pack-design.md` (read it first; this plan argues from it).

## Global Constraints

- Core pack, `kind: code`, `domain: energy`, `scales: [region]`, `requires: { node: ">=<the release it ships in>" }`.
- Every figure carries a provenance word, `measured` or `estimated`, and the card shows it.
- Bali's headline is a range (`fossil_share_low_pct`, `fossil_share_high_pct`) while the Java share is unpublished.
  `fossil_share_pct` is used only where one measured figure exists. A measured grid also writes low = high = the
  value, so `fossil_share_low_pct` is present on every node with a grid, and the issue reads that one.
- The headline covers the trailing 12 months on both nodes. Menorca adds `fossil_share_now_pct`.
- Household readings are `role: private` in `channels.yml`. They never leave the machine (packs.public_sql).
- Distances are straight lines. Overpass requests send the User-Agent `planetai-node/energy (https://planetai.fab.city; info@fab.city)`.
- A node outside every grid shows the `none` sentence and never borrows a neighbour's figure.
- Attribution: `© OpenStreetMap contributors, ODbL, via Overpass`, plus each mix source's own line.
- Sentences in en/id/es. id and es are marked "ASSISTANT-WRITTEN, not read by a native speaker", as in terrain.
- Public copy (README, docs page, sentences) is written in Tomas's voice and passes the avoid-ai-writing skill twice
  before the PR.
- Tests end in `sys.exit(1 if fails else 0)`. Nothing is appended below it (tests-after-sys-exit trap).
- Local Python is 3.14 and CI is 3.12, so run new suites in a uv 3.12 venv before pushing.

## Review Focus

1. **The mix source is down:** REE answered 400/502 on 8 Nov. A failed fetch keeps the last good figure and its age,
   and never writes 0%. Task 4 pins it.
2. **The node is outside every grid:** a Barcelona or Singapore node gets the `none` sentence, no number and no
   empty bar. Task 2 pins it.
3. **An OSM plant has no capacity or an odd unit** (`plant:output:electricity=yes`, `100 kW`, `1,5 MW`). It is listed
   without MW and left out of the capacity sums, never parsed as 0 or 1. Task 2 pins it.
4. **Home Assistant is unreachable or returns `unavailable`/`unknown`:** that hour has no household line, rather than
   a household on 100% grid. Task 8 pins it.
5. **A first fetch with a year of REE to backfill** must not hammer REE. It goes month by month, resumes from a state
   file after a failure, and the headline says "N months so far" until 12 are in. Task 4 pins it.

---

### Task 1: Sources, licences and `grids.yml`

Data and reading, no code. Later tasks test against what this task writes down.

**Files:**
- Create: `packs/energy/grids.yml`, `packs/energy/README.md` (the sources section only, for now)
- Create: `packs/energy/tests/fixtures/ree-baleares-<date>.json`, `ree-peninsular-<date>.json`
- Existing: `packs/energy/tests/fixtures/overpass-bali-2026-11-08.json`, `overpass-menorca-2026-11-08.json` (read 8 Nov, ODbL)

**Interfaces:**
- Produces: `grids.yml`, a list of grids with this shape (values in `<>` are found in this task):

```yaml
- id: bali
  name: PLN Bali system
  polygon: [[lon, lat], ...]          # Bali island and its near islands, closed ring
  rings:
    city: [[lon, lat], ...]           # Denpasar + Badung, drawn by hand (my call, open to Tomas)
  mix: { kind: estimated, method: capacity-factors }
  capacity_factors: { coal: <>, gas: <>, oil: <>, solar: <>, wind: <> }   # assumed; README says where from
  links:
    - { name: Java–Bali cable, at: Cable Head Gilimanuk, rated_mw: <>, fossil_share: <>, ring: beyond,
        source: "<Ember Indonesia <year>, CC BY 4.0>" }
  demand_mw: <>                        # Bali average demand, with its source
- id: balearic
  name: REE Balearic system
  polygon: [[lon, lat], ...]          # Mallorca, Menorca, Ibiza, Formentera
  rings:
    city: [[lon, lat], ...]           # Menorca island
    region: [[lon, lat], ...]         # the Balearic Islands
  mix: { kind: measured, source: ree, geo_limit: baleares, geo_id: 8 }
  links:
    - { name: Mallorca–peninsula link, ring: beyond, mix_from: { source: ree, geo_limit: peninsular, geo_id: 8741 } }
```

- [ ] **Step 1: Read REE's reuse terms** (ree.es legal notice for REData) and quote the sentence that grants reuse.
  If the terms fail the open rule, set `balearic.mix.kind: estimated`, stop, and tell Tomas before going on.
- [ ] **Step 2: Capture REE responses** once the API answers: `generacion/estructura-generacion` for `baleares` and
  `peninsular`, `time_trunc=hour`, one full day each. Save them as fixtures. Record the `geo_id` the response carries
  (8741 for peninsular is from memory and unchecked).
- [ ] **Step 3: Read Ember's yearly Indonesia electricity data** (CC BY 4.0). Record the latest year's fossil share
  as `links[0].fossil_share`, with the year, labelled a proxy for Java.
- [ ] **Step 4: Find the Java–Bali cable's rated MW and Bali's average demand,** from a source whose licence allows
  quoting. If none is found, write `rated_mw: ~`. Task 3 then gives the high end as "not known", and the card says
  so. A guessed number is not allowed.
- [ ] **Step 5: Settle Nusa Penida:** is it connected to Bali's main grid (submarine cable) or a separate system?
  Draw `bali.polygon` with or without it, and say which in the README.
- [ ] **Step 6: Write the capacity factors** with their source (an open national or IEA/IRENA figure). Where none is
  open, use the value and mark it `assumed` in the README.
- [ ] **Step 7: Commit**

```bash
git add packs/energy/grids.yml packs/energy/README.md packs/energy/tests/fixtures/
git commit -m "energy: grids.yml for Bali and the Balearics, fixtures, sources read"
```

Owed outside this repo, and asked for before opening: awesome-fabcity-data entries for REE REData and Ember
Indonesia, each with its licence quoted.

### Task 2: Which grid, which ring, what's there (`grids.py`, `osm.py`)

**Files:**
- Create: `packs/energy/grids.py`, `packs/energy/osm.py`
- Test: `tests/test_energy.py` (one suite for the whole pack, sections per module)

**Interfaces:**
- Produces:
  - `grids.load(path: Path | None = None) -> list[dict]`
  - `grids.grid_for(lat: float, lon: float, gs: list[dict]) -> dict | None`
  - `grids.ring_for(lat: float, lon: float, g: dict) -> str` (`'city'`, `'region'`; a link's sources are `'beyond'`)
  - `osm.QUERY: str` (format keys `s, w, n, e`)
  - `osm.parse(doc: dict) -> list[dict]`. Each source is `{"name", "kind": "plant"|"substation"|"cable_head",
    "fuel": str|None, "fossil": bool|None, "mw": float|None, "lat", "lon"}`.
  - `osm.mw(tag: str | None) -> float | None`
  - `osm.near(sources: list[dict], lat: float, lon: float) -> list[dict]`: adds `km`, sorted nearest first

- [ ] **Step 1: Write the failing tests**

```python
g = G.load()
check(G.grid_for(-8.8161, 115.1635, g)["id"] == "bali", "node #1's cell is on the Bali grid")
check(G.grid_for(39.9493, 4.0500, g)["id"] == "balearic", "mahon1 is on the Balearic grid")
check(G.grid_for(41.39, 2.17, g) is None, "Barcelona is on no grid in grids.yml: no figure, no fallback")
check(G.ring_for(39.9493, 4.0500, G.grid_for(39.9493, 4.0500, g)) == "city", "mahon1 sits in Menorca's city ring")
check(O.mw("380 MW") == 380.0 and O.mw("100 kW") == 0.1 and O.mw("1,5 MW") == 1.5, "MW units")
check(O.mw("yes") is None and O.mw(None) is None, "no capacity is None, never 0")
bali = O.parse(json.load(open(FIX / "overpass-bali-2026-11-08.json")))
plants = [s for s in bali if s["kind"] == "plant"]
check(len(plants) == 19, f"19 plants in Bali on 8 Nov, got {len(plants)}")
check(any(s["kind"] == "cable_head" and "Gilimanuk" in s["name"] for s in bali), "the Java cable head is a cable_head")
n = O.near(bali, -8.816082625619444, 115.16354382246635)
check(n[0]["name"] == "GIS Pecatu" and abs(n[0]["km"] - 2.4) < 0.1, "nearest is GIS Pecatu, 2.4 km")
big = next(s for s in n if s["kind"] == "plant" and (s["mw"] or 0) >= 100)
check("Pesanggaran" in big["name"] and abs(big["km"] - 12.0) < 0.2, "nearest large plant is Pesanggaran, 12 km")
men = O.parse(json.load(open(FIX / "overpass-menorca-2026-11-08.json")))
check(any(s["fuel"] == "oil" and s["mw"] == 270.0 and s["fossil"] for s in men), "Maó's oil plant, 270 MW, fossil")
```

- [ ] **Step 2: Run** `PYTHONPATH=/tmp/stub:app python3 tests/test_energy.py`. Expected: FAIL (no module).
- [ ] **Step 3: Implement.**
  - Point-in-polygon is ray casting in stdlib, with no shapely.
  - `km` is haversine, R = 6371.
  - Fuels in `{coal, gas, oil, diesel}` are fossil, and `{solar, wind, hydro, geothermal, biomass}` are not; any
    other fuel is `None`.
  - A substation whose name starts with `Cable Head` is a `cable_head`.
  - `QUERY` asks for `power=plant|substation`, `power=generator` with `generator:source`, and
    `power=line|cable|minor_line`, with `out tags center;`.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `energy: grids and OSM sources, with node #1's distances`

### Task 3: Bali's range (`mix.py`)

**Interfaces:**
- Consumes: `osm.parse` sources, a grid dict from `grids.load`
- Produces: `mix.estimate(sources: list[dict], g: dict) -> dict` with keys `low`, `high` (fractions 0–1, `high` may be
  `None`), `mid`, `island`, `import_max` (fraction or `None`), `method: "capacity-factors"`, `kind: "estimated"`,
  `split: {"city": f, "region": f, "beyond": f}`

Algorithm (fixed by the spec, §5.3):

```
island = Σ mw·cf[fuel] over fossil plants inside g.polygon / Σ mw·cf[fuel] over all plants with mw and a known fuel
import_max = min(1, Σ link.rated_mw / g.demand_mw)    (None if any rated_mw or demand_mw is null)
f(j) = (1 - j)·island + j·link.fossil_share
low, high = sorted(f(0), f(import_max)); mid = (low + high) / 2      (high None when import_max None)
split: in-island generation by each plant's ring, times (1 - j_mid); beyond = j_mid, with j_mid = import_max / 2
```

- [ ] **Step 1: Write the failing tests** against a synthetic grid, so they don't depend on Task 1's values:

```python
g = {"polygon": [[0,0],[0,10],[10,10],[10,0],[0,0]], "rings": {"city": [[0,0],[0,5],[5,5],[5,0],[0,0]]},
     "capacity_factors": {"coal": 0.6, "solar": 0.2},
     "links": [{"rated_mw": 100, "fossil_share": 0.8, "ring": "beyond"}], "demand_mw": 400}
src = [{"kind": "plant", "fuel": "coal", "fossil": True, "mw": 300, "lat": 2, "lon": 2},
       {"kind": "plant", "fuel": "solar", "fossil": False, "mw": 100, "lat": 7, "lon": 7},
       {"kind": "plant", "fuel": "coal", "fossil": True, "mw": None, "lat": 3, "lon": 3}]
e = M.estimate(src, g)
check(abs(e["island"] - 180/200) < 1e-9, "island share is 180 of 200 MW-weighted")
check(abs(e["import_max"] - 0.25) < 1e-9, "100 MW cable against 400 MW demand")
check(abs(e["low"] - 0.875) < 1e-9 and abs(e["high"] - 0.9) < 1e-9, "range 87.5–90%")
check(abs(sum(e["split"].values()) - 1) < 1e-9, "the ring split sums to one")
g2 = dict(g, demand_mw=None); e2 = M.estimate(src, g2)
check(e2["high"] is None and e2["import_max"] is None, "an unknown cable rating gives no high end, never a guess")
```

- [ ] **Step 2: Run.** Expected: FAIL. **Step 3:** implement. **Step 4:** run, PASS.
- [ ] **Step 5:** add a node #1 check on the real fixture and grids.yml: `0.85 < e["low"] <= 1`. That's a sanity floor,
  not a pinned value.
- [ ] **Step 6: Commit** `energy: Bali's fossil share as a range`

### Task 4: Menorca measured (`ree.py`)

**Interfaces:**
- Produces:
  - `ree.URL: str`
  - `ree.parse(doc: dict) -> list[tuple[datetime, float, float]]`: `(hour, fossil_mwh, total_mwh)`. Fossil is
    every series REE types as non-renewable, minus storage consumption if REE reports it as negative.
  - `ree.share(rows) -> float | None`
  - `ree.months_to_fetch(have: set[str], today: date) -> list[str]`: the `YYYY-MM` keys of the trailing 12 months
    not yet held, oldest first
  - `ree.fetch(hc, state: dict, today: date) -> dict`: updates `state["months"]`, fetches at most 3 months a call,
    and returns `{"value", "now", "months", "as_of", "kind": "measured"}`, or the last good state with `stale: True`
    after an error.
  - The peninsular link: the hours' imports count at that hour's peninsular share (`parse` of the peninsular fixture).
  - The ring split for Menorca: `beyond` is the link's import share. REE reports the Balearic system as one, so
    `city` (Menorca) against `region` (the rest of the islands) is split by OSM capacity inside each ring polygon, and
    the route marks that split as estimated, even though the headline is measured.

- [ ] **Step 1: Write the failing tests** with the Task 1 fixtures:

```python
rows = R.parse(json.load(open(FIX / "ree-baleares-<date>.json")))
check(len(rows) == 24, "one day is 24 hours")
check(all(0 <= f <= t for _, f, t in rows), "fossil never exceeds total")
check(R.months_to_fetch(set(), date(2026, 11, 8))[0] == "2025-12", "the trailing year starts December 2025")
check(R.months_to_fetch({"2025-12", "2026-01"}, date(2026, 11, 8))[0] == "2026-02", "held months are skipped")
class Down:                       # REE down, as on 8 Nov
    def get(self, *a, **k): raise RuntimeError("502")
st = {"months": {"2026-10": [0.4, 600.0, 1500.0]}, "last": {"value": 0.4, "as_of": "2026-11-07T23:00Z"}}
out = R.fetch(Down(), st, date(2026, 11, 8))
check(out["stale"] and out["value"] == 0.4, "a failed fetch keeps the last figure and says it is stale, never 0")
check(out["months"] == 1, "headline says how many months it holds until twelve are in")
```

- [ ] **Step 2:** run, FAIL. **Step 3:** implement. The state file is `out/energy/ree.json`, like fire's `_state_file`.
  Request one month per call at `time_trunc=hour`.
- [ ] **Step 4:** run, PASS. **Step 5: Commit** `energy: Menorca's hourly mix from REE, a trailing year`

### Task 5: The pack, the issue and the readings (`adapter.py`, `pack.yaml`, `issue.yml`)

**Files:**
- Create: `packs/energy/adapter.py`, `pack.yaml`, `issue.yml`, `channels.yml`
- Modify:
  - `tests/all`: the `test_energy` line, and bump the count sentence;
  - `update.sh` 5d: the `energy:energy` pair;
  - `docs/DOMAINS.md`: the energy row, and remove "energy" from "Not written yet";
  - `docs/PACKS.md`: the table row, and "Twenty-five ship" becomes "Twenty-six";
  - `config/rules.yml` or `check_rules` vocab, only if a lint asks.

**Interfaces:**
- Consumes: Tasks 2–4
- Produces:
  - `adapter.fetch(hc) -> (list[dict], list[tuple])`, with sensor `energy-grid` (`kind: model`, `scale: region`,
    `local: False`, `cadence: PT1H`, meta with attribution, grid id, provenance and method).
  - Metrics: `fossil_share_pct` (measured only), `fossil_share_low_pct`, `fossil_share_high_pct`,
    `fossil_share_now_pct` (measured only), `substation_km`, `large_plant_km`, `import_share_max_pct`, `grid_months`.
  - `adapter.result() -> dict`, which writes and reads `out/energy/result.json`, the body `GET /energy` serves (Task 6).
  - OSM refreshes every `ENERGY_REFRESH_DAYS=30`. The mix refreshes every `ENERGY_POLL_HOURS=6`.

`issue.yml` keys: `key: energy`, `kind: context`, `metric: fossil_share_low_pct` (present on every node with a grid) for the dial's slot (the doors draw
the panel instead, Task 7), `unit: "%"`, `dp: 0`, `line: ~`, and distances region-only `from: observations`,
`sensor_id: energy-grid`. Readouts are the metrics above, with en/id/es labels. Sentences: `context`,
`context_plain`, and `none` ("This node is on no grid the energy pack knows yet: add it to packs/energy/grids.yml.").

- [ ] **Step 1: Write the failing tests:**
  - `fetch()` with a stub `hc` that replays the fixtures returns `energy-grid` readings that include
    `fossil_share_low_pct`, with no `fossil_share_pct`, for node #1's point;
  - it returns `fossil_share_pct`, `fossil_share_now_pct`, and `fossil_share_low_pct == fossil_share_high_pct` for mahon1's point;
  - it returns `([], [])` for Barcelona;
  - `issues.load()` finds `energy` with `kind == "context"` and `line is None`.
- [ ] **Step 2:** run, FAIL. **Step 3:** implement, following terrain's `fetch`/`result()` shape.
- [ ] **Step 4:** `make lint` and the suite PASS, and the `tests/all` count matches.
- [ ] **Step 5: Commit** `energy: the pack and its issue`

### Task 6: `GET /energy` (`routes.py`)

**Interfaces:**
- Consumes: `adapter.result()`
- Produces: `GET /energy`, answering 404 while the pack is off (the node's own rule). Body:

```json
{"grid": "bali", "kind": "estimated", "method": "capacity-factors", "months": null,
 "share": {"low": 0.95, "high": 0.98, "value": null, "now": null, "stale": false, "as_of": "..."},
 "bar": [{"label": "coal", "fossil": true, "share": 0.31, "hatched": false},
         {"label": "Java cable", "fossil": true, "share": 0.25, "hatched": true, "note": "share not published"}],
 "sources": [{"name": "GIS Pecatu", "kind": "substation", "fuel": null, "mw": null, "km": 2.4, "ring": "city"}],
 "today": {"sun_kwh_m2": 5.8, "roof_kwh": 8.7, "use_kwh": 9.0, "measured": false},
 "household": null, "attribution": ["© OpenStreetMap contributors, ODbL, via Overpass", "..."]}
```

- `sources` is cut to the nearest substation, then every plant with `mw >= 1`, then each link. A household's line is
  served only to a reader holding the admin token, through the same `_shows_private` gate `/observations` uses.

- [ ] **Steps:** failing test (TestClient: 404 with the pack off; with it on, the body keys above; `household` is
  `null` without the token even when HA rows exist), implement, PASS, commit `energy: GET /energy`.

### Task 7: The panel on Now (`doors-now.js`, `mobile.js`)

**Files:**
- Modify: `app/static/doors-now.js` (`drawNow`), `app/static/mobile.js`, `app/static/doors.html` (one container)
- Test: `tests/test_doors_energy.py` (the lift-and-run pattern of `test_doors_draw`; JSON goes through a temp file,
  never argv, because of the 128 KB E2BIG on Linux CI)
- Visual: `tests/visual/rich-fixture.json` gets an `energy` issue, and the baseline is re-measured

**Interfaces:**
- Consumes: `GET /energy` (Task 6)
- Produces: `drawEnergy(el: Element, E: object): void` in `doors-now.js`. `drawNow()` calls it when
  `S.issue === 'energy'`, in place of `dayWeek` on `#svg` and `#figfoot`. The issue row in `#rows` stays.

Layout per mockup A (`docs/superpowers/specs/2026-11-08-energy-mockup.html`):
- the headline, `95–98%` or `41%`, in `--d-energy`, with `data-num`/`data-cmp` on every numeral;
- the sentence;
- the bar (hatched segments via a CSS `repeating-linear-gradient`);
- the sources list;
- the Today box;
- the provenance line, using the existing `prov()` words (`model` for estimated, `live` for measured).

- [ ] **Step 1: Failing tests:**
  - an estimated body renders `95–98%` and a hatched segment;
  - a measured body renders one figure and "right now";
  - a body with `share.high == null` renders `≥95%` and "the Java share is not known";
  - an empty `sources` renders the none sentence and no bar.
- [ ] **Step 2–4:** implement, then `bash tests/visual/gate.sh` locally. Run it locally, because string tests have
  passed a doors file that never booted.
- [ ] **Step 5: Commit** `energy: the panel on Now`

### Task 8: The household through Home Assistant (`ha.py`)

**Interfaces:**
- Produces:
  - `ha.state(hc, url: str, token: str, entity: str) -> float | None`: `GET {url}/api/states/{entity}` with header
    `Authorization: Bearer {token}`. Returns `None` for `unavailable`, `unknown`, a non-number, or any error.
  - `ha.kwh(samples: list[tuple[datetime, float]]) -> float`: trapezoid over W samples inside one hour, then ÷1000.
  - `ha.share(roof_kwh: float, grid_kwh: float, grid_fossil: float) -> float | None`:
    `grid_kwh / (roof_kwh + grid_kwh) * grid_fossil`, or `None` when both are 0.
- Settings in `pack.yaml` `env:`: `ENERGY_HA_URL`, `ENERGY_HA_TOKEN`, `ENERGY_HA_SOLAR`, `ENERGY_HA_GRID`,
  `ENERGY_HA_BATTERY`. `secrets: [ENERGY_HA_TOKEN]`.
- Readings on sensor `energy-home` (`local: True`, `indoor: False`, `kind: sensor`): `home_roof_w`, `home_grid_w`,
  `home_battery_w` every 5 minutes, and hourly `home_roof_kwh`, `home_grid_kwh` and `home_fossil_pct`. Every one is
  `role: private` in `channels.yml`.

- [ ] **Step 1: Failing tests** with a recorded `/api/states` body (HA's documented shape, saved as a fixture):
  - `state()` reads `"3120"` as 3120.0, `"unavailable"` as None, and a 401 as None;
  - `kwh()` of a constant 1000 W over the hour is 1.0;
  - `share(3, 1, 0.97)` is 0.2425;
  - `share(0, 0, 0.97)` is None;
  - `packs.public_sql` leaves out a `home_grid_kwh` row (the channel role check).
- [ ] **Step 2–4:** implement, PASS. **Step 5: Commit** `energy: the household, live through Home Assistant`

Ships proven on recorded responses only, because no house in the fleet has solar in HA (Tomas, 8 Nov). The PR says
so.

### Task 9: Today (`today.py`)

**Interfaces:**
- Produces: `today.box(sun_w_m2_hourly: list[float], panel_kw: float, use_kwh: float | None,
  roof_kwh_measured: float | None) -> dict`, returning `{"sun_kwh_m2", "roof_kwh", "use_kwh", "measured"}`.
  - `sun_kwh_m2 = Σ W/m² ÷ 1000` over today's hours.
  - `roof_kwh = roof_kwh_measured` if one is given, else `panel_kw × sun_kwh_m2 × PR`, with `PR = 0.75`
    (a `ponytail:` comment says it's a typical performance ratio, with the knob `ENERGY_PANEL_PR`).
- Reads today's `fc_shortwave` from `forecast-om` rows in the node's own database.
- Settings: `ENERGY_PANEL_KW=2`, `ENERGY_HOUSE_KWH_DAY=9`, `ENERGY_PANEL_PR=0.75`. The README marks all three as
  placeholders.

- [ ] **Steps:** failing tests (`box([0]*6+[1000]*6+[0]*12, 2, 9, None)["roof_kwh"] == 9.0`; a measured roof wins;
  no forecast rows gives `sun_kwh_m2: None` and no roof line), implement, PASS, commit `energy: today's sun on the roof`.
- [ ] **Check on node #1** that `forecast-om` writes `fc_shortwave` there. Its forecast is BMKG, and Open-Meteo's
  limit is per IP. If it doesn't, the box shows use only and says why.

### Task 10: The Place map

**Files:** `app/static/doors-cake.js` (the `built` row), `app/static/doors-placemap.js` (a layer)

**Interfaces:**
- Consumes: `GET /energy` `sources` (with `lat`/`lon` added to the route body in this task) and the lines. Add
  `GET /energy/lines`, returning GeoJSON LineStrings for `power=line|cable` inside the grid, simplified to about 50 m.
- Produces:
  - in the `built` row, a line `N plants, M substations on this grid · nearest X km`;
  - a map layer of plants (sized by MW, `--d-energy`), substations and lines;
  - per seven-cell numbers: MW generated inside each cell, plus the household's kW when the token is held.

- [ ] **Steps:** failing test (cake line text from a fixture body; the seven-cell sum on the Bali fixture is 0 MW for
  node #1's cells, since no plant is within them), implement, visual gate, commit `energy: the grid on the Place map`.

### Task 11: The flows note, docs and the voice pass

- [ ] Amend `packs/flows/resources.yml`'s `electricity` note to the text in spec §5.7, if that file is on main;
  otherwise leave it to the flows PR and say so in this PR.
- [ ] Finish `packs/energy/README.md`: where each number comes from, the capacity-factor assumptions, the
  placeholders, and how to add a grid.
- [ ] Add a docs page or a packs page entry in the site repo (`fabcity/planetai`). That's a separate PR, asked for
  before opening.
- [ ] Run the avoid-ai-writing skill twice over the README, the sentences and the PR text, with Tomas's voice as the
  target.
- [ ] Commit `energy: README, docs, flows note`

### Task 12: Node #1, then the PR

- [ ] CI green on the branch.
- [ ] Node #1 on the branch:
  - `energy` added to the `PACKS_ENABLED` and `NODE_ISSUES` settings rows (PUT /settings with the admin token);
  - save the old rows first, as for paddy.
- [ ] `planetai run energy fetch` on node #1. Read `/energy` and the Now panel. Check that the headline is a range, and
  that Pecatu is at about 2.4 km from the node's own `.env` point, not the cell centre.
- [ ] Open the PR with:
  - `tested: node 1`;
  - owed: the Menorca measured path on `mahon1` (ask Lucas), and the HA path on a house with panels;
  - the REE licence quote.
- [ ] Never pipe `planetai update` into grep.
