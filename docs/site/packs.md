# Packs

A pack is a folder in `packs/` with a `pack.yaml`. It carries rules, Index cells, channel roles, and — for a
code pack — an adapter for a new source and scripts you can ask for. The core's rules and cells name no metric: what `pm25` means, and what to do about it, is written in a pack. Everything that makes a node useful for a place is
a pack, and anyone can write one. What ships is on [Packs that ship](packs-reference.md).

```
packs/<id>/
  pack.yaml     id, name, description, kind (data | code), version, requires, domain, pip:, env:
  rules.yml     alerts: SQL that returns rows, one message per row; or a contribution to the report
  cells.yml     Index cells: SQL that returns one `value`
  channels.yml  what the pack's own metrics ARE — ambient, enclosure, device_health, derived, index
  adapter.py    a new source; code packs only
  *.py          scripts, run with `planetai run <pack> <script>`
  README.md     where the thresholds came from, which place they were written for, what the pack does not know
```

## How packs load

Every folder under `packs/` with a `pack.yaml` is a pack, in sorted order. `PACKS_ENABLED` (blank = all;
else a comma list of ids) filters the list. A pack is a **code pack** if it has an `adapter.py` — the `kind:`
line in `pack.yaml` is descriptive, presence of the file is what the loader reads — and its adapter runs
only when `PACKS_ALLOW_CODE=1`, because it runs with the node's privileges: read it first. Loading is
deliberately dumb: a broken YAML or adapter is logged and skipped, there is no registry and no dependency
resolution. Rule ids are namespaced `<pack>/<id>`; core rules keep bare ids.

Fields in `pack.yaml`. The node reads `id`, `description`, `kind`, `domain`, `pip` and `env`; `requires` and `needs` are documentation for people and are read by no code in this version. `sources` is **validated**: every id in it has to resolve to an entry in the registry the node carries at `data/sources/`, or `make lint` fails and names the id — see `docs/SOURCES.md`.

| field | used for |
|---|---|
| `id` | the pack's name; defaults to the folder |
| `description` | shown by `planetai packs` and `GET /packs` |
| `requires: {node: ">=0.40.0"}` | the node version the pack was written against |
| `domain` | which dashboard issue the pack feeds (`air`, `heat`, `land`, `coast`, …). A cross-domain pack's rules are claimed one by one in `app/issues/*.yml`; a pack that reaches no issue and is not named as deliberately outside them fails `tests/test_issues.py` |
| `pip: [earthengine-api]` | libraries `planetai packs install` builds into the image, once, as the union of every pack's list |
| `env: ["# comment", "KEY=default"]` | settings `planetai packs install` appends to `.env` under a dated marker when the key is absent; comment lines travel with the key under them. No space after `=` |
| `sources: [environmental/community/bali-air-dispatch]` | the registry ids of the data sources, from `awesome-fabcity-data`. Checked by `tools/check_registry.py`; file the source upstream first, then name it here. `planetai sources` lists what is available |
| `needs: [api.bmkg.go.id]` | hosts the pack reaches |

## Data packs: rules

YAML only. A rule's SQL runs every 60 seconds as the read-only role `planetai_ro` — every table but
`settings`, no writes — so a rule cannot read a token into an alert or change a row. Postgres does the
maths, including `corr()`.

```yaml
- id: indoor_pm25_high
  level: act                 # info | warn | act
  cooldown_minutes: 120
  sql: SELECT sensor_id, name, mean_15m FROM stats WHERE local AND indoor AND metric='pm25' AND mean_15m > 35.5
  message:
    en: "Indoor PM2.5 at {name} is {mean_15m:.0f} µg/m³. Purifier on, windows shut."
    id: "PM2.5 dalam ruangan di {name} {mean_15m:.0f} µg/m³. Nyalakan pembersih udara, tutup jendela."
```

| field | required | meaning |
|---|---|---|
| `id` | yes | becomes `<pack>/<id>` |
| `sql` | yes | one `SELECT`; every returned row is a candidate alert. A `sensor_id` column keys the cooldown; without one the row is the node's |
| `level` | no (`info`) | `info`, `warn`, `act` — see [Alerts](alerts.md) |
| `cooldown_minutes` | no (60) | per rule and sensor, enforced against `alerts` |
| `long_cooldown_ok: true` | when cooldown > 20160 | tells the lint a cooldown over a fortnight is deliberate |
| `message` | unless `contributes` | a string or `{en, id, es}`; filled with the row by `str.format`; `None` renders as `—` |
| `contributes: report` | instead of `message` | never sent; the first row lands in the report bundle under the rule's id |

Every `{placeholder}` in every language must be a column the top-level `SELECT` returns. `make lint`
(`tools/check_rules.py`, with sqlglot) parses the SQL against `init.sql` and refuses unknown tables and
columns, placeholders the SQL does not return, a cell without a `value`, a cooldown over a fortnight without
`long_cooldown_ok`, a rule with both a message and a contribution, and one with neither — which could fire
and reach nobody.

What a rule may read: the `stats` view (`sensor_id, metric, indoor, local, kind, scale, lat, lon, name,
last, last_ts, silent_minutes, mean_15m, mean_1h, mean_24h` — the last 24 hours, sensors only),
`readings_1h` (hourly `mean, min, max, n` over all history), `observations` (the latest value per slow
source), `readings`, `sensors`, `channel_roles`, and the node's own position and time zone as Postgres
settings: `current_setting('planetai.lat')`, `current_setting('planetai.lon')`, `current_setting('TimeZone')`.
Days are local days — `NODE_TZ` is the session time zone — so `date_trunc('day', ts)` means the household's
day, not UTC's.

A contributor:

```yaml
- id: digest
  contributes: report        # no level, no cooldown, no message: this is never sent
  sql: SELECT round(avg(mean_1h)) AS inside FROM stats WHERE local AND indoor AND metric='pm25'
```

## Data packs: cells

```yaml
- cell: "Environmental|Community"
  unit: "µg/m³ PM2.5 (24h mean, sensors in this node's custody)"
  state: live                # live | partial | mock
  min_buckets: 12
  notes: "your own outdoor and indoor kits, hourly means, last 24 h"
  sql: SELECT avg(mean) AS value FROM readings_1h r JOIN sensors s USING (sensor_id)
       WHERE s.custody AND r.metric='pm25' AND r.bucket > now() - interval '24 hours'
```

`state` is provenance, not confidence. `live` means measured here; `partial` means derived, a model or a
portal, whatever its quality; never claim `live` for a model. The core demotes `live` to `partial` when the
in-custody hourly buckets in 24 hours are fewer than `min_buckets`, or when too few in-custody sensors
report — two where the node has children or is above community scale, one otherwise — and appends
`have/need hourly buckets` to the note. A `NULL` value omits the cell: absent, not zero. The cell's source is
recorded as `planetai-node · pack:<id>`, and the core adds one cell of its own, `Governance|<Scale>` = [ρ](rho.md).

## Channel roles

A pack that adds a metric says what it is, keyed on `(source, metric)`:

```yaml
- { source: forecast-om, metric: fc_wind_speed, role: derived, comparable: false, unit: "km/h" }
```

Roles are `ambient`, `enclosure`, `device_health`, `derived` and `index` — defined on the
[sensors](sensors.md) page. The core's `config/channels.yml` is read first; a pack may not redeclare a pair
the core already claimed. A pack that adds no metric ships `channels.yml: []` to say so, as `trust` does.

## Code packs: adapters

`adapter.py` with `fetch(hc) -> (sensors, readings)`, the same contract as `app/sources.py`. Off unless
`PACKS_ALLOW_CODE=1`. Dependencies and settings go in `pack.yaml`; `planetai packs` lists what is loaded
and what is missing, and `planetai packs install` installs the libraries into the image once and adds the
settings to `.env`. A pack that needs a key or a service must log once and return nothing when it is
missing. `packs/earth-engine` is the worked example: a dependency, a credential, four remote datasets, and
it idles until configured.

## Scripts

Things you ask for rather than things that run on a schedule:

```bash
planetai run                          # lists every script with its first line
planetai run earth change --all       # the land change for every year pair this node has cached
planetai run nearby stations          # every station in the ring, with the reason for each exclusion
planetai run place gaps               # a mapping brief: what is undrawn within the kilometre
```

They run inside the app container, where the dependencies are, with `PACK_OUT=/app/out`; `out/` is the one
writable path, and what they write there is yours to send anywhere. Every `*.py` in a pack except
`adapter.py` is listed, so a helper module shows up too (`place/satellite.py` does).

## A dashboard section

A pack can put a section on the dashboard by registering one object with the page contract:

```js
window.PAI.register({
  id: 'meshtastic',            // required, unique; the band's DOM id
  pack: 'meshtastic',          // required
  stage: 'observe',            // required: observe · decide · act · measure
  title: 'The mesh in this house',
  render(ctx) { … },           // required; captions belong here, explanations do not
  order: 41,                   // within the stage, lower first (default 50)
  needs: ['H3.radio.mesh'],    // dotted paths off window; absent → one honest line, never a blank
  controls(ctx) { … },         // optional control strip
  wall(ctx) { … },             // what this section contributes to the wall
  notes(ctx) { … },            // the explanations, gathered at the foot of the page
});
```

A section may not invent a fifth card kind (readout · stack · series · row), colour a state by hue, print a
numeral without `data-num`, or put its explanation in its body. In this version a section lives inline in `app/static/dashboard.js`, because the node serves its static files from a fixed allowlist by name; serving a pack's own `dashboard.js` needs a name on that list the node does not have yet. Proposing a section today is sending the
file with its `render()` and its `notes()`. The page itself is described on [Dashboard](dashboard.md).

## Writing one

Copy `packs/heat`. Change the metrics, the thresholds, the messages. Say in the README where the thresholds
come from and which place you wrote for — thresholds for Kuta Selatan are not thresholds for Barcelona.
Run `make lint`. Fork, add the folder, open a PR. A rule should end in something a person does; a rule that
fires on indoor sensors as if they were ambient will not be merged — `NOT s.indoor` is not decoration.

Ten more ideas, with who might write them, are on [Pack ideas](pack-ideas.md); the issue a new domain
declares is explained on [Issues](issues.md).
