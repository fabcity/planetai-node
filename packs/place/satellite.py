"""Google Open Buildings, from Earth Engine, for the place pack.

Two datasets, both open (CC BY 4.0), both behind the Earth Engine credentials the earth-engine pack already uses:
  V3 polygons   GOOGLE/Research/open-buildings/v3/polygons        footprints detected from imagery, with a confidence
  Temporal v1   GOOGLE/Research/open-buildings-temporal/v1        yearly presence, count and height, 2016-2023, 4 m

Footprints go into PostGIS beside the OpenStreetMap ones, so the node can say how many buildings the satellite sees
and how many the map has. The yearly series becomes readings dated 1 July of each year: the place's growth, in numbers.
"""
from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime, timezone

log = logging.getLogger("planetai.place.satellite")

V3 = "GOOGLE/Research/open-buildings/v3/polygons"
TEMPORAL = "GOOGLE/Research/open-buildings-temporal/v1"

DDL = """
CREATE TABLE IF NOT EXISTS place_buildings_sat (
  id BIGSERIAL PRIMARY KEY, source TEXT NOT NULL, confidence REAL, area_m2 REAL,
  geom geometry(Polygon, 4326) NOT NULL, fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS place_buildings_sat_geom ON place_buildings_sat USING GIST (geom);
"""


def init_ee():
    import ee
    key = os.getenv("EE_KEY_FILE")
    if not (key and os.path.exists(key)):
        raise RuntimeError("EE_KEY_FILE must point at a readable service-account key (config/ee-key.json); the earth-engine pack's README explains")
    kj = json.load(open(key))
    proj = os.getenv("EE_PROJECT") or ""
    if not proj or proj.isdigit():
        proj = kj.get("project_id") or proj
    sa = os.getenv("EE_SERVICE_ACCOUNT") or kj.get("client_email")
    ee.Initialize(ee.ServiceAccountCredentials(sa, key), project=proj)
    return ee


def _quadrants(ee, lat, lon, radius_m):
    """getInfo() on a FeatureCollection is capped near 5,000 features; a dense kilometre has more. Fetch by quadrant."""
    dlat = radius_m / 111_320
    dlon = radius_m / (111_320 * math.cos(math.radians(lat)))
    circle = ee.Geometry.Point([lon, lat]).buffer(radius_m)
    quads = []
    for (y0, y1) in ((lat - dlat, lat), (lat, lat + dlat)):
        for (x0, x1) in ((lon - dlon, lon), (lon, lon + dlon)):
            quads.append(ee.Geometry.Rectangle([x0, y0, x1, y1]).intersection(circle, 1))
    return circle, quads


def footprints(ee, con, lat, lon, radius_m, min_confidence=0.65):
    """Open Buildings V3 footprints within the radius → place_buildings_sat. Returns (count, mean_confidence)."""
    circle, quads = _quadrants(ee, lat, lon, radius_m)
    fc = ee.FeatureCollection(V3).filterBounds(circle).filter(ee.Filter.gte("confidence", min_confidence))
    rows = []
    for q in quads:
        feats = fc.filterBounds(q).map(lambda f: f.intersection(q, 1)).getInfo().get("features", [])
        for f in feats:
            g = f.get("geometry") or {}
            if g.get("type") == "Polygon":
                rows.append(("open_buildings_v3", float(f["properties"].get("confidence") or 0), float(f["properties"].get("area_in_meters") or 0), json.dumps(g)))
            elif g.get("type") == "MultiPolygon":
                for poly in g["coordinates"]:
                    rows.append(("open_buildings_v3", float(f["properties"].get("confidence") or 0), 0.0, json.dumps({"type": "Polygon", "coordinates": poly})))
    with con.cursor() as cur:
        cur.execute(DDL)
        cur.execute("DELETE FROM place_buildings_sat WHERE source='open_buildings_v3'")
        cur.executemany("INSERT INTO place_buildings_sat (source, confidence, area_m2, geom) VALUES (%s,%s,%s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326))", rows)
    con.commit()
    conf = sum(r[1] for r in rows) / len(rows) if rows else 0.0
    log.info("place: %d Open Buildings footprints within %d m (mean confidence %.2f)", len(rows), radius_m, conf)
    return len(rows), conf


def yearly(ee, lat, lon, radius_m):
    """Open Buildings Temporal: per year, the building count (sum of fractional counts) and the mean height where
    presence > 0.5, inside the radius. Returns [(year, count, height_m)]."""
    circle = ee.Geometry.Point([lon, lat]).buffer(radius_m)
    coll = ee.ImageCollection(TEMPORAL).filterBounds(circle)
    out = []
    epochs = coll.aggregate_array("inference_time_epoch_s").distinct().getInfo()
    for ep in sorted(epochs):
        img = coll.filter(ee.Filter.eq("inference_time_epoch_s", ep)).mosaic()
        count = img.select("building_fractional_count").reduceRegion(ee.Reducer.sum(), circle, 4, maxPixels=1e9).getInfo().get("building_fractional_count")
        h = img.select("building_height").updateMask(img.select("building_presence").gt(0.5)).reduceRegion(ee.Reducer.mean(), circle, 4, maxPixels=1e9).getInfo().get("building_height")
        year = datetime.fromtimestamp(int(ep), timezone.utc).year
        if count is not None:
            out.append((year, float(count), float(h) if h is not None else None))
    log.info("place: Open Buildings Temporal %s", [(y, round(c)) for y, c, _ in out])
    return out
