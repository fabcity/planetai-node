# How it works

Two containers on one machine: `db`, Postgres with PostGIS, bound to the machine itself; and `app`, one
Python process that runs the HTTP API on port 8080 and four loops in the background, a fifth when the Reticulum bridge is on. Everything a node does
is one of those loops or one of the API's answers. This page follows a reading through the whole of it.

## Three layers, one loop

```
   INDEX      the twenty cells of the Fab City Index · ρ, the share of alerts that led to an action
     ▲ cells                                          ▲ ρ
   OBSERVE    store · aggregate · publish        ACT   rules · alerts · actions
     ▲ readings                                   ▲ what a person did
   SENSE      adapters: your sensors · other people's stations · open data · Earth models
```

**Sense** gets data in. Every adapter — a Smart Citizen kit, the ring of Bali Air Dispatch stations, a CKAN
portal, the Copernicus model sampled at your coordinates, a pack's own `adapter.py` — returns the same two
things: a list of sensors and a list of readings `(ts, sensor_id, metric, value)`. The core does not know what
`pm25` means. It stores rows.

**Observe** stores, aggregates and publishes. Readings land in one table; three views do the arithmetic —
`stats` (the last 24 hours per sensor and metric: 15-minute, hourly and daily means, and how long a sensor
has been silent), `readings_1h` (hourly means over all history) and `observations` (the latest value from
every slow source: a portal, a model, a map). Every node exposes the same read [API](api.md). The
dashboard, the CLI, the bot and a NAS are its clients; a parent node is what it pushes to.

**Act** turns an observation into a human decision. A rule is SQL that returns rows plus a message
template; the loop runs every rule once a minute, and every row that comes back is a candidate alert. A
cooldown per rule and sensor stops it repeating; a level decides whether it interrupts anyone; quiet hours
hold everything but `act`. The alert goes out on [Telegram](channels.md), the LoRa mesh, LXMF and Home
Assistant. When a person does something about it, that is recorded as a row in `actions` — from the
dashboard, `planetai act`, `/act` in Telegram or an agent.

**Index** is what the other two layers measure themselves against. A pack's `cells.yml` computes the Fab
City Index cells the node can honestly fill, each carrying a `state` — `live` if measured here, `partial` if
derived or modelled — and the core adds one cell of its own: `Governance|<scale>`, which is [ρ](rho.md), the
share of act-level alerts that led to an action within a day. Two generations of the Index measured a
snapshot with ρ implicit at 1. A node measures it, because it is the thing sending the alert and the thing
receiving the acknowledgement.

## The loops

| loop | every | what it does |
|---|---|---|
| poll | `POLL_SECONDS` (300) | asks every enabled adapter for sensors and readings and upserts them; a source that fails leaves its error in `/health.last_error`; a loop that fails outright appears under its name in `/health.errors` |
| rules and report | 60 s | writes the [report](report.md) if its hour is due, then runs every rule as the read-only role `planetai_ro` |
| push aggregates | hourly | if `PARENT_API_URL` is set, posts the last two hours of hourly means to the parent's `/aggregates` |
| push events | hourly | if `PARENT_API_URL` is set, posts this node's alert timestamps of the last 36 hours to the parent's `/events` |
| Reticulum | 300 s | only with `RETICULUM_URL` set: asks the bridge for its health and the peers it has heard, for `/health.reticulum`. An `act <id>` message is turned into `POST /actions` by the bridge itself |

One more thread runs when `MQTT_HOST` is set: it subscribes to the broker for Meshtastic radios and DIY
sensors and publishes Home Assistant discovery entities.

## One shape at every scale

A node at a house polls devices. A node at a lab also watches its city's open-data portal. A node anywhere
can sample a global model at its coordinates. Same code, same contracts; what differs is the `kind` of each
source and the `scale` the node declares:

| `sensors.kind` | what it is | cadence | lands in |
|---|---|---|---|
| `sensor` | a device on your LAN, or a nearby public one | minutes | `stats` |
| `portal` | an open-data or statistical API | days–months | `observations` |
| `model` | a global model sampled at a point | hours | `observations` |
| `map` | what is around the node, from OpenStreetMap | monthly | `observations` and PostGIS tables |
| `child` | a node below this one, pushing hourly means | hourly | `readings`, as `<child>/<sensor_id>` |
| `peer` | another node whose numbers are shown, never counted | — | display only |

Aggregation of Index cells stops at Region. Bioregion and Planet enter as boundary conditions — context
published downward, never rolled up — which is the Index's own methodology and the architecture honours it.

## What leaves the machine, and what never does

Raw readings stay. What travels is a summary: hourly means and alert timestamps to a parent node, if there
is one; the daily [export](storage.md) — hourly means by role (`indoor-1`, `outdoor-2`), cells, the first line
of each alert, ρ, the node's position to three decimals — under CC BY 4.0; a coarse H3 cell on the Reticulum
network if presence is turned on; and, only if you give a model a key, the question you asked the bot. Exact
coordinates, room names, sensor ids and a household's own sentences never leave. `/health` rounds the node's
position to about 110 m for everyone, and the shape of the building behind `/place/geojson` needs a token at
every [sharing level](sharing.md).

## Where the decisions live

| decision | where |
|---|---|
| what a metric means, thresholds, messages | a pack's `rules.yml` — see [Packs](packs.md) |
| which cells the node fills | a pack's `cells.yml` |
| what a metric *is* — ambient, the box, battery, derived | `channels.yml`, core and per pack |
| what a place watches, and in which order | `NODE_ISSUES`, declared in `app/issues/*.yml` — see [Issues](issues.md) |
| how the node speaks | `ALERT_LOCALE`, `ALERT_LEVEL`, `QUIET_*`, `REPORT_*` — see [Configuration](configuration.md) |
| who may read it | `SHARE_LEVEL` and four tokens — see [Sharing and security](sharing.md) |
| what is retired and when it returns | [`SPEC.md`](spec.md) §6 |

## Refusals that hold at every stage

No raw readings leave the instance that recorded them. No cell is upgraded from `partial` to `live` by
aggregation. No agent dispatches without a human row in `actions`. No layer requires a cloud provider to
function. No scale is skipped: a city aggregator is built from nodes, not declared from above. The longer
form, with the staging from one node to a bioregion, is [Architecture](architecture.md).
