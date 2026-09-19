# HTTP API

Every node exposes the same read API on port 8080. The dashboard, the `planetai` command, the MCP tools, a NAS pulling backups, Home Assistant and a parent node are all clients of it; none of them has a private path in. A request either carries a token as `Authorization: Bearer <token>` or carries nothing, and a request carrying nothing is judged by the `SHARE_LEVEL` setting. The container publishes `${APP_PORT:-8080}:8080` on every host interface; Postgres is published on `127.0.0.1:5432` only. There is no TLS on the node itself: the tailnet encrypts the hop, and the [sharing page](sharing.md) says what to do on a network that is not a tailnet.

This page was read from the code of the version in the footer. Where an older document disagrees, the code wins.

## Access rules

Two middlewares run before any handler. `/mcp` is checked by the first against `ADMIN_TOKEN` and passed straight through the second. Everything else is checked by the second: a request is *trusted* when it comes from loopback or carries any of the four node tokens; a trusted request reaches every handler. An untrusted request is looked up against an allowlist for the current `SHARE_LEVEL` and refused with 403 if its path is not on it. The handler then applies its own token check, if it has one. The pages on this site name the result with one of these classes.

| Class | Who is answered |
|---|---|
| `public` | On the `off` allowlist. Answers anyone, at every `SHARE_LEVEL`, with no token. |
| `open` | On the `open` allowlist only. Without a token, answers only when `SHARE_LEVEL=open`. Always answers loopback or any node token. |
| `token` | On neither allowlist. Answers loopback or a request carrying any of the four node tokens (`ADMIN_TOKEN`, `BACKUP_TOKEN`, `AGGREGATE_TOKEN`, `ACT_TOKEN`); then the handler's own check, if any. |
| `admin` | `token`, then the handler requires `ADMIN_TOKEN`. |
| `pull` | `token`, then the handler requires `ADMIN_TOKEN` or `BACKUP_TOKEN`. The read-only token for a NAS. |
| `act` | Loopback needs no token. From anywhere else the handler requires `ACT_TOKEN` or `ADMIN_TOKEN`. |
| `children` | `token`, then the handler requires `AGGREGATE_TOKEN`. What a parent demands of a child. |

The `off` allowlist (the default) is exactly: `/`, `/ui`, `/health`, `/settings`, `/export`, `/presence`, and any path under `/static/`.

The `open` allowlist is the `off` list plus: `/stats`, `/sensors`, `/observations`, `/alerts`, `/series`, `/sparks`, `/rho`, `/cells`, `/packs`, `/trust`, `/nearby`, `/forecast`, `/earth`, `/earth/change.png`, `/earth/year.png`, `/earth/frame.png`, `/report/latest`, `/readings`, `/history`, `/exports`, and any path under `/static/`, `/exports/` or `/issues`.

A `SHARE_LEVEL` value that is neither `off` nor `open` is treated as `off`. The allowlist is applied to reads and writes alike: `POST /readings` and `POST /actions` are on neither list, so a request with no token is refused before it reaches the handler, at both levels.

**How a token travels.** In the `Authorization` header only, as `Bearer <token>`. There is no query parameter and no `X-Token` form. The node strips one leading `Bearer `, then compares the rest against every candidate token in constant time, without returning early, so the time taken does not say which token matched. `ADMIN_TOKEN` is read from the environment (`.env`); the other three come from settings, which the dashboard may overlay on `.env`. An optional `X-Agent` header names the caller in the audit trail; `PUT /settings` writes it into the `actions` ledger and defaults it to `gui`.

**What loopback means.** The peer address of the socket, never a header: `X-Forwarded-For` is not read and uvicorn runs without `--proxy-headers`. Inside Docker, loopback is true for the node's own MCP tools (they call `http://127.0.0.1:8080`) and for a shell inside the container. It is false for a browser on the machine that hosts the node, which arrives as the Docker bridge gateway. That is deliberate: on a Docker that forwards through a VM, a LAN client arrives as the gateway too, so trusting it would trust the whole network. A browser on the host is treated like any other client on the network and must carry a token or be let in by `SHARE_LEVEL=open`.

**The two refusal shapes.** The middlewares answer with `{"error": ...}`:

- 403 from `_share_level`: `{"error": "this node is set to SHARE_LEVEL=off, so /alerts answers only this machine or a request carrying a token. Set SHARE_LEVEL to open in the dashboard's Set up view to let anything on your network read it."}` — the level and the path are filled in from the request.
- 401 from `/mcp`: `{"error": "the agent surface needs Authorization: Bearer <ADMIN_TOKEN>"}`.

Handlers answer with FastAPI's default `{"detail": "..."}`. The handler checks and their texts:

| Check | Missing on the node | Wrong or absent in the request |
|---|---|---|
| `admin` | 403 `ADMIN_TOKEN is not set in .env; run planetai ui to create one` | 401 `bad or missing admin token` |
| `pull` | 403 `no BACKUP_TOKEN or ADMIN_TOKEN set on this node` | 401 `bad or missing token` |
| `act` | 403 `no ACT_TOKEN or ADMIN_TOKEN set on this node; run planetai ui to create one` | 401 `closing a loop from off this machine needs Authorization: Bearer <ACT_TOKEN>` |
| `children` | 403 `this node accepts no children: set AGGREGATE_TOKEN in .env and give it to them` | 401 `bad or missing Authorization: Bearer <AGGREGATE_TOKEN>` |

Timestamps in every response are ISO 8601 strings in UTC. Positions are rounded to 3 decimals (about 110 m) in `/health`, `/export` and, for an untrusted caller, `/sensors`; they are unrounded in `/forecast`, `/earth`, `/place/geojson` and `/stats`.

## Status

### GET /health
Access: public

What every screen in the house polls. Answers at every `SHARE_LEVEL` and never makes an outbound request of its own.

Returns one object with: `ok` (true once a poll has run), `node`, `version` (`NODE_VERSION`, or `?`), `schema` (the latest applied schema version, or `pre-0.4 (run ./update.sh)`), `uptime_s`, `lat` and `lon` rounded to 3 decimals for every caller at every level, `city`, `polls`, `last_poll`, `last_error`, `ingested`, `errors` (a map of loop name to its last error line), `bootstrap` (only if the first-start bootstrap ran in this process), `locale` (`ALERT_LOCALE`), `tz` (`NODE_TZ`), `cell` (the node's H3 cell facts, or null before setup), `mesh` (`{root_topic, gateway, packets, last}`, only when `MQTT_HOST` is set) and `reticulum` (`{ok, address, destinations, announce_s, announcing, peers, last}`, only when `RETICULUM_URL` is set).

```json
{"ok": true, "node": "bayu-2", "version": "v0.57", "schema": "0.51", "uptime_s": 86121,
 "lat": -8.827, "lon": 115.157, "city": "bali",
 "polls": 287, "last_poll": "2026-09-16T08:35:02+00:00", "last_error": null, "ingested": 41230,
 "errors": {}, "locale": "id", "tz": "Asia/Makassar",
 "cell": {"id": "...", "res": 8, "edge_m": 525, "...": "..."}}
```

### GET /presence
Access: public

What this node is willing to announce about itself on Reticulum. Public at every level on purpose: the Reticulum bridge is another container with no token and reads this to know what to announce.

Returns `{"enabled": false}` unless `RETICULUM_PRESENCE=1`. When enabled: `{enabled: true, node, cell, res, version, kind}`, where `cell` is the node's cell coarsened to resolution `res` (`RETICULUM_PRESENCE_RES`, default 3, clamped to 0..6; resolution 6 is the finest allowed) and `kind` is `NODE_KIND` or null.

### GET /
Access: public

### GET /ui
Access: public

The dashboard: `app/static/index.html`, one file, no build step, sent with `cache-control: no-cache, must-revalidate` so a wall screen follows the version after `planetai update`. A stub page if the file is missing. Hidden from the OpenAPI schema.

### GET /static/{name}
Access: public

The files the dashboard cannot inline: the ground SVG, the fonts, the renderer's script and stylesheets, the signs and the kilometre-cells JSON. Named one by one; a name that is not on the list is 404 `no such asset`. Sent with the same no-cache header.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `name` | path | — | One of `node-ground.svg`, `jetbrains-mono-latin.woff2`, `FunnelSans-VariableFont_wght.ttf`, `Figtree-VariableFont_wght.ttf`, `Figtree-Italic-VariableFont_wght.ttf`, `dashboard.js`, `dashboard.css`, `planetai-theme.css`, `tokens.css`, `signs.svg`, `kilometre-cells.json` |
| `variant` | string | `dark` | Register for `node-ground.svg`; anything but `paper` is treated as `dark` |

`node-ground.svg` is drawn live from `NODE_LAT` and `NODE_LON` when they are set, so the hero shows this node's own cell. Without coordinates the shipped file is served.

### GET /briefing
Access: token

A 301 redirect to `/report/latest`, kept for a dashboard left open in a browser through the update that removed the briefing in v0.38. Takes and ignores `kind`. Hidden from the OpenAPI schema.

> **Gap in v0.57.** `/briefing` is on neither allowlist. A stale dashboard with no token is refused with 403 by the middleware before it can be redirected, at both levels. The route works as intended only for loopback or a request with a token.

## Sensors and readings

### GET /sensors
Access: open

Every sensor this node reads, its position, and where its numbers come from. One row per sensor with `sensor_id`, `source`, `name`, `lat`, `lon`, `indoor`, `local`, `custody`, `kind`, `scale`, `cadence`, `meta`, ordered by custody, then local, then name. The columns are named rather than `SELECT *`, so a column added to the table stays private until someone lists it here.

For a caller that is neither loopback nor carrying a token, `lat` and `lon` are rounded to 3 decimals and `meta` is cut to the provenance keys `licence`, `attribution`, `model`, `dataset`, `network`, `note`, `corrected` (null if none remain). That drops a unit's `host`, `firmware`, `mesh_node`, `gateway`, `channel`, `root_topic` and `topic`. A trusted caller gets the full rows.

### GET /readings
Access: open

Raw readings, newest first.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `sensor_id` | string | any | Only this sensor |
| `metric` | string | any | Only this metric |
| `limit` | int | 200 | 1..10000 |

Returns a list of `{ts, sensor_id, metric, value}`.

### POST /readings
Access: admin

A contributor on the LAN (a phone, a DIY pod) posts raw readings. The sensor is upserted as `local=TRUE`; on conflict only `lat`, `lon` and `indoor` are updated. Admin token because a posted reading becomes a local sensor whose values fire act-level alerts and enter live cells.

Body:

```json
{"sensor": {"sensor_id": "phone-abc", "source": "mobile", "name": "kitchen phone",
            "lat": -8.827, "lon": 115.157, "indoor": true, "meta": {}},
 "readings": [{"ts": "2026-09-16T08:30:00+00:00", "metric": "pm25", "value": 12.3}]}
```

`sensor.sensor_id` is required (422 `sensor.sensor_id is required` otherwise). `source` defaults to `contributor`, `name` to the id, `indoor` to false. Each reading needs `metric` and `value`; `ts` defaults to now. A duplicate `(sensor_id, metric, ts)` is ignored. Returns `{"accepted": <number of readings in the body>}`.

### GET /stats
Access: open

Rolling statistics per sensor and metric over the last 24 hours, sensors only (`kind = 'sensor'`). This is the `stats` view: `sensor_id`, `metric`, `indoor`, `local`, `kind`, `scale`, `lat`, `lon`, `name`, `last`, `last_ts`, `silent_minutes`, `mean_15m`, `mean_1h`, `mean_24h`. Ordered local first, then sensor and metric. Slow sources are in `/observations`.

> **Careful.** `/stats` is `SELECT *` on the view and carries each sensor's `lat` and `lon` unrounded. At `SHARE_LEVEL=open` a caller with no token reads them here even though `/sensors` rounds them for the same caller.

### GET /observations
Access: open

The latest value per slow-moving source and metric: a city statistic, a model point sample, a survey. The `observations` view: `sensor_id`, `metric`, `value`, `ts`, `name`, `kind`, `scale`, `local`, `cadence`, `meta`, for every sensor whose `kind` is not `sensor`. Ordered by scale, sensor and metric.

### GET /trust
Access: open

One row per local sensor, for the dashboard's trust card and the agent's health check, computed once here so the two never drift from `packs/trust/rules.yml`.

Returns a list of `{sensor_id, name, coverage_7d, frozen_channels, age_hours}`: `coverage_7d` is the percentage of the last 168 hourly buckets its comparable ambient channels reported in; `frozen_channels` counts channels flat for 6 or more of the last 24 hours, still flat in the latest bucket, while the kit itself still produced raw readings in the last 2 hours; `age_hours` is the time since its first reading, so a value under 168 explains a low coverage without a fault.

### GET /history
Access: open

Every reading of one metric from one sensor, oldest first. For series that are not hourly: a yearly building count, a monthly refresh.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `sensor_id` | string | required | The sensor |
| `metric` | string | required | The metric |
| `limit` | int | 500 | 1..5000 |

Returns a list of `{ts, value}`.

### GET /series
Access: open

Hourly means for the dashboard's strip, as aligned arrays: local indoor sensors, everything outdoor (yours and the references), and the model (`cams-point`, metric `<metric>_model`).

| Name | Type | Default | Meaning |
|---|---|---|---|
| `metric` | string | `pm25` | The metric |
| `hours` | int | 24 | 1..168 |

Returns `{metric, hours, buckets, indoor, outdoor, model}`; the four arrays have one entry per bucket, null where there is no data.

### GET /sparks
Access: open

Per-sensor hourly means on the same buckets, for the small traces in the dashboard's sensor tiles.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `metric` | string | `pm25` | The metric |
| `hours` | int | 24 | 1..168 |

Returns `{hours: [bucket, ...], series: {sensor_id: [mean or null, ...]}}`; the buckets travel with the values so a trace can draw its own time axis.

## Context

### GET /nearby
Access: open

The ring: other people's stations around this node, and where this node sits inside it. Reads only what is stored, so the dashboard never waits on someone else's server. In v0.57 the ring is Bali Air Dispatch stations only (`source = 'baliairdispatch'`), within `BAD_RADIUS_KM`, that reported in the last 24 hours.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `audit` | bool | false | Also call the archive and return a verdict for every station it lists, the same answer `planetai run nearby stations` prints |

Returns `{ring, stations, lowest, p25, median, p75, highest, nearest_km, mine, mine_sensors, radius_km, attribution, mine_minus_ring}`. Each `ring` row is `{sensor_id, name, lat, lon, indoor, network, km, pm25, silent_minutes, last_ts, reporting}`, nearest first; `reporting` is true when the station spoke in the last 120 minutes. `mine` is the mean of this node's own outdoor sensors and `mine_minus_ring` the difference from the ring's median, or null. With `?audit=1` the response also carries `audit: [{station_id, name, network, km, verdict}]`, or `audit_error` if the archive did not answer.

### GET /forecast
Access: open

Official and model weather for this point: wind, expected rain, and when the forecast was issued. Context for reading the node's own air; the node fetches it, it does not predict.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `hours` | int | 24 | 1..72 hours ahead |

Returns `{point: {lat, lon}, sources: [{sensor_id, name, lat, lon, issued, fetched, km_from_node}], hours: [{ts, source, <metric>: value, ...}], attribution, far_from_node}`. The sources are the forecast sensors `forecast-bmkg`, `forecast-om` and `forecast-gap`. `far_from_node` lists any source more than 10 km away as `{sensor_id, km}`, or is null. `point` is the node's position, unrounded.

### GET /earth
Access: open

What the earth pack has: the years of AlphaEarth embeddings cached for this node's square, the comparisons it computed from them, and the frames the earth-engine pack fetched. Empty until `planetai run earth fetch`; never an error, so the card can say what is missing.

Returns `{node, enabled, years, bytes, latest, changes, frames, dir, imagery: {sentinel, landsat, credit}, png, lat, lon, radius_m, attribution, hint}`. Each entry in `changes` is the pack's own JSON with a `png_url` added (`/earth/change.png?pair=<a>_<b>`). `frames` are the years with a `year_<year>.png`; `imagery.sentinel` and `imagery.landsat` are the years with real satellite frames, kept separate because a model output is not a photograph. `radius_m` is `EARTH_RADIUS_M` (default 5000). `hint` says the next command when something is missing. `lat` and `lon` are unrounded.

### GET /earth/change.png
Access: open

A land-change map the earth pack drew. The file name comes from the pack's own JSON, never from the request.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `pair` | string | latest | `YYYY_YYYY`, one of the comparisons this node computed |

Returns a PNG, or 404 `no such land-change map: planetai run earth change`.

### GET /earth/year.png
Access: open

One year of the square as the earth pack drew it from the embeddings: a model's description flattened to grey, not a photograph.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `year` | int | required | 1900..2200 |

Returns a PNG, or 404 `no frame for <year>: planetai run earth frames`.

### GET /earth/frame.png
Access: open

One year from the other record: a Sentinel-2 or Landsat annual median fetched through Earth Engine, brightness-matched across years. The file comes from a glob of `out/`; neither parameter reaches the filesystem as a path.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `year` | int | required | 1972..2200 |
| `source` | string | `sentinel` | `sentinel` or `landsat` |

Returns a PNG, or 404 naming the years this node has.

### GET /place/geojson
Access: token

The geometry the place pack stored: OpenStreetMap buildings, uses, green and roads within `PLACE_RADIUS_M` of the node, and the satellite footprints (`sat`) with no mapped building within 3 m, as one FeatureCollection for the dashboard's plan. Empty until the place pack has run; never an error.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `kinds` | string | `building,poi,green,road,sat` | Which feature kinds to include |
| `tolerance` | float | 0.00002 | Simplification tolerance in degrees, 0.000001..0.01 |

Returns `{type: "FeatureCollection", features, diag: {tables, rows, error, hint}, center: [lon, lat], radius_m}`. Each feature's properties are `{kind, category, name, building, highway}`, or `{kind: "sat", confidence}` for a satellite footprint.

This route is on no allowlist at any level: loopback or a token, and nothing else. It is the exact building footprints and roads around the address, drawn; unlike a coordinate there is no rounded version of it that is safe to hand to the network. The dashboard's plan card is therefore empty on a screen with no token, and says so.

## Issues

### GET /issues
Access: open

Every issue this node declares, computed: state, stack by distance, the line it is compared against, attribution, a sentence in each locale, open asks, series. The order is `NODE_ISSUES`; an issue not declared still appears with `watched: false`, so a stranger can see what the node could report. The node computes and the page draws: nothing in the response needs arithmetic to render and nothing in it came from a model. `/issues/` answers the same.

Returns `{order, undeclared, dropped, headline, as_of, distances, labels, issues, stations, metrics, asks, mesh, geometry}`. `headline` is the key of the issue with the highest state, ties going to the declared order. Each entry of `issues` carries `state`, `watched`, `reason`, `reason_text`, `name`, `kind`, `metric`, `unit`, `dp`, `headline`, `stack`, `line`, `attribution`, `trend`, `open_asks`, `series`, `buckets`, `readouts`, `provenance` and `sentence` (keyed by locale). The full key set is defined in `app/issues/engine.py`.

The whole `/issues` prefix is on the `open` list and never on the `off` list: a snapshot carries 15-minute means, alert texts and sensor names, which are the household's own data.

### GET /issues/fixtures
Access: open

Which committed snapshots this node ships, so a design round does not have to guess a name. Returns `{"fixtures": ["name", ...]}`.

### GET /issues/fixtures/{name}
Access: open

One committed snapshot with its issues recomputed at the hour it was captured, through the same engine the live route uses. The dashboard reads this with `?fixture=<name>`.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `name` | path | — | Matches `^[a-z0-9][a-z0-9._-]{0,63}$`; a name, never a path |

Returns the snapshot JSON with `issues` replaced by the recomputation, or `{"error": ...}` in `issues` if the snapshot lacks a table the engine reads. 404 lists the names available.

## Alerts, actions, reports

### GET /alerts
Access: open

Alerts newest first, each with the id that `planetai act <id>` and the dashboard's Act button need, and whether anyone has acted.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `limit` | int | 50 | 0..1000 |

Returns a list of `{id, ts, rule_id, sensor_id, level, text, acted_at}`; `acted_at` is the first `acknowledged` or `acted` row for that alert, or null.

### POST /actions
Access: act

A human closes the loop. A mobile app, a Telegram reply handler or `curl` all make the same call. From loopback it needs no token, so the MCP `act` tool and a shell in the container keep working. From anywhere else it needs `ACT_TOKEN` or `ADMIN_TOKEN`: the weaker token on purpose, so someone in the house can be given the ability to close a loop without the key to `/settings/raw`. The check is made by the handler even at `SHARE_LEVEL=off`, because `BACKUP_TOKEN` gets past the middleware and a read-only NAS token must not be able to write rho.

Body:

```json
{"alert_id": 12, "stage": "acted", "actor": "ibu wayan", "note": "closed windows"}
```

`stage` must be `acknowledged` or `acted` (400 `stage must be acknowledged or acted`); `settings` rows are written by the node itself and never posted. `actor` is cut to 80 characters, `note` to 500. 404 `no such alert` if the id is unknown. There is no one-action-per-alert cap: two people who both acted are both recording something true. Returns `{"ok": true}`.

### POST /test-alert
Access: admin

Fires one act-level alert now, through every configured channel, the same as `planetai test-alert`. Writes an alert with rule `gui/test` and sends it with a hint on how to close the loop. Returns `{"ok": true, "alert_id": <id>}`.

### GET /report/latest
Access: open

The last report this node wrote, sent or held. What the dashboard's Here band shows and what the MCP tool `report_latest` returns. Ordered by write time, not by due hour, so a report written on request shows here.

Returns the latest `reports` row: `{id, ts, due_local, window_hours, depth, rung, text, sent, held_quiet, fallback_reason}`. Before the first report: `{text: null, ts: null, depth: null, rung: null, held_quiet: null, note: "no report yet; the first one lands at the next due hour"}`.

### GET /report/bundle
Access: pull

Every number the node has about a window, as one document: what a report is written from. Behind the read-only token because this is more of the household's data in one place than any other endpoint returns. SQL only; nothing is polled and nothing leaves the machine.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `hours` | int | 0 | Window in hours, 0..168; 0 means `REPORT_EVERY` |

Returns the bundle from `app/report.py`: `meta` (node, locale, timezone, local time, window), `series`, `observations`, `now`, `alerts`, `open_act`, `sensors_quiet`, `rho`, `previous`, `cells`, `rules`, `health`, plus one key per pack that contributes a report block. Series are dropped from the end if the document goes over the size cap, and `meta.truncated` counts them.

### POST /report/now
Access: admin

Write and send a report immediately, whatever the hour. `planetai report` and `/report` in Telegram call this. The row has no `due_local`, so the next scheduled report still happens. Returns `{id, text, depth: "sheet", rung: "node", sent: true}`.

## The Index contract

### GET /cells
Access: open

The Index cells this node can honestly compute, in the fci-cells-v0 row shape used by the FCI Observations base. Domain cells come from packs (`cells.yml`); the core evaluates their SQL as a read-only role and polices the provenance. A `Governance|<Scale>` row is appended only when there has been at least one act-level alert in the last 30 days; it is `partial` while fewer than 5 have been acted on. A pack may not claim `live` before its `min_buckets` of in-custody hourly data exist, nor off too few instruments: a node with children needs two sensors from two different children.

Each row:

```json
{"city": "bali", "cell": "Environmental|Community", "value": 18.4,
 "unit": "µg/m³ PM2.5 (24h mean, sensors in this node's custody)",
 "source": "planetai-node · pack:air-quality", "observed_at": "2026-09-16T08:35:02+00:00",
 "state": "live", "notes": "this node's own sensors and its children's hourly means; indoor and outdoor kept separate by the rules · 24/12 hourly buckets"}
```

`value` is rounded to 3 decimals or null; `state` is `live`, `partial` or `mock` and is never upgraded here or downstream; `source` is `planetai-node · pack:<id>` or `planetai-node actions ledger`.

### GET /rho
Access: open

Action latency over the last 30 days: the share of act-level alerts that got an `acknowledged` or `acted` row within 24 hours, pooled over this node's own alerts and the events its children pushed. The child never sends a ratio; it sends timestamps and the definition stays here. See [rho](rho.md).

Returns `{window_days: 30, days_ago: 0, alerts_act, acted, rho, median_minutes}`: `rho` is `acted / alerts_act` to 3 decimals, or null with no act-level alerts; `median_minutes` is the median detect-to-act time of the alerts acted within 24 hours, or null.

### GET /packs
Access: open

What this node has loaded beyond the core. Returns a list of pack manifests: each `pack.yaml` as parsed, with `id`, `path` and `kind` (`data` for rules and cells only, `code` for a pack with an `adapter.py`).

## Federation

### GET /aggregates
Access: token

This node's hourly means from `readings_1h`, newest first. Not on the `open` list.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `hours` | int | 24 | 1..2160 |

Returns a list of `{bucket, sensor_id, metric, mean, min, max, n}`.

### POST /aggregates
Access: children

The parent side. A child pushes its hourly means; raw readings never travel this path.

Body:

```json
{"node": "bayu-2", "scale": "community",
 "rows": [{"bucket": "2026-09-16T07:00:00+00:00", "sensor_id": "sc-1234", "metric": "pm25", "mean": 18.4}]}
```

The parent stores each row as one reading at the child's bucket under the namespaced sensor id `<node>/<sensor_id>`, and upserts that sensor with `source='child'`, `kind='child'`, `cadence='PT1H'`, `local=FALSE` and the body's `scale` (default `community`). The metric keeps its own name; the cadence is in the sensor row, not the key. A re-push of the same hour is ignored by the readings table's unique constraint. `min`, `max` and `n` in a row are not stored. Returns `{"accepted": <number of rows in the body>}`.

### POST /events
Access: children

The parent side of rho. A child pushes one row per alert it raised, as timestamps only: no text, no actor, no sensor id, no note. The parent computes rho over its own alerts and these together.

Body:

```json
{"node": "bayu-2", "scale": "community",
 "rows": [{"alert_id": "812", "raised_at": "2026-09-16T06:12:00+00:00", "rule": "air-quality/indoor_pm25_high",
           "level": "act", "kind": "air-quality", "responded_at": null,
           "acted_at": "2026-09-16T06:40:00+00:00", "measured_at": null}]}
```

The parent stores `child`, `alert_id`, `rule`, `level`, `kind`, `scale`, `raised_at`, `responded_at`, `acted_at`, `measured_at` and `received_at`, upserting on `(child, alert_id)`, so a row re-sent with new timestamps is an update. Any other key in a row is dropped rather than stored. A row without `alert_id` or `raised_at` is skipped. Returns `{"accepted": <rows kept>}`.

## Open data and backups

### GET /export
Access: public

One day of this node as open data, licensed CC BY 4.0: hourly means per sensor and metric, the Index cells, the alerts and rho. Never raw readings, never secrets. The node's own sensors are named by role (`indoor-1`, `outdoor-1`), not by device id; public references and models keep their ids. `backup.sh` fetches this nightly over `http://localhost:${APP_PORT}` and writes `exports/<node>/YYYY-MM-DD.json`, which is why the route is on the `off` list.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `day` | string | required | `YYYY-MM-DD`; 422 `day must be a real date, YYYY-MM-DD` otherwise |

Returns:

```json
{"node": "bayu-2", "city": "bali", "scale": "community", "lat": -8.827, "lon": 115.157,
 "day": "2026-09-15", "generated": "2026-09-16T00:05:11+00:00", "version": "v0.57", "licence": "CC BY 4.0",
 "hourly": [{"t": "2026-09-15T00:00:00+00:00", "sensor": "indoor-1", "local": true, "indoor": true,
             "kind": "sensor", "metric": "pm25", "mean": 11.2, "min": 9.0, "max": 14.1, "n": 12}],
 "alerts": [{"t": "2026-09-15T06:12:00+00:00", "rule": "air-quality/indoor_pm25_high", "level": "act", "text": "..."}],
 "cells": [], "rho": {}}
```

`alerts[].text` is the first line only. `cells` and `rho` are the same shapes as `/cells` and `/rho`, computed at export time.

### GET /exports
Access: open

The daily exports on disk. Returns a list of `{node, name, bytes}` from `exports/*/*.json`, newest name first; `[]` if the directory is missing.

### GET /exports/{node}/{name}
Access: open

One export file as JSON. Path components are stripped from both parameters; the file must end in `.json`. 404 `no such export`.

### GET /backups
Access: pull

The database dumps this node has made, newest first, so a NAS can fetch the ones it lacks. Returns a list of `{name, bytes, mtime}` from `backups/*.sql.gz`; `[]` if the directory is missing.

### GET /backups/{name}
Access: pull

One dump as `application/gzip`. The name is taken as a basename only and must end in `.sql.gz`. 404 `no such backup`.

## Settings

### GET /settings
Access: public

Every runtime setting with its group, label, help and current value, plus the bootstrap keys read-only. Secrets are always masked as `•••• set`. Without the admin token, every value outside the public set is masked too: chat ids, sensor hosts, account names and remote URLs are the household's. A wrong token reads as no token, with no error, so the dashboard's layout read keeps working on every screen.

At `SHARE_LEVEL=off`, a caller that is neither loopback nor carrying a token sees the values of `UI_LAYOUT` and `SHARE_LEVEL` only. Every other row is still present, masked, so the Set up view still renders and says what would be unlocked. At `SHARE_LEVEL=open`, or from loopback, or with any node token, the anonymous reader sees the public set (`REPORT_EVERY`, `ALERT_LEVEL`, `QUIET_HOURS`, `SHARE_LEVEL`, `NODE_ISSUES`, `MAP_TILES`, `PACKS_ENABLED` and the rest of `settings.PUBLIC`).

Returns `{unlocked, runtime: [{key, group, label, secret, restart, help, value, set, source, choices, outward}], bootstrap: [{key, label, value}]}`. `source` is `gui`, `env` or `default`; `choices` lists the accepted values where the key has a fixed set; `outward` marks a key that changes what leaves the machine.

### PUT /settings
Access: admin

Change runtime settings. Blank returns a key to its `.env` value. Effective within about 20 seconds (the settings cache TTL).

Body: `{"KEY": "value", ...}`. Header `X-Agent` names the caller (default `gui`).

400 `<KEY> is not a runtime setting` for a key outside the runtime set; 400 with the validation message for a value outside the key's choices. Every call writes one row to the `actions` ledger with `stage='settings'`, `actor` = the `X-Agent` value and `note` = the keys changed. Returns `{changed: [keys], by, effective_within_s: 20}`.

### GET /settings/raw
Access: admin

Every runtime setting unmasked, as `{KEY: value}`, for the node's own processes: the agent loop reads its model ladder here every minute. Admin token only, explicitly not `BACKUP_TOKEN`, so a NAS's read-only token cannot unmask the Telegram token or the AI keys. Never call this from a browser.

## The agent surface

### /mcp
Access: admin

The MCP server, over streamable HTTP at exactly `/mcp` (GET, POST and DELETE as the transport defines; no trailing-slash redirect). The whole surface needs `Authorization: Bearer <ADMIN_TOKEN>`, checked by its own middleware against the environment, because the tools can write as well as read; a missing or wrong token is 401 `{"error": "the agent surface needs Authorization: Bearer <ADMIN_TOKEN>"}`. It bypasses the `SHARE_LEVEL` check, since it has already been decided. The tools call the API back on `http://127.0.0.1:8080`, so they arrive at every other route as loopback. In v0.57 the tools are `status`, `health_check`, `sensors`, `context`, `readings`, `report_latest`, `report_now`, `report_bundle`, `history`, `alerts`, `act`, `settings_get`, `settings_set`, `packs`, `cells`, `issues`, `series`, `export_day`, `run_pack_script` and `maintenance`; the [MCP page](mcp.md) describes each.

## What the node calls out

The API is the read side. These are the requests the node makes of other machines.

| To | When | What travels |
|---|---|---|
| `POST {PARENT_API_URL}/aggregates` | Hourly, if `PARENT_API_URL` is set | `{node, rows, scale}`: hourly means from the last 2 hours, with `Authorization: Bearer <PARENT_TOKEN>` if set |
| `POST {PARENT_API_URL}/events` | Hourly, if `PARENT_API_URL` is set | `{node, rows, scale}`: one row per alert from the last 36 hours as timestamps (`alert_id`, `rule`, `level`, `kind`, `raised_at`, `responded_at`, `acted_at`, `measured_at`), same header |
| Telegram `sendMessage` | Each alert or report, per chat id | The message text, to `api.telegram.org` with `TELEGRAM_BOT_TOKEN` |
| `POST {RETICULUM_URL}/send` | Each act-level alert, if `RETICULUM_URL` is set | `{"text": ...}` to the bridge container |
| MQTT publish | Each act-level alert (`MESH_ALERTS=1`), and Home Assistant discovery (`HA_DISCOVERY=1`) | The first line of the alert to the mesh downlink; discovery and state topics to the broker at `MQTT_HOST` |

The sources the node polls (Smart Citizen, Bali Air Dispatch, Open-Meteo, CKAN portals, packs) are on the [sensors page](sensors.md).

## Not in this version

- `/plan.png` and `/provenance` do not exist. Provenance travels inside `/cells` rows (`state`, `source`, `notes`) and in the `meta` of `/sensors` (`licence`, `attribution`, `model`, `dataset`, `network`, `note`, `corrected`).
- There is no query-parameter or `X-Token` form of authentication, and no per-route token other than the ones named above.
- `X-Forwarded-For` is never read; a proxy in front of the node does not make its clients loopback.
