# Concepts

The words the rest of these pages use, each with what it means in the code. When two of them sound alike
— `local` and `custody`, domain and issue, `kind` and `scale` — the difference is the point.

## The node and its place

**Node.** The program at one address: two containers, one database, one API. It has a name (`NODE_NAME`,
lowercase with dashes), a position (`NODE_LAT`, `NODE_LON`), a time zone (`NODE_TZ`) and a city key
(`NODE_CITY`). Node #1 is `bayu-2` in Kuta Selatan; node #2 is in Menorca.

**Kind** (`NODE_KIND`): `home`, `business`, `community` or `district`. What the node is for. It is not the
Index scale; the setup wizard sets `NODE_SCALE=city` when the kind is `district`.

**Scale** (`NODE_SCALE`): `community`, `city` or `region` — the Full Stack Metrics Framework's scales, of
which a node declares one. It is stamped on every sensor and every push, and it names the core's own cell,
`Governance|<Scale>`. Metadata, not code.

**The H3 cell.** The node stands in a hexagon of the H3 grid at resolution 8 — an edge of roughly half a
kilometre; 525 m for node #1's cell — printed in the mono as a fifteen-character id such as
`8839446033fffff`, with its edge length beside it. Resolution 8 is coarser than the three-decimal rounding of the node's position, so
publishing the cell does not put the position back. The dashboard's ground is that cell, its six neighbours
and its seven resolution-9 children.

**Issue.** What a household calls a quality of its place: `air`, `heat`, `land`, `coast`, with water, noise
and energy designed. Declared one file each in `app/issues/*.yml`, ordered by `NODE_ISSUES` — the keeper's
order, most important first. An issue is *sensed* when it has eyes on it and rules that can ask for
something, *context* when it informs and never asks. See [Issues](issues.md).

**Domain.** What a pack declares it is about. Fewer issues than domains: weather feeds air and heat but
nobody asks how the weather is doing as a quality of their place; place is the ground; governance is the loop
and the Index; trust is the instruments.

## Sources and sensors

**Adapter.** One function returning `(sensors, readings)`. In `app/sources.py` for the sources that ship
with the core; in a pack's `adapter.py` for a code pack. The contract is on the [sensors](sensors.md) page.

**Sensor.** A row in `sensors`: `sensor_id`, `source`, `name`, `lat`, `lon`, `indoor`, `local`, `kind`,
`scale`, `cadence`, `meta`. The id is `<source>-<upstream id>` — `sc-19880`, `bad-pa-46949` — stable and
never reassigned.

**`local`.** Two facts at once: an adapter says whether a sensor is *yours*, and the node checks whether it
is *here*, within `LOCAL_RADIUS_M` (500 m) of the node. A kit on your account 1.2 km away is yours and is
not this node's measurement. A sensor with no coordinates that arrives over your own gateway stays local.

**`indoor`.** Carried on every sensor and honoured by every rule. An indoor sensor measures a room and never
enters an ambient average.

**`kind`.** How the number was produced: `sensor`, `portal`, `model`, `map`, `child`, `peer`, with `survey`
reserved. Only `sensor` rows enter `stats`.

**`custody`.** A generated column: `kind = 'child' OR (local AND kind <> 'peer')`. The only thing a cell may
count, and the thing that may roll up to a parent. Custody splits geography from responsibility: a peer's
station can be closer than your own kit and still never be counted.

**Peer.** Another node whose numbers you may show and must never act on. A `kind='peer'` row reaches no
cell, no custody count, no aggregate, no alert, no report line.

**Channel role.** What a metric *is* for a given source, declared in `channels.yml` and written to
`channel_roles`: `ambient` (the air, water or land at a place — comparable between sensors there),
`enclosure` (the inside of the instrument's own box — a BME680 sealed in a radio reports the box, not the
street), `device_health` (battery, radio utilisation), `derived` (computed by us), `index` (a vendor's own
composite, never pooled).

**Metric names.** Lowercase, no units in the name: `pm25 pm25_raw pm10 pm1 temp humidity pressure aqi
gas_resistance noise light eco2 tvoc co2 tvoc_index nox_index`. Units are fixed: µg/m³, °C, %, kPa. `pm25`
is the published value; if a correction was applied, the uncorrected figure sits beside it as `pm25_raw`.
Raw is never overwritten.

**The four distances.** Where a reading comes from, nearest first: `room` (local, indoor), `yard` (local,
outdoor), `ring` (somebody else's device near here) and `region` (a model, a portal — what only the models
know). A child node is a fifth place that is not a column. In Bahasa: ruangan · halaman · sekitar · wilayah.

## Rules, alerts, actions

**Rule.** SQL that returns rows, plus a message template with `{placeholders}` for the row's columns, a
`level` and a `cooldown_minutes`. No rules engine, no expression language: if Postgres cannot express the
condition, the condition is wrong. Core rules live in `config/rules.yml` and know no metric; a pack's
rules live in `packs/<id>/rules.yml`, namespaced `<pack>/<id>`.

**Level.** `act` — something needs doing; `warn` — something changed; `info` — everything else.
`ALERT_LEVEL` is the floor for interrupting a person; below it an alert is still recorded, still on the
dashboard, still in the next report.

**Alert.** A row in `alerts` (`ts`, `rule_id`, `sensor_id`, `level`, `text`), whether or not it was sent.
Three paragraphs: what is happening, what it means, what to do.

**Cooldown.** Per rule and sensor, enforced in SQL against `alerts`: a rule does not fire again for the same
sensor until its cooldown has passed.

**Action.** A row in `actions`: `alert_id`, `stage`, `actor`, `note`. Stages `acknowledged` (someone saw it),
`acted` (someone did the thing), `measured` (the outcome was checked — in the schema, written by nothing yet),
and `settings` (an audit row for a setting change, with no alert). This table is the Index's instrument, not
an app feature.

**ρ (rho).** The share of act-level alerts in the last 30 days that had an `acknowledged` or `acted` action
within 24 hours, pooled with the children's events. The one number on the page that comes from a person.
See [ρ](rho.md).

**Report.** The node's one scheduled message: every `REPORT_EVERY` hours from `REPORT_ANCHOR`, local time,
six parts, under a hundred words, written by the node itself from SQL. See [The report](report.md).

## Packs and cells

**Pack.** A folder in `packs/` with a `pack.yaml`. A *data pack* is YAML only: rules, cells, channel roles. A
*code pack* also carries an `adapter.py` and runs only when `PACKS_ALLOW_CODE=1`. See [Packs](packs.md).

**Cell.** One of the twenty cells of the Fab City Index — four pillars (Environmental, Economic, Social,
Governance) by five scales (Community, City, Region, Bioregion, Planet) — written `Pillar|Scale`. A pack's
`cells.yml` computes a value with SQL that returns one `value`.

**State.** Provenance, not confidence: `live` means measured here, in custody, in the last 24 hours;
`partial` means derived, modelled, or from a portal; `mock` means a placeholder. The core demotes `live` to
`partial` when there are too few hourly buckets or too few sensors, and aggregation never upgrades it.

**Contributor.** A rule with `contributes: report` and no message. Never sent; its first row lands in the
report bundle under the rule's id.

## Reaching the node

**`SHARE_LEVEL`.** What a request with no token may read: `off` (the dashboard shell, `/health`, `/presence`, the daily export, and `/settings` reduced to the layout and the sharing level — nothing else) or `open` (the whole read API, which is what a wall screen without a
token needs). Two more rungs, `cell` and `means`, are named and refused. See [Sharing](sharing.md).

**Tokens.** `ADMIN_TOKEN` unlocks every write and the agent surface; `BACKUP_TOKEN` is read-only, for a NAS
pulling dumps and the report bundle; `ACT_TOKEN` closes a loop from a phone and can read no secret;
`AGGREGATE_TOKEN` is what this node demands from its children; `PARENT_TOKEN` is what it presents to its
parent. All travel as `Authorization: Bearer <token>`.

**Loopback.** A request from `127.0.0.1` inside the container — the node's own MCP tools, a shell in the
container — is trusted without a token. A browser on the host machine arrives from Docker's bridge and is
not loopback.

**Parent and child.** A child posts hourly means to its parent's `/aggregates` and alert timestamps to
`/events`; the parent stores them under `<child>/<sensor_id>` with `kind='child'`. Raw never travels the
link. See [Federation](federation.md).

**The tailnet.** Tailscale, joined with `planetai mesh`. The node is reachable by its MagicDNS name, `<name>.<your-tailnet>.ts.net`, from your devices with no open port. The answer to "how do I reach it from outside" is always this, never a port
forward.

## Provenance words on the page

`live` — measured by this node, room or yard. `partial` — derived, a portal, the ring. `model` — a model
row. `cached` — a committed fixture replayed through the node's own engine. `stale` — a fixed label in the wall's foot in this version; the page does not yet judge staleness. `refused` — not a word but a page: what a reader without a token sees at
`SHARE_LEVEL=off`, with the node's own sentence explaining why. Provenance is ink only and square, never a
coloured pill.
