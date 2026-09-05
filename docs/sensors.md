# Sensors and sources

How readings enter a node, and the rules that keep the numbers right. Several rules come from Bali Air Dispatch's
methodology; where we copy one, we say so.

## The adapter contract

One function in `app/sources.py` (or a pack's `adapter.py`):

```python
def my_source(hc: httpx.Client, ...) -> tuple[list[dict], list[tuple]]:
    sensors  = [{"sensor_id": "xx-123", "source": "my_source", "name": "...", "lat": .., "lon": ..,
                 "indoor": False, "local": True, "kind": "sensor", "scale": "community", "meta": {...}}]
    readings = [(ts_utc, "xx-123", "pm25", 12.3), ...]
    return sensors, readings
```

Readings dedupe on `(sensor_id, metric, ts)`, so polling twice is harmless. `local` means yours. `indoor` must be
honest; the rules depend on it. `kind` is `sensor`, `portal`, `model` or `child`; only `sensor` enters `stats`.

Metrics: `pm25 pm25_raw pm10 pm1 temp humidity pressure aqi gas_resistance noise light eco2 tvoc`. Units: µg/m³, °C, %, kPa.

## What ships

**Smart Citizen** (`SC_USER=you`, or `SC_DEVICES=19880,...`). Public API, no key. With a username every kit on the
account is read as yours; indoor/outdoor from each kit's own `exposure`. `SC_EXCLUDE` drops kits at another site.
Metrics are mapped by measurement name, since sensor ids differ between kit generations. Not humidity-corrected: the
Seeed HM-3301 is not a Plantower and the EPA correction was not derived for it.

**AirGradient** (`AIRGRADIENT_HOSTS=airgradient_abc.local`). Read on the LAN, never through the cloud. Plantower inside:
EPA 2021 correction applied, raw kept as `pm25_raw`.

**PurpleAir** (`PURPLEAIR_HOSTS=192.168.1.50`). LAN, `/json`. Two Plantower channels averaged; corrected; raw kept.

**Meshtastic** (`planetai meshtastic`). Telemetry from radios via the gateway's MQTT uplink. `MESH_INDOOR_NODES` marks the
indoor ones. DIY pods publish to `planetai/sensors/<id>/<metric>` on the same broker.

**Bali Air Dispatch** (`BAD_ENABLED=1`, Bali). The island's public stations within `BAD_RADIUS_KM` as outdoor references.
Kits you read directly are skipped, so nothing is counted twice.

**Open-Meteo, CAMS, NASA POWER**. Free, key-free, anywhere. Weather now; PM2.5, PM10, O₃, NO₂, dust, UV from the
Copernicus model at 11 km; climate normals. `kind='model'`, never in an ambient average.

**CKAN portals** (`CKAN_PORTALS=slug=url`). A portal's maintenance state → `Governance|City`.

## The rules we inherit

1. **Indoor sensors measure a room.** Never in an ambient average.
2. **Latest held ≠ latest measured.** A dead sensor still has a "latest". `stats` looks back 24 h and exposes `silent_minutes`.
3. **A daily mean can be one reading.** Check `n` before trusting an aggregate.
4. **Instants are UTC; days are local.** Daily buckets use `NODE_TZ`. Bali's 9 am burn peak vanishes on a UTC day.
5. **Corrected ≠ raw.** Store both. Never overwrite raw.
6. **Gaps are real.** No fill, no zero, no interpolation.
7. **These are not reference instruments.** Good for patterns and magnitudes. Say so.

## "Outside" resolves in one order

Your own outdoor sensors; else the three nearest public references; else the model. The same order in the rules, the
digest and the dashboard. Averaging every station within 15 km once put an Uluwatu reading of 3 next to the street's 15.

## The EPA 2021 humidity correction

Optical PM sensors over-read in humid air. Bali runs 45–70% RH. `epa_2021_correct(pm_raw, rh)` implements the US EPA 2021
Plantower correction; raw 28 at Bali humidity → about 15. Near-zero raw in dry air lifts to 1–2: a property of the
regression, no health meaning. Apply to PurpleAir, AirGradient, DIY PMS5003. Do not apply to Smart Citizen, IQAir,
AQICN, Airly.

## Siting

Three to six metres up. Away from a kitchen exhaust, a chimney, a parking spot. Outdoor air, sheltered from horizontal
rain. 2.4 GHz WiFi. Name it after the place. For our own enclosures, the outdoor-sensor-enclosure work is the printable
answer; Fab Lab Bali prints it.

## Thresholds

| PM2.5 µg/m³ | scale | used for |
|---|---|---|
| 15 | WHO 2021 24-hour | "clean" line everywhere; `inside_worse_ventilate` floor |
| 35 | WHO interim target 1 | `indoor_pm25_high`, `outside_worse_keep_shut`, "moderate" ceiling |
| 55.5 | US EPA Unhealthy | reserved |

Spikes: 2.5× today's mean, above 12 indoors or 15 outdoors. That says "something changed" before anything is unhealthy.
