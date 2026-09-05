"""Google Earth Engine, sampled around the node once a day (results change once a year, so dedupe does the rest).

Everything is computed server-side in Earth Engine and only scalars come back: the mean over a 1 km buffer of
  · Dynamic World class fractions for the year (trees, built, crops, water)     GOOGLE/DYNAMICWORLD/V1
  · Sentinel-2 annual median NDVI                                               COPERNICUS/S2_SR_HARMONIZED
  · VIIRS monthly night-lights radiance, latest month                           NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG
  · AlphaEarth satellite-embedding change: 1 − cosine similarity between this   GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL
    year's and last year's 64-dim mean embedding — how much the land changed

kind='model', scale='bioregion'. Context published downward; never a `live` cell.

Auth is a service account, not a browser login, because a node has no browser:
  EE_PROJECT=my-gee-project  EE_SERVICE_ACCOUNT=planetai@my-gee-project.iam.gserviceaccount.com  EE_KEY_FILE=/app/config/ee-key.json
and mount the key file into the app container (config/ is already mounted read-only).

Dataset IDs are as published in the Earth Engine catalog at the time of writing. If Google renames one the fetch
logs which and skips it; the others still land. This pack has NOT been run against a live Earth Engine account yet:
its logic is unit-tested with a fake `ee`; the first real run should be watched in `planetai logs`.
"""
import logging
import os
import time
from datetime import datetime, timezone

log = logging.getLogger("planetai.pack.earth-engine")
_state = {"last": 0.0, "warned": False}
DW = "GOOGLE/DYNAMICWORLD/V1"
S2 = "COPERNICUS/S2_SR_HARMONIZED"
VIIRS = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG"
EMB = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
DW_CLASSES = {0: "water_frac", 1: "tree_frac", 4: "crop_frac", 6: "built_frac"}


def _init(ee):
    """The service-account key file names its own project and service account, so EE_PROJECT and EE_SERVICE_ACCOUNT
    are optional: the key is the source of truth. Setting EE_PROJECT to the service account's 21-digit unique id
    instead of the project id is an easy mistake and Earth Engine reports it as `project not found`."""
    key = os.getenv("EE_KEY_FILE")
    if not (key and os.path.exists(key)):
        raise RuntimeError("EE_KEY_FILE must point at a readable service-account key (config/ee-key.json)")
    import json
    kj = json.load(open(key))
    proj = os.getenv("EE_PROJECT") or ""
    if not proj or proj.isdigit():
        proj = kj.get("project_id") or proj
    sa = os.getenv("EE_SERVICE_ACCOUNT") or kj.get("client_email")
    if not (proj and sa):
        raise RuntimeError("the key file has no project_id/client_email; set EE_PROJECT and EE_SERVICE_ACCOUNT")
    ee.Initialize(ee.ServiceAccountCredentials(sa, key), project=proj)


def compute(ee, lat: float, lon: float, year: int, buffer_m: int = 1000) -> dict:
    """All the Earth Engine work. Returns {metric: value}. Separated so it can be tested with a fake ee."""
    pt = ee.Geometry.Point([lon, lat])
    aoi = pt.buffer(buffer_m)
    y0, y1 = f"{year}-01-01", f"{year}-12-31"
    out = {}

    # Dynamic World: modal class per pixel over the year, then class fractions in the buffer
    try:
        dw = ee.ImageCollection(DW).filterBounds(aoi).filterDate(y0, y1).select("label").mode()
        hist = dw.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=aoi, scale=10, maxPixels=1e8).get("label").getInfo() or {}
        total = sum(float(v) for v in hist.values()) or 1.0
        for cls, metric in DW_CLASSES.items():
            out[metric] = float(hist.get(str(cls), 0.0)) / total
    except Exception as e:  # noqa: BLE001
        log.warning("earth-engine: Dynamic World failed (%s)", type(e).__name__)

    # Sentinel-2 annual median NDVI, clouds masked with the scene classification band
    try:
        def ndvi(img):
            scl = img.select("SCL")
            clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
            return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(clear)
        s2 = ee.ImageCollection(S2).filterBounds(aoi).filterDate(y0, y1).map(ndvi).median()
        v = s2.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=10, maxPixels=1e8).get("ndvi").getInfo()
        if v is not None:
            out["ndvi_median"] = float(v)
    except Exception as e:  # noqa: BLE001
        log.warning("earth-engine: Sentinel-2 NDVI failed (%s)", type(e).__name__)

    # VIIRS night lights: latest monthly composite
    try:
        img = ee.ImageCollection(VIIRS).filterBounds(aoi).sort("system:time_start", False).first().select("avg_rad")
        v = img.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=500, maxPixels=1e8).get("avg_rad").getInfo()
        if v is not None:
            out["night_lights"] = float(v)
    except Exception as e:  # noqa: BLE001
        log.warning("earth-engine: VIIRS failed (%s)", type(e).__name__)

    # AlphaEarth embeddings: cosine distance between this year's and last year's mean 64-d vector over the buffer
    try:
        def vec(yr):
            img = ee.ImageCollection(EMB).filterBounds(aoi).filterDate(f"{yr}-01-01", f"{yr}-12-31").first()
            d = img.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=10, maxPixels=1e8).getInfo() or {}
            return [float(d[f"A{i:02d}"]) for i in range(64) if d.get(f"A{i:02d}") is not None]
        a, b = vec(year), vec(year - 1)
        if len(a) == 64 and len(b) == 64:
            dot = sum(x * y for x, y in zip(a, b))
            na, nb = sum(x * x for x in a) ** 0.5, sum(y * y for y in b) ** 0.5
            out["land_change_score"] = 1.0 - dot / (na * nb) if na and nb else 0.0
    except Exception as e:  # noqa: BLE001
        log.warning("earth-engine: satellite embedding failed (%s)", type(e).__name__)
    return out


def fetch(hc):
    """Contract: (sensors, readings). At most one Earth Engine round trip per day; results are yearly so the
    readings dedupe on (sensor, metric, ts) and repeated runs insert nothing."""
    if time.time() - _state["last"] < 86400:
        return [], []
    try:
        import ee  # noqa: PLC0415
    except ImportError:
        if not _state["warned"]:
            log.warning("earth-engine pack: earthengine-api is not installed. planetai packs installs code-pack dependencies.")
            _state["warned"] = True
        return [], []
    try:
        _init(ee)
    except Exception as e:  # noqa: BLE001
        if not _state["warned"]:
            log.warning("earth-engine pack: %s — the pack is idle until configured", e)
            _state["warned"] = True
        return [], []
    _state["last"] = time.time()
    lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
    year = datetime.now(timezone.utc).year - 1            # the last complete year
    values = compute(ee, lat, lon, year)
    if not values:
        return [], []
    ts = datetime(year, 7, 1, tzinfo=timezone.utc)      # mid-year stamp for annual quantities
    sensor = {"sensor_id": "ee-point", "source": "earth-engine", "name": f"Land within 1 km (Earth Engine, {year})",
              "lat": lat, "lon": lon, "indoor": False, "local": False, "kind": "model", "scale": "bioregion", "cadence": "P1Y",
              "meta": {"datasets": [DW, S2, VIIRS, EMB], "buffer_m": 1000,
                       "attribution": "Google Earth Engine; Dynamic World (Google/WRI, CC BY 4.0); Copernicus Sentinel-2; NOAA VIIRS; Google Satellite Embedding V1 (CC BY 4.0)"}}
    readings = [(ts, "ee-point", m, v) for m, v in values.items()]
    log.info("earth-engine: %d metrics for %d around the node", len(readings), year)
    return [sensor], readings
