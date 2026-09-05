# PLANETAI Node — Spec v0.1

2 September 2026. Two containers. This document is the brick; `ARCHITECTURE.md` is the building. Everything here is
either a contract that must survive rewrites, or a retired piece with the condition that brings it back.

## 1. Contracts

These are the things node #7 needs to share with node #1. They cost nothing to keep and everything to lose.

**Sensor identity.** `sensor_id` is `<source>-<upstream id>`: `sc-19880`, `bad-pa-46949`, `ag-<serial>`. Stable, human-readable, never reassigned.

**Local vs reference.** `sensors.local = TRUE` means the sensor is physically at this node and we're responsible for it. `FALSE` means context pulled from a public network. Rules and pushes treat them differently; the distinction is the whole point of a node.

**Indoor.** `sensors.indoor` is carried on every sensor and honoured by every rule. Indoor sensors never enter an ambient average. Inherited from Bali Air Dispatch's `suspected_indoor`.

**Domain neutrality.** The core evaluates rules and cells; it does not know what a metric means. Thresholds, messages and pillar mappings live in packs; `app/main.py`, `app/index.py` and `app/packs.py` must name no domain metric. Adapters in `app/sources.py` do name metrics — they translate a device's fields into the schema, which is a driver's job, not a domain's.

**Metric names.** Lowercase, no units in the name. Air today: `pm25 pm25_raw pm10 pm1 temp humidity pressure aqi gas_resistance noise light eco2 tvoc co2 tvoc_index nox_index`. Other domains propose their own in `docs/DOMAINS.md` — first pack to ship a metric names it. Units are fixed: µg/m³, °C, %, kPa. `pm25` is the *published* value; if a correction was applied, the uncorrected figure sits next to it as `pm25_raw`. Never overwrite raw.

**Time.** Readings are UTC instants. Daily anything is a `NODE_TZ` calendar day (WITA in Bali), because the burn pattern has a 9am peak and an after-dark climb and a UTC day cuts the evening in half. Say which basis you're on.

**Rules.** A rule is SQL that returns rows plus a message template. Cooldown is enforced in SQL against the `alerts` table. No rules engine, no expression language. If Postgres can't express the condition, the condition is wrong.

**Up-link.** Child → parent is `POST /aggregates {node, rows:[{bucket, sensor_id, metric, mean, min, max, n}]}`, hourly. Raw never travels it. The parent stores rows as `<child>/<sensor_id>`, metric `<metric>_1h`.

**Registry.** `registry.json` in this repo. Fields: name, scale, operator, place, lat, lon, sources, parent, since, contact. Adding a node is a PR. Approval is a merge.

**Cells.** `fci-cells-v0` — `{city, cell:"Pillar|Scale", value, unit, source, observed_at, state}`. Exactly the `FCI Observations` row (base `appmNQaDGEFE9VcYh`). `state` is never upgraded by aggregation.

**Actions.** `{alert_id, stage: acknowledged|acted|measured, actor, note}`. ρ is computed from these against `alerts`. This is the only place ρ can be measured, so this table is the Index's instrument, not an app feature.

**Scale vocabulary.** `community | city | region | bioregion | planet` — the Full Stack Metrics Framework's scales. A node has one. It's metadata, not code.

## 2. What runs

| | |
|---|---|
| `db` | postgres:16-alpine. Bound to localhost. Volume `db`. Nightly `pg_dump` via `backup.sh`. |
| `app` | Python 3.12. Three timer threads (poll, rules, push) + FastAPI on :8080. ~210 lines. |

`GET /health /sensors /readings /stats /alerts /aggregates /cells /rho` · `POST /aggregates` (parent) · `POST /actions` (ρ) · `POST /readings` (downstream contributors).

Compute at node #1: an M-series Mac. Postgres and one Python process idle at under 200 MB. A Pi 4 with 2 GB does this without noticing.

## 3. Sources (adapters)

An adapter is a function returning `(sensors, readings)`. Two ship; see `docs/sensors.md` for the next four.

- `smartcitizen` — polls `api.smartcitizen.me/v0/devices/<id>`. Maps on measurement *name* so SCK 2.1 and 2.3 both work. Marks `indoor` from the kit's `exposure`. `local = TRUE`.
- `baliairdispatch` — polls `baliairdispatch.com/api/v1/latest`. Drops `stale`, keeps stations within `BAD_RADIUS_KM`, stores `pm25` and `pm25_raw`, carries `suspected_indoor`. `local = FALSE`. Attribution: Bali Air Dispatch + the row's network.

## 4. Security, v0.1

Nothing listens on the network except `app:8080` (LAN). Postgres is localhost-only. `.env` is `chmod 600`, never committed. No mesh, no auth, no TLS — because no packet crosses a network boundary yet. The moment node #2 exists on another network, §6 applies.

## 5. Update and rollback

`./update.sh`: backup → pull → apply schema to the live database → rebuild → verify. See [`docs/UPDATING.md`](docs/UPDATING.md).

The non-obvious part, and the one that bit us: Postgres runs `init.sql` **only when the data volume is first created**.
A running node never sees new columns or views unless something applies them. So `init.sql` is the whole schema, written
idempotently (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`, `DROP VIEW` then `CREATE VIEW` —
because `CREATE OR REPLACE VIEW` cannot reorder columns), and both fresh installs and updates apply the same file.
`schema_version` records where a node is; `/health` reports it.

Schema changes are **additive only**. No dropped columns, no renames, no destructive migrations — which is what makes
rollback `git checkout <tag> && docker compose up -d --build` rather than a restore. Breaking that needs a major version
and a written migration.

## 6. Staged upgrades — retired pieces and their triggers

Each was built, audited, and cut on 2 September 2026. None is lost; each returns on its named condition, not on a
roadmap. Four triggers have since fired, and they are struck through below rather than deleted, so the record of
what was deferred and why stays legible.

| piece | returns when | what it looks like |
|---|---|---|
| **Mesh (Tailscale)** | ~~node #2 exists on a different network~~ **fired, v0.7** | `planetai mesh`; `PARENT_API_URL` becomes a tailnet hostname. See `docs/NETWORKING.md` |
| **Headscale** (self-hosted control plane) | a partner's governance requires no third-party coordinator, or the free tier is exceeded | swap the login server; nothing else changes |
| **MQTT broker** | ~~the first sensor that publishes~~ **fired, shipped v0.8** | `mqtt` profile; `planetai meshtastic`; `msh/#` and `planetai/sensors/#` |
| **Reticulum** bridge (LXMF inbox/outbox) | ~~—~~ **shipped v0.8**: `planetai reticulum`, TCP today, RNode a config block | `reticulum` profile |
| **Reticulum** node-to-node data transport | a district and a community node with no internet between them | Transport-enabled node + store-and-forward; see `docs/NETWORKING.md §3` |
| **Node registry service + signed handshake** | `registry.json` PRs stop scaling — roughly 30 nodes or a second operator org | FastAPI + SQLite, Ed25519 identity, human approval |
| **Federated learning (Flower)** | a model exists whose parameters can't be averaged by the hourly push, *and* the sovereignty claim is being examined by someone outside the team | self-hosted SuperLink at the district, SuperNodes at hubs; FedAvg first, FedProx when climates diverge |
| **Local LLM (Ollama)** | someone asks the node a question the alert doesn't answer | a `/brief` endpoint that turns 24h stats into a paragraph in the local language |
| **Edge role / MQTT bridge** | a real network partition between sensors and the hub | a Pi with a broker forwarding upstream |
| **TimescaleDB** | `readings` passes ~50M rows or `stats` takes over a second | swap the image, `create_hypertable`, the SQL is already compatible |
| **Telegram reply → action** | the first operator who says "I did it" in the chat instead of curl | a 20-line webhook that maps a reply to `#<alert_id>` into `POST /actions` |
| **Cells → Airtable / index.fab.city** | the Index surface wants to pull from a node rather than read Airtable | aggregator (or a cron) pushes `GET /cells` rows into `FCI Observations`; states preserved |
| **Upstream model / compute** | a rule or brief needs inference a Pi can't do | `UPSTREAM_MODEL_URL` (OpenAI-compatible) / `UPSTREAM_COMPUTE_URL`. Removed from `.env.example` in v0.9 because no code reads them: the names are the contract, the settings return with the code that uses them |
| **Separate notifier service** | a second channel (WhatsApp Business) with its own auth lifecycle | until then, a function. Note: Telegram, the LoRa mesh, LXMF and Home Assistant are now four channels and all four are still functions in `notify()`. The trigger is an auth lifecycle, not a channel count. |
| **Artifacts from packs** | ~~—~~ **shipped v0.12**: `out/` is mounted writable and `planetai run <pack> <script>` executes a pack's scripts | `packs/earth-engine/timelapse.py` is the worked example |

The rule: a piece comes back when its trigger fires, with a PR that names the trigger. Not before.

## 7. What this spec refuses

Kubernetes. Cloud providers. Embedding cascades. Causal-inference machinery. Four continents at once. If the network reaches thirty live nodes with a paying operator behind each, reopen this section.
