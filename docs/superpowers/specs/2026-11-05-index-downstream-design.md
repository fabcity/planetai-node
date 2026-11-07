# The city comes down to the node

Design, 5 November 2026. Status: draft for Tomas.

A node sits in a place the Fab City Index already knows something about. Today it learns none of it: it carries a
pinned copy of the source registry and never reads the Index. This document is the other direction from the upstream
tiers (home → community → pilot → Index, still on hold since 28 September). Data comes **down**, straight, through a
core pack, into the Place door's cake.

## 1 · What Tomas asked for, 5 November 2026

- Home nodes do not publish to the Index. Unchanged.
- A node is fed by the Index's data sources for the official city it sits in. Downstream is a direct connection, as a
  core pack.
- The node shows an indicator of the Index somewhere.
- Some of the sources feed the Place tab, where the layers help understand the cell: soil and the rest. More sources
  connect to the hyperlocal GIS the node is developing (SPEC_place_microgis).
- Where a city has its own source for a layer and a global model covers it too, **both show**.
- A new source reaches a node **when it is merged in the registry**, not with a node release, and the node is
  **alerted** to it.
- The node **waits for someone to say yes** before it reads a new source.
- Each node reads **straight from the source**, a home under a community node too, because what a home reads has a
  private use. A community node follows the same logic. Its public use comes later, once that is developed.
- Look through awesome-fabcity-data for candidates to become packs or feeds for home and community nodes (§9).

## 2 · Goals, non-goals, anti-goals

**Goals**

- A node knows which Index place it belongs to, and shows that place's indicator.
- Every registry source filed for that place, and every global one that fits a layer, appears on the cake as a row:
  read, available, or filed with no reader yet.
- A source merged upstream shows up on the node the next day as an alert, with a yes and a no.
- A layer reads the city's source and the global one side by side, each with its own name, date, resolution and
  licence.

**Non-goals**

- Publishing anything upstream. No cell, no reading, no consent decision leaves the node.
- A community node serving layers to its homes. Later, and its own design.
- Recomputing the Index on the node. The node shows the Index's numbers; it never makes its own.
- One pack per source. Readers are by format (§7).

**Anti-goals** (it works and it is still wrong)

- A node fetching from a new host before anyone at home said yes.
- City and global numbers blended into one figure, or one quietly preferred.
- A request to an outside host that names the house. The invariant holds: exact place never leaves (§8).
- A node that stops showing its sources because GitHub or the Index is down. It shows an older list, and says how old.
- Thirty alerts the morning after a large registry merge.

## 3 · What exists today

Read on 5 November 2026 at node `7a2f8f0`, registry `8099744`, Index API generated the same morning.

| piece | where | what it does |
|---|---|---|
| place at setup | `bin/planetai` init, the pilot boxes | four hard-coded bounding boxes (bali, barcelona, boston, santiago). Inside one, `NODE_CITY` takes the pilot key; elsewhere it is a free key no Index place matches |
| registry copy | `data/sources/`, `tools/sync_registry.sh`, `app/registry.py` | a snapshot pinned to a commit sha, changed only by a commit and a release. Filters by `pilot_relevance` (4 pilots + `global`), not by `places` (61) |
| Index per place | `index.fab.city/api/v0/places/<slug>.json` | `format: fci-api-v0`, `registry_commit`, `place`, `score`, `cells[]` (each with its registry `sources`), `indicators[]` (with yearly `series`), `boundaries`, brackets, `links`. 61 places: 6 partial, 55 simulated |
| place list | registry `places.yaml` | 61 slugs with name, country, NUTS codes, `kind`. **No coordinates and no boundaries** |
| place points | `fci-3-prototype/js/map-geo.js` | 53 hand-drawn centres, marked "approximate · v0, asserts no border" |
| the cake | `app/static/doors-cake.js` (`CAKE`), `app/static/doors-placemap.js` (`LAYERS`) | ten sections; `LAYERS` is a **hard-coded list** in the page, each row naming its `cake` section and `pack` |
| alerts with answers | `app/main.py` run_rules, `app/buttons.py`, SPEC_alerts | a rule may carry buttons; answers land in the actions ledger with stage `acted` or `acknowledged`; Telegram and the dashboard both answer |
| readers that exist | `core:ckan`, `core:openmeteo`, `core:power_climatology`, 13 `pack:` adapters | 16 of 212 live registry entries have one |

## 4 · Finding the city

- A new setting, `NODE_PLACE`: the Index slug, or empty. It replaces the pilot boxes as the source of truth.
  `NODE_CITY` keeps working as it does, so nothing that reads it today breaks.
- At `planetai init`, and once on update for an existing node, the node **suggests** the nearest place by centre
  (the 53 points, copied into the node with their date and their "approximate" note) and the person confirms or picks
  another, or none. A centre is not a border: Occitanie, Bhutan and Barcelona are different kinds of territory, so the
  machine proposes and a person decides. *(My call.)*
- None is a real answer. A node with no place reads global sources only and the indicator slot says the place is not
  in the Index yet, with the link to how a place joins.
- The eight places with no centre can still be picked by name.

## 5 · The daily read

Once a day, and at start:

1. `GET index.fab.city/api/v0/places/<NODE_PLACE>.json`. Kept with its `generated` date.
2. Resolve the registry's `main` to its commit sha (`api.github.com/repos/fabcity/awesome-fabcity-data/commits/main`),
   and fetch `index.json` **at that sha** (`raw.githubusercontent.com/fabcity/awesome-fabcity-data/<sha>/index.json`).
   The node records the sha it read, so it still reads a commit, never a moving branch. It does not wait for the
   Index's `registry_commit`: index.fab.city is deployed by hand, and Tomas's rule is that a source reaches the node
   when it is merged. A source the node lists that the Index file does not name yet is shown as "merged, not yet in
   the Index".
3. Diff against the last list the node held: new entries for this place or for `global` become the alert (§6).
4. On any failure, keep the last good copy. On a node that has never reached either host, `data/sources/` (the pinned
   copy) is the list. Every page that shows sources says which list it is and its date.

Step 1 needs no yes: it is the core connection and one known host. Every other host waits for a yes.

This changes what the pinned copy is for. `sync_registry.sh` says a node in a release should answer the same question
the same way. After this, two nodes on the same release can see different registries for a day. The pin stays as the
floor a node falls back to, and the release still re-pins it.

**The indicator.** Place's lower band ("the place in figures") gains the Index row: the place's name, its label
(complete, partial, simulated), its FCI or its range, and the indicators the Index computed for it, each with its
latest year and its source line, linking to the place's page on index.fab.city. Nothing is recomputed. *(Placement is
my guess from Tomas's "somewhere"; it follows the rule that a door gains a part in its reading order, never a
sub-switch.)*

## 6 · New sources, and the yes

- One rule, `index/new-sources`, raises **one alert per daily read** that found anything, listing every new source:
  its name, the cake layer it fills (or "figures" if none), its licence, what it covers, and whether a reader exists.
- Each listed source has two answers: **Read it** and **Not now**. They use the existing buttons and the ledger
  (`stage: acknowledged`, value `read:<id>` or `skip:<id>`). Telegram and the dashboard both work, as for any alert.
- Level `info` *(my call)*: it is recorded, shows on the dashboard and goes in the morning message; it does not
  interrupt, and quiet hours hold it.
- **Not now is final** for that alert. The source stays on its cake row as "available, not read" with the same
  switch, and the node never asks again by itself.
- Who answers: anyone holding the node token on a home node, the operator on a community node.
- A source with no reader yet is still announced, marked "filed, no reader yet", and a yes waits until a release
  brings the reader.
- The answers are the consent record: a `source_consent` table (`source_id`, `answer`, `ts`, `alert_id`) that every
  reader checks before any request. Turning a source off later is the same switch in reverse; the cached layer keeps
  its date until cleared.

## 7 · Sources on the cake

**Which layer.** The registry has no field that says which cake section a source fills, and the node may not edit an
entry. So the field goes **upstream**: a new optional `layer` key on registry entries, one of the cake's ids
(`microclimate`, `built`, `animals`, `plants`, `soil`, `water`, `ground`), filled by PR to awesome-fabcity-data. An
entry without `layer` goes to the figures band as a listed source, not onto the map. *(My call; it keeps "nothing here
edits an entry" true.)*

**City and global, side by side.** For a layer, the node draws every read source as its own row:

- a **city** row for an entry whose `places` holds `NODE_PLACE`, whatever else it lists. "City" here means filed for
  this place; the row also names the source's own scale, so the Generalitat's parcels say Catalonia, region;
- a **global** row for an entry whose `pilot_relevance` holds `global` and whose `places` does not hold `NODE_PLACE`;
- **nothing** for an entry with neither: it was filed for some other place (17 such entries today, such as French
  and Japanese municipal finance tables), and it is not a planet-wide source.

*(My call: the registry today has 20 `global` entries that also list places, and 17 with neither, so the plain
reading would draw some sources twice and show others everywhere.)*

Each row names its source, date, resolution and licence. Two rows of one layer can be on together; the legend and the
table keep them apart. Where they disagree the page shows both values and says nothing about which is right. A layer
with no city source says "no city source filed yet" and links to the registry's contributing page, the Index's own
"add a source" action. A layer with neither stays dotted, as the cake already does.

**`LAYERS` stops being only a constant.** The hard-coded rows stay; the page also asks the node for the registry rows
(`GET /place/layers`, my name) and adds them under their sections.

**Readers by format, in a core pack.** The readers live in one core pack, `packs/index` (Tomas: "as a core pack"),
so anything heavy they need follows the pack rule and never enters the app image; SPEC_place_microgis keeps rasterio
and numpy out of it, and the page computes no geography. A reader is code shipped in a release; a registry entry only
points it at a URL. A second new optional upstream key, `read`, names the format and its parameters, including the
one variable it reads (SoilGrids' organic carbon at 0–5 cm is one entry's `read`; a second variable is a second
`read` on the same entry, and a second row on the cake).

**What a row shows** *(my call)*: a value per H3 cell at res 10 over the node's area, drawn on the map the way the
grid is drawn, plus one figure for the node's own cell in the table. Values per cell, not a picture, so a city row and
a global row of one layer can be compared cell by cell. The pack writes them; the page reads them.

**`adapter` upstream** *(my call)*: when a reader ships, the entries it reads get `adapter: core:<format>` in the
registry. It is true (code on every node reads them), and it is what the registry's own count of "capable" means. It
does not make a cell measured: the Index's measured cells come from fci-index's `MEASURED`, not from this field.

1. `cog` — a Cloud Optimized GeoTIFF read over the node's area with range requests (rasterio/GDAL `/vsicurl/` inside
   the pack). Fills soil (OLM-SoilDB, SoilGrids), plants
   (WorldCover), people (GHSL).
2. `h3` — a dataset already keyed by H3 (Kontur population). People per cell, the denominator a home and a community
   node both miss.
3. `ckan` — widen `core:ckan` from four portals to any CKAN entry for the place: about 36 entries (Boston, Barcelona,
   Montreal, Québec and the 19 tagged `ckan`).

An entry with no `read` key, or a format no reader knows, is "filed, no reader yet".

## 8 · Privacy and safety

- **A request names an area, never the house.** Readers ask for the bounding box of the node's res-7 parent cell
  (about 5 km²) or a coarser one, never a point. A COG read pulls the tiles covering that box and clips at home. The
  node then draws its own cell and ring from what it holds. *(My call. Some existing packs send coordinates to
  forecast APIs; this design does not change them, and a later look should.)*
- **What a household chose stays home.** Consent answers, cached layers and the dates of reads never leave the node.
  Nothing in this design adds an upstream call.
- **The registry now decides what homes connect to.** A merged entry makes every node in its place ask whether to
  fetch from the host it names. Review in awesome-fabcity-data now guards that, not only what the Index counts. The
  node adds its own floor: `https` only, the registry's open-licence status (`live` or a usable review) required,
  a size cap and a timeout per read, and no code is ever taken from an entry. Only URLs and parameters.
- **Peers never roll up** still holds: a registry layer is display and context. It reaches no Index cell and drives
  no alert.

## 9 · Candidates in awesome-fabcity-data

Registry `8099744`, 293 entries, 212 live, 16 of them read by something on a node. Of the 196 live entries with no
reader, about 140 are yearly economic and governance tables at city, region or planet scale (budgets, trade,
procurement, census). Those are not packs: they are what the Index already turns into the indicator of §5.

**For the cake (home and community)**

| rank | layer | sources | reader | note |
|---|---|---|---|---|
| 1 | soil | OLM-SoilDB 30 m (candidate, PR #102), ISRIC SoilGrids 250 m | `cog` | label "modelled, no sample nearby" where WoSIS has none (Bali has none) |
| 2 | people | Kontur population, JRC GHSL, WorldPop | `h3`, `cog` | Kontur's licence version is "not stated" in the entry; check before reading |
| 3 | plants | ESA WorldCover 10 m; Generalitat crop parcels (Barcelona) as the city row | `cog`, vector | the first real city + global pair |
| 4 | water | Caravan hydrology, HydroBASINS, GEOID flood (Paris, Rennes, Montpellier) | vector | HydroSHEDS licence needs a read |
| 5 | built | Overture places and buildings (CDLA permissive) beside OSM | vector | Overture is a candidate |
| 6 | microclimate | Landsat C2 and MODIS land surface temperature (Bali) | `cog` | surface-heat already reads Landsat |
| 7 | animals | GBIF | API | the species door already counts it |

**City portals:** the `ckan` reader (§7.3) for Governance|City context on community nodes.

**Live readings beside the outdoor kit** (time series, not layers; they belong with the `nearby` pack's stations):
`sensor-community` (DbCL), `opensensemap` (PDDL, candidate), and official hourly networks per city: RIVM
Luchtmeetnet (Amsterdam, Velsen), ARSO hourly (Ljubljana), Montreal RSQA, Zagreb, EPA AirData (Charlotte, candidate).
`openaq` covers most of them but needs a key.

**Alerts:** USGS earthquakes (Bali, Santiago; candidate), CoCoRaHS rain (Boston area; candidate).

**Blocked by licence:** iNaturalist (CC-BY-NC by default), hackerspaces.org, SpaceAPI, Maps of Making ("not stated"),
fablabs.io and Precious Plastic (not open). None of them is read until that is settled.

## 10 · Steps

Each step is its own pull request, runs on node #1 before merge, and lands with its docs page and its place in the
UI (standing rules).

1. **Upstream schema.** awesome-fabcity-data: optional `layer` and `read` keys, documented, filled for the soil
   and people entries. Its own repository, its own review.
2. **The place.** `NODE_PLACE`, the suggestion at init and on update, the 53 centres in the node.
3. **The daily read and the indicator.** The Index file, the registry at `registry_commit`, the fallback, the Index row
   in Place's figures band.
4. **The alert and the yes.** `index/new-sources`, `source_consent`, the "available, not read" row state.
5. **`GET /place/layers` and the `cog` reader**, with soil first.
6. **`h3`**, then the wider `ckan`.
7. **Docs.** A page on how a node is fed by its city (docs site: NAV and `docsPages`), and `docs/SOURCES.md` rewritten
   for a list that is no longer only pinned.

## 11 · Open, for Tomas

- **A node outside every Index place.** Is "global only" right, or should it be offered the nearest place's sources
  as a neighbour's?
- **Where the indicator goes** if not Place's figures band (Node door, Now's morning message).

## 12 · Left to the builder

- GDAL in the pack or a smaller COG reader.
- The cache's form on disk and its size cap per source.
- How the alert lists many sources in Telegram's button limits (8 rows of 4).
- Names of the endpoint, the table and the rule, beyond what is written here.
