# Energy: where the power behind a node's cells comes from

*Asked by Tomas, 8 November 2026: "a pack for the planetai nodes that maps where the energy of a node comes from."
Brainstormed the same day. The mockup he chose is `2026-11-08-energy-mockup.html` beside this file, option A.*

**Status: design, waiting for Tomas to read it. Nothing built.**

## 1. Intent

Water, air and heat are on Now. Energy isn't, and Tomas called it crucial. The question a household or a lab asks is
"where does the power we use come from?" That covers which plants, what they burn, how far away they are, and how much
crosses the sea from another island. The point of answering it is to move people: a household or a fab lab that sees
97% fossil next to what the sun on its own roof gave today has a reason to put up panels, or later to look at hydrogen.

It maps the energy of the **place**, meaning the H3 cells the node watches (its own res-8 cell and the six around it,
the seven cells of SPEC_eyes §5), not the meter in the house. The house joins in only if the household connects its
own solar, battery or meter through Home Assistant.

## 2. Goals

1. An `energy` issue on **Now**, beside air, heat and water, laid out like mockup A:
   - **headline:** the fossil share of the electricity reaching these cells, e.g. "97% fossil";
   - **one sentence:** names the nearest large source and its distance;
   - **a bar:** the share by source, e.g. coal, gas, the Java cable, sun + wind;
   - **the sources list:** the substation that feeds the cell, then each plant or link with fuel, size and
     straight-line distance;
   - **a "Today" box:** what the sun gave this roof today, beside what the household used;
   - **a provenance line:** says which numbers are measured and which are estimated.
2. It works on **node #1 (Ungasan, Bali)** and **node #2 `mahon1` (Menorca)** in the first version. Both use the same
   card with different provenance: Menorca can be measured hour by hour, Bali can only be estimated by year.
3. **Live household readings through Home Assistant.** Solar output, grid import and battery, read from entities the
   household already has in HA. With them, the household's own line goes live and its own fossil share moves through
   the day, even in Bali.
4. An **energy row on the Place map:** plants, substations, lines and cables around the node, and per cell what
   generates inside it.

## 3. Non-goals for this version

- Hydrogen. Tomas raised it as a later motivation. It is left out until the card works.
- Guessing which Bali plant runs at which hour. PLN publishes no dispatch, and the pack doesn't model one.
- Following the actual wires. Distances are straight lines, as everywhere else in Place (SPEC_place_microgis), and
  which grid a node belongs to is written down by hand (§5.1), not traced through OSM line topology.
- Carbon intensity in gCO₂/kWh, tariffs and bills. Tomas chose fossil share as the one figure.
- Controlling anything in the house. The pack reads from Home Assistant and never switches a device.
- Every grid on earth. Two grids ship. A third is added by adding its entry (§5.1).

## 4. Anti-goals: failures even if it works

- An estimated number that reads as measured. Every figure carries its provenance word (`measured` or `estimated`),
  and the card shows it. This is the same lie as a full cell drawn empty (absence has four shapes).
- A renewable share that rounds up, or a frozen source that hides what's missing. The WRI list stops at 2019 and has
  no rooftop solar, so wherever it is used the card says so.
- One household's consumption leaving the machine. Upstream, a cell may say "N kW of rooftop solar here", never a
  house's draw (AGENTS.md: sensor ids stay on the machine).
- A card with no next step. Without the "Today" box, the card is a fact about the island that nobody can act on.
- Ranking a place against itself (the TWI percentile trap in SPEC_terrain). The fossil share is an absolute figure.

## 5. How it works

### 5.1 Grids, written down

`packs/energy/grids.yml` holds one entry per grid system, each with its sources:

- `bali`, PLN's Bali system:
  - its own plants (OSM);
  - the Java link, landing at Cable Head Gilimanuk / Ketapang (OSM `power=substation`), counted at Java's mix;
  - mix: `estimated`, yearly.
- `balearic`, REE's Balearic system:
  - Menorca's own plants (OSM);
  - the 132 kV Mallorca–Menorca cable (OSM `power=cable`);
  - Mallorca's plants, and the Mallorca–peninsula link;
  - mix: `measured`, hourly, from REE REData (`geo_limit=baleares`).

A node finds its grid by its point, inside a hand-drawn polygon per entry. A node outside every entry shows the card's
`none` sentence and says how to add its grid. It never borrows a neighbour's figure (the 11 Sep no-fallback rule).

### 5.2 What's in and around the cells: OSM

One Overpass query per refresh, following `packs/place/adapter.py`: the same `OVERPASS_URL` and the same User-Agent
header. overpass-api.de answers 406 without one. The query asks for `power=plant`, `power=generator` (with
`generator:source`), `power=substation`, `power=line|cable|minor_line` inside the grid's polygon. The rows are kept on
the node like Place's, and refreshed monthly.

Read on 8 Nov 2026, Bali island box: 19 plants, 23 substations, 251 line segments, all 150 kV. From node #1's cell
`8895a4c843fffff`:

| source | fuel | MW (OSM) | km |
|---|---|---|---|
| GIS Pecatu (substation) | — | — | 2.4 |
| Pesanggaran PLTG + PLTDG | gas | 200 + 325 | 12 |
| Nusa Penida (8 turbines, solar, PLTD Kutampi) | wind, sun, diesel | 5.8 + 3.5 + 11.7 | 41–47 |
| Pemaron | gas | 97.6 | 76 |
| Celukan Bawang | coal | 380 | ~85 |
| Gilimanuk PLTG, cable head to Java | gas / link | 133.8 | ~100 |

Menorca box, same day: Endesa's oil plant at Maó (270 MW), Son Salomó solar (52 + 4 MW), Es Milà wind (3.2 MW), small
solar parks, and two 132 kV `power=cable` segments west towards Mallorca.

Whether Nusa Penida is on Bali's main grid or runs as its own island system is **not checked**. The builder settles it
before it goes into the `bali` entry.

### 5.3 The fossil share

- **Menorca, measured:** REE REData `generacion/estructura-generacion` for the Balearic system, hourly. Power from the
  peninsula link counts at the peninsula's mix that hour (same API, `peninsular`). On 8 Nov the API answered 400 and
  502 ("data not available right now"), so neither the endpoint nor REE's reuse terms are confirmed yet.
  **Licence first:** if REE's terms fail the open rule, Menorca falls back to `estimated` like Bali, and the doc gets
  updated.
- **Bali, estimated:** the yearly share by fuel. The builder picks the method and the card names it. The candidates,
  in the order I'd try them:
  1. PLN Statistik's yearly generation by fuel for the Bali system, if its licence passes;
  2. otherwise plant capacity (OSM) weighted by typical capacity factors per fuel, with the Java cable's share at Java's
     mix taken from Ember's Indonesia figures (CC BY 4.0) as a proxy, labelled as a proxy.

  The share of Bali's power that comes from Java is **not published openly** as far as I found. **Tomas decided (8 Nov):
  the headline is then a range**, e.g. "95–98% fossil". The two ends come from the Java share at its lowest and highest
  plausible values: none, and the cable running at its rated capacity against Bali's demand. Java's own mix is applied
  in both. The issue stores `fossil_share_low_pct` and `fossil_share_high_pct`, and `fossil_share_pct` is used only
  where a grid gives one measured figure (Menorca). In the bar, the Java part is drawn hatched, and its label says the
  share is not published. Once an open source gives the share, the range collapses to one figure.
- The WRI Global Power Plant Database is already in the registry (`environmental/region/global-power-plant-database`,
  candidate). Use it for capacity and fuel where OSM lacks them, never as the figure on its own, because it stops at
  2019.

### 5.4 The household, live through Home Assistant

The node reads a few entities from the household's HA over its REST API (`GET /api/states/<entity_id>`, long-lived
access token):

```
ENERGY_HA_URL=              # e.g. http://homeassistant.local:8123
ENERGY_HA_TOKEN=            # secret: masked once saved (pack `secrets:`)
ENERGY_HA_SOLAR=            # entity id, W, what the panels make now
ENERGY_HA_GRID=             # entity id, W, positive = drawn from the grid
ENERGY_HA_BATTERY=          # optional, entity id, W
```

Readings land as local readings with the node's usual sensor ids. They are polled every 5 minutes.

The household's fossil share for an hour is the share of its use that came from the grid, times the grid's fossil share
for that hour (or the year, in Bali).

My call: the read lives in the energy pack, not in `packs/home-assistant`. That pack promises "The node publishes;
Home Assistant automates", and it stays one-way. Any setting that makes the node reach into the house is marked in Set
up as a setting that changes what the node touches.

**No house in the fleet has solar in Home Assistant yet (Tomas, 8 Nov).** The HA path ships tested on recorded HA
`/api/states` responses only, and the PR says so. It is proven on the first node whose house has panels in HA. Until
then node #1's Today box always shows the forecast fallback, so the fallback is the path node #1 has to prove. The
panel size (2 kW in the mockup) and the household's daily use (9 kWh) become pack settings, with defaults the README
says are placeholders.

Without HA, or without panels, the card shows the grid alone, and the "Today" box falls back to the forecast:
`fc_shortwave` from the forecast pack (Open-Meteo). Check that node #1's forecast source carries it. BMKG may not, and
Open-Meteo's daily limit is per IP. The household's daily use then comes from a Set up number, or is left out.

### 5.5 The issue

Mockup A is the layout, not only the content. The issue card Now draws today (four distance dials and a readout
strip, `doors-now.js`) can't hold a bar, a sources list and a Today box, so energy ships a **core section** on Now
(PACKS.md: only core packs ship page script), served by its own route for the sources list. It takes in
`doors-now.js`, `mobile.js` and the visual-gate baselines. This roughly doubles the front-end work compared with a
terrain-shaped issue, and it's still the cost of what Tomas chose (my reading of "A, year first").

The headline stays the grid's figure for the cells. The household's own share never replaces it, because Tomas framed
this as the cells, not the house (my call). With Home Assistant connected, the household gets its own line in the
sources list ("this house: 3.1 kW from the roof now, 40% fossil today") and the Today box shows measured rooftop output
instead of the forecast.

The period of the headline is the **trailing 12 months** on both nodes, so the same metric means the same thing on
node #1 and node #2 (my call). Menorca adds a readout "right now: N%" from the latest REE hour. This needs a year of
hourly REE rows stored, backfilled on the first fetch.

`packs/energy/issue.yml`, shaped like `packs/terrain/issue.yml`:

- `key: energy`, `kind: context`;
- `metric: fossil_share_pct` (or the low/high pair, §5.3), `unit: %`, `line: ~`: no alert and no threshold;
- the distances are `region` only;
- readouts: nearest substation (km), nearest large plant (km), the imported share where it's known, the sun today
  (kWh), the household's use today (kWh);
- sentences in en/id/es, each marked unread by a native speaker like terrain's;
- a `none` sentence for a node outside every grid.

The domain colour already exists: `--d-energy` (#F28C28 on the dark doors). `signs.svg` has no energy sign, so the
issue has no hero, as water has none.

### 5.6 The Place map

Energy goes in the `built` row of the cake: plants, substations, lines and cables are stock (my call). The `flows`
row is marked "soon" because the flows pack isn't on main, so nothing goes there in v1. The cake's `electricity` class
stays in `microclimate` as the sun a roof could turn into power, unchanged. The map draws the grid entry's sources out
to the island, and the cables to where they land, so Celukan Bawang and the Gilimanuk cable head are on node #1's map.
The per-cell numbers cover the seven cells only.

Per cell, the row shows the MW generated inside it (from OSM) and the kW of household solar the node knows about (its
own, from HA). Drawing follows the shared map conventions (`doors-placemap.js`, the projecting-h3-cells skill).

### 5.7 In the flows vocabulary (`fabcity-flows` 1.0)

Checked on 8 Nov against `packs/flows/resources.yml` (branch `flows-pack-2026-09-28`, published at
planetai.fab.city/vocab/flows/1.0/). Energy fits the profile without a new class.

- **The class is `electricity`:** kWh, physical, pillar social, ceiling climate, foundation energy, mfa none. The
  profile's note already names this pack's two flows: "`produce.electricity.cell` is the roof;
  `consume.electricity.beyond` is the grid."
- **A genset is two lines:** `consume.fuel.<ring>` (litres) and `produce.electricity.cell`. That covers a hotel or a lab
  with its own diesel, with no new class.
- **Plants, substations, lines and cables are stock with no class**, like buildings in SPEC_place_microgis. That's why
  they sit in the `built` row (§5.6).
- **The household's flows are hourly kWh**, integrated from HA's W readings: `produce.electricity.cell` from the roof,
  and `consume.electricity.<ring>` from the grid. The battery is not a flow, because it moves the roof's own kWh in time.
  These lines stay on the machine like every flows line: `push_aggregates` leaves `source = 'flows'` out.
- **PITO and DIDO fall out of the profile's own rule.** Physical from `beyond` is PITO, so the Java share is literally
  the PITO share of Bali's electricity, and the roof is DIDO. The Index can read the card's split with no new logic.

Two gaps:

1. **The note fixes the grid at `beyond`.** This pack's whole point is that grid power comes from different rings:
   Pesanggaran is in the city or the region, Celukan Bawang is on the island, Java is beyond. Writing every grid kWh as
   `beyond` throws away "where comes what". **Decided by Tomas, 8 Nov:** amend the note so a grid kWh carries the
   ring where it was made, split by this pack's shares (`consume.electricity.city`, `.region`, `.beyond`). No place has
   logged `electricity` yet, so the class isn't frozen and the change is allowed by the profile's own rule. Each source
   gets its ring in `grids.yml`, assigned against the Index's place boundaries. In Bali, where the Java share is a range
   (§5.3), the split uses the range's midpoint and says so.

   The amended note, which **rides in the energy PR** (Tomas, 8 Nov). The flows branch is 632 commits behind main, and
   its lint fails for reasons unrelated to this change:

   > `produce.electricity.cell` is the roof. A grid kWh carries the ring where it was made, split by the energy pack's
   > shares of the grid's sources (`consume.electricity.city`, `.region`, `.beyond`); a node with no energy pack logs
   > it as `beyond`.

   If `packs/flows/resources.yml` isn't on main when the energy PR opens, the line goes in with flows instead. The
   published vocabulary page needs a site rebuild and deploy, and that is asked for separately.
2. **The flows pack is not on main.** Until `resources.yml` and the `check_rules` vocabulary assertion reach main,
   the energy pack keeps its own metric names (`energy_roof_kwh`, `energy_grid_kwh`). When flows lands, it writes the
   same hourly kWh as `produce.electricity.cell` and `consume.electricity.<ring>`. That switch is one step in the plan,
   not a redesign.

Hydrogen would need a new class (kg) when it comes back. That is noted here and not proposed.

## 6. Constraints

- A core pack: Tomas wants it on Now for every node. `requires:` the node release it ships in.
- New-issue chores:
  - the update.sh 5d `energy:energy` pair, with the test that ties pairs to issue owners;
  - `energy` added to node #1's `PACKS_ENABLED` and `NODE_ISSUES` rows (DB rows override `.env`);
  - the `tests/all` line for every new suite;
  - the DOMAINS.md row and the packs page entry (a new docs page needs the site repo too);
  - the domain count in prose.
- Node #1 runs it before merge (CI green, then node #1 on the branch). **The measured Menorca path merges tested on
  recorded REE responses (Tomas, 8 Nov), and is proven on `mahon1` afterwards.** That's Lucas's machine, so ask him
  first. The PR names that as owed, and the REE licence check still comes before merge.
- Registry entries owed in awesome-fabcity-data: REE REData (licence quoted from the text), and PLN Statistik or Ember
  if used. OSM is already filed. The pack's `sources:` line waits until the node's registry pin reaches them.
- Python as the node runs it: the CLI is 3.9 stdlib, CI is 3.12, and local Python is 3.14.

## 7. Decided by Tomas, 8 Nov 2026

- The grid mix behind the node: sources, how far, where each part comes from.
- The node's cells, not the house. A household adds its own source.
- On Now, next to air, heat and water.
- Fossil share is the headline figure, and yearly is fine. In Bali, where Java's share is unknown, it is a range.
- Today's indicators sit beside it, so a household or lab is moved to act.
- Mockup **A**: the year first, today underneath.
- **Both** Bali and Menorca in the first version. Menorca merges on recorded REE responses and is proven on `mahon1` after.
- Grid power carries the ring where it was made (the `electricity` note in `fabcity-flows` is amended, §5.7).
- **Live** household readings, **through Home Assistant**. No house in the fleet has solar in HA yet, so that path ships tested on recorded responses only.

## 8. My calls, open to Tomas

- Core pack, not wild.
- OSM for infrastructure everywhere, plus one mix source per grid, with hand-written `grids.yml`.
- Straight-line distances.
- The HA read in the energy pack, leaving the HA pack one-way.
- A context issue with no line.
- No hero sign until `signs.svg` has one.
- Hydrogen deferred.
- Upstream sends at most a cell's rooftop kW.

## 9. Left to the builder

- The Bali estimate method (§5.3), within its order and labelling rules.
- How to draw the grid polygons, and whether Nusa Penida belongs to `bali`.
- Overpass query shape, storage tables and refresh timing, following Place.
- The REE request details, and the fallback if REE's terms fail.
- Exact sentence wording (voice: Tomas's, plain).
