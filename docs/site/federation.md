# Federation and the Index

A node at a house and an aggregator for a district run the same code with different sources, different
rules and a different parent. What connects them is three small contracts — readings up, cells out, actions
in — and a set of refusals that hold at every scale. This page is the contracts. The reasoning behind them is
[Architecture](architecture.md); the cells a node can fill today, and the ones nobody fills yet, are on
[Coverage](coverage.md).

## Parent and child

A node with `PARENT_API_URL` set (a tailnet hostname, once a district node exists) pushes to its parent
every hour, presenting `PARENT_TOKEN`:

**`POST /aggregates`** — the last two hours of hourly means:

```json
{"node": "bayu-2", "scale": "community",
 "rows": [{"bucket": "2026-09-16T05:00:00Z", "sensor_id": "sc-19880", "metric": "pm25",
           "mean": 12.4, "min": 9.1, "max": 17.0, "n": 12}]}
```

The parent keeps the `mean` as one reading on the child's own hour, under the sensor `<child>/<sensor_id>`
with `source='child'`, `kind='child'`, `cadence='PT1H'`, `local=FALSE` — and, because custody is
`kind='child' OR …`, in custody; the metric keeps its own name, so a parent's pack SQL matches it. `min`,
`max` and `n` travel and are not stored in this version. A child's sensors have no coordinates at the
parent, and a re-push is idempotent.

**`POST /events`** — the last 36 hours of alerts, as timestamps only:

```json
{"node": "bayu-2", "scale": "community",
 "rows": [{"alert_id": "812", "raised_at": "…", "rule": "air-quality/indoor_pm25_high", "level": "act",
           "kind": "air-quality", "responded_at": "…", "acted_at": "…", "measured_at": null}]}
```

`kind` is the pack prefix of the rule id — the pack is the domain tag.

No text, no actor, no sensor, no note, no ratio: the parent computes [ρ](rho.md) under whatever definition
it runs, pooled with its own alerts. A row without `alert_id` or `raised_at` is skipped.

The parent accepts children only when `AGGREGATE_TOKEN` is set, and refuses with "this node accepts no
children" otherwise. Raw readings never travel the link; a parent never sees a child's rows, its room names,
its people or its coordinates.

## Cells — `fci-cells-v0`

Every node exposes `GET /cells`: the Fab City Index cells it can honestly compute, one row per cell,
exactly the shape of an `FCI Observations` row:

```json
{"city": "bali", "cell": "Environmental|Community", "value": 11.8,
 "unit": "µg/m³ PM2.5 (24h mean, sensors in this node's custody)",
 "source": "planetai-node · pack:air-quality", "observed_at": "2026-09-16T06:00:00Z",
 "state": "live", "notes": "your own outdoor and indoor kits, hourly means, last 24 h"}
```

`state` is provenance and travels end to end: `live` — measured here, in custody, in the last 24 hours;
`partial` — derived, modelled, from a portal, or demoted for too few buckets or sensors; `mock` — a
placeholder. **It is never upgraded on the way**: a parent's cell is `partial` if any input was, and `live`
at a parent needs in-custody measurement in the last 24 hours at the parent's own rung — from at least two
sensors, across at least two children where there are children. One child reporting is one household's
kitchen. A cell with no source is absent, not zero.

Aggregation of cells stops at Region. Bioregion and Planet publish context downward as boundary conditions
and are never rolled up.

## Publishing to the Index

**One node per pilot writes to the Index. A home node never does.** A pilot city has one City-tier node,
run by the partner accountable for that city's numbers; it is the only node in that city whose cells reach
the Index's spine. Every other node — every home, lab, classroom and community centre — computes its own
cells, shows them on its own dashboard, and passes them no further. That is not a lesser rung; it is the
architecture: readings stay where they were made, and exactly one identified operator per city stands behind
what the Index publishes.

The writer, `cells-ingest`, lives with the Index's own code, not in this repository. It refuses to run
without `FCI_PUBLISHER=1` and a per-pilot write token issued by hand. Nothing in the node publishes, and
`SHARE_LEVEL` has nothing to do with it: sharing is reach on your own network, publishing is a different act
gated by the tier contract and a token issued to a person. To publish: confirm the tier; run `planetai cells
--json` and read every row's `state`; if a row is wrong, fix the source or the pack, not the label; then
write to **info@fab.city** with the node's name, the city and that output.

The Index's own methodology, sources and cells are at [index.fab.city](https://index.fab.city). The
discovery list of every open data source the network has found, organised by pillar and scale, is
[`awesome-fabcity-data`](https://github.com/fabcity/awesome-fabcity-data); a source a pack reads should be
a row there first.

## The registry

`registry.json` in the repository is the node directory until there are too many nodes for a file: `name,
scale, operator, place, lat, lon, sources, parent, since, contact`. Adding a node is a pull request; approval is a merge. A registry
service with a signed handshake returns when PRs stop scaling — roughly thirty nodes or a second operator
organisation — with its trigger written in [`SPEC.md`](spec.md) §6.

## Peers

An observatory that is not ours — Bali Air Dispatch today, a city's own portal tomorrow — is a source. Its
readings enter through an adapter, flagged `local=FALSE`, credited. A `kind='peer'` row — another node's
numbers, shown for context — reaches no cell, no custody count, no aggregate and no alert, whatever its
coordinates say. This is how the network grows without owning everyone's data. Listening to other nodes as
peers (`PEERS`) is proposed and not built in this version.

## The commons

The daily export — `GET /export?day=` written nightly to `exports/<node>/` — is what a parent, the Index, a
researcher or the commons should receive: hourly mean, min, max and count per sensor and metric, the cells,
the first line of each alert, ρ, the node's coordinates to three decimals; sensors named by role
(`indoor-1`, `outdoor-2`) rather than id; no raw rows, no tokens, no chat ids; CC BY 4.0 stated in the file as `licence`; each source's own attribution is in its sensor's `meta` on `/sensors`, not in the export. `planetai ipfs` pins it on IPFS; the
database and its dumps never go there.

## The refusals

No raw readings leave the instance that recorded them. No cell is upgraded from `mock` or `partial` to
`live` by aggregation. No agent dispatches without a human row in `actions`. No layer requires a cloud
provider to function. No scale is skipped: a city aggregator is built from nodes, not declared from above.
Peers never roll up and never drive an alert or a report line. Exact place never leaves; a coarse cell may,
and says how coarse. Exactly one node per pilot writes to the spine.

## Where the network is

Node #1, `bayu-2`, Kuta Selatan, Bali, since 2 September 2026 — Meaningful Design Group, community scale,
a Smart Citizen kit and the Bali Air Dispatch ring. Node #2, Menorca, on Linux put onto a 2015 laptop. Stage 1 — a district aggregator receiving hourly means from five nodes over
the tailnet — begins when five nodes have been alive thirty days with at least one acted alert each.
