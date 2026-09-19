# The dashboard

The node serves `index.html` and a fixed allowlist of companion files — three stylesheets (`tokens.css`,
`planetai-theme.css`, `dashboard.css`), `dashboard.js`, two SVGs, `kilometre-cells.json` and the self-hosted
fonts, by name from `GET /static/{name}` — and the page they make reads six things from the node and draws
them: `/issues`, `/health`, `/settings`, `/rho`, `/earth` and
`/place/geojson`, plus `/trust`, `/forecast`, `/sensors` and `/cells` at boot. The node computes; the page
draws. A number the page works out for itself is a bug. `planetai ui` prints its addresses.

The page speaks the programme's visual language: paper and ink, every number in the mono, square corners,
colour only as argument — blue an H3 cell, data and identity; green a loop closed; red a line crossed;
orange what only the satellite knows — and state carried by weight, fill and dash, never by hue. Provenance
is an ink-only square pill: `live`, `partial`, `model`, `cached`.

## Views

| view | URL | what it shows |
|---|---|---|
| **Now** | `#now` | the lead — the headline issue as a sentence, why, what is asked, the grain line — then the sections in loop order: the ground, what the stations read, the day ahead, whose word over how much ground, what each grain is worth, what this node has asked, whether it worked |
| **Network** | `#network` | this node in relation to the network and nothing else: what moves through it, what leaves by radio, the mesh in the house, the hardware |
| **Historical** | `#historical` | what the satellite says year by year, and what the node doubts about its own sensors |
| **Set up** | `#setup` | the settings, behind the admin token, and every registered section with whether it is drawing |
| **Wall** | `#wall` | the dark register, for a screen on a wall — see [Wall mode](wall.md) |
| **Arrange** | `#arrange` | a mode over Now: move a section within its stage, hide one, restore, Default, Done; saved as `UI_LAYOUT` |

`?view=` works too, `?fixture=<name>` replays a committed snapshot through the node's own engine (the pill
says `cached`), and `?state=empty` or `?state=refused` draws those states for a capture.

## The lead

The first thing on Now is the headline issue's sentence in the household's language — "Falling to 9
micrograms, under the street, under the model, under the line" — with the kicker naming the issue, a line
saying why, and the ask strip if something is open. Under it the **grain line**: "At resolution 8 one cell is
0.74 km² and this node's 7 stations fall in 3 of them. 4 sit in this node's own cell, of which 3 are its
own." Then the as-of time, the version stamp, and the provenance pill: `live` on a live node, `cached` on a
fixture.

A **dial** sits under the header: one stop per H3 resolution the node's grain table knows, opening at 8.
Stops at a resolution coarse enough that the cell may leave the machine (at or above the presence floor,
resolution 6) are shaded in the cells blue; stops finer than the published resolution are struck through.
Turning the dial re-draws the ground and the grain at that resolution.

## Issues, states and distances

`GET /issues` is the whole of what the page knows about the place. For every issue the keeper declared in
`NODE_ISSUES` (an undeclared one is still shown, greyed, as `watched: false`): a `state` — `act` (something
is asked), `notable` (something changed), `quiet`, `context` (an issue that informs and never asks), `none`
(no record); the four distances — `room` (local indoor), `yard` (local outdoor), `ring` (somebody else's
device near here), `region` (a model or a portal, over this square of the map) — each with its value and its
provenance word; the sentence in three languages; the open asks; and the series for the day. The `headline`
is the highest state. The same object comes back from the `issues` MCP tool, so an agent and the household
describe the same evening in the same words. The declarations are one file per issue in `app/issues/*.yml`
— see [Issues](issues.md).

## The sections

Every section is registered with the page contract — `id`, `pack`, `stage`, `title`, `render`, and
optionally `order`, `needs`, `controls`, `wall`, `notes` — and rendered in the stage it belongs to, in the
order the loop runs:

| stage | sections (pack) |
|---|---|
| **observe** — what is read, seen and heard about this place | The ground (place) · This node, and what moves through it (core) · What the stations read (air-quality) · What the satellite says (earth) · What leaves this house by radio (reticulum) · The mesh in this house (meshtastic) · The hardware in this house · The day it is about to have (forecast) |
| **decide** — what may be said about it, and at what grain | Whose word, over how much ground · What each grain is worth · What the node doubts about its own sensors (trust) |
| **act** — what has been asked, of whom | What this node has asked |
| **measure** — whether it worked, and how long it took | Whether it worked (ρ) |

A section whose `needs` are not on this node prints one honest line — "The `earth` pack has nothing here
yet: `PLAN` is not on this node" — never a blank and never a guess. A section that throws prints that it did
not render and why, and every other section still draws: a failure is not an answer. The explanations every
section wants to make are gathered into one folded band at the foot, *Where these numbers come from*.

Four card kinds and no fifth: readout, stack, series, row. A gap in a series is a gap in the line, never a
ramp across the WHO line nobody measured. The node's own words are never uppercased — `µg/m³` once became
`MG/M³` on the hero, a factor of a thousand.

## The ground

The section behind everything is the node's H3 cell at resolution 8, its six neighbours and its seven
resolution-9 children, drawn by the node itself as `/static/node-ground.svg?variant=paper|dark` and loaded
as an image so page CSS cannot reach it. Three bases: `plan` — offline, from `/place/geojson`, the buildings
and roads within `PLACE_RADIUS_M` projected in the browser with every vertex kept, nothing leaving the house;
`sat` — Sentinel-2 cloudless tiles; `osm` — OpenStreetMap tiles. Live tiles need `MAP_TILES=on`, are fetched
only at resolutions coarser than 9, and a press on the dial may only ever reduce what leaves the house. Own
cell: stroke 2.5, fill 0.18; a cell read by others: 1.5, 0.07; an empty cell a dashed hairline. An H3 id is
printed in full, once per object, never truncated.

Three things the grid forces the page to say: a cell is not the thing (three indoor sensors share one
coordinate); containment is exact in the index and approximate on the ground; and the four distances are
not four resolutions.

## Set up

Behind the admin token, once per browser (it is kept in the browser's local storage as `planetai_admin`;
`planetai_act` holds an act token). Nine groups: Issues · Sources · Alerts · Packs · Integrations · Keys · Agent · Node · Bootstrap (the last read-only). A value set here is live within 20
seconds and wins over `.env`; the page says so beside it; a blank returns the key to `.env`. Every change is an `actions` row with `stage='settings'` and the actor `dashboard` (`planetai-cli` from the command line, the agent's name over MCP). The section list under it names every
registered section by pack and whether it is drawing or has nothing here yet.

## What a reader without a token sees

At `SHARE_LEVEL=off` a browser on another machine gets the dashboard shell, the node's name and city from
`/health`, and the refused page: "This node is not sharing its readings with the network", the node's own
403 sentence, and "Ask whoever set this node up to turn sharing on, or open this page on the machine the node
runs on." A blank would be the node lying about being broken. At `open` the whole read API answers and the
page draws; the plan card still needs a token at every level, because it is the shape of your building. See
[Sharing](sharing.md).

## Languages

The page reads the household's language from `/health.locale` — `ALERT_LOCALE`, which answers at every
sharing level — and draws the issue sentences, labels and distances in English, Bahasa Indonesia or Spanish.

## Looking at it without a node

`python3 tools/shots.py` renders every fixture the node ships, in Now and on the wall, at four widths,
with every request fulfilled from disk — the same computation as `GET /issues/fixtures/<name>`. It needs
Chromium from the sibling design repository and is not a gate a node runs. `tests/visual/gate.sh` measures
what the section contract cannot enforce: the four card kinds, state never by hue, numerals carrying
`data-num`, explanations in `notes()`.

> **Gap in v0.57.** `docs/GUI.md` and the `planetai ui` text still describe a `?kiosk=1` mode with big numbers
> refreshing every thirty seconds. That mode is gone: the wall is `#wall`, and it turns its own dial every
> eight seconds. `docs/GUI.md` also describes the older bands (Here, Room, Street, Neighbourhood, Region,
> Act here); the page now has the sections above.
