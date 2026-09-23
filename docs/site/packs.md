# Packs

A pack is how a place teaches its node what to watch and what to say about it. The core names no metric:
what `pm25` means, which line matters in this house, and the sentence a person should read at 9 pm are all
written in a pack. A data pack is SQL and words. A code pack also fetches: it adds a source the core does not
read. The loader's own description of the point is one line: "most useful contributions are a rule and a
threshold that someone learned the hard way in their city."

This page is the contract as `app/packs.py` reads it, and one small data pack built step by step. What ships
is on [Packs that ship](packs-reference.md).

```
packs/<id>/
  pack.yaml     id, name, description, version, requires, domain, sources:, pip:, env:
  rules.yml     alerts: SQL that returns rows, one message per row; or a contribution to the report
  cells.yml     Index cells: SQL that returns one `value`
  channels.yml  what the pack's own metrics ARE: ambient, enclosure, device_health, derived, index
  adapter.py    a new source; its presence makes this a code pack
  *.py          scripts, run with `planetai run <pack> <script>`
  README.md     where the thresholds came from, which place they were written for, what the pack does not know
```

## How packs load

Every folder under `packs/` with a `pack.yaml` is a pack, in sorted order. `PACKS_ENABLED` filters that
list: blank means every pack, otherwise a comma list of ids. The loader reads the folders on every pass, and
`packs/` is mounted into the app container, so a folder you add is seen within a minute without a restart.

A pack is a **code pack** if its folder has an `adapter.py`. The loader sets `kind` from that file and
ignores the `kind:` line in `pack.yaml`. An adapter runs only when `PACKS_ALLOW_CODE=1`, because it runs
with the node's privileges and network access: read it first. Without that setting the node logs
`pack <id> ships code; set PACKS_ALLOW_CODE=1 to run it` and loads the pack's rules and cells anyway.

Because blank `PACKS_ENABLED` means every pack, a pack that must stay off by default needs its own switch.
One pack has one: `make` reads a directory that is not openly licensed, so it does nothing until
`MAKE_ENABLED=1`, on top of `PACKS_ALLOW_CODE=1`. v0.65 shipped without that switch and the pack turned
itself on at update on node #1; v0.66 added it (see [`CHANGELOG.md`](../../CHANGELOG.md)).

Loading is plain. A `pack.yaml`, `rules.yml`, `cells.yml` or adapter that does not parse is
logged and skipped, and the rest of the node carries on. The settings loader logs a broken `pack.yaml` too,
because it reads every installed pack, enabled or not, to put each pack's `env:` keys in Set up → Packs with
their help text and default. Rule ids are namespaced `<pack>/<id>`; the two core rules keep bare ids.

## Your first data pack

Five steps, each with something to check. The pack watches temperature, because most kits report it. If
your sensors do not, pick a metric they do report and change `temp` in both files.

**1. See what your node measures.** Run `planetai sensors`. The rows marked `yours` are the ones a rule
written with `local` will read. A pack teaches the node about readings it already holds; it adds no
sensor.

**2. Make the folder.** In the node's directory (`~/planetai` on an installed node), create
`packs/my-room/pack.yaml`:

```yaml
id: my-room
name: My room
description: How warm the rooms this node measures have been, as one alert a day and one Index cell.
version: 0.1.0
requires: { node: ">=0.72.0" }
domain: heat
```

Within a minute `planetai packs` lists it under `loaded now:` as `my-room          data  How warm the rooms…`.
If it does not appear and `PACKS_ENABLED` is not blank, add `my-room` to that list. `domain: heat` puts
the pack's alerts under the heat issue on the dashboard.

**3. Teach it one thing to say.** Create `packs/my-room/rules.yml`. The line is set low on purpose, so it
fires now and you see the whole path; step 5 moves it.

```yaml
- id: room_warm
  level: info
  cooldown_minutes: 1440
  sql: |
    SELECT sensor_id, name, mean_1h FROM stats
    WHERE local AND metric = 'temp' AND mean_1h > 20
  message:
    en: "🌡️ {name} has averaged {mean_1h:.1f} °C over the last hour.\n\n👉 Open a window on the shaded side, or switch on a fan."
    id: "🌡️ Suhu rata-rata {name} {mean_1h:.1f} °C selama satu jam terakhir.\n\n👉 Buka jendela di sisi yang teduh, atau nyalakan kipas angin."
    es: "🌡️ {name} ha promediado {mean_1h:.1f} °C durante la última hora.\n\n👉 Abre una ventana del lado de la sombra, o enciende un ventilador."
```

Rules run every 60 seconds. Run `planetai status`: under `alerts` it prints the time and the start of
your message, with your sensor's name and its last hour filled in. That row is in the `alerts` table now,
under the id `my-room/room_warm`, and it will not repeat for that sensor for 1440 minutes. At the default
`ALERT_LEVEL=act` an `info` alert is recorded, shown on the dashboard and carried by the next report, and
interrupts nobody (see [Alerts](alerts.md)). If nothing appears, `planetai logs | grep my-room` shows `rule my-room/room_warm failed: …` with
Postgres's reason.

**4. Say which Index cell it becomes.** Create `packs/my-room/cells.yml`:

```yaml
- cell: "Environmental|Community"
  unit: "°C (24h mean, sensors in this node's custody)"
  state: live
  min_buckets: 12
  notes: "my-room: every temperature channel in custody, hourly means, last 24 h"
  sql: |
    SELECT avg(mean) AS value FROM readings_1h r JOIN sensors s USING (sensor_id)
    WHERE s.custody AND r.metric = 'temp' AND r.bucket > now() - interval '24 hours'
```

Run `planetai cells`. A new `Environmental|Community` row carries your value, its state and your unit,
beside the ones other packs already emit. `planetai cells --json` shows the full row, including
`source: "planetai-node · pack:my-room"` and a note ending in `<have>/12 hourly buckets`. The state
reads `partial` until the node holds 12 hourly buckets from sensors in its custody and enough of those
sensors report; the core demotes a `live` claim the data does not yet support. A row like this is the
only form in which a place's measurements reach the Fab City Index: a mean with its provenance, never a
reading (see [Federation](federation.md)).

**5. Move the line to your place.** Change `20` in the SQL to the temperature this room should not pass,
and say in a `README.md` where that number came from. To make it an ask rather than a note, set
`level: act`, keep `cooldown_minutes` at or under 2880, and add `watch: {metric: temp, over: <the same
number>}` so the node can later time how long an action took to work. At `act`, the alert becomes an
open ask on the heat issue, and the sentence after 👉 is what the dashboard's Decide card shows as "what
this node suggests". The cooldown still counts from the `info` alert of step 3, so the first `act` alert
comes once those 1440 minutes have passed with the room still over the line. Then a 🔴 message reaches
Telegram if it is connected, the heat issue's state is `act`, and the lead's last line counts the ask
(`1 ask open · #<id> · in 3 Act` when it is the only one).
The pack now asks a person to do something, and what they record against it counts in [ρ](rho.md).

On a checkout of the repository, `python3 tools/check_rules.py` (it needs `sqlglot`) parses the pack
against `init.sql`. At v0.72.1 it prints `48 rules and cells check out against init.sql`; with your
folder added the count is 50, one rule and one cell more. A `{placeholder}` the SQL does not return is
refused here and named; on a running node the same mistake sends the raw template, braces and all.

## Fields in pack.yaml

Code reads `id` and `description` (the loader, `planetai packs`), `domain` (the issue engine), `env` (Set
up and `planetai packs install`), `pip` (`planetai packs install`) and `sources` (`tools/check_registry.py`).
`requires` and `needs` are for people and are read by no code in v0.72.1. `kind` is overwritten from the
presence of `adapter.py`.

| field | used for |
|---|---|
| `id` | the pack's name; defaults to the folder |
| `description` | shown by `planetai packs` and `GET /packs` |
| `requires: {node: ">=0.40.0"}` | the node version the pack was written against |
| `domain` | which dashboard issue the pack feeds (`air`, `heat`, `land`, `coast`, …). A cross-domain pack's rules are claimed one by one in `app/issues/*.yml`; a pack that reaches no issue and is not on the list of domains outside them (`weather`, `place`, `governance`, `repair`) fails `tests/test_issues.py` |
| `sources: [environmental/community/bali-air-dispatch]` | the registry ids of the data sources it reads. `make lint` runs `tools/check_registry.py`, which fails and names any id that is not an entry in the registry the node carries. See [The source registry](sources.md) |
| `pip: [earthengine-api]` | libraries `planetai packs install` builds into the image, once, as the union of every pack folder's list |
| `env: ["# comment", "KEY=default"]` | settings `planetai packs install` appends to `.env` under a dated marker when the key is absent; a comment line travels with the key under it. No space after `=` |
| `needs: [api.bmkg.go.id]` | hosts the pack reaches |

An issue file under `app/issues/` may carry its own `where:` block, which replaces the shared phrase for a
distance in each language (`coast.yml` says "at the nearest ocean cell", `land.yml` "of the square this
node watches"). That block belongs to the issue, not to the pack.

## Rules

YAML only. A rule's SQL runs every 60 seconds as the read-only role `planetai_ro`: every table but
`settings`, no writes. A rule cannot read a token into an alert or change a row. Postgres does the maths,
including `corr()`. The first rule in `packs/air-quality/rules.yml`, with its message shortened:

```yaml
- id: indoor_pm25_high
  level: act
  cooldown_minutes: 120
  watch: {metric: pm25, over: 35.5}
  sql: |
    SELECT sensor_id, name, mean_15m FROM stats
    WHERE local AND indoor AND metric = 'pm25' AND mean_15m > 35.5
  message:
    en: "🏠😷 The air inside at {name} is unhealthy right now.\n\n…\n\n👉 Run the purifier if you have one. …"
    id: "🏠😷 Udara di dalam {name} sedang tidak sehat.\n\n…\n\n👉 Nyalakan pembersih udara kalau ada. …"
    es: "🏠😷 El aire dentro de {name} no es saludable ahora mismo.\n\n…\n\n👉 Enciende el purificador si tienes uno. …"
```

| field | required | meaning |
|---|---|---|
| `id` | yes | becomes `<pack>/<id>` |
| `sql` | yes | one `SELECT`; every returned row is a candidate alert. A `sensor_id` column keys the cooldown; without one the row is the node's |
| `level` | no (`info`) | `info`, `warn`, `act`; see [Alerts](alerts.md) |
| `cooldown_minutes` | no (60) | per rule and sensor, enforced against `alerts`. An `act` rule may not exceed 2880, the window after which the node counts a silent rule as cleared; `tests/test_share.py` fails a slower one |
| `long_cooldown_ok: true` | when cooldown > 20160 | tells the lint a cooldown over a fortnight is deliberate |
| `watch: {metric, over}` | no | the indicator and the line the rule is about, so `GET /effect` can time how long after an action the reading came back under it. The lint fails if the metric or the number is missing from the SQL. Leave it out where the rule fires on a relation between two readings |
| `message` | unless `contributes` | a string or `{en, id, es}`; filled with the row by `str.format`; `None` renders as `—` |
| `contributes: report` | instead of `message` | never sent; the first row lands in the report bundle under the rule's id |

The node picks `message[ALERT_LOCALE]` and falls back to `en`. Every shipped rule carries all three
languages. Every `{placeholder}` in every language must be a column the top-level `SELECT` returns.

End a message with a paragraph that starts with 👉 and says what a person does. The dashboard's Decide card
lifts that paragraph out and shows it on its own as "what this node suggests"; a rule without one gets a line
saying the rule carries no recommendation, because the page will not invent one. A rule should end in
something a person does, and one that fires on indoor sensors as if they were ambient will not be merged:
`NOT s.indoor` is not decoration.

`make lint` (`tools/check_rules.py`, with sqlglot) parses the SQL against `init.sql` and refuses unknown
tables and columns, placeholders the SQL does not return, a cell without a `value`, a cooldown over a
fortnight without `long_cooldown_ok`, a `watch:` whose metric or number is not in the SQL, a rule with both a
message and a contribution, and one with neither, which could fire and reach nobody.

What a rule may read: the `stats` view (`sensor_id, metric, indoor, local, kind, scale, lat, lon, name,
last, last_ts, silent_minutes, mean_15m, mean_1h, mean_24h`: the last 24 hours, sensors only),
`readings_1h` (hourly `mean, min, max, n` over all history), `observations` (the latest value per slow
source), `readings`, `sensors`, `channel_roles`, and the node's own position and time zone as Postgres
settings: `current_setting('planetai.lat')`, `current_setting('planetai.lon')`, `current_setting('TimeZone')`.
Days are local days (`NODE_TZ` is the session time zone), so `date_trunc('day', ts)` means the household's
day, not UTC's.

A contributor has no level, no cooldown and no message:

```yaml
- id: digest
  contributes: report
  sql: SELECT round(avg(mean_1h)) AS inside FROM stats WHERE local AND indoor AND metric='pm25'
```

## Cells

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
portal, whatever its quality. Never claim `live` for a model. The core demotes `live` to `partial` when the
in-custody hourly buckets in 24 hours are fewer than `min_buckets`, or when too few in-custody sensors
report (two where the node has children or is above community scale, one otherwise), and appends
`have/need hourly buckets` to the note. A `NULL` value omits the cell: absent, not zero. The cell's source is
recorded as `planetai-node · pack:<id>`, and the core adds one cell of its own, `Governance|<Scale>` =
[ρ](rho.md). Each row also carries `registered` and `adapter` from [the source registry](sources.md). On
`main` after v0.72.1 (the changelog's Unreleased section), it also carries `reviewed`, `candidate` and
`capable`, and `registered` means `reviewed`.

## Channel roles

A pack that adds a metric says what it is, keyed on `(source, metric)`:

```yaml
- { source: forecast-om, metric: fc_wind_speed, role: derived, comparable: false, unit: "km/h" }
```

Roles are `ambient`, `enclosure`, `device_health`, `derived` and `index`, defined on the
[sensors](sensors.md) page. The core's `config/channels.yml` is read first; a pack may not redeclare a pair
the core already claimed, and the duplicate is logged and dropped. A pack that adds no metric ships
`channels.yml` as `[]` to say so, as `trust` does.

## Code packs: adapters

`adapter.py` with `fetch(hc) -> (sensors, readings)`, the same contract as `app/sources.py`. Off unless
`PACKS_ALLOW_CODE=1`. Dependencies and settings go in `pack.yaml`. `planetai packs` lists what is loaded
and says when a dependency or a setting is missing; `planetai packs install` adds the missing `env:` keys to
`.env` and rebuilds the image once with every pack's `pip:` list. A pack that needs a key or a service must
log once and return nothing when it is missing. `packs/earth-engine` is the worked example: a dependency, a
credential, several remote datasets, and it idles until configured. `packs/make` is the example of a code
pack that stores places rather than numbers.

## Scripts

Things you ask for rather than things that run on a schedule:

```bash
planetai run                          # lists every script with its first line
planetai run earth change --all       # the land change for every consecutive year pair this node has cached
planetai run nearby stations          # every station in the ring, with the reason for each exclusion
planetai run place gaps               # a mapping brief: what is undrawn within the kilometre
planetai run season window            # every paired station, its week, its baseline, the step
```

They run inside the app container, where the dependencies are, with `PACK_OUT=/app/out`. `out/` is the one
writable path, and what they write there is yours to send anywhere. Every `*.py` in a pack except
`adapter.py` is listed, so a helper module shows up too (`place/satellite.py` does).

## A dashboard section

A pack can put a section on the dashboard by registering one object with the page contract:

```js
window.PAI.register({
  id: 'meshtastic',            // required, unique; the band's DOM id
  pack: 'meshtastic',          // required
  stage: 'observe',            // required: observe · decide · act · measure
  title: 'The mesh in this house',  // required
  render(ctx) { … },           // render or lead is required; captions belong here, explanations do not
  order: 41,                   // within the stage, lower first (default 50)
  level: 'advanced',           // default; 'simple' opts the section into simple mode
  needs: ['H3.radio.mesh'],    // dotted paths off window; absent → one honest line, never a blank
  learn: ['states'],           // learn marks this section carries
  controls(ctx) { … },         // optional control strip
  wall(ctx) { … },             // what this section contributes to the wall
  notes(ctx) { … },            // [{ id, label, text }]: the explanations, gathered at the foot of the page
});
```

A section may not invent a fifth card kind (readout · stack · series · row), colour a state by hue, print a
numeral without `data-num`, or put its explanation in its body. In v0.72.1 a section lives inline in
`app/static/dashboard.js`, because the node serves its static files from a fixed allowlist by name, and
serving a pack's own file needs a name on that list the node does not have. Proposing a section today is
sending the code with its `render()` and its `notes()`. The page itself is described on
[Dashboard](dashboard.md).

## Sending one upstream

Fork, add the folder, run `make lint`, open a PR. Say in the README where the thresholds come from and which
place you wrote for: thresholds for Kuta Selatan are not thresholds for Barcelona. A source the pack reads
has to be an entry in the registry first, so `sources:` can name it. Ten ideas, with who might write
them, are on [Pack ideas](pack-ideas.md); the issue a new domain declares is explained on [Issues](issues.md).

## Where this leads

A pack reads what the node already holds. When the thing your place needs measured is not held yet, the
next page is [the source registry](sources.md): what the network has filed as measurable at each pillar and
scale, which of it any code reads, and which is waiting for somebody to write the adapter.
