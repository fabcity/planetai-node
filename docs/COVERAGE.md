# Coverage — the node against the Fab City Index matrix

The Index is twenty cells: four pillars (Environmental, Economic, Social, Governance) across five scales
(Community, City, Region, Bioregion, Planet). A node is not a Community-scale sensor box that happens to publish
upward. It is an ingestion and decision engine that can fill cells at any scale — the *kind* of source changes, not
the architecture.

This page is the honest map: what fills today, what the source registry already knows about, and what nobody has built.

## 1. What a cell needs at each scale

| scale | what a number describes | how it arrives | cadence | `sensors.kind` |
|---|---|---|---|---|
| **Community** | this address, this block, this lab | a device you own on your LAN, or a nearby public sensor | minutes | `sensor` |
| **City** | a municipality, a district | an open-data portal (CKAN, Socrata, ArcGIS), a municipal sensor network, a peer observatory | days | `portal` |
| **Region** | a province, a metro area, a grid zone | statistical APIs, grid operators, regional GIS, economic complexity data | months | `portal` |
| **Bioregion** | a watershed, a biome, a procurement zone | hydrology and biodiversity datasets, procurement feeds, material-flow accounts | months | `portal` |
| **Planet** | boundary conditions | Earth-observation models and global datasets, sampled at your coordinates | hours to years | `model` |

Two rules from the methodology that the code enforces:

**Aggregation stops at Region.** Bioregion and Planet publish context *downward*; they are never rolled up into a
higher cell. An Open-Meteo point sample tells a node what the atmosphere is doing above it. It is not that node's
measurement and never becomes one.

**Provenance never improves on the way up.** A cell is `live`, `partial` or `mock`, and no aggregation upgrades it.
A pack may not claim `live` before the data supports it — the core checks bucket counts and demotes the claim.

## 2. The matrix today

Sources counted from the Index's own registry (`Data Sources`, synced from `awesome-fabcity-data`), 32 entries
across four pilots — Bali, Barcelona, Boston, Santiago — plus global.

|  | Community | City | Region | Bioregion | Planet |
|---|---|---|---|---|---|
| **Environmental** | **3** · Smart Citizen, AirGradient, iNaturalist | **3** · OpenAQ, Sensor.Community, Google AQ | — | **2** · Caravan hydrology, GBIF | **3** · Open-Meteo, Aurora, Flood Hub |
| **Economic** | **1** · Fab Lab Activity Index | — | **3** · Metroverse, Asian KLEMS, LAKLEMS | **1** · materialflows.net | **2** · Atlas of Economic Complexity, What a Waste |
| **Social** | — | — | **3** · GDELT, WHO, IHME GBD | — | — |
| **Governance** | — | **4** · Open Data BCN, Analyze Boston, datos.gob.cl, Bali Satu Data | **3** · MassGIS, Generalitat, ENTSO-E | **3** · TED, ChileCompra, LKPP/SPSE | **1** · OONI |

Seven of twenty cells have no source at all: `environmental|region`, `economic|city`, `governance|community`, and
**four of the five Social cells**. Social is the weakest pillar in the whole framework, and no amount of sensor
deployment fixes it — it needs surveys, participation records and civic data, which is a `kind: survey` adapter
nobody has written.

## 3. What a node fills, right now

| cell | how | pack | state |
|---|---|---|---|
| `Environmental\|Community` | your own sensors: PM2.5 24h mean, WHO exceedance days | `air-quality` | the 24h mean reaches **live** after 12 hourly buckets; the exceedance-day cell stays `partial` (it needs 30 days) |
| `Environmental\|City` | nearby public sensors, read as reference | `air-quality` | `partial` — never `live`, it isn't our measurement |
| `Governance\|City` | CKAN portal maintenance: share of datasets touched in 90 days | `open-data-health` | `partial` |
| `Governance\|Community` | **ρ** — share of act-level alerts a human answered within 24 h | core, every node | `partial` → `live` at 5 acted alerts |

That last row is the interesting one. `governance|community` is one of the seven cells the registry has **no source
for**, because no dataset exists that says whether people act on what they know about their own street. A node is the
source. That is the strongest argument for this architecture that doesn't involve a single sensor.

## 4. What ships to reach further up

Three adapter classes exist in `app/sources.py`. Only the first is about hardware.

**`sensor`** — Smart Citizen (cloud API), AirGradient and PurpleAir (LAN, no cloud). Community scale, minutes.

**`portal`** — the `ckan` adapter reads *any* CKAN portal. Four of the registry's `governance|city` sources are CKAN,
so one adapter covers Barcelona, Boston, Santiago and Bali. It asks the question the Index needs: how much of this
city's data was touched in the last 90 days.

```bash
CKAN_PORTALS=open-data-bcn=https://opendata-ajuntament.barcelona.cat/data,analyze-boston=https://data.boston.gov
```

**`model`** — the `openmeteo` adapter samples a global weather model at the node's coordinates. Free, key-free,
works at any point on earth. This is the one adapter that needs nothing local at all: a node in a city with no sensors
still has something true to say about the air above it. Planet scale, boundary condition, never aggregated upward.

Slow sources don't belong in a 24-hour rolling view, so they land in `observations` (latest value per source per
metric) rather than `stats` (15m/1h/24h, sensors only). Rules and cells read whichever fits.

## 5. What's missing, in the order I'd build it

1. **Socrata and ArcGIS adapters.** `analisi.transparenciacatalunya.cat` is Socrata; MassGIS is ArcGIS REST. Two adapters, the same shape as `ckan`, and `governance|region` fills for Barcelona and Boston. Cheapest real gain on the matrix.
2. **A `survey` kind.** Four empty Social cells, and the thing that fills them is participation data a node's operator already has: how many people are in the alert group, how many answered the last campaign, how many acted. This is the Making Sense pattern and it needs a form, not a sensor.
3. **Procurement adapters** — TED, ChileCompra, LKPP. All three are already in the registry under `governance|bioregion`, all three are tagged `action-latency`, and all three measure ρ at institutional scale: how long between a decision and a contract. That's the same number the node measures at an address, four scales up.
4. **`economic|city`** — completely empty and arguably the Fab City question. A fab lab's own machine log is the closest available proxy: hours run, jobs completed, material consumed. Nobody outside the network can produce it.
5. **Earth-observation with geometry.** Open-Meteo is a point sample. Real bioregion work — Caravan for a watershed, GBIF for a biome, Sentinel imagery — needs polygons and raster handling. Heavier, and the trigger is a bioregion partner asking for it.

## 6. Reading the map honestly

A node at one address fills two cells well and contributes to two more. That is not a planetary observatory, and
saying so would be dishonest. What it is: the smallest working piece of one, with the ingestion classes for the other
scales already present and one adapter each proving they work.

The number that matters isn't cells filled. It's whether a cell that gets filled changes what someone does — which is
why `Governance|Community` is the cell we can produce and nobody else can.
