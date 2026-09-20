# Database schema

One Postgres database, `planetai`, on the `imresamu/postgis:16-3.4-alpine` image, bound to the machine
itself. `init.sql` is the whole schema, written idempotently — `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE …
ADD COLUMN IF NOT EXISTS`, `DROP VIEW` then `CREATE VIEW` — and the same file runs on a fresh volume and on
every update, because Postgres runs it on its own only when the data volume is first created. Schema changes are additive by rule (SPEC §5): no dropped columns, no renames, no destructive migrations, which is what makes rollback `git checkout <tag>` and a restart rather than a restore. The one exception so far is `events.cleared_at`, a column nothing ever wrote, dropped in 0.51. `schema_version` records where a node is
and `/health` reports it.

## Tables

### `sensors`

One row per thing that produces readings.

| column | type | meaning |
|---|---|---|
| `sensor_id` | text, primary key | `<source>-<upstream id>`: `sc-19880`, `bad-pa-46949`; a child's as `<child>/<sensor_id>`. Never reassigned |
| `source` | text | the adapter: `smartcitizen`, `baliairdispatch`, `open-meteo`, `open-meteo-cams`, `nasa-power`, `ckan`, `meshtastic`, `child`, a pack's |
| `name` | text | the place, as the person named it |
| `lat`, `lon` | double | position; rounded before it leaves for a reader without a token |
| `indoor` | bool | measures a room; never in an ambient average |
| `local` | bool | the person's own **and** within `LOCAL_RADIUS_M` of the node |
| `kind` | text | `sensor` · `portal` · `model` · `map` · `child` · `peer` (`survey` reserved) |
| `scale` | text | `community` · `city` · `region` · `bioregion` · `planet` |
| `cadence` | text | ISO 8601 duration: `PT5M`, `PT1H`, `P1D`, `P1Y` |
| `meta` | jsonb | licence, attribution, model, dataset, network, note, corrected — the public keys; the rest for trusted readers |
| `custody` | bool, generated | `kind = 'child' OR (local AND kind <> 'peer')`. The only thing a cell may count |

### `readings`

| column | type | |
|---|---|---|
| `ts` | timestamptz | a UTC instant |
| `sensor_id` | text → `sensors` | |
| `metric` | text | lowercase, no unit in the name |
| `value` | double | |

Unique on `(sensor_id, metric, ts)`, so polling twice is harmless; indexed `(sensor_id, metric, ts desc)`.
Node #1, with four local sensors and the public references, adds about 1 MB a day.

### `alerts`

| column | | |
|---|---|---|
| `id` | bigserial | the number a person acts on |
| `ts` | timestamptz | when the rule fired |
| `rule_id` | text | `<pack>/<id>`, or a bare core id |
| `sensor_id` | text | the row's sensor, or `node` |
| `level` | text | `info` · `warn` · `act` |
| `text` | text | the filled message |

Indexed `(rule_id, sensor_id, ts desc)` for the cooldown check. There is no notion of an alert clearing,
only of cooldowns.

### `actions`

The ρ instrument.

| column | | |
|---|---|---|
| `ts` | timestamptz | |
| `alert_id` | bigint → `alerts.id` | null for `settings` rows |
| `stage` | text | `acknowledged` · `acted` · `measured` · `settings` |
| `actor` | text | who: `tomas`, `dashboard`, `planetai-cli`, `local-model/telegram`, `lxmf:<hash>` |
| `note` | text | in the person's words |

### `reports`

| column | | |
|---|---|---|
| `id`, `ts` | | |
| `due_local` | timestamptz | the local due hour; the row is the scheduler's lock. Null for `POST /report/now` |
| `window_hours` | int | |
| `depth` | text | `sheet` today; `brief` · `standard` · `deep` reserved |
| `rung` | text | `node` today; `local` · `remote` · `online` reserved |
| `text` | text | what was sent; equal to `sheet` until a model rewrites it |
| `sheet` | text | the node's own six parts, always |
| `sent`, `held_quiet` | bool | |
| `fallback_reason` | text | why `text` is the sheet and not a model's |
| `cells` | jsonb | the Index cells at the time of the report |

### `events`

ρ from below: one row per child alert, pushed hourly by children to `POST /events`.

| column | | |
|---|---|---|
| `child`, `alert_id` | text, primary key together | |
| `rule`, `level`, `kind`, `scale` | text | `kind` is the pack prefix |
| `raised_at`, `responded_at`, `acted_at`, `measured_at` | timestamptz | timestamps only — no text, no actor, no sensor, by design |
| `received_at` | timestamptz | |

`cleared_at` was dropped in schema 0.51: a node has no notion of an alert clearing.

### `channel_roles`

What each `(source, metric)` **is**, written at every start from `config/channels.yml` and every pack's
`channels.yml`: `role` (`ambient` · `enclosure` · `device_health` · `derived` · `index`), `comparable`,
`unit`, `reference`, `declared_by`.

### `settings`

`key`, `value`, `updated_at`: the runtime overlay over `.env`, written from Set up, `planetai config set`,
`PUT /settings` and the `settings_set` tool. Not readable by the rules' role, and excluded from dumps so a
saved token never travels.

### `schema_version`

`version`, `applied_at`; one row per schema step: 0.4, 0.14, 0.20 … 0.50, 0.51.

### Pack tables

The `place` pack creates `place_features` (OpenStreetMap features with a PostGIS geometry), `place_runs`,
`place_yearly` and `place_buildings_sat` (Open Buildings). Tables a pack creates inherit the read-only role's
`SELECT` through default privileges.

## Views

| view | rows | columns |
|---|---|---|
| `readings_1h` | hourly means over all readings | `bucket, sensor_id, metric, mean, min, max, n` |
| `stats` | one per (sensor, metric), last 24 h, `kind='sensor'` only | `sensor_id, metric, indoor, local, kind, scale, lat, lon, name, last, last_ts, silent_minutes, mean_15m, mean_1h, mean_24h` |
| `observations` | the latest row per (sensor, metric) for `kind <> 'sensor'` | `sensor_id, metric, value, ts, name, kind, scale, local, cadence, meta` |

Sensors land in `stats`; slow sources — portals, models, maps — land in `observations`. `observations`
keeps the latest row per source per metric forever, which is why a retired metric must not be read as this
year's answer.

## The read-only role

`planetai_ro` — `NOLOGIN`, `SELECT` on every table but `settings`, no writes — is the role every rule and
every cell runs as, one statement at a time with `SET LOCAL ROLE`. A rule cannot read a token into an alert
text or change a row.

## Time and place inside the database

The session time zone is `NODE_TZ`, so `date_trunc('day', ts)` and `extract(hour from ts)` mean the
household's day and hour; readings themselves are UTC instants. The node's position is available to SQL as
`current_setting('planetai.lat')` and `current_setting('planetai.lon')`.

## Backups and restore

`backup.sh` nightly at 03:17: `pg_dump` gzipped into `BACKUP_DIR`, checked to be a valid gzip with a
readings table, kept `BACKUP_KEEP` days, `LAST_OK` written; the `settings` rows excluded. `planetai restore
<dump>` takes a safety backup, stops the app, drops and recreates the database, restores, re-applies
`init.sql` and starts. The database stays on a local disk — SMB and NFS do not honour `fsync` and file
locking, and a mount path that is not mounted becomes an empty local folder with the NAS's name. Where the
copies go is on [Storage](storage.md).
