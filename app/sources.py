"""Sources. Each adapter is a function that returns (sensors, readings).

    sensors : list of dicts  {sensor_id, source, name, lat, lon, indoor, local, meta,
                              kind:  sensor | portal | model | survey   (how the number was produced)
                              scale: community | city | region | bioregion | planet (what it describes)
                              cadence: ISO-8601 duration, optional}
              kind and scale default to sensor/community — set them on anything that isn't a device at the address.
    readings: list of tuples (ts: datetime UTC, sensor_id, metric, value)

That's the whole contract. Add a source = add a function here + register it in SOURCES.
Four ship: smartcitizen (cloud API), airgradient (LAN), purpleair (LAN), baliairdispatch (peer observatory, reference).
See docs/sensors.md to add another.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone

import httpx

# ---------------------------------------------------------------- helpers

def _km(lat1, lon1, lat2, lon2) -> float:
    from math import asin, cos, radians, sin, sqrt
    p1, p2, dl = radians(lat1), radians(lat2), radians(lon2 - lon1)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def epa_2021_correct(pm_raw: float, rh: float) -> float:
    """US EPA 2021 humidity correction for Plantower-based sensors (PurpleAir, AirGradient, DIY PMS5003).
    Barkjohn et al. 2021, extended 2022. Same formula Bali Air Dispatch applies before publishing those networks.
    Do NOT apply to Smart Citizen (Seeed HM-3301) or Nafas/IQAir/AQICN, which are published as-supplied.
    Verify coefficients against https://www.epa.gov before relying on this for anything published."""
    x, h = pm_raw, rh
    if x <= 30:
        return 0.524 * x - 0.0862 * h + 5.75
    if x <= 50:
        w = x / 20 - 1.5
        return (0.786 * w + 0.524 * (1 - w)) * x - 0.0862 * h + 5.75
    if x <= 210:
        return 0.786 * x - 0.0862 * h + 5.75
    if x <= 260:
        w = x / 50 - 4.2
        return (0.69 * w + 0.786 * (1 - w)) * x - 0.0862 * h * (1 - w) + 2.966 * w + 5.75 * (1 - w) + 8.84e-4 * x * x * w
    return 2.966 + 0.69 * x + 8.84e-4 * x * x


# ---------------------------------------------------------------- Smart Citizen
# Map on measurement *name*, not sensor id — ids change between kit generations (2.1 vs 2.3), names don't.
SC_METRICS = {
    "PM2.5": "pm25", "PM10": "pm10", "PM1": "pm1",
    "Air Temperature": "temp", "Relative Humidity": "humidity", "Barometric Pressure": "pressure",
    "AQI": "aqi", "Gas Resistance": "gas_resistance", "Noise Level": "noise", "Light": "light",
    "eCO2": "eco2", "TVOC": "tvoc",
}


def smartcitizen_account(hc: httpx.Client, user: str, max_age_days: int = 3) -> list[int]:
    """The kits in a Smart Citizen account that have published recently. The account listing carries no location,
    so whether a kit is local is decided in smartcitizen() from the device record it fetches anyway.
    Plain usernames work (`tomasdiez`); a numeric user id also works."""
    r = hc.get(f"https://api.smartcitizen.me/v0/users/{user}")
    r.raise_for_status()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return [int(d["id"]) for d in r.json().get("devices") or []
            if d.get("state") == "has_published" and (_iso(d.get("last_reading_at")) or cutoff) > cutoff]


def smartcitizen(hc: httpx.Client, device_ids: list[int], explicit_local: set[int] | None = None,
                 node: tuple[float, float] | None = None, local_km: float = 0.5):
    """explicit_local: ids from SC_DEVICES, always local. Others (from account discovery) are local only if the
    device's own coordinates fall within local_km of the node; an outdoor kit a kilometre away is a reference."""
    sensors, readings = [], []
    for did in device_ids:
        r = hc.get(f"https://api.smartcitizen.me/v0/devices/{did}")
        r.raise_for_status()
        d = r.json()
        data = d.get("data") or {}
        loc = d.get("location") or data.get("location") or {}
        ts = _iso(data.get("recorded_at") or d.get("last_reading_at"))
        sid = f"sc-{did}"
        sensors.append({
            "sensor_id": sid, "source": "smartcitizen", "name": d.get("name") or sid,
            "lat": loc.get("latitude"), "lon": loc.get("longitude"),
            "indoor": (loc.get("exposure") == "indoor"),
            # explicit_local=None means every id was named by hand, so all are yours. With discovery, only the
            # named ones and the ones within local_km of the node are local; the rest are references you own.
            "local": (explicit_local is None or did in explicit_local) or bool(
                node and loc.get("latitude") is not None and _km(node[0], node[1], loc["latitude"], loc["longitude"]) <= local_km),
            "meta": {"hardware": (d.get("hardware") or {}).get("name"), "state": d.get("state"),
                     "url": f"https://smartcitizen.me/kits/{did}"},
        })
        if ts is None:
            continue
        for s in data.get("sensors") or []:
            m = s.get("measurement") or {}
            metric = SC_METRICS.get(m.get("name") if isinstance(m, dict) else m)
            if metric and s.get("value") is not None:
                readings.append((ts, sid, metric, float(s["value"])))
    return sensors, readings


# ---------------------------------------------------------------- Bali Air Dispatch (ambient reference)
# Public, key-free, edge-cached 5–60 min. Aggregates 8 networks. We take /latest, drop stale rows, keep stations
# within BAD_RADIUS_KM, and store pm25 (as published) + pm25_raw when present so the correction stays auditable.
# Attribution required: "Bali Air Dispatch, baliairdispatch.com" + the row's source network. See docs/sensors.md.
BAD_LATEST = "https://baliairdispatch.com/api/v1/latest"


def baliairdispatch(hc: httpx.Client, node_lat: float, node_lon: float, radius_km: float,
                    skip_station_ids: set[str] | None = None):
    """skip_station_ids: BAD station ids this node already reads directly (e.g. `sc-19236` for a Smart Citizen kit
    it polls itself). Without this the same physical kit lands twice — once as sc-19236, once as bad-sc-19236 —
    and is counted twice in the ambient average, with BAD's metadata (which disagreed with Smart Citizen's own
    indoor/outdoor flag on two kits) winning half the time."""
    sensors, readings = [], []
    r = hc.get(BAD_LATEST)
    r.raise_for_status()
    for row in r.json().get("readings", []):
        if row.get("stale") or row.get("latitude") is None or row.get("longitude") is None:
            continue
        if skip_station_ids and str(row.get("station_id")) in skip_station_ids:
            continue
        if km(node_lat, node_lon, row["latitude"], row["longitude"]) > radius_km:
            continue
        ts = _iso(row.get("observed_at"))
        if ts is None:
            continue
        sid = f"bad-{row['station_id']}"
        sensors.append({
            "sensor_id": sid, "source": "baliairdispatch", "name": f"{row.get('name')} ({row.get('source')})",
            "lat": row["latitude"], "lon": row["longitude"],
            "indoor": bool(row.get("suspected_indoor")), "local": False,
            "meta": {"network": row.get("source"), "corrected": row.get("pm25_corrected"),
                     "attribution": "Bali Air Dispatch, baliairdispatch.com"},
        })
        for k, metric in (("pm25", "pm25"), ("pm25_raw", "pm25_raw"), ("pm10", "pm10"), ("pm1", "pm1"),
                          ("temperature", "temp"), ("humidity", "humidity"), ("aqi", "aqi")):
            if row.get(k) is not None:
                readings.append((ts, sid, metric, float(row[k])))
    return sensors, readings



# ---------------------------------------------------------------- AirGradient (LAN, no cloud)
# Every AirGradient ONE / Open Air exposes http://airgradient_<serial>.local/measures/current on your WiFi.
# Fields (firmware 3.x): pm01 pm02 pm10 pm003Count rco2 atmp rhum tvocIndex noxIndex serialno model firmware.
# Newer firmware adds *Compensated fields; we take the raw pm02 and apply EPA 2021 ourselves so the audit trail is ours.
# Set AIRGRADIENT_HOSTS=airgradient_84fce6.local,192.168.1.52   (hostname or IP, comma-separated)
AG_METRICS = {"pm01": "pm1", "pm10": "pm10", "rco2": "co2", "atmp": "temp", "rhum": "humidity",
              "tvocIndex": "tvoc_index", "noxIndex": "nox_index"}


def airgradient(hc: httpx.Client, hosts: list[str], lat: float | None, lon: float | None, indoor: bool):
    sensors, readings = [], []
    ts = datetime.now(timezone.utc)
    for host in hosts:
        d = hc.get(f"http://{host}/measures/current", timeout=10).json()
        serial = str(d.get("serialno") or host.replace(".local", "")).lower()
        sid = f"ag-{serial}"
        sensors.append({"sensor_id": sid, "source": "airgradient", "name": f"AirGradient {d.get('model', '')} {serial}".strip(),
                        "lat": lat, "lon": lon, "indoor": indoor, "local": True,
                        "meta": {"host": host, "firmware": d.get("firmware"), "model": d.get("model"),
                                 "correction": "EPA 2021 applied to pm02 (Plantower)"}})
        for k, metric in AG_METRICS.items():
            if d.get(k) is not None:
                readings.append((ts, sid, metric, float(d[k])))
        if d.get("pm02") is not None:
            raw = float(d["pm02"])
            readings.append((ts, sid, "pm25_raw", raw))
            rh = float(d["rhum"]) if d.get("rhum") is not None else 50.0
            readings.append((ts, sid, "pm25", max(0.0, epa_2021_correct(raw, rh))))
    return sensors, readings


# ---------------------------------------------------------------- PurpleAir (LAN, no cloud)
# Every PurpleAir sensor serves http://<ip>/json?live=true on its WiFi. Fields: pm2_5_cf_1, pm2_5_cf_1_b (two laser
# channels), pm2_5_atm, pm10_0_cf_1, current_humidity, current_temp_f, pressure, SensorId, lat, lon, Geo.
# EPA 2021 is defined on the A/B average of cf_1 — we do exactly that. Temp is °F and reads high; we convert, not correct.
# Set PURPLEAIR_HOSTS=192.168.1.60   (IP; the .local name is unreliable on PurpleAir)
def purpleair(hc: httpx.Client, hosts: list[str], lat: float | None, lon: float | None, indoor: bool):
    sensors, readings = [], []
    ts = datetime.now(timezone.utc)
    for host in hosts:
        d = hc.get(f"http://{host}/json?live=true", timeout=10).json()
        sid = f"pa-{str(d.get('SensorId') or host).replace(':', '').lower()}"
        sensors.append({"sensor_id": sid, "source": "purpleair", "name": f"PurpleAir {d.get('Geo') or sid}",
                        "lat": d.get("lat") or lat, "lon": d.get("lon") or lon, "indoor": indoor, "local": True,
                        "meta": {"host": host, "hardware": d.get("hardwarediscovered"), "correction": "EPA 2021 on mean(cf_1 A,B)"}})
        chans = [float(d[k]) for k in ("pm2_5_cf_1", "pm2_5_cf_1_b") if d.get(k) is not None]
        if chans:
            raw = sum(chans) / len(chans)
            rh = float(d.get("current_humidity", 50.0))
            readings.append((ts, sid, "pm25_raw", raw))
            readings.append((ts, sid, "pm25", max(0.0, epa_2021_correct(raw, rh))))
            if len(chans) == 2 and abs(chans[0] - chans[1]) > max(5.0, 0.7 * raw):
                readings.append((ts, sid, "channel_disagreement", abs(chans[0] - chans[1])))   # a laser is failing; rule on this later
        if d.get("pm10_0_cf_1") is not None:
            readings.append((ts, sid, "pm10", float(d["pm10_0_cf_1"])))
        if d.get("current_humidity") is not None:
            readings.append((ts, sid, "humidity", float(d["current_humidity"])))
        if d.get("current_temp_f") is not None:
            readings.append((ts, sid, "temp", (float(d["current_temp_f"]) - 32) * 5 / 9))
        if d.get("pressure") is not None:
            readings.append((ts, sid, "pressure", float(d["pressure"]) / 10))   # hPa → kPa
    return sensors, readings


# ---------------------------------------------------------------- registry
def enabled(hc: httpx.Client):
    """Yield (name, fetch) for every configured source. Failures are per-source, never fatal.
    Core adapters first, then any from community packs (docs/PACKS.md)."""
    out = []
    explicit = {int(x) for x in os.getenv("SC_DEVICES", "").replace(" ", "").split(",") if x}
    ids = set(explicit)
    node = (float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])) if os.getenv("NODE_LAT") else None
    if os.getenv("SC_USER", "").strip():
        try:
            ids |= set(smartcitizen_account(hc, os.environ["SC_USER"].strip()))
        except Exception as e:  # noqa: BLE001
            import logging; logging.getLogger("planetai").warning("smartcitizen account discovery failed: %s", e)
    ids = sorted(ids)
    local_km = float(os.getenv("SC_LOCAL_KM", "0.5"))
    if ids:
        out.append(("smartcitizen", lambda: smartcitizen(hc, ids, explicit, node, local_km)))
    lat = float(os.environ["NODE_LAT"]) if os.getenv("NODE_LAT") else None
    lon = float(os.environ["NODE_LON"]) if os.getenv("NODE_LON") else None
    indoor = os.getenv("SENSOR_INDOOR", "0") == "1"
    ag = [h for h in os.getenv("AIRGRADIENT_HOSTS", "").replace(" ", "").split(",") if h]
    if ag:
        out.append(("airgradient", lambda: airgradient(hc, ag, lat, lon, indoor)))
    pa = [h for h in os.getenv("PURPLEAIR_HOSTS", "").replace(" ", "").split(",") if h]
    if pa:
        out.append(("purpleair", lambda: purpleair(hc, pa, lat, lon, indoor)))
    if os.getenv("BAD_ENABLED", "0") == "1":
        # BAD republishes Smart Citizen kits as station id `sc-<kit>`; skip the ones this node reads directly
        skip = {f"sc-{i}" for i in ids}
        out.append(("baliairdispatch", lambda: baliairdispatch(hc, lat, lon, float(os.getenv("BAD_RADIUS_KM", "15")), skip)))
    if os.getenv("OPENMETEO_ENABLED", "1") == "1" and os.getenv("NODE_LAT"):
        _lat, _lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
        out.append(("open-meteo", lambda: openmeteo(hc, _lat, _lon)))
        out.append(("open-meteo-cams", lambda: openmeteo_air(hc, _lat, _lon)))
    portals = dict(p.split("=", 1) for p in os.getenv("CKAN_PORTALS", "").split(",") if "=" in p)
    if portals:
        out.append(("ckan", lambda: ckan(hc, portals, os.getenv("CKAN_SCALE", "city"))))
    try:
        import packs
        out += packs.adapters(hc)
    except Exception as e:  # noqa: BLE001  — a broken pack must never stop the core sources
        import logging; logging.getLogger("planetai").warning("packs: %s", e)
    return out


# ---------------------------------------------------------------- Open-Meteo (planet/bioregion context, anywhere)
# Free, key-free, global. A point sample of a global model — boundary conditions, not a measurement of your place.
# Per ARCHITECTURE §2, bioregion and planet publish context *downward*; they are never rolled up into an index cell.
# Set OPENMETEO_ENABLED=1. Works at any coordinates on earth, which is the point: this is the one adapter that
# needs nothing local at all, so a node in a city with no sensors still has something true to say.
OM_CURRENT = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,surface_pressure"
OM_MAP = {"temperature_2m": "temp_model", "relative_humidity_2m": "humidity_model", "precipitation": "precipitation",
          "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_direction", "surface_pressure": "pressure_model"}


def openmeteo(hc: httpx.Client, lat: float, lon: float):
    r = hc.get("https://api.open-meteo.com/v1/forecast",
               params={"latitude": lat, "longitude": lon, "current": OM_CURRENT, "timezone": "UTC"})
    r.raise_for_status()
    d = r.json()
    cur = d.get("current") or {}
    ts = _iso(cur.get("time") + "Z" if cur.get("time") and not str(cur.get("time")).endswith("Z") else cur.get("time")) or datetime.now(timezone.utc)
    sid = "om-point"
    sensors = [{"sensor_id": sid, "source": "open-meteo", "name": "Open-Meteo (model point sample)",
                "lat": lat, "lon": lon, "indoor": False, "local": False, "kind": "model", "scale": "planet",
                "cadence": "PT1H", "meta": {"model": "ECMWF/GFS blend via open-meteo.com", "licence": "CC-BY 4.0",
                                            "note": "boundary condition; never aggregated upward into a cell"}}]
    readings = [(ts, sid, m, float(cur[k])) for k, m in OM_MAP.items() if cur.get(k) is not None]
    return sensors, readings


# ---------------------------------------------------------------- CKAN open-data portal (city/region governance)
# Four of the Index's governance|city sources are CKAN: Open Data BCN, Analyze Boston, datos.gob.cl, Bali Satu Data.
# One adapter reads all of them, and asks the question the Index actually needs answered about a portal:
# is it alive? Datasets published, and how many were updated in the last 90 days. That is a DIDO signal —
# a portal nobody maintains is not open data, it is an archive.
# Set CKAN_PORTALS=open-data-bcn=https://opendata-ajuntament.barcelona.cat/data,analyze-boston=https://data.boston.gov
def ckan(hc: httpx.Client, portals: dict[str, str], scale: str = "city"):
    from datetime import timedelta
    sensors, readings = [], []
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S")
    for slug, base in portals.items():
        base = base.rstrip("/")
        total = hc.get(f"{base}/api/3/action/package_search", params={"rows": 0}).json()["result"]["count"]
        fresh = hc.get(f"{base}/api/3/action/package_search",
                       params={"fq": f"metadata_modified:[{cutoff}Z TO NOW]", "rows": 0}).json()["result"]["count"]
        sid = f"ckan-{slug}"
        sensors.append({"sensor_id": sid, "source": "ckan", "name": f"{slug} (CKAN portal)", "lat": None, "lon": None,
                        "indoor": False, "local": False, "kind": "portal", "scale": scale, "cadence": "P1D",
                        "meta": {"portal": base, "registry_slug": f"governance/{scale}/{slug}"}})
        readings += [(now, sid, "datasets_total", float(total)),
                     (now, sid, "datasets_fresh_90d", float(fresh)),
                     (now, sid, "datasets_fresh_pct", 100.0 * fresh / total if total else 0.0)]
    return sensors, readings


# ---------------------------------------------------------------- Open-Meteo Air Quality (CAMS) — zero-config
# Free, key-free, global. Copernicus Atmosphere Monitoring Service: satellite + model reanalysis, ~11 km grid.
# This is the adapter that makes a node useful before any hardware exists: modelled PM2.5 at your coordinates,
# anywhere on earth, from the first minute. It is a MODEL, not a measurement — kind='model', never 'live' in a cell,
# and it is the thing your sensor gets compared against, not the thing that replaces it.
# Attribution required: CAMS ENSEMBLE data provider and Open-Meteo. Carried in sensors.meta.
OM_AIR = "pm2_5,pm10,dust,aerosol_optical_depth,carbon_monoxide,nitrogen_dioxide,ozone,uv_index"
OM_AIR_MAP = {"pm2_5": "pm25_model", "pm10": "pm10_model", "dust": "dust", "aerosol_optical_depth": "aod",
              "carbon_monoxide": "co", "nitrogen_dioxide": "no2", "ozone": "o3", "uv_index": "uv_index"}
OM_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _om_air_sensor(lat, lon):
    return {"sensor_id": "cams-point", "source": "open-meteo-cams", "name": "CAMS air quality (model point sample)",
            "lat": lat, "lon": lon, "indoor": False, "local": False, "kind": "model", "scale": "planet",
            "cadence": "PT1H",
            "meta": {"model": "Copernicus CAMS global/European ensemble via open-meteo.com",
                     "attribution": "CAMS ENSEMBLE data provider and Open-Meteo",
                     "note": "modelled, not measured — the baseline a local sensor is compared against"}}


def openmeteo_air(hc: httpx.Client, lat: float, lon: float):
    r = hc.get(OM_AIR_URL, params={"latitude": lat, "longitude": lon, "current": OM_AIR, "timezone": "UTC"})
    r.raise_for_status()
    cur = (r.json().get("current") or {})
    t = cur.get("time")
    ts = _iso(t if not t or str(t).endswith("Z") else f"{t}Z") or datetime.now(timezone.utc)
    readings = [(ts, "cams-point", m, float(cur[k])) for k, m in OM_AIR_MAP.items() if cur.get(k) is not None]
    return [_om_air_sensor(lat, lon)], readings


# ---------------------------------------------------------------- Meshtastic (LoRa mesh, via the gateway's MQTT uplink)
# The gateway radio (an ESP32 with WiFi) uplinks the mesh to the node's Mosquitto. With "JSON output" enabled on the
# gateway, each packet arrives on   msh/<REGION>/2/json/<channel>/!<gateway>   as a JSON object with "type" and
# "payload". This is a pure function: one MQTT message in, sensors and readings out, so it is tested offline.
#   telemetry  -> readings (environment_metrics / air_quality_metrics / power fields flattened into payload)
#   position   -> the sensor's lat/lon (Tracker L1 boards carry GPS)
#   nodeinfo   -> the sensor's name
# Metric names follow the rest of the node; field names follow Meshtastic firmware 2.x. If a future firmware renames
# them the adapter logs the unknown keys once rather than silently dropping them.
MESH_METRICS = {
    # environment_metrics
    "temperature": "temp", "relative_humidity": "humidity", "barometric_pressure": "pressure_hpa",
    "gas_resistance": "gas_resistance", "iaq": "iaq", "lux": "light", "uv_lux": "uv_lux",
    "wind_speed": "wind_speed", "wind_direction": "wind_direction", "rainfall_1h": "rainfall_1h",
    "soil_moisture": "soil_moisture", "soil_temperature": "soil_temp",
    # air_quality_metrics (Plantower / SEN5x / HM3301 family)
    "pm10_standard": "pm1", "pm25_standard": "pm25", "pm100_standard": "pm10",
    "pm10_environmental": "pm1_env", "pm25_environmental": "pm25_env", "pm100_environmental": "pm10_env",
    "co2": "co2", "voc_idx": "tvoc_index", "nox_idx": "nox_index",
    # device health, useful for the dead-sensor rule and for battery planning
    "battery_level": "battery_pct", "voltage": "battery_v", "air_util_tx": "lora_util_pct", "channel_utilization": "lora_channel_pct",
}
_MESH_UNKNOWN: set = set()


def meshtastic_message(topic: str, payload: bytes, indoor_ids: set | None = None):
    """Parse one uplinked packet. Returns (sensors, readings, info) where info carries what the node needs to reply:
    the root topic and the gateway id, so alerts can go back down the same channel."""
    import json as _json
    import logging as _logging
    log = _logging.getLogger("planetai.meshtastic")
    parts = topic.split("/")
    if "json" not in parts:
        return [], [], {}            # protobuf topics: the gateway has JSON output off. planetai meshtastic says how to turn it on.
    j = parts.index("json")
    # msh/<REGION>/2/json/<channel>/!<gateway> : the "2" is the protocol version, not part of the root topic
    root = "/".join(parts[:j - 1]) if j >= 1 and parts[j - 1] == "2" else "/".join(parts[:j])
    channel, gateway = (parts[j + 1] if len(parts) > j + 1 else ""), (parts[j + 2] if len(parts) > j + 2 else "")
    try:
        m = _json.loads(payload)
    except Exception:  # noqa: BLE001
        return [], [], {}
    kind, p = m.get("type"), m.get("payload") or {}
    node = m.get("sender") or (f"!{m['from']:08x}" if isinstance(m.get("from"), int) else None)
    if not node:
        return [], [], {}
    sid = f"msh-{node.lstrip('!')}"
    ts = datetime.fromtimestamp(m["timestamp"], tz=timezone.utc) if isinstance(m.get("timestamp"), (int, float)) and m["timestamp"] > 1_600_000_000 else datetime.now(timezone.utc)
    indoor = bool(indoor_ids and (node in indoor_ids or sid in indoor_ids))
    sensor = {"sensor_id": sid, "source": "meshtastic", "name": None, "lat": None, "lon": None, "indoor": indoor, "local": True,
              "kind": "sensor", "scale": "community", "cadence": "PT15M",
              "meta": {"mesh_node": node, "gateway": gateway, "channel": channel, "root_topic": root}}
    readings = []
    if kind == "telemetry" and isinstance(p, dict):
        for k, v in p.items():
            if not isinstance(v, (int, float)):
                continue
            metric = MESH_METRICS.get(k)
            if metric:
                if metric == "pressure_hpa":
                    readings.append((ts, sid, "pressure", float(v) / 10.0))   # hPa -> kPa, same unit as the rest of the node
                else:
                    readings.append((ts, sid, metric, float(v)))
            elif k not in _MESH_UNKNOWN:
                _MESH_UNKNOWN.add(k); log.info("meshtastic: unknown telemetry field %r (value %r) — add it to MESH_METRICS if it matters", k, v)
    elif kind == "position" and isinstance(p, dict):
        lat = p.get("latitude_i"); lon = p.get("longitude_i")
        if isinstance(lat, int) and isinstance(lon, int) and lat and lon:
            sensor["lat"], sensor["lon"] = lat / 1e7, lon / 1e7
        if p.get("altitude") is not None:
            readings.append((ts, sid, "altitude_m", float(p["altitude"])))
    elif kind == "nodeinfo" and isinstance(p, dict):
        sensor["name"] = p.get("longname") or p.get("shortname")
        sensor["meta"]["hardware"] = p.get("hardware")
    elif kind == "text":
        sensor["meta"]["last_text"] = str(p.get("text", ""))[:200] if isinstance(p, dict) else str(p)[:200]
    else:
        return [], [], {"root_topic": root, "gateway": gateway}
    # a sensor row is only worth writing if it carries something new (name, position) or has readings
    if not readings and sensor["name"] is None and sensor["lat"] is None and kind != "text":
        return [], [], {"root_topic": root, "gateway": gateway}
    if sensor["name"] is None:
        sensor["name"] = f"mesh {node}"
    return [sensor], readings, {"root_topic": root, "gateway": gateway, "channel": channel, "kind": kind, "node": node}


def meshtastic_downlink(root_topic: str, gateway_node_num: int, text: str, channel: int = 0) -> tuple[str, bytes]:
    """The (topic, payload) to publish so the gateway transmits `text` on the mesh. Requires JSON output and
    downlink enabled on the gateway's channel. LoRa frames are small: ~200 bytes of text is the practical ceiling."""
    import json as _json
    text = text if len(text.encode()) <= 200 else text.encode()[:197].decode("utf-8", "ignore") + "..."
    return f"{root_topic}/2/json/mqtt/", _json.dumps({"from": gateway_node_num, "type": "sendtext", "payload": text, "channel": channel}).encode()
