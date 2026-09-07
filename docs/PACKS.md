# Packs

A pack is a folder in `packs/`. It carries rules, Index cells, or an adapter for a new source. The core knows nothing
about air, water or heat; the packs do. Node #1 runs twelve.

```
packs/<id>/
  pack.yaml     id, name, description, kind (data | code), version, pip:, env:
  rules.yml     alerts: SQL that returns rows, one message per row
  cells.yml     Index cells: SQL that returns one `value`
  adapter.py    a new source; code packs only
  channels.yml  what a pack's own metrics ARE — ambient, enclosure, index, etc.
  README.md     where the thresholds come from, what the pack assumes
```

## Data packs

YAML only. Anyone can write one. Rules read `stats` (24-hour rolling, per sensor and metric), `readings_1h` (hourly
means, all history) and `observations` (portals and models). Postgres does the maths, including `corr()`. The SQL runs
as a read-only role (`planetai_ro`, in `init.sql`): every table but `settings`, and no writes, so a rule cannot read a
token into an alert text or change a row.

```yaml
- id: indoor_pm25_high
  level: act                 # info | warn | act
  cooldown_minutes: 120
  sql: SELECT sensor_id, name, mean_15m FROM stats WHERE local AND indoor AND metric='pm25' AND mean_15m > 35
  message:
    en: "Indoor PM2.5 at {name} is {mean_15m:.0f} µg/m³. Purifier on, windows shut."
    id: "PM2.5 dalam ruangan di {name} {mean_15m:.0f} µg/m³. Nyalakan pembersih udara, tutup jendela."
```

Every column the message uses must come from the SQL. `make lint` checks that, plus unknown columns, cells without a
`value`, and cooldowns over a fortnight (add `long_cooldown_ok: true` if that is deliberate).

A rule can compute something for the report instead of interrupting anyone:

```yaml
- id: digest
  contributes: report        # no level, no cooldown, no message: this is never sent
  sql: SELECT round(avg(mean_1h)) AS inside FROM stats WHERE local AND indoor AND metric='pm25'
```

Its first row lands in the report bundle under the rule's own id (`bundle.digest`), where the node's own report
reads it and a model, if one is reachable, may quote from it. A contributor has no message and is never sent;
`make lint` refuses a rule with both, and refuses a rule with neither, which could fire and reach nobody.

A cell:

```yaml
- cell: "Environmental|Community"
  unit: "PM2.5 µg/m³ 24h mean"
  state: live                # live | partial | mock. The core demotes live to partial below min_buckets.
  min_buckets: 12
  sql: SELECT avg(mean_24h) AS value FROM stats WHERE local AND indoor AND metric='pm25'
```

`state` is provenance, not confidence. `live` means measured here; `partial` means derived or a model; never claim `live`
for a model.

### Channel roles

A pack that adds a metric says what it IS in `channels.yml`, keyed on `(source, metric)`:

```yaml
- { source: my-sensor, metric: co2, role: ambient, comparable: true, unit: "ppm" }
```

Five roles: `ambient` (the air, water or land at a place — comparable between sensors there), `enclosure` (the
inside of the instrument's own box — a BME680 sealed inside a radio reports the box, not the street, so this is
never averaged as ambient), `device_health` (the instrument talking about itself, e.g. battery), `derived`
(computed by us from other readings), and `index` (a vendor's own composite number, never pooled with anyone
else's). `config/channels.yml` has the core declarations; `make lint` checks every metric against `app/sources.py`.
A role is keyed per source and metric, not per device: every sensor an adapter drives shares it, so a node whose
hardware differs from that adapter's usual shape (an external probe on a Meshtastic pod) cannot override it yet.

## Code packs

`adapter.py` with `fetch(hc) -> (sensors, readings)`, the same contract as `app/sources.py`. Off unless
`PACKS_ALLOW_CODE=1`: a pack runs with the node's privileges, so read it first.

Dependencies and settings are declared in `pack.yaml`; `planetai packs` lists what is loaded and what is missing, and
`planetai packs install` installs the libraries into the image once and
adds the settings to `.env` under a dated marker:

```yaml
pip: [earthengine-api]
env:
  - "# earth-engine: project id, or blank to read it from the key file"
  - "EE_PROJECT="
```

No padding after `=`: a value pasted after spaces becomes `VAR= value`, which the shell runs as a command.

A pack that needs a key or a service must log once and return nothing when it is missing. It must never take the node
down. `packs/earth-engine` is the worked example: a dependency, a credential, four remote datasets, and it idles until
configured.

## Scripts

A pack can ship scripts: things you ask for rather than things that run on a schedule.

```bash
planetai run earth-engine timelapse --n 4 --gap 5
```

They run inside the app container, where the dependencies are, and write to `out/`, the one writable path. `planetai run`
alone lists them.

## What ships

| pack | kind | what |
|---|---|---|
| air-quality | data | PM2.5 rules (inside/outside, spikes), cells |
| heat | data | apparent temperature, heat stress, nights over 28 °C, a Social cell |
| insight | data | the air three ways, contributed to every report; daily agreement between indoor, street and model |
| nearby | data | the ring of other people's stations: is this address worse than everywhere, or is everywhere worse — no cell, by design |
| forecast | code | wind and rain for the next day, from BMKG and Open-Meteo — context for the report, no alerts, no cell |
| trust | data | coverage, frozen channels, collocated disagreement — needs a week of a sensor before it names it; all three `info`, no cell, by design |
| cold-start | data | day one with no hardware: modelled air, normals |
| open-data-health | data | a CKAN portal's maintenance state → Governance\|City |
| coast | code | waves, swell, sea temperature (Open-Meteo Marine, key-free) |
| earth-engine | code | tree cover, built-up, NDVI, night lights (Google Earth Engine) |
| earth | code | this node's own copy of the AlphaEarth embeddings: the land change computed here, and a picture of the place for every year |
| place | code | what is around the node from OpenStreetMap, in PostGIS: buildings, shops, schools, clinics, roads, green, walking distances |
| example-cooking-hours | data | a worked example |

Ten more ideas, with who might write them: [`PACK_IDEAS.md`](PACK_IDEAS.md).

## Contributing one

Fork, add the folder, `make lint`, open a PR. The README must say where the thresholds came from and what the pack does
not know. Thresholds for Kuta Selatan are not thresholds for Barcelona; say which place you wrote for.
