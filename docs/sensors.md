# Sensors and sources

How readings get into a node, how to add a new kind, and the rules we inherit so our numbers stay honest.
Much of this is learned from Bali Air Dispatch's methodology and API documentation; where we copy a rule, we say so.

## 1. The adapter contract

An adapter is one function in `app/sources.py`:

```python
def my_source(hc: httpx.Client, ...) -> tuple[list[dict], list[tuple]]:
    sensors  = [{"sensor_id": "xx-123", "source": "my_source", "name": "...", "lat": .., "lon": ..,
                 "indoor": False, "local": True, "meta": {...}}]
    readings = [(ts_utc_datetime, "xx-123", "pm25", 12.3), ...]
    return sensors, readings
```

Register it in `enabled()` behind an env flag. Readings are deduplicated by `(sensor_id, metric, ts)` so polling
twice is harmless. Set `local=True` only for hardware physically at this node. Set `indoor` honestly.

Metric names: `pm25 pm25_raw pm10 pm1 temp humidity pressure aqi gas_resistance noise light eco2 tvoc`.
Units fixed: µg/m³, °C, %, kPa.

## 2. Sources that ship (pick your sensor in `.env` or with installer flags)

### Smart Citizen (`SC_DEVICES=19880,...`)

Polls `https://api.smartcitizen.me/v0/devices/<id>`. Public, no key. The device id is the number in
`smartcitizen.me/kits/<id>`. We map on `measurement.name`, not sensor id, because ids differ between kit
generations (SCK 2.1: PM2.5 is sensor 87; SCK 2.3 with the Seeed HM-3301: sensor 234). Names don't.

Node #1 (19880, "Bayu 2 – Indoor"): PM1/2.5/10 (Seeed HM-3301), temp/humidity/pressure/gas/AQI (Bosch BME68x).
`exposure: indoor` in the kit's location → `indoor=True`. This is what makes the indoor/outdoor rules work.

Smart Citizen PM values are **not** humidity-corrected here. BAD publishes SC as-supplied; we do the same.
The HM-3301 is not a Plantower and the EPA correction wasn't derived for it.

For historical backfill, `GET /v0/devices/<id>/readings?sensor_id=<n>&rollup=1h&from=YYYY-MM-DD&to=YYYY-MM-DD`
returns `[ts, value]` pairs. Not implemented — the node starts recording the day it starts.

### Bali Air Dispatch (`BAD_ENABLED=1`) — Bali only

Polls `https://baliairdispatch.com/api/v1/latest`. Public, key-free, GET-only, edge-cached 5–60 min. Aggregates
Nafas, IQAir, PurpleAir, AQICN, OpenAQ, AirGradient, Smart Citizen and Airly. We:

- drop rows where `stale: true` (reading older than 24 h — "latest held" is not "latest measured")
- keep stations within `BAD_RADIUS_KM` of the node
- store `pm25` (published) and `pm25_raw` (uncorrected, present only where BAD corrected)
- carry `suspected_indoor` into `sensors.indoor`
- record the originating network in `meta.network`

Bali only. Set `BAD_ENABLED=0` (`--no-bad`) everywhere else, which the presets already do.

What replaces it elsewhere: the Copernicus CAMS model point sample, which ships on by default and works at any
coordinates on earth. It is a model rather than a measurement, so it is coarser than a station down the road, but it
needs no key and never leaves you without a reference. OpenAQ carries measured regulatory and low-cost stations
worldwide and would be the better source in Delhi, Santiago or Barcelona; it now requires a free API key, so it is
an opt-in adapter rather than a default. See `PREFILL.md`.

**Attribution is required and non-negotiable:** credit *Bali Air Dispatch, baliairdispatch.com* and the network in
`meta.network` in anything published from these rows. They kept the record; the networks did the measuring.

Two sources of the same PurpleAir/AirGradient reading may appear (an `ag-` row and an `oq-` row at the same
coordinates). The `outside_worse_keep_shut` rule averages across reference stations, so a duplicate double-weights
one device slightly. Acceptable at v0.1; de-duplicate on coordinates if it ever matters.

If we deploy an outdoor sensor of our own, it should also publish to a network BAD reads (AirGradient → OpenAQ,
PurpleAir, or SC). Then it's on the public map and we're a contributor, not only a consumer.

### AirGradient (`AIRGRADIENT_HOSTS=airgradient_84fce6.local,…` / `--airgradient`)

BAD's recommended hardware for Bali: ONE kit $125, Pro $225, ships from Chiang Mai in 5–8 days, open hardware,
PM1/2.5/10 + CO2 + TVOC + NOx + temp/humidity. Read **directly over your WiFi** at
`http://<host>/measures/current` — no account, no cloud, no third party. This is the outdoor sensor for node kits.

We store the device's raw `pm02` as `pm25_raw` and `epa_2021_correct(pm02, rhum)` as `pm25`; also `pm1 pm10 co2 temp
humidity tvoc_index nox_index`. `sensor_id` is `ag-<serial>`. Set `SENSOR_INDOOR=1` (`--indoor`) if it's inside —
the device doesn't know. Field names are from firmware 3.x; if a newer firmware renames them the adapter logs
`0 readings` and the fix is one dict in `sources.py`.

### PurpleAir (`PURPLEAIR_HOSTS=192.168.1.60` / `--purpleair`)

Read directly at `http://<ip>/json?live=true`. Use the IP; PurpleAir's `.local` name is unreliable. We average the two
laser channels' `pm2_5_cf_1` (that is what EPA 2021 was fitted on), store the average as `pm25_raw` and the corrected
value as `pm25`; also `pm10 humidity pressure` and `temp` (converted from °F — PurpleAir's temperature reads high and
we convert, not correct). If channels A and B disagree badly we record `channel_disagreement` — one laser is dying,
and that's a rule for later. Tested against BAD's published Klungkung row: raw 47.8 → 36.6 on their side, 47.3 → 36.0
on ours from the A/B mean. `sensor_id` is `pa-<mac>`.

### Meshtastic mesh sensors (`planetai meshtastic`)

Any Meshtastic radio with a sensor on it — a Wio Tracker L1 with a BME680 or HM3301 on the Grove port — reports over
LoRa to the gateway radio, which uplinks to the node's own broker. Readings land as `msh-<nodeid>` with the radio's GPS
position and its long name. `environment_metrics` (temperature, humidity, pressure, gas, IAQ, lux, wind, rainfall,
soil) and `air_quality_metrics` (PM1/2.5/10 standard and environmental, CO₂, VOC and NOx indices) are mapped; battery
level and LoRa channel utilisation come along for the dead-sensor rule and battery planning. Field names follow
Meshtastic 2.x; an unknown one is logged once. HM3301 needs no humidity correction (Seeed, not Plantower); a Plantower
PMSA003I on a mesh radio would, and that case is not handled yet.

### DIY pods over MQTT

With the broker up, anything that can publish `planetai/sensors/<id>/<metric>` with `{"value": 12.3, "indoor": false}`
is a sensor. An ESP32 with a PMS5003 and a BME280 on your WiFi is the cheapest outdoor unit there is; correct its
PM with `epa_2021_correct` in firmware or in a small pack.

## 3. Sources to add next, in order of usefulness

### DIY: PMS5003 + BME280 on an ESP32 → MQTT

The cheapest route (~$30–50 per pod) and the one fab labs can build in a workshop. Publishes over MQTT. This is
the trigger for bringing the Mosquitto container back (SPEC §6): a 30-line `mqtt` adapter that subscribes to
`planetai/sensors/<id>/<metric>` with payload `{"value": 12.3, "ts": "..."}`. Correct with EPA 2021 (Plantower).

### Open-Meteo (context, not a sensor)

Wind speed and direction at the node's coordinates, free, no key. BAD uses it for the wind layer. Useful the day
a rule wants "upwind" — not before.

## 4. The rules we inherit (read before averaging anything)

Copied, gratefully, from BAD's "reading the data honestly" section and applied to our own data:

1. **Indoor sensors measure a room.** Never in an ambient average. `sensors.indoor` is on every row; rules filter on it.
2. **Latest held ≠ latest measured.** A sensor that died months ago still has a "latest" value. Filter by age. Our `stats` view only looks back 24 h and exposes `silent_minutes`.
3. **A daily mean can be one reading.** Check the sample count (`n` in `readings_1h`) before plotting or alerting on an aggregate.
4. **Instants are UTC; days are local.** Daily buckets use `NODE_TZ` (WITA). The burn pattern — 9am peak, after-dark climb — disappears on a UTC day.
5. **Corrected ≠ raw, and only from a date.** Store both. Never overwrite raw. Say which one you're showing.
6. **Gaps are real.** No forward-fill, no zero, no interpolation. A hole means nobody was measuring.
7. **These are not reference instruments.** Low-cost sensors drift, disagree and are affected by humidity and siting. Good for patterns and magnitudes; say so.

## 5. The EPA 2021 humidity correction

Low-cost optical PM sensors size particles with a laser. In humid air, water-swollen particles scatter more light
and the sensor over-reads. Bali runs 45–70% RH, so the over-read is large. The US EPA 2021 correction (Barkjohn et
al., extended 2022) for Plantower-based sensors is implemented as `epa_2021_correct(pm_raw, rh)` in `sources.py`.
It reproduces BAD's example: raw 28 µg/m³ at Bali humidity → ~15. It has a floor: near-zero raw in dry air lifts
to ~1–2, which is a property of the regression, not the sensor, and has no health meaning.

Apply to: PurpleAir, AirGradient, DIY PMS5003/PMS7003. Do **not** apply to: Smart Citizen (Seeed HM-3301), Nafas,
IQAir, AQICN, Airly — published as-supplied. Verify the coefficients against the EPA source before publishing
anything derived from them; the function carries a note saying so.

## 6. Siting (from BAD's install guide, which is right)

Three to six metres above ground. Away from a kitchen exhaust, a chimney, a busy parking spot. Direct exposure to
outdoor air but sheltered from horizontal rain — a balcony rail or a north-facing eave, not the inside of a kitchen
window. 5 V USB power, cable through a wall pass-through sealed with silicone. 2.4 GHz WiFi only; disable 5 GHz on
mesh routers during pairing. Name it after the place, not the default hex string. Mark it public.

For our own enclosures: the outdoor-sensor-enclosure work (radiation shield, breathe-but-stay-dry, tropical
monsoon) is the printable answer. Fab Lab Bali prints it.

## 7. Thresholds used in `config/rules.yml`

| PM2.5 µg/m³ | scale | what we do |
|---|---|---|
| 5 | WHO 2021 annual | context only |
| 15 | WHO 2021 24-hour | `inside_worse_ventilate` floor |
| 35.5 | US EPA Unhealthy for Sensitive Groups | `indoor_pm25_high`, `outside_worse_keep_shut` |
| 55.5 | US EPA Unhealthy | (reserved: "everyone indoors") |

Same scale BAD publishes, so a node's message and the public map never disagree about what "bad" means.
