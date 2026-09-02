"""Sources. Each adapter is a function that returns (sensors, readings).

    sensors : list of dicts  {sensor_id, source, name, lat, lon, indoor, local, meta}
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
    """Yield (name, sensors, readings) for every configured source. Failures are per-source, never fatal."""
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
    return out
