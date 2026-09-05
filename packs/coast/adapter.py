"""Open-Meteo Marine at the node's coordinates. The API snaps to the nearest ocean grid cell (~5 km), so an inland
node gets the closest coast; a node 200 km from the sea gets a number about somewhere it has never been. The pack
therefore refuses to run if the returned cell is more than COAST_MAX_KM (default 30) from the node.

kind='model', scale='bioregion': this is a regional boundary condition, never a local measurement, never a `live` cell.
Contract: fetch(hc) -> (sensors, readings), like everything in app/sources.py.
"""
import os
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt

URL = "https://marine-api.open-meteo.com/v1/marine"
CURRENT = "wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_period,sea_surface_temperature"
MAP = {"wave_height": "wave_height_m", "wave_direction": "wave_direction", "wave_period": "wave_period_s",
       "swell_wave_height": "swell_height_m", "swell_wave_period": "swell_period_s", "sea_surface_temperature": "sea_surface_temp"}


def _km(lat1, lon1, lat2, lon2):
    p1, p2, dl = radians(lat1), radians(lat2), radians(lon2 - lon1)
    return 6371 * 2 * asin(sqrt(sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2))


def fetch(hc):
    lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
    r = hc.get(URL, params={"latitude": lat, "longitude": lon, "current": CURRENT, "timezone": "UTC"})
    r.raise_for_status()
    d = r.json()
    cell_lat, cell_lon = float(d["latitude"]), float(d["longitude"])
    dist = _km(lat, lon, cell_lat, cell_lon)
    if dist > float(os.getenv("COAST_MAX_KM", "30")):
        raise RuntimeError(f"nearest ocean cell is {dist:.0f} km away; this node is not coastal (COAST_MAX_KM)")
    cur = d.get("current") or {}
    t = cur.get("time")
    ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc) if t else datetime.now(timezone.utc)
    sensor = {"sensor_id": "marine-point", "source": "open-meteo-marine", "name": f"Sea, {dist:.0f} km off ({cell_lat:.2f}, {cell_lon:.2f})",
              "lat": cell_lat, "lon": cell_lon, "indoor": False, "local": False, "kind": "model", "scale": "bioregion",
              "cadence": "PT1H", "meta": {"attribution": "Open-Meteo Marine (CC BY 4.0); Copernicus Marine / MFWAM",
                                          "distance_km": round(dist, 1), "units": d.get("current_units")}}
    readings = [(ts, "marine-point", m, float(cur[k])) for k, m in MAP.items() if cur.get(k) is not None]
    return [sensor], readings
