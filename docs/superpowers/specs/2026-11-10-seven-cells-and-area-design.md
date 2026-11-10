# Seven cells and the area pull

Status: draft, 10 Nov 2026. Builds SPEC_eyes §7 step 4 ("Seven cells") and adds a way to ask the node about any set
of cells or any drawn area. Gemini builds it task by task (plan beside this file); Claude reviews and commits.

## What Tomas decided (10 Nov 2026)

1. **A home node grows from one cell to seven by "picked, then held".** The keeper claims a neighbour; it shows as
   *claimed* until one of the node's own readings lands in it, then *held*. It drops back to *claimed* after 24 h
   with nothing there.
2. **The area pull reads three kinds of stream:** open sources by area, the node's own readings, and peers and radio.
3. **Bounds:** own readings only inside the node's own cells; open sources for any area, under a cell cap.

## 1 · Seven cells

The shape is fixed by SPEC_eyes §5: the res-8 cell the node stands in plus the six that touch it (`h3.grid_disk(home, 1)`),
4.48 km² at node #1 (SPEC_eyes rounds it to 5.2). Not the parent's children: node #1 is not its parent's centre child, so three of its six neighbours
sit in other res-7 parents.

Each of the seven is in one state:

| state | means |
|---|---|
| `home` | the cell of NODE_LAT/NODE_LON at res 8. Always the node's, never claimable or releasable |
| `claimed` | the keeper said "this one is ours too". No reading from the node in it in the last 24 h |
| `held` | claimed, and at least one reading in the last 24 h from a sensor of this node (`custody AND kind = 'sensor'`) whose point falls in it |
| `open` | a neighbour nobody claimed |

`held` is derived on every read, never stored, so it cannot disagree with the readings.

**Only the node's own sensors hold a cell, for now.** A child's hourly push (`POST /aggregates`) carries no location:
the parent writes `kind='child'` rows with no lat/lon (app/main.py, `receive_aggregates`). Children holding cells needs
a `cell` on each aggregates row, a wire change that belongs with the community tier (SPEC_eyes §6), not here.

**`local` follows the cells.** `sources.stamp_local` narrows an adapter's claim by distance today (`LOCAL_RADIUS_M`,
500 m). It changes to: local when the sensor's res-8 cell is `home` or claimed (held or not). Otherwise a sensor in a
claimed cell could never become local, and so could never hold it. A sensor with no coordinates keeps its claim, as now.

**Nothing on node #1 may drop out.** The first time a node stands in a home cell (no `home` row for that cell yet),
it adopts: every neighbour holding a sensor that is local today under the old 500 m rule is claimed with
`claimed_by = 'adopted'`. That row also marks adoption as done, so releasing every cell later does not re-adopt. A node
that moves (new NODE_LAT/LON) gets a new home cell and adopts again; claims that are no longer neighbours are ignored.

**`LOCAL_RADIUS_M` goes.** Its other readers (the "The street" claim in `app/issues/geometry.py`, the list in
`app/issues/engine.py`, the docstring in `packs/bali-air-dispatch/adapter.py`) move to the own cells: the street claim's
footprint becomes the area of home plus claimed cells. The setting leaves `app/settings.py` and `.env.example`.

**Community:** `GET /place/cells` says how many of the seven are held. Four or more is SPEC_eyes §6's draft threshold for
asking to become a community node; the node only says so, the registry PR is still the approval.

### Where it shows

- **Place**, at the Cell zoom: the seven drawn, each in its state. The inspector on a neighbour has Claim or Release.
  A line under the map: "3 of 7 cells held".
- **Data › Node** (or wherever the review puts it): the same line.
- `GET /place/cells`, `POST /place/cells/{cell}/claim`, `DELETE /place/cells/{cell}/claim` (`/cells` is the Index contract, fci-cells-v0). On no SHARE_LEVEL allowlist: this machine
  or a token. Every claim and release is an `actions` row with stage `place`, so the history survives.

## 2 · The area pull

A selection is one of:

- `cells`: H3 ids at res 5 to 10, covered at res 8 (`cell_to_children` for coarser, `cell_to_parent` for finer);
- `polygon`: a GeoJSON Polygon or MultiPolygon, covered at res 8 with `h3.geo_to_cells` (or `polygon_to_cells`);
- `mark_id`: an `area` mark from a Place map (`place_marks.kind = 'area'`), the "defined area" a keeper already draws.

Covering is capped at `AREA_CAP = 500` res-8 cells (about 370 km²), refused before computing when the estimate is
over, the way `geo.grid` refuses past `GRID_CAP`.

`POST /area` answers with three blocks, one per stream:

- **own**: per metric, latest value and 24 h mean over this node's custody sensors whose cell is in the selection
  **and** in home or held. Plus `children_unplaced`: how many child sensors exist that could not be placed.
- **peers**: the same over `kind = 'peer'` sensors with a point in the selection. Radio peers with only a distance are
  counted as `unplaced`, never guessed into a cell (`geometry.radio` already refuses to place them).
- **open**: whatever each enabled pack answers to the new hook `area(cells, bbox)`. A pack that has nothing for an
  area returns None. Each answer is `{"pack": id, "source": ..., "licence": ..., "rows": [...], "as_of": ...}` or
  `{"pack": id, "error": "..."}`. v1 packs:
  - `hydro`: rivers and level-12 basins from the file it already keeps, clipped to the bbox. No network.
  - `eyes`: GBIF open-record counts per species in the selection (the weekly code's polygon and licence filter),
    cached a day per selection.
  - `forecast`: Open-Meteo now and next 24 h at the selection's centroid, one call, cached an hour. Open-Meteo's daily
    limit is per IP and node #1 already spends most of it, so no per-cell fan-out.

**Privacy.** The answer stays on the node: token or this machine, never exported, never pushed upstream. Open
sources are sent the selection's polygon or centroid and nothing else, which for a selection inside the seven cells
tells them the area the house is in, as the GBIF weekly call already does.

### Where it shows

Place, Tools menu: **Pull**. Tap cells on the map, or pick a drawn area from the map's list, then the three blocks
in the side panel, each with its source and age. Empty blocks say why (no own cells in the selection, no peers,
pack off). A missing number stays missing.

## Not in this

- children holding cells (needs `cell` on the aggregates wire);
- the community promotion itself (SPEC_eyes §6);
- eyes' own seven-cell set (`packs/eyes/routes.py:_node_cells`) stays the full ring: it is where the node may map,
  not what it holds;
- more open packs on the `area` hook (surface-heat, terrain, place OSM) once the three prove the contract;
- named or saved selections beyond Place maps.
