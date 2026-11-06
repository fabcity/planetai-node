# Place, light GIS: drawing, named maps, the 7 cells

*Asked, 4 November 2026, by Tomas, after Part A of `docs/SPEC_place_microgis.md` merged (#376): "the place tab and the
new micro GIS needs a deep revision … using the GIS example I gave you" (RustGIS). Then: "when the base Satellite is
enabled, it loads on top of the map area the yearly change we did with alpha earth, that should not be there, it should
be in the bottom, with all the indicators that explain what changed during the years"; "We should have more options in
the map, like create an area, colour it, some light GIS capabilities"; "I might want to save a location image, to
indicate where I want to do an intervention. Also, please load the satellite base as default … add a way to contribute
to OSM, as well as adding the built areas identified with the satellite analysis, which we should be able to do by
cells, and expand up to 7 cells according the the design of this node. Also, indicate where the drone images are when
there is no enough zoom, a pin could help"; "Some anotation in the map is good, distance and area calculator help, add
some basic markers, store them in different maps"; "It should be compatible with upstream nodes, if there is a larger
GIS capability by the community/fablab node"; "at this level, only one token"; "it should be possible to download an
image or the geoJson, or any other GIS compatible file, as well as CAD (if possible)"; on the side columns: "should be
possible to hide, or collapse … Recommend what is better". Mockup approved: "allgood, go ahead". Then, on running
tools: "the local model should be able to launch it too, or connect it via mcp with your agent should be possible, so
there are two ways to work with it"; on agents drawing: "yes they should be able to draw. Also, all the local GIS work
should be also recorded as actions, and data in our logs"; on whether a drawn intervention counts as acting on an open
issue: "yes, it should".*

**Status: proposed 4 November 2026. Nothing is built.** This design takes over Part B of `docs/SPEC_place_microgis.md`
(its steps 2 and 3: the tool registry, the Run panel, the agent, the local model on node #1). Where the two differ,
this one holds; §6 names each change. It is built as three pull requests (§13), each run on node #1 before it merges. The approved mockup is `2026-11-04-place-light-gis-mockup.html` beside this
file: it is the layout authority for §4 (open it in a browser; its figures are placeholders).

## 1 · Why

Part A made Place a place to look: McHarg's layers in order, a black screen, the house's inside gone. Tomas wants to
mark things on it too: where a rain garden could go, how long a hose run is, which tree to plant where, with a photo
of the spot. He also wants the satellite's view first, the yearly change explained below the map instead of over it,
and the work the node already does on missing buildings turned into something he can act on in OpenStreetMap.

This stays a light GIS for one house. Overlays, buffers, topology and the heavier analysis belong to the fab lab
node's GIS. What a home draws has to open there without a converter.

## 2 · Goals, non-goals, anti-goals

**Goals**

1. Draw on the map: markers, lines that measure as you draw, areas that give their surface as you close them, and
   notes. Each drawing takes a colour, a label, a note and, optionally, an image.
2. Keep drawings in named maps that switch on and off like layers, stored on the node.
3. Download a map, or everything on the screen, as PNG, GeoJSON, KML or DXF.
4. Open with the satellite base on, where the node holds satellite imagery.
5. Move the then-and-now pair and the AlphaEarth figures off the screen into the lower band, beside the yearly
   indicators of what changed.
6. Fetch the satellite's buildings (Open Buildings v3) per H3 cell, starting with the house's cell and growing to the
   7 cells around it, and say per cell how many OSM lacks.
7. Give a way into OpenStreetMap from the page to trace those buildings.
8. Show a pin where drone imagery exists when the map is zoomed out too far to draw it.
9. Let both side columns collapse, with a map-only key and a full-screen key.
10. A map the owner shares goes to the community or fab lab node as GeoJSON, by the up-link the node already uses.
11. Run a tool three ways with the same command: pressed on the page, asked of the node's own model (the Ask line,
    Telegram), or called by an outside agent over MCP. A tool runs on what is selected, or on the house's cell.
12. Agents draw, into a map of their own, never into the household's.
13. Every piece of GIS work is an action in the node's ledger, with who did it; drawings and tool results are kept in
    the database; a daily count of the work is a reading.
14. A drawn intervention can be tied to an open issue, and then it counts as acting on it (ρ).

**Non-goals** (the fab lab node's, or later)

- GeoPackage and Shapefile downloads. GeoJSON opens in QGIS, which writes both.
- Accounts or a map per person. A home node has one token; a map's owner is a name typed on it.
- Buffers, overlays, snapping, topology, routing, editing OSM from the node.
- Uploading anything to OSM automatically.
- Sharpening the satellite base. Sentinel-2 is 10 m a pixel; sharper open imagery exists only where a drone flew.

**Anti-goals** (failure even if it works)

- A drawing reaching anyone the household did not choose. Drawings on a house are the household's own, and a shared
  map carries its places exactly, so sharing is said plainly before it happens (§5).
- The cake and its order disappearing under a toolbar. The drawing keys sit on the screen; the layer column keeps its
  McHarg order.
- A Place that needs dragging to draw. Every shape can be drawn with taps, and with the keyboard.
- A second palette for the page. Drawing colours live on the screen only.

## 3 · Constraints from the node

- One token. Writes need the token the page already carries (`planetai_admin` or `planetai_act`). The drawings and
  their routes are token-only at every `SHARE_LEVEL`, like `/place/geojson`. What an agent may read and write is §7.
- No build step. Plain browser JS in the doors files, MapLibre 5.24 and deck.gl as vendored, no new front-end
  dependency. Lengths and areas in the browser are computed with a few lines of geodesic math. The stored figure is
  PostGIS's (`ST_Length`/`ST_Area` on geography), and the page shows the stored one once saved.
- PostGIS is there, with PROJ, so KML (`ST_AsKML`) and UTM transforms (`ST_Transform`) need nothing new. DXF is
  written by hand as ASCII R12 in Python, which needs no library.
- The design layer: ink on paper, the black screen, state shown by fill, outline and dash. The drawing colours are a
  bend of the layer and need a line in `planetai-design/decisions/design-log.md`.
- The up-link pushes from child to parent (`push_aggregates()` posts to `PARENT()` with `PARENT_TOKEN`). The parent
  never pulls from a house. Sharing follows the same direction.
- Captures already strip EXIF and keep the picture at home (`packs/eyes/routes.py`, `POST /captures`). An image on a
  drawing is a capture.

## 4 · The page

Layout follows the approved mockup.

**5 Nov 2026, after Tomas used it on node #1:** one side menu, the left. The tools left the right column for a
**Tools** button on the top line, in the place of **+ Add an image**, with a menu: the ones that run first, then the
ones not yet. Only the left folds (`[`, `\` for map only, F full screen). What changed, year on year is a band of its
own under the screen, end to end. The readout folds to a chip. The mockup still shows the right column; this note wins.

**Left column.** A new top section, **your maps**: one row per map with a square dot (a map, as against a layer's round
one), its name and how many drawings it holds, then **New map**. Below it the cake as Part A built it. Pressing a map's
row switches it on or off; a second control on the row (or the open map's header in the lower band) renames, shares or
deletes it. Deleting asks first, naming the map and its count. One map is the open map: new drawings go into it.

**On the screen, left edge: the drawing keys.** A column of 44 px keys in the screen's chip style: select (V), marker
(M), line (L), area (A), note (N), image (I), then a gap and undo (⌘Z / Ctrl+Z). The letter sits small in a corner of
each key. The pressed key is filled (the screen's ink), the others outlined. On a phone the keys run as a row along the
screen's bottom edge.

**Beside the keys: the readout.** The one memorable thing on the page, the device's own screen line. It names the tool
and the open map, shows the live figure large in mono (a line's metres and segments, an area's m², hectares and
perimeter, a marker's coordinates), carries the six colour swatches, and one line of how to draw with that key.

Drawing, for every shape:

- tap or click to add a point; double-tap, Enter, or a tap on the first point finishes;
- Backspace removes the last point; Esc cancels the drawing in progress;
- with the keyboard, the map's centre is the cursor: arrows pan, Enter adds a point there;
- a saved drawing is selected with V or a tap; its points then move with a tap on the point and a tap on the new place
  (no drag needed), or with the arrows;
- the label and note are typed in a small form under the readout when a drawing is selected; the swatch changes its
  colour.

The existing measure tool becomes the line key, and the existing PNG key moves into the download menu. "From the
house" stays as a tool in the right column. Inspect becomes select.

**On the screen, right edge**, top to bottom: map only (both sides fold), full screen, back to the house, download,
OpenStreetMap. Zoom stays bottom right. A small switch at the bottom (satellite · streets · drone) sets the base;
drone appears only where the node holds drone imagery.

**Download menu.** For the open map: an image of the screen (PNG), GeoJSON ("for upstream and QGIS"), KML ("for Google
Earth, phones"), DXF ("for CAD, in metres"). A last row downloads everything on the screen as one zip of the four.
Files are named `<node>-<map>-<date>.<ext>`.

**Collapsing.** Each side has a small arrow at its top that folds it to a 36 px strip with its name written down the
strip; pressing the strip opens it again. Map-only folds both and lets the screen grow to the window's height
(`100vh` less the header). Full screen uses the browser's Fullscreen API on the screen element, with the keys, readout
and controls coming along; where the browser has no element full screen (Safari on iPhone) the key is not drawn. Each
side's state is remembered per browser in `localStorage`, read and written in try/catch, and the page is correct
without it. Shortcuts: `[` and `]` for each side, `\` for map only, `F` for full screen, all shown in the keys' titles.

**Right column.** Tools as Part A left them. Then **satellite buildings, by cell**: seven rows, the house's cell first
and the six around it named by direction (north-east, east, south-east, south-west, west, north-west). A fetched cell
shows its building count and how many have no OSM building within 3 m. An unfetched one shows **Fetch**; a cell being
fetched says so. The cells' outlines are drawn on the screen: the house's solid, fetched ones solid and thinner,
unfetched ones dashed. The satellite's buildings keep the satellite's orange.

Then **OpenStreetMap**: one line with the count of buildings OSM lacks across the fetched cells, then **Open in iD
here**, which opens `https://www.openstreetmap.org/edit?editor=id#map=18/<lat>/<lon>` at the selected cell's centre (or
the map's centre), and **Missing buildings**, which downloads them as GeoJSON for iD's custom-data panel. A short line
says OSM takes these traced by a person, never uploaded, and links the node's existing mapping brief
(`planetai run place gaps`). iD cannot load a file from a LAN node by URL, which is why it is a download.

**Drone pins.** Below the drone layer's zoom (13), each mosaic in `/ground/meta`'s `drone.mosaics` draws as a pin at its
bbox centre, labelled with its provider's resolution and date ("drone, 4 cm, Mar 2024"). Pressing a pin flies to the
mosaic's bbox at zoom 16.

**Lower band.** Left: the open map's drawings as a table (colour, label, kind, measure, note, image thumbnail), each row
selecting its drawing on the map. Right: **what changed, year on year**. The then-and-now Sentinel-2 pair moves here
from `.altc`, with its year arrows, the hectares changed from `/earth` with their `model` word, the buildings the
satellite counts per year from `place_yearly` (as small bars, one per year), and the Land figure Part A shows today.
`.altc` and its markup leave the screen entirely.

**Defaults.** The satellite row (`imagery`) is on when the node holds imagery (`G.imagery`). Otherwise streets stay the
base, as now. The cake's other defaults are unchanged.

## 5 · Storage and API

Two tables in core, created in `init.sql`, which gains `CREATE EXTENSION IF NOT EXISTS postgis` ahead of them: the
db image is PostGIS (`imresamu/postgis:16-3.4-alpine`) and its user creates extensions, so drawing does not wait on
the place pack. A node whose database lacks PostGIS must fail `planetai update` with a sentence that says so, never
half-apply; the CI database must be the same image (*my call*). A third table, `place_tool_runs`, is §6's and
arrives with the third pull request; until then `place_marks.run_id` is a plain column and gains its foreign key
with it.

```
place_maps   id BIGSERIAL PK, name TEXT NOT NULL, owner TEXT, agent TEXT,  -- set = an agent's own map (§7)
             shared BOOLEAN NOT NULL DEFAULT false,
             shared_at TIMESTAMPTZ, share_error TEXT, created_at, updated_at,
             from_node TEXT, remote_id BIGINT,  -- both NULL = drawn here; UNIQUE (from_node, remote_id)
place_marks  id BIGSERIAL PK, map_id BIGINT NOT NULL REFERENCES place_maps ON DELETE CASCADE,
             kind TEXT NOT NULL CHECK (kind IN ('marker','line','area','note')),
             geom geometry(Geometry, 4326) NOT NULL, colour SMALLINT NOT NULL DEFAULT 1 CHECK (colour BETWEEN 1 AND 6),
             label TEXT, note TEXT, capture_id BIGINT REFERENCES captures ON DELETE SET NULL,
             length_m REAL, area_m2 REAL, drawn_by TEXT,  -- the person's name, or the agent's
             run_id BIGINT,  -- kept from a tool's result (§6)
             alert_id BIGINT, event_id BIGINT,  -- the open issue it acts on (§8)
             created_at, updated_at
```

`length_m` and `area_m2` are written by the server on every insert and update, from `geom::geography`. A colour is a
number 1–6 so the palette can change without a data migration.

Routes (all token-only, at every `SHARE_LEVEL`, in a new `app/maps.py` router; add them to `DOORS_LOCKED`):

| route | does |
|---|---|
| `GET /place/maps` | the maps with counts |
| `POST /place/maps` | create `{name, owner?}` |
| `PATCH /place/maps/{id}` | rename, owner, `shared` |
| `DELETE /place/maps/{id}` | delete with its drawings (the page confirms first) |
| `GET /place/maps/{id}.geojson` | the map as a FeatureCollection |
| `GET /place/maps/{id}.kml` | the same as KML |
| `GET /place/maps/{id}.dxf` | the same as DXF, in the UTM zone of the node's point, metres |
| `POST /place/maps/{id}/marks` | add a drawing (a GeoJSON Feature) |
| `PATCH /place/marks/{id}` | geometry, colour, label, note, capture |
| `DELETE /place/marks/{id}` | remove one drawing |

**GeoJSON is the contract**, the one upstream nodes read. Each Feature carries `properties`: `kind`, `label`, `note`,
`colour` (1–6) and `colour_hex`, `length_m`, `area_m2`, `image` (the capture's id, never its file), `updated_at`. The
collection carries `map`, `owner`, `node` and `schema: "planetai.place.map/v0"`. Coordinates are WGS84, as GeoJSON
requires.

**KML** is one Placemark per drawing, its colour as a style, label as name, note as description.

**DXF** is ASCII R12: a layer per kind (`MARKERS`, `LINES`, `AREAS`, `NOTES`), markers as `POINT`, lines as
`POLYLINE`, areas as closed `POLYLINE`, labels and notes as `TEXT`. Coordinates are transformed to the node's UTM zone
(EPSG 326xx north, 327xx south, the zone from the node's longitude) and given in metres from the zone's origin. The
header names the EPSG code in a comment so a CAD user can place it. ACI colours approximate the six swatches.

**PNG** stays a browser download of the canvas, which already keeps its drawing buffer for that (`preserveDrawingBuffer`
in the map's options). The drawings, the scale bar and the credit line must be in the canvas when it is read.

**"Everything on the screen"** is built in the browser: the PNG plus the three files for every map that is switched on,
in one zip. If a zip needs code the node doesn't have, it is four downloads instead (builder's call, §11).

**Images.** The image key opens a picker: pick an existing capture from Data › Images, or take or choose a new photo,
which goes through `POST /captures` as kind `phone` with the drawing's point. The drawing's location is the one that
counts; a photo's own location is stripped by the captures pipeline as it is today. The image stays on the node.

**Sharing upstream.** A map marked shared is pushed to its parent, the same direction and token as the hourly
aggregates (my call, from the builder check):

- the child sends `POST {PARENT()}/place/maps/received` with `Authorization: Bearer PARENT_TOKEN`, body
  `{schema: "planetai.place.map/v0", node, map_id, op: "put" | "delete", geojson}`; `put` carries the whole
  FeatureCollection of §5, `delete` none;
- on the parent the route sits in `auth._CHILD_WRITES` and checks `AGG_TOKEN`, as `POST /aggregates` does. It is not in
  `DOORS_LOCKED`; the household routes of §5 are;
- the parent upserts on `(from_node, remote_id)`: the map's row with `from_node` and `remote_id` set, its drawings
  replaced whole. `delete` removes the map and its drawings;
- the child sends `put` when a map is shared and after each change to a shared map (at most once a minute, coalesced),
  and `delete` when it is unshared or deleted. A failed send keeps `shared` true, writes `share_error`, and is retried
  at the next hourly push. A 404 means the parent's node predates maps: the share row says "the node upstream does not
  take maps yet";
- on the parent, received maps are listed by its own `GET /place/maps` (its token) and in its Place's **your maps**
  under "from <node>", read-only: they draw, they download in the four formats, the keys never edit them. That route
  and the GeoJSON download are what a fab lab node's larger GIS reads;
- with no `PARENT` set, the share switch says there is no node upstream and stays off.
- the first time a map is shared, the page says what goes before it sends anything: every drawing at its exact place,
  with its labels, notes and measures, to the node upstream, where that node's token holders can see it. Sharing
  needs a second press after that sentence. Drawings are sent as drawn, never blurred near the house (Tomas, 4 Nov:
  "Exact, with a warning"). The warning is shown again when a shared map gains a drawing within the house's own res-10
  cell, the same cell `captures.at_home` uses.

Nothing else about a house leaves with the map: no house point, no capture file, only the drawings and their words.

## 6 · Tools: one list, three ways to run them

Part B's registry stands (`docs/SPEC_place_microgis.md` §6): `GET /place/tools` lists every tool with its id, name,
kind, the layers it reads, its arguments as JSON Schema and whether it can run now; `POST /place/run/<id>` returns
`{features, figures, word, inputs, as_of}`; look tools compute in `app/geo.py`, analyses and fitness read what the
place pack worked out; the first tools are Part B's table. What changes here:

- **The tools that run in the third pull request** (*my call*): the look tools (`geo.select`, `geo.measure`,
  `geo.area`, `geo.rings`), `place.walk`, `place.changed` and `water.runoff`, which read data the node holds today.
  The rest of Part B's table is listed with "cannot run now" and the data it waits for, until those steps land.
- **A tool runs on the selection.** Every tool takes an optional `on` argument: a drawing (`mark:<id>`), a map
  (`map:<id>`), a cell (`cell:<h3>`, one of the seven), or nothing, which means the house's cell. Pressing a tool with a
  drawing selected fills `on` with it.
- **The Run panel** is the v2 mockup's: pressing a tool in the right column opens its settings under it, Run (Enter) is
  the one filled button, and under it the same run is printed as the command an agent sends,
  `place.sun {"day":"2026-11-04","at":"14:00","on":"mark:12"}`.
- **A result shows in three places**: a row under **results** at the top of the left column (a switch like a layer,
  with a clear), drawn on the screen, and as a table in the lower band. **Keep** on a result copies its features into
  the open map as drawings, labelled with the tool and its settings.
- **Every run is kept**, in a `place_tool_runs` table (id, ts, tool, args, actor, via, features, figures,
  word, inputs; not `place_runs`, which is the place pack's OSM-fetch log),
  whoever started it. This replaces Part B's `place_tool_runs.jsonl` file trimmed to 200 and Part B's rule that an agent's
  run is not stored (Tomas: "all the local GIS work should be also recorded"). The conversation itself is still not
  stored; the run is.
- **The node's own model** runs tools through the Ask line and Telegram, as Part B planned, with a small local model on
  node #1 (Part B step 2). Place tools are offered on a screen holding the token only, as today.
- **Outside agents over MCP.** `app/agent.py` gains `place_tools()`, `place_run(tool, args)`, `place_maps()`,
  `place_map(id)`, `place_draw(map, feature)` and `place_keep(run, ids)`. Part B held MCP back until the pane had run on
  node #1; Tomas wants both ways, so both ship in the same pull request (§13). Writes need the admin token and record
  the agent's name (`X-Agent`), as every MCP write does now.

## 7 · Agents draw, and what they may see

An agent draws into a map of its own, created the first time it draws and named for it ("Suggestions from Claude",
"Suggestions from the node"). It never edits, moves or deletes a drawing in the household's maps. Each drawing keeps
`drawn_by`. The household keeps a suggestion by moving it into one of its maps, and it stays marked as the agent's.

What a model reads can go to its provider, and a drawing on a house is the house. Tomas, 4 Nov: "House network only".
So home is the rule the node already keeps for this, `agent_loop.models_stay_home` (a model on this house's own
network counts as home; `/learned` uses the same rule through `household._models_home()`):

- **The node's own model, on a rung that is home** (on this machine or on the house's network, as gemma4:26b on the
  LAN is for node #1 today), reads and writes drawings with their coordinates. The test is made per rung when a tool
  is called, not once per request, because the pane falls through rungs mid-request; the scrub the model's tool
  results pass through is built for the rung that will read them.
- **A rung that is not home** (an online model) reads figures, measures, kinds, colours, ids and directions
  ("north-east"), never coordinates, the house's cell ids, labels or notes: `scrub`'s existing drop list already takes
  `note` and `name` out, and it gains `coordinates`, `bbox`, `at` arrays and H3 ids of the seven cells.
- **Every agent over MCP is not home** (*my call*): the MCP tools cannot tell a Claude on the tailnet from one on
  localhost, and the model behind any of them runs at its provider. So the MCP place tools return what a not-home rung
  reads, and the agent draws by reference: `place_keep(run, ids)` keeps features a run found, and `place_draw` takes
  a feature placed `at` a drawing, a cell by its direction, or a run's feature (`{"kind":"marker","at":"mark:12",
  "label":"…"}`) instead of coordinates. The node does the geometry. Each MCP place tool takes the agent's name as its
  `agent` argument, as `act` and `settings_set` do, and records it.
- **The pane's promise changes by one line.** `ask.py` tells the household nothing is changed by the pane. Drawing
  adds a tool class, `draw`, offered only on a screen holding the token, which writes into the agent's own map and
  nowhere else, so the promise becomes: nothing of yours is changed; the node's model may draw in its own map.

The page draws what any agent drew, and the ledger says which agent.

## 8 · The ledger, the data, and acting on an issue

**Actions.** The node's `actions` table is already its ledger for more than alerts (stages `settings`, `decided`,
`dismissed` besides the three of an alert's loop), and the Data door shows it. GIS work joins it as a new stage,
`place`, with the verb in `choice` (`drew`, `changed`, `deleted`, `kept`, `ran:<tool>`, `fetched`, `shared`,
`unshared`, `downloaded:<format>`, `osm`) and a short note naming the map, the drawing or the tool. `actor` is the
name the page keeps (`planetai_actor`, as captures use it), the Ask model, or the agent's `X-Agent`. Edits to one
drawing within a minute are one row. The ledger's stage filter gains **place**.

**Data.** Drawings live in `place_marks` and results in `place_tool_runs` (§5, §6). Once a day the node writes readings
for a `place` sensor: drawings in all maps, area marked (m²), tool runs, cells fetched. They are `private`, so they
never travel upstream and never reach an agent's provider, and they show on the Data door like any other series.

**Acting on an issue** (Tomas: "yes, it should"). A drawing in one of the household's maps can be tied to an open
issue, from the drawing's form: a short list of the issues open on Now, and a line for what the person did, in their
own words, which is required (an `acted` note is the household's words, as v0.63 settled; the diary reads it so).
Tying writes the row the Done button writes, from the maps route directly and not through `POST /actions`, whose
choice check would refuse it: `stage = 'acted'`, the issue's id the way the Done button on that issue row carries it
(`alert_id` under `ALERT_ENGINE=rules`, `event_id` when the engine owns the issue), the person's name, their words,
and `choice = 'place.mark:<id>'`. Where the Done button would be refused (a decision required first), tying is
refused with the same sentence. ρ then counts it as the issue's acted step. Rules, *my call*:

- only a person ties: an agent's suggestion counts once a person has kept it into their map and tied it;
- untying deletes that row, found by its `choice` (the table has no id); deleting the drawing keeps it, because the
  person did act;
- the drawing shows its issue in the table and on the map's label;
- `measured` stays what it is today, the issue's own reading coming back under the line.

## 9 · The satellite's buildings by cell

Today `packs/place/satellite.py` fetches Open Buildings in a circle of `PLACE_RADIUS_M` (1000 m) around the node, split
into quadrants to stay under Earth Engine's feature cap. This changes to H3 cells:

- the cells are the house's res-8 cell and its ring (`grid_disk(home, 1)`), the same seven the captures table already
  calls the node's own (`captures.outside`);
- `footprints()` takes a cell's boundary polygon instead of a circle; a dense cell may still need splitting;
- the place pack's published readings do not change (*my call*): `buildings`, `built_share`, `sat_buildings`,
  `osm_building_coverage` and the rest stay counted inside the `PLACE_RADIUS_M` circle, as pack.yaml declares, and
  `place_yearly` stays circle-based. The circle's own Open Buildings fetch stays as the default. Rows a cell fetch
  adds beyond the circle, and OSM rows fetched beyond it, are tagged with their cell and serve the cells' counts and
  the gaps view only, so the readings' history and the Index inputs are not broken;
- `place_buildings_sat` gains a `cell` column; a new `place_sat_cells (cell PK, requested_at, fetched_at, buildings,
  not_in_osm, error)` holds each cell's state. A cell is pending while `requested_at` is later than `fetched_at`, or
  it has no `fetched_at` (my call);
- a fetch replaces only that cell's rows, never the whole table as `footprints()` does today;
- `POST /place/cells/{cell}/fetch` (token) refuses any cell outside the seven, records the request, and the place pack
  does the fetch on its next run or in a short job, so the page never waits on Earth Engine; the page shows "fetching"
  until `place_sat_cells` has the row;
- the circle's fetch covers the house's cell, which counts as fetched; the other six are fetched when pressed, each
  counted only once it is fully covered. A fetched cell
  has a quiet **Fetch again**, and a cell whose fetch failed shows the error and **Fetch again** (my call);
- `not_in_osm` uses the same test `gaps.py` uses (no OSM building within 3 m). OSM's own fetch has to cover the seven
  cells for that to be true: the ring's far corners are about 1.3 km out, past the 1000 m default, so the OSM refresh
  covers the seven cells' bounds, with the readings still clipped to the circle;
- without an Earth Engine key, the section says so once and the Fetch buttons are not drawn, as the pack's other
  satellite figures do now. Node #1 has a key (`EE_PROJECT`, `EE_KEY_FILE`) and 5,994 footprints today, so §12's
  cell fetch runs there for real; the suites use a stubbed Earth Engine.

`place_yearly` (buildings per year) stays as it is and feeds the lower band.

## 10 · Accessibility and the phone

- Every key is a `<button>` with a name and `aria-pressed`; the readout is `aria-live="polite"` for the finished
  figure, not for every mouse move.
- Drawing needs no drag (§4). Moving a point needs no drag.
- Focus is visible on the black screen (the cells' blue outline, as on the hour pill).
- 44 px targets on the screen, as Part A's map tools. Tomas ruled on 5 Nov 2026 that with a pointer the keys inside
  the screen are 36 px; under `@media (pointer: coarse)` they stay 44 px.
- At 390 px: keys along the bottom of the screen, the readout above them, the sides as the bottom sheet Part A built
  with **your maps** first in it, the download and OSM keys in the screen's right column as on desktop.

## 11 · Left to the builder

- How the drawing state is held in `doors-placemap.js` (a new `PM.draw`), and whether drawings render as deck.gl
  layers or MapLibre GeoJSON layers. Either must be inside the canvas for the PNG.
- The geodesic math for the live readout (a spherical excess formula is enough at this scale).
- Whether "everything on the screen" is a zip or four downloads.
- The exact six colour values, within: none is the satellite's orange or the cells' blue, each reads on satellite and
  on the black street map, and each pairs with an ACI colour in DXF.
- Whether the cell fetch runs as a job from the route or on the pack's next cycle, as long as the page never blocks.
- Copy, under the house rules: plain, first person where the household speaks, no AI patterns.

## 12 · Done means

- Node #1 on the branch: satellite on by default, the then-and-now pair in the lower band and nothing over the screen,
  a map drawn with each key, downloaded in all four formats, the DXF opened in a CAD program at the right size, the
  GeoJSON opened in QGIS, a second cell fetched, the drone pin drawn where node #1 has a mosaic, both sides folded and
  remembered after a reload.
- The doors visual gate passes with the new panes (keys, readout, folded sides) at 1440 and 390, paper and dark.
- `docs/site/dashboard.md`'s Place section says how to draw, keep and download a map, in Tomas's voice.
- A design-log line in planetai-design for the drawing colours and the keys.

## 13 · Three pull requests

1. **Drawing and maps.** §4 and §5 without the tools: the keys and readout, named maps, the four downloads, sharing
   with the warning, satellite by default, the then-and-now pair in the lower band, drone pins, folding sides, the
   `place` stage in the ledger and the daily readings, acting on an issue.
2. **Cells and OSM.** §9 and the OSM section of §4.
3. **Tools and agents.** §6 and §7: the registry, the Run panel, `place_tool_runs`, the Ask model's tools, the MCP tools,
   agents' maps, the local model on node #1. This is Part B of the Place spec, as changed here.

Each is run on node #1 for a real cycle before it merges, with CI green first.

