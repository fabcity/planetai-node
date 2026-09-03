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
from datetime import datetime, timezone

import httpx

# ---------------------------------------------------------------- helpers

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


def smartcitizen(hc: httpx.Client, device_ids: list[int]):
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
            "indoor": (loc.get("exposure") == "indoor"), "local": True,
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


def baliairdispatch(hc: httpx.Client, node_lat: float, node_lon: float, radius_km: float):
    sensors, readings = [], []
    r = hc.get(BAD_LATEST)
    r.raise_for_status()
    for row in r.json().get("readings", []):
        if row.get("stale") or row.get("latitude") is None or row.get("longitude") is None:
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
    ids = [int(x) for x in os.getenv("SC_DEVICES", "").replace(" ", "").split(",") if x]
    if ids:
        out.append(("smartcitizen", lambda: smartcitizen(hc, ids)))
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
        out.append(("baliairdispatch", lambda: baliairdispatch(hc, lat, lon, float(os.getenv("BAD_RADIUS_KM", "15")))))
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
