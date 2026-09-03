"""First-run bootstrap: give a node a filled database before it has a single sensor.

Runs once, on first start, if the readings table is empty. Everything here is free, key-free, global, and
needs nothing but the node's coordinates:

  · 92 days of hourly CAMS air quality      -> the node has three months of history in its first minute
  · NASA POWER climatology (1981-present)   -> 12 monthly normals for solar, temperature, rainfall
  · a place name from OpenStreetMap         -> so alerts say somewhere real, not a pair of decimals

Why bother: the worst moment in any sensing deployment is the first week, when there is nothing to look at and
nothing to compare against. A node that knows what normal looks like at its coordinates before the hardware
arrives is a node someone keeps.

None of this is a measurement. Everything lands with kind='model' and is never eligible for a `live` cell.
Failures are logged and skipped — a node with no internet on day one still runs on its own sensors.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

import sources

log = logging.getLogger("planetai.bootstrap")
POWER = "https://power.larc.nasa.gov/api/temporal/climatology/point"
POWER_PARAMS = "ALLSKY_SFC_SW_DWN,T2M,PRECTOTCORR,RH2M,WS10M"
POWER_MAP = {"ALLSKY_SFC_SW_DWN": "solar_irradiance_norm", "T2M": "temp_norm",
             "PRECTOTCORR": "precipitation_norm", "RH2M": "humidity_norm", "WS10M": "wind_speed_norm"}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def cams_history(hc: httpx.Client, lat: float, lon: float, days: int = 92):
    """Hourly CAMS PM2.5/PM10 for the past N days (92 is the API maximum). One call, ~2200 rows."""
    r = hc.get(sources.OM_AIR_URL, params={"latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10",
                                           "past_days": min(days, 92), "forecast_days": 0, "timezone": "UTC"})
    r.raise_for_status()
    h = r.json().get("hourly") or {}
    times = h.get("time") or []
    out = []
    for key, metric in (("pm2_5", "pm25_model"), ("pm10", "pm10_model")):
        for t, v in zip(times, h.get(key) or []):
            if v is None:
                continue
            ts = sources._iso(t if str(t).endswith("Z") else f"{t}Z")
            if ts:
                out.append((ts, "cams-point", metric, float(v)))
    return [sources._om_air_sensor(lat, lon)], out


def power_climatology(hc: httpx.Client, lat: float, lon: float):
    """NASA POWER long-term monthly means, satellite-derived, 1981-present, 0.5 degree grid. No key.
    Stored at the 15th of each month of the current year so they plot as a seasonal curve."""
    r = hc.get(POWER, params={"parameters": POWER_PARAMS, "community": "RE",
                              "latitude": lat, "longitude": lon, "format": "JSON"})
    r.raise_for_status()
    params = ((r.json().get("properties") or {}).get("parameter") or {})
    year = datetime.now(timezone.utc).year
    sensors = [{"sensor_id": "power-point", "source": "nasa-power", "name": "NASA POWER climatology (satellite)",
                "lat": lat, "lon": lon, "indoor": False, "local": False, "kind": "model", "scale": "planet",
                "cadence": "P1Y",
                "meta": {"dataset": "NASA POWER, CERES/MERRA-2 derived, 1981-present, 0.5 deg",
                         "attribution": "NASA Langley Research Center POWER Project",
                         "note": "long-term monthly normals — what a normal year looks like here"}}]
    readings = []
    for key, metric in POWER_MAP.items():
        vals = params.get(key) or {}
        for i, m in enumerate(MONTHS, start=1):
            v = vals.get(m)
            if v is None or float(v) <= -900:      # POWER's fill value
                continue
            readings.append((datetime(year, i, 15, tzinfo=timezone.utc), "power-point", metric, float(v)))
    return sensors, readings


def place_name(hc: httpx.Client, lat: float, lon: float) -> str | None:
    """One reverse geocode so messages say a place, not coordinates. OpenStreetMap Nominatim: free, no key,
    but its usage policy is one request per second and a real User-Agent — hence once, at install, never in a loop."""
    try:
        r = hc.get("https://nominatim.openstreetmap.org/reverse",
                   params={"lat": lat, "lon": lon, "format": "json", "zoom": 12},
                   headers={"User-Agent": f"planetai-node/{os.getenv('NODE_VERSION', '0.3')} (+https://planetai.fab.city)"})
        r.raise_for_status()
        a = r.json().get("address") or {}
        parts = [a.get(k) for k in ("suburb", "village", "town", "city_district", "city", "county", "state", "country")]
        return ", ".join([p for p in parts if p][:3]) or None
    except Exception as e:  # noqa: BLE001
        log.debug("reverse geocode skipped: %s", e)
        return None


def run(con, hc: httpx.Client, lat: float, lon: float) -> dict:
    """Called once when the readings table is empty. Returns a summary for the log and /health."""
    from psycopg.types.json import Jsonb
    done = {}
    for name, fn in (("cams_history", lambda: cams_history(hc, lat, lon)),
                     ("power_climatology", lambda: power_climatology(hc, lat, lon))):
        try:
            sensors, readings = fn()
        except Exception as e:  # noqa: BLE001
            log.warning("bootstrap %s skipped: %s", name, e)
            done[name] = 0
            continue
        with con.cursor() as cur:
            for s in sensors:
                cur.execute("""INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind, scale, cadence, meta)
                               VALUES (%(sensor_id)s,%(source)s,%(name)s,%(lat)s,%(lon)s,%(indoor)s,%(local)s,%(kind)s,%(scale)s,%(cadence)s,%(meta)s)
                               ON CONFLICT (sensor_id) DO NOTHING""", {**s, "meta": Jsonb(s.get("meta") or {})})
            cur.executemany("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", readings)
        done[name] = len(readings)
        log.info("bootstrap %s: %d readings", name, len(readings))
    place = place_name(hc, lat, lon)
    if place:
        done["place"] = place
        log.info("bootstrap: this node is in %s", place)
    return done
