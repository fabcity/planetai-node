# PLANETAI — Architecture

The whole building, drawn once, so every brick knows where it goes. What exists today is marked. What doesn't is
drawn anyway, because the contracts between layers are the thing that can't be retrofitted.

## 1. Three layers, one loop

```
                     ┌──────────────────────────────────────────────────────┐
                     │  INDEX        FCI = DIDO · (1 − PITO) · ρ             │
                     │  20 cells (4 pillars × 5 scales). ρ = action latency. │
                     └───────────────▲───────────────────────────▲──────────┘
                          cells (fci-cells-v0)             ρ (detect→act timestamps)
                     ┌───────────────┴──────────┐   ┌────────────┴─────────────┐
                     │  OBSERVE                 │   │  ACT                     │
                     │  store · aggregate ·     │──▶│  rules · alerts ·        │
                     │  publish (read API,      │   │  protocols · actions ·   │
                     │  maps, briefs)           │◀──│  fabrication queue       │
                     └───────────────▲──────────┘   └──────────────────────────┘
                                     │ readings
                     ┌───────────────┴──────────────────────────────────────┐
                     │  SENSE     adapters: our sensors · peer networks ·    │
                     │            open data · Earth models · people          │
                     └──────────────────────────────────────────────────────┘
```

**Sense** gets data in. Our own hardware, other people's networks (Bali Air Dispatch, OpenAQ, Sensor.Community),
open data portals (Bali Satu Data, Open Data BCN), Earth foundation models (Open-Meteo, Aurora, Flood Hub),
and people (surveys, reports, WhatsApp campaigns). Everything arrives as `readings` with a `sensor_id`, a metric,
a time, and provenance.

**Observe** stores, aggregates, and publishes. Every instance exposes the same read API. The public surfaces
(planetai.fab.city observatory, index.fab.city atlas and city pages) are clients of that API. Bali Air Dispatch is
an observatory instance for one island — a good one, and a source we read — not *the* observatory. PLANETAI's
observatory is the layer: any node, any aggregator, any region publishes the same shape.

**Act** turns an observation into a human decision and, when the decision is physical, a fabrication ticket.
Rules → alerts → acknowledgement → action → outcome. Each step is timestamped. Agents *draft, never dispatch*;
every dispatch is a human approval written to a ledger.

**Index** is what the other two layers measure themselves against. DIDO and PITO cells from Observe; ρ from Act.
The Act layer is the only place ρ can be measured, which is why the Index isn't a separate product — it's the
loop closing on itself.

## 2. One shape at every scale

Three ingestion classes, not one. A node at a house polls devices; a node at a lab also watches its city's portal;
a node anywhere on earth can sample a global model at its coordinates. Same core, same contracts, different `kind`:

| `sensors.kind` | what it is | cadence | scales it serves | shipped |
|---|---|---|---|---|
| `sensor` | a device on your LAN or a nearby public one | minutes | Community, City | Smart Citizen, AirGradient, PurpleAir |
| `portal` | an open-data or statistical API | days–months | City, Region, Bioregion | `ckan` (any CKAN portal) |
| `model` | a global model sampled at a point | hours | Planet, Bioregion | `openmeteo` |
| `survey` | people answering | campaign | Community, City | **not built** — the four empty Social cells |
| `child` | a node below this one | hourly | the scale below | the aggregate push |

Slow sources land in the `observations` view (latest per source per metric); sensors land in `stats` (15m/1h/24h).
Full matrix and gaps: [`docs/COVERAGE.md`](docs/COVERAGE.md).


The same three layers exist at every scale of the Full Stack Metrics Framework. A node at a house and an
aggregator for a province run the same code with different sources, different rules, and a different parent.

| scale | instance | sense | observe | act | index cells |
|---|---|---|---|---|---|
| **Community** | node at an address, a lab, a banjar | own sensors + nearby public sensors | readings, hourly means, local API | shut windows / ventilate / swap sensor / print a part | `*\|Community` |
| **City** | aggregator for a district or municipality | children's hourly means + municipal open data (Bali Satu Data, Open Data BCN) | district means, maps, public API | advisories to a kelian or a council; fabrication queue for a lab | `*\|City` |
| **Region** | aggregator for a province / metro | children + regional inventories (Metroverse, KLEMS, procurement) | regional feeds | inter-city coordination, procurement templates | `*\|Region` |
| **Bioregion** | partner-hosted server (BSC, MIT CBA, UC Chile, ITDel) | children + hydrology / biodiversity / boundary data | decision-tier dashboards, knowledge graph | community-council veto; OSH/OKH response library | boundary conditions |
| **Planet** | federation over Earth models | Aurora, GraphCast, GenCast, AlphaEarth | global summary | none directly — it informs | boundary conditions |

Aggregation of Index cells **stops at Region**. Bioregion and Planet enter as boundary conditions, not roll-ups.
That's the FCI 3.0 methodology and the architecture honours it: those two tiers publish context downward, they
don't summarise upward.

## 3. Contracts (the parts that must not change casually)

Every layer speaks three protocols. Compute, apps, and partner systems attach by speaking one of them.

**Readings** — `(ts, sensor_id, metric, value)` + a `sensors` row `(source, name, lat, lon, indoor, local, meta)`.
Up: children push hourly means (`POST /aggregates`). Down: anyone with a sensor or a phone posts raw
(`POST /readings`). The instance decides what it keeps.

**Cells** — `fci-cells-v0`: `{city, cell: "Pillar|Scale", value, unit, source, observed_at, state: live|partial|mock}`.
Exactly the `FCI Observations` row. Every instance exposes `GET /cells`. The Index surface (or the aggregator above)
pulls them. Provenance `state` travels end to end and is never upgraded on the way.

**Actions** — `{alert_id, stage: acknowledged|acted|measured, ts, note}` via `POST /actions`. This is how ρ is
measured: detect (alert `ts`) → decide (`acknowledged`) → deploy (`acted`) → measure (`measured`). Five FCC-era
stages collapse to these four at an address; `fabricate` appears between decide and act when the action is a part.

**Read API** (the Observe contract): `GET /sensors /readings /stats /aggregates /alerts /cells /rho /health`.
Same at every scale. A mobile app, the planetai.fab.city observatory, a partner's dashboard, and the aggregator
above are all just clients.

## 4. Compute can attach at both ends without moving anything else

The point of fixing the contracts is that compute is a *deployment decision*, not an architecture change.

**Downstream — phones and small devices.**
A mobile app is a client of the nearest node: reads `/stats` and `/alerts`, writes `POST /readings` (phone
sensors, photos, "burning here" reports) and `POST /actions` (I shut the windows). It needs no server of its own.
When on-device models arrive (classify a photo of smoke, run the tiny persistence model), they run against the same
endpoints. Federated participation, if ever wanted, is a `POST` of model deltas to the same node — the Flower
Android/iOS SDKs speak to a SuperNode that would sit next to the node's API. Nothing above the node changes.

**Upstream — clusters, data centres, frontier models.**
Every instance has one optional `UPSTREAM_MODEL_URL` (OpenAI-compatible chat/completions) and one optional
`UPSTREAM_COMPUTE_URL` (job submission). Point the first at Ollama on the same box, at vLLM on a regional cluster
(BSC for Barcelona, a partner HPC for Bali), or at a frontier API — the caller is identical. Point the second at
a district aggregator with a GPU, or at a cloud job runner, for things a node can't do: Earth-model inference,
federated training rounds, synthetic-control computation for H0-T. The node never *needs* upstream compute; it
*can use* it. Sovereignty is preserved by what travels (hourly means, cells, model deltas — never raw), not by
where compute happens.

**Peer — other observatories.**
An observatory instance that isn't ours (Bali Air Dispatch today; a city's own portal tomorrow) is a *source*.
Its readings enter through an adapter, flagged `local=false`, credited. If it exposes something like our read API,
one generic adapter reads it. This is how the network grows without owning everyone's data.

## 5. Where the Fab City Index plugs in

The Index has three ways data enters (index.fab.city methodology): observe, maintain data (adapters or operators),
run a campaign. The node is an **adapter that lives at the address**. Concretely:

The table below uses the Bali pilot because it is the one running. The same mapping applies at any site: swap the
named sources for whatever your place has, and where it has none, the global model still fills the reference row.

| cell (Bali pilot, as an example) | source at the node | state today |
|---|---|---|
| `Environmental\|Community` | local sensors: PM2.5 24h mean; days over WHO 24h in last 30d; sensor count | **live** as soon as node #1 runs 24h |
| `Governance\|Community` | ρ from the actions table; is a council/operator acknowledging alerts | **partial** until someone acts |
| `Economic\|Community` | fablabs.io activity for Fab Lab Bali (Fab Lab Activity Index, Boeing 2024) | adapter not written; **planned** |
| `Social\|Community` | participation: WhatsApp group size, campaign responses (Making Sense Bali pattern) | operator-entered; **mock → partial** |
| `Environmental\|City` | Bali Air Dispatch ambient means (peer observatory) + OpenAQ | **partial** (reference, not ours) |
| `Governance\|City` | Bali Satu Data open-data health | adapter not written; registry entry exists |

`GET /cells` emits whatever the node can honestly compute, each row carrying its `state`. The `Data Sources`
registry (synced from `awesome-fabcity-data`) needs one new entry — `environmental/community/bali-air-dispatch` —
proposed in `contrib/awesome-fabcity-data/`. Add the source via PR to that repo; the Airtable mirror follows.

**ρ is the brick nobody else has.** Two generations of the Index measured a snapshot with ρ implicit at 1. The node
measures ρ for real, because it's the thing sending the alert and the thing receiving the acknowledgement. Every
address running a node is a ρ instrument. That's the H0-A hypothesis reduced to a table with four columns.

## 6. Staging — the building, one brick at a time

Not a roadmap. Each stage names what exists, what it proves, and the trigger for the next.

**Stage 0 — now.** One node, two containers, ~650 lines. Sense: Smart Citizen 19880 + Bali Air Dispatch.
Observe: Postgres, hourly view, read API. Act: five rules → Telegram, `POST /actions` records acknowledgement.
Index: `GET /cells` emits `Environmental|Community` live and ρ partial. Compute: one Mac mini. *Proves:* a reading
becomes a message someone acts on, and the node reports that fact as a cell.
→ Trigger for Stage 1: five nodes alive 30 days, at least one `acted` row per node.

**Stage 1 — a district.** One aggregator (City scale) receiving hourly means from five nodes over Tailscale.
Sense adds: AirGradient LAN adapter (our first outdoor units), Bali Satu Data. Observe adds: district map on
planetai.fab.city reading `/aggregates` and `/cells` from the aggregator. Act adds: advisory to the banjar; the first
fabrication ticket (a printed enclosure, an air-filter frame) with `fabricate` timestamped. Index: `*|City` cells for
Bali go partial→live. *Proves:* the same code runs at two scales and ρ is measurable across a district.
→ Trigger for Stage 2: a second pilot city asks to run it, or Fab Academy 2027 adopts the module.

**Stage 2 — a second city, the observatory layer proper.** Barcelona node(s) on Smart Citizen's 15-year archive
+ Sentilo + Open Data BCN. The observatory reads two countries through one API. Upstream compute appears for real:
`UPSTREAM_MODEL_URL` → vLLM at BSC or ITDel; a first federated round if — and only if — there's a model averaging
can't express. Index: two pilots' Community and City cells live; the phase plot (ΔFCI/Δt) gets its first two points.
→ Trigger for Stage 3: 30 nodes across ≥2 bioregions, a paying operator behind most.

**Stage 3 — bioregion and planet as boundary conditions.** Partner-hosted bioregion servers publish context down
(hydrology, boundaries, Earth-model summaries). Community-council veto is a real gate on what the observatory
publishes. Mobile app ships as the domestic client. The Index publishes a quarterly ΔFCI/Δt per pilot.

## 7. Refusals that hold across stages

No raw readings leave the instance that recorded them. No cell is upgraded from mock or partial to live by
aggregation. No agent dispatches without a human row in `actions`. No layer requires a cloud provider to function.
No scale is skipped: a city aggregator is built from nodes, not declared from above.
