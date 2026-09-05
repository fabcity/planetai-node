# Packs

A pack is a folder in `packs/`. It carries rules, Index cells, or an adapter for a new source. The core knows nothing
about air, water or heat; the packs do. Node #1 runs eight.

```
packs/<id>/
  pack.yaml     id, name, description, kind (data | code), version, pip:, env:
  rules.yml     alerts: SQL that returns rows, one message per row
  cells.yml     Index cells: SQL that returns one `value`
  adapter.py    a new source; code packs only
  README.md     where the thresholds come from, what the pack assumes
```

## Data packs

YAML only. Anyone can write one. Rules read `stats` (24-hour rolling, per sensor and metric), `readings_1h` (hourly
means, all history) and `observations` (portals and models). Postgres does the maths, including `corr()`.

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

## Code packs

`adapter.py` with `fetch(hc) -> (sensors, readings)`, the same contract as `app/sources.py`. Off unless
`PACKS_ALLOW_CODE=1`: a pack runs with the node's privileges, so read it first.

Dependencies and settings are declared in `pack.yaml`; `planetai packs` installs the libraries into the image once and
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
| insight | data | digest every 3 h; daily agreement between indoor, street and model |
| cold-start | data | day one with no hardware: modelled air, normals |
| open-data-health | data | a CKAN portal's maintenance state → Governance\|City |
| coast | code | waves, swell, sea temperature (Open-Meteo Marine, key-free) |
| earth-engine | code | tree cover, built-up, NDVI, night lights, land change (Google Earth Engine) |
| example-cooking-hours | data | a worked example |

Ten more ideas, with who might write them: [`PACK_IDEAS.md`](PACK_IDEAS.md).

## Contributing one

Fork, add the folder, `make lint`, open a PR. The README must say where the thresholds came from and what the pack does
not know. Thresholds for Kuta Selatan are not thresholds for Barcelona; say which place you wrote for.
