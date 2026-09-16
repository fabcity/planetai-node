# Sensors and sources

How readings enter a node, which sources ship, and the rules that keep the numbers right. Several of the
rules come from Bali Air Dispatch's methodology and are credited where used. What the node knows before
any sensor exists is on [Before a sensor](before-a-sensor.md).

## The adapter contract

One function in `app/sources.py` (or a pack's `adapter.py`), returning two lists:

```python
def my_source(hc: httpx.Client, ...) -> tuple[list[dict], list[tuple]]:
    sensors  = [{"sensor_id": "xx-123", "source": "my_source", "name": "...", "lat": .., "lon": ..,
                 "indoor": False, "local": True, "kind": "sensor", "scale": "community", "meta": {...}}]
    readings = [(ts_utc, "xx-123", "pm25", 12.3), ...]
    return sensors, readings
```

Readings dedupe on `(sensor_id, metric, ts)`, so polling twice is harmless. `sensor_id` is
`<source>-<upstream id>` and is never reassigned. `local` means yours. `indoor` must be correct; the rules
depend on it. `kind` is `sensor`, `portal`, `model`, `map` or `child`; only `sensor` rows enter `stats`.

`local` is two facts at once: an adapter says whether a sensor is *yours*, and the node checks whether it is
*here*. A kit on your account 1.2 km away is yours and is not this node's measurement. `LOCAL_RADIUS_M`
(500 m) is the line. A sensor with no coordinates that arrives over your own gateway stays local.

Metric names are lowercase with no unit in the name: `pm25 pm25_raw pm10 pm1 temp humidity pressure aqi
gas_resistance noise light eco2 tvoc co2 tvoc_index nox_index`. Units are fixed: µg/m³, °C, %, kPa. The
first pack to ship a metric names it.

A pack's adapter must log once and return nothing when its key or service is missing. It must never take the
node down.

## What ships

The poll loop asks `sources.enabled()` which adapters to run. In this version:

| source | enabled by | `kind` | `local` | what it reads |
|---|---|---|---|---|
| **Smart Citizen** | `SC_DEVICES=19880,…` or `SC_USER=name` (every kit on the account; `SC_EXCLUDE` drops some) | `sensor` | yes, then narrowed by `LOCAL_RADIUS_M` | Public API, no key. Metrics mapped by measurement *name*, so SCK 2.1 and 2.3 both work. `indoor` from each kit's own `exposure`. Not humidity-corrected: the Seeed HM-3301 is not a Plantower and the EPA correction was not derived for it. |
| **Bali Air Dispatch** | `BAD_ENABLED=1` (the Bali preset; off elsewhere) | `sensor` | never | The ring: other people's stations within `BAD_RADIUS_KM` (15; the Bali preset says 8), the outdoor reference this node is read against. Drops stations the archive suspects are indoor or malfunctioning (`BAD_INCLUDE_INDOOR=1` keeps the indoor ones), and keeps this node's own kit out of its own ring three ways — the ids it already polls, anything within `BAD_MIN_SEPARATION_M` (150) of the node, and `BAD_EXCLUDE` by hand — plus one rule against a single device arriving under two networks' ids. Stores `pm25` and `pm25_raw`. Attribution: Bali Air Dispatch and the row's network. |
| **Open-Meteo** and **CAMS** | `OPENMETEO_ENABLED=1` (default) | `model` | never | Weather now at the node's coordinates; PM2.5, PM10, O₃, NO₂, dust and UV from the Copernicus model at 11 km, as `cams-point`. Free, key-free, anywhere on Earth. Never in an ambient average. |
| **NASA POWER** | the first-start bootstrap (`BOOTSTRAP=1`) | `model` | never | Forty years of monthly temperature, humidity and rain normals, as `power-point`. |
| **CKAN portals** | `CKAN_PORTALS=slug=url,…` (the presets name one per pilot) | `portal` | never | A portal's maintenance state — datasets total, share touched in 90 days — for the `open-data-health` pack's `Governance|City` cell. Scale from `CKAN_SCALE` (`city`). |
| **Meshtastic radios** | `MQTT_HOST` (set by `planetai meshtastic`) | `sensor` | yes | Telemetry from field radios through the gateway's MQTT uplink, `msh/#`. `MESH_INDOOR_NODES=!id,!id` marks the indoor ones. DIY pods publish to `planetai/sensors/<id>/<metric>` on the same broker. A radio's own temperature, humidity and pressure are its enclosure, not the street — see channel roles below. |
| **Code packs** | `PACKS_ALLOW_CODE=1` and the pack's own settings | as declared | as declared | `coast` (Open-Meteo Marine), `forecast` (BMKG, Open-Meteo), `earth` (AlphaEarth embeddings), `earth-engine` (Dynamic World, Sentinel-2, VIIRS), `place` (OpenStreetMap into PostGIS). See [Packs that ship](packs-reference.md). |

> **Gap in v0.57.** Two LAN adapters are written and tested but not registered for polling. **AirGradient**
> (`AIRGRADIENT_HOSTS`, read on the LAN, EPA 2021 correction applied with raw kept as `pm25_raw`) and
> **PurpleAir** (`PURPLEAIR_HOSTS`, `/json`, two Plantower channels averaged and corrected) have functions in
> `app/sources.py` and rows in `config/channels.yml`, and `sources.enabled()` never calls them; the hosts you
> set are used only to keep your own devices out of the Bali Air Dispatch ring. `SENSOR_INDOOR` has no
> reader. The changelog records both adapters as shipped, so read this as a regression to be fixed rather
> than a decision.

Opt-in sources that need a key or an account — OpenAQ, Google Flood Hub, Sentinel-5P, NASA FIRMS — are a
code pack or an adapter behind a flag each, off by default. Nothing that needs an account runs unless you
turn it on.

## Channel roles

A metric means different things from different devices. `config/channels.yml`, and a pack's own
`channels.yml`, declare what each `(source, metric)` **is**, and the declarations are written to
`channel_roles` at every start:

| role | meaning | examples |
|---|---|---|
| `ambient` | the air, water or land at a place; comparable between sensors there | Smart Citizen `pm25`, `temp`, `noise`; Bali Air Dispatch `pm25`; a Meshtastic pod's `pm25` |
| `enclosure` | the inside of the instrument's own box; never averaged as ambient | a Meshtastic radio's `temp`, `humidity`, `pressure`, `gas_resistance` — a BME680 sealed in a radio reports the box, not the street |
| `device_health` | the instrument talking about itself | `battery_pct`, `battery_v`, `lora_util_pct`, `lora_channel_pct` |
| `derived` | computed by us from other readings | `open-meteo-cams` `pm25_model`; every `fc_*` forecast metric |
| `index` | a vendor's own composite, never pooled with anyone else's | `aqi`, `bme_iaq`, `eco2`, `tvoc_index`, `nox_index` |

`comparable` says whether two sensors' values of that metric may be compared (`pm25_raw` is not); `reference`
names the sensing element (`plantower`, `sc`, `bme680`). A role is keyed per source and metric, not per
device, so a node whose hardware differs from an adapter's usual shape cannot override it yet.

## The rules we inherit

1. **Indoor sensors measure a room.** Never in an ambient average.
2. **Silence is defined by value change, not by a timestamp.** `stats` exposes `silent_minutes`, and that
   number is true per kit and false per channel: Smart Citizen's per-reading timestamp is null on every kit
   node #1 reads, so the adapter stamps every channel with one kit-level time at poll. A channel that has
   stopped producing new values still gets a fresh timestamp on every poll, and its frozen value is
   re-inserted under it — forever — which pulls the 24-hour mean toward the frozen number and shrinks its
   variance, so a dying channel looks steadier, not worse. The `trust` pack's `channel_dead` rule looks at the
   value instead.
3. **A daily mean can be one reading.** Check `n` before trusting an aggregate.
4. **Instants are UTC; days are local.** Daily buckets use `NODE_TZ`. Bali's 9 am burn peak vanishes on a UTC
   day.
5. **Corrected ≠ raw.** Store both. Never overwrite raw.
6. **Gaps are real.** No fill, no zero, no interpolation. A gap in a series is a gap in the line.
7. **These are not reference instruments.** Good for patterns and magnitudes; the node labels them as such.
8. **Sensors in the same place disagree.** Three kits at one address read the same air and do not agree: one
   of them runs about 1.5× the other two. Collocation is the cheapest calibration a node can run, and most
   nodes have it by accident. The `trust` pack's `peer_disagreement` rule is what reads it.

## "Outside" resolves in one order

Your own outdoor sensors; else the three nearest public references; else the model. The same order in the
rules, the report's digest and the dashboard. Averaging every station within 15 km once put an Uluwatu
reading of 3 next to the street's 15.

## The EPA 2021 humidity correction

Optical PM sensors over-read in humid air; Bali runs 45–70% RH. `epa_2021_correct(pm_raw, rh)` implements
the US EPA 2021 Plantower correction: raw 28 at Bali humidity becomes about 15. Near-zero raw in dry air
lifts to 1–2, a property of the regression with no health meaning. It applies to PurpleAir, AirGradient and a
DIY PMS5003, and not to Smart Citizen, IQAir, AQICN or Airly.

## Siting

Three to six metres up. Away from a kitchen exhaust, a chimney, a parking spot. Outdoor air, sheltered from
horizontal rain. 2.4 GHz WiFi. Name it after the place: the name becomes the sensor's name on the page and in
every message. For our own enclosures, the outdoor-sensor-enclosure work is the printable answer, and Fab Lab
Bali prints it. Indoor units in cases have read 2–6 °C above the room; one logged action on node #1 was
"opened sensor cases".

## Thresholds the air rules use

| PM2.5 µg/m³ | scale | used for |
|---|---|---|
| 15 | WHO 2021, 24-hour | the "clean" line everywhere; the floor of `inside_worse_ventilate` |
| 35.5 | US EPA / WHO interim target 1 | `indoor_pm25_high`, `outside_worse_keep_shut`, the "moderate" ceiling |
| 55.5 | US EPA Unhealthy | `outdoor_pm25_high` |

Spikes: 2.5× the day's mean, above 12 indoors or 15 outdoors — "something changed" before anything is
unhealthy. Thresholds for Kuta Selatan are not thresholds for Barcelona; a pack's README says which place it
was written for.

## Adding a source

An adapter is one function returning `(sensors, readings)`. Test it against a saved payload from the real
device before opening a PR, and set `local` and `indoor` honestly — every rule depends on them. A source
that belongs to a domain goes in a pack's `adapter.py` ([Packs](packs.md)); a device driver the core should
know goes in `app/sources.py`. Either way, add its metrics' roles to a `channels.yml`, and add the source to
[`awesome-fabcity-data`](https://github.com/fabcity/awesome-fabcity-data) so the Index knows it exists.
