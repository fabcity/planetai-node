"""The node's own copy of the AlphaEarth Satellite Embedding layers for its square of the planet, and the
year-over-year arithmetic on top of them.

Google publishes the Satellite Embedding dataset as Cloud-Optimized GeoTIFFs in a public bucket: one file per
UTM zone per year, 8192x8192 pixels at 10 m, 64 signed-8-bit channels, 2017-2025. This pack range-reads the
window around the node, keeps it under out/earth/, and compares two years pixel by pixel. Nothing is sent
anywhere; the node holds its own square.

kind='model', scale='city'. A Google artifact, mirrored under CC BY 4.0. Never a `live` cell.

The de-quantisation is not a scale factor. Each raw value maps to the analysis value by
    (v / 127.5) ** 2 * sign(v)
and the 64-vector has Euclidean length 1 AFTER that mapping, not before. Cosine arithmetic on the raw
integers is wrong by a factor of about 321 and silently plausible. Measured on 20,000 pixels of the Bali
tile: de-quantised norms 1.000093 +/- 0.002, raw norms ~321.

This module holds the shared work; the four scripts beside it are the commands. It imports numpy and rasterio
lazily so that a node without them loads the pack, logs once and idles.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from pathlib import Path

log = logging.getLogger("planetai.pack.earth")

GCS = "https://storage.googleapis.com"
BUCKET = f"{GCS}/alphaearth_foundations"
ROOT = f"{BUCKET}/satellite_embedding/v1/annual"
INDEX = f"{ROOT}/aef_index.csv"
DATASET = "satellite_embedding/v1/annual (AlphaEarth Foundations)"
ATTRIBUTION = ("The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind. "
               "CC BY 4.0.")
YEARS = tuple(range(2017, 2026))            # what the bucket holds today; verify re-reads the listing
# The columns of aef_index.csv, in order. The file has a header row, but a range read starts mid-file, so the
# header travels here instead.
COLUMNS = ("WKT,crs,path,year,utm_zone,utm_west,utm_south,utm_east,utm_north,"
           "wgs84_west,wgs84_south,wgs84_east,wgs84_north")
_ZONE_IN_PATH = re.compile(r"/annual/(\d{4})/(\d+)([NS])/")
_state = {"warned": False}


# ---------------------------------------------------------------- where and what

def node() -> str:
    return os.getenv("NODE_NAME", "node")


def aoi() -> tuple[float, float, int]:
    """The node's point and the radius the pack describes around it. EARTH_RADIUS_M is a half-width: 5000 asks
    for a 10 km square."""
    return float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"]), int(os.getenv("EARTH_RADIUS_M", "5000") or 5000)


def wanted_years() -> list[int]:
    """EARTH_YEARS blank means every year the dataset has."""
    raw = (os.getenv("EARTH_YEARS", "") or "").replace(" ", "")
    if not raw:
        return list(YEARS)
    return sorted({int(y) for y in raw.split(",") if y})


def cache() -> Path:
    return Path(os.getenv("PACK_OUT", "/app/out")) / "earth" / node()


def utm_zone(lat: float, lon: float) -> str:
    """The UTM zone the dataset files this point under. Zones are 6 degrees wide from -180."""
    z = min(60, max(1, int((lon + 180) // 6) + 1))
    return f"{z}{'N' if lat >= 0 else 'S'}"


# ---------------------------------------------------------------- the tile index

def _get(url: str, start: int | None = None, end: int | None = None, timeout: int = 120) -> bytes:
    headers = {} if start is None else {"Range": f"bytes={start}-{end}"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:                    # noqa: S310  (https, fixed host)
        return r.read()


def _size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:                         # noqa: S310
        return int(r.headers["Content-Length"])


def _zone_key(zone: str) -> tuple[int, int]:
    return (0 if zone.endswith("N") else 1, int(zone[:-1]))


def _zone_at(url: str, offset: int) -> tuple[int, int] | None:
    """The zone of whichever row straddles this byte offset. A row is about 3 kB (the WKT polygon is most of
    it), so 12 kB always contains at least one complete path."""
    chunk = _get(url, offset, offset + 12000).decode("utf-8", "replace")
    m = _ZONE_IN_PATH.search(chunk)
    return _zone_key(m.group(2) + m.group(3)) if m else None


def zone_block(zone: str, log_bytes: dict | None = None) -> str:
    """The rows of aef_index.csv for one UTM zone.

    The index is 798 MB and there is no GeoJSON form of it, so downloading it is not on. It is sorted by UTM
    zone (1N..60N, then 1S..60S) with the years interleaved inside each zone, so a binary search over byte
    offsets finds the zone's block and one range read fetches it. Measured for 50S: 26 probes, 189 kB, then a
    single 8.8 MB read. The bounds are deliberately loose; the caller filters by zone.
    """
    size = _size(INDEX)
    target = _zone_key(zone)
    lo, hi = 0, size
    probes = 0
    while hi - lo > 200000:
        mid = (lo + hi) // 2
        k = _zone_at(INDEX, mid); probes += 1
        if k is None or k < target:
            lo = mid
        else:
            hi = mid
    low = lo
    lo, hi = low, size
    while hi - lo > 200000:
        mid = (lo + hi) // 2
        k = _zone_at(INDEX, mid); probes += 1
        if k is None or k <= target:
            lo = mid
        else:
            hi = mid
    body = _get(INDEX, low, hi)
    if log_bytes is not None:
        log_bytes["index_bytes"] = probes * 12001 + len(body)
        log_bytes["index_probes"] = probes
    text = body.decode("utf-8", "replace")
    return text[text.index("\n") + 1: text.rindex("\n")]                       # drop the two partial rows


def resolve(lat: float, lon: float, log_bytes: dict | None = None) -> dict[str, dict]:
    """{year: row} for the tiles covering this point, one per year. The dataset's own words: it is not
    possible to tell from a file name what part of the world it covers."""
    import csv
    import io
    zone = utm_zone(lat, lon)
    rows = csv.DictReader(io.StringIO(COLUMNS + "\n" + zone_block(zone, log_bytes)))
    out = {}
    for r in rows:
        if r["utm_zone"] != zone:
            continue
        if not (float(r["wgs84_west"]) <= lon <= float(r["wgs84_east"])
                and float(r["wgs84_south"]) <= lat <= float(r["wgs84_north"])):
            continue
        r.pop("WKT", None)
        out[r["year"]] = r
    if not out:
        raise RuntimeError(f"no tile in the index covers {lat},{lon} (zone {zone})")
    return out


# ---------------------------------------------------------------- the arithmetic

def dequantize(raw):
    """Raw signed bytes to the analysis values the embedding norms are defined on. README of the bucket:
    divide by 127.5, square, multiply by the sign."""
    import numpy as np
    f = raw.astype(np.float32) / 127.5
    return (f * f) * np.sign(f)


def cosine_distance(a, b, rows: int = 100):
    """1 - cosine similarity, per pixel, between two (64, H, W) raw arrays.

    The vectors are already unit length once de-quantised, so the dot product is the cosine and no
    renormalisation is needed. Done in row bands because a de-quantised year is 256 MB of float32 and a node
    may have 2 GB of memory; a band of 100 rows is 26 MB. Returns (distance, masked) as (H, W) arrays;
    -128 in any channel means no data and the README says it is then in every channel.
    """
    import numpy as np
    h, w = a.shape[1], a.shape[2]
    dist = np.empty((h, w), dtype=np.float32)
    masked = np.empty((h, w), dtype=bool)
    for i in range(0, h, rows):
        x = dequantize(np.asarray(a[:, i:i + rows, :]))
        y = dequantize(np.asarray(b[:, i:i + rows, :]))
        dist[i:i + rows] = 1.0 - np.clip((x * y).sum(0), -1.0, 1.0)
        masked[i:i + rows] = (np.asarray(a[0, i:i + rows, :]) == -128) | (np.asarray(b[0, i:i + rows, :]) == -128)
    dist[masked] = np.nan
    return dist, masked

# ---------------------------------------------------------------- reading a COG over HTTPS

# GDAL's defaults are wrong for this file in two ways that cost minutes. Its 16 kB range chunks turn one
# 230 kB internal block into fourteen requests, and its block cache is smaller than the 256 MB a 64-band
# read touches, so blocks are fetched, evicted and fetched again. Measured on the Bali tile: 9+ minutes
# for one AOI-year with the defaults and one ds.read(), 149 s with these and one band at a time.
GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",     # no directory listing per open
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tiff",
    "CPL_VSIL_CURL_CHUNK_SIZE": "262144",            # about one internal block
    "CPL_VSIL_CURL_CACHE_SIZE": "268435456",
    "GDAL_CACHEMAX": "64",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}


def open_cog(url: str):
    """rasterio.open on the bucket's HTTPS URL, with the settings that make it finish. No credentials: the
    bucket answers anonymous range requests."""
    for k, v in GDAL_ENV.items():
        os.environ.setdefault(k, v)
    import rasterio
    return rasterio.open("/vsicurl/" + url.replace("gs://", GCS + "/"))


def window_px(row: int, col: int, radius_m: int, height: int, width: int):
    """The square of side 2*radius centred on one pixel, clipped to the raster. Pure arithmetic, no raster and
    no projection, so the offline tests can check it. Returns (r0, c0, r1, c1, clipped), end-exclusive."""
    half = radius_m // 10                                                       # the dataset is 10 m
    r0, c0, r1, c1 = row - half, col - half, row + half, col + half
    kr0, kc0, kr1, kc1 = max(0, r0), max(0, c0), min(height, r1), min(width, c1)
    if kr1 <= kr0 or kc1 <= kc0:
        raise RuntimeError("the node's square falls outside the tile the index gave")
    return kr0, kc0, kr1, kc1, (kr0, kc0, kr1, kc1) != (r0, c0, r1, c1)


def window_for(ds, lat: float, lon: float, radius_m: int):
    """The pixel window of the square of side 2*radius centred on the point, clipped to the tile. Returns
    (window, bounds, clipped, node_rc) where bounds is {north, south, east, west} in the tile's UTM metres and
    node_rc is the node's (row, col) inside the window, in the file's own row order."""
    from rasterio.warp import transform as warp_transform
    from rasterio.windows import Window
    xs, ys = warp_transform("EPSG:4326", ds.crs, [lon], [lat])
    row, col = ds.index(xs[0], ys[0])
    kr0, kc0, kr1, kc1, clipped = window_px(row, col, radius_m, ds.height, ds.width)
    w = Window(kc0, kr0, kc1 - kc0, kr1 - kr0)
    left, bottom, right, top = ds.window_bounds(w)
    bounds = {"west": min(left, right), "east": max(left, right),
              "south": min(bottom, top), "north": max(bottom, top)}
    return w, bounds, clipped, (row - kr0, col - kc0)


def read_window(ds, w):
    """One band at a time into one array. See GDAL_ENV for why not ds.read(window=w)."""
    import numpy as np
    out = np.empty((ds.count, int(w.height), int(w.width)), dtype="int8")
    for i in range(1, ds.count + 1):
        out[i - 1] = ds.read(i, window=w)
    return out


# ---------------------------------------------------------------- drawing, without a library

# The ramp's top. Fixed rather than per-image so two years of the same place, or two places, can be put side
# by side and mean the same thing. 0.30 is above the 99.9th percentile of every consecutive-year pair
# measured at node #1, so a normal year uses the lower half of the ramp and a cleared hillside saturates.
RAMP_CEILING = 0.30
NODATA_IX, NODE_IX, RULE_IX = 0, 253, 254


def _palette() -> bytes:
    """256 RGB entries: black for no data, a grey ramp for the distance, one orange for the node, white for
    the scale bar."""
    out = bytearray(b"\x00\x00\x00")                       # 0: no data
    for i in range(1, 253):                                  # 1..252: grey 30..255
        g = 30 + round((i - 1) * (255 - 30) / 251)
        out += bytes((g, g, g))
    out += b"\xe8\x64\x1e"                                  # 253: the node
    out += b"\xff\xff\xff"                                  # 254: the scale bar
    out += b"\x00\x00\x00"                                  # 255: unused
    return bytes(out)


def ramp_indices(dist, masked):
    """(H, W) float distances to (H, W) palette indices."""
    import numpy as np
    x = np.clip(np.nan_to_num(dist, nan=0.0) / RAMP_CEILING, 0.0, 1.0)
    ix = (1 + np.rint(x * 251)).astype(np.uint8)
    ix[masked] = NODATA_IX
    return ix


def write_png(path, ix, texts: dict | None = None) -> int:
    """An indexed-colour PNG from a (H, W) uint8 array of palette indices. zlib and struct are enough; the
    node has no image library and this pack is not going to add one. Returns the file size.

    The attribution travels inside the file as a tEXt chunk, so a PNG that leaves the node still carries it.
    """
    import struct
    import zlib
    h, w = ix.shape
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = bytearray()
    for r in range(h):
        raw.append(0)                                        # filter: none
        raw += ix[r].tobytes()
    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
    out += chunk(b"PLTE", _palette())
    for k, v in (texts or {}).items():
        out += chunk(b"tEXt", k.encode("latin-1", "replace") + b"\x00" + v.encode("latin-1", "replace"))
    out += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    out += chunk(b"IEND", b"")
    path.write_bytes(out)
    return len(out)


def draw_marks(ix, node_rc: tuple[int, int] | None = None) -> None:
    """A 1 km scale bar bottom left, and optionally a ring where the node is. In place."""
    h, w = ix.shape
    bar = 100                                                # 100 px at 10 m is one kilometre
    y, x0 = h - 14, 14
    if w > x0 + bar + 4 and h > 20:
        ix[y:y + 3, x0:x0 + bar] = RULE_IX
        ix[y - 4:y + 7, x0] = RULE_IX
        ix[y - 4:y + 7, x0 + bar - 1] = RULE_IX
    if node_rc:
        r, c = node_rc
        for dr in range(-6, 7):
            for dc in range(-6, 7):
                d = (dr * dr + dc * dc) ** 0.5
                if 4.0 <= d <= 6.0 and 0 <= r + dr < h and 0 <= c + dc < w:
                    ix[r + dr, c + dc] = NODE_IX


# ---------------------------------------------------------------- the cache on disk

def year_file(year: int) -> Path:
    return cache() / f"{year}.npy"


def cached_years() -> list[int]:
    return sorted(int(p.stem) for p in cache().glob("*.npy") if p.stem.isdigit())


def meta() -> dict:
    p = cache() / "meta.json"
    return json.loads(p.read_text()) if p.is_file() else {}


def write_meta(d: dict) -> None:
    cache().mkdir(parents=True, exist_ok=True)
    (cache() / "meta.json").write_text(json.dumps(d, indent=1, sort_keys=True))


def change_file(a: int, b: int, suffix: str) -> Path:
    return cache() / f"change_{a}_{b}.{suffix}"


def changes() -> list[dict]:
    """Every computed comparison, newest pair last."""
    out = []
    for p in sorted(cache().glob("change_*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception as e:                                                  # noqa: BLE001
            log.warning("earth: %s is not readable json (%s)", p.name, e)
    return sorted(out, key=lambda c: (c.get("year_b", 0), c.get("year_a", 0)))


def latest_pair() -> tuple[int, int] | None:
    """The two most recent consecutive cached years. A gap is not a year-over-year comparison."""
    ys = cached_years()
    pairs = [(a, b) for a, b in zip(ys, ys[1:]) if b - a == 1]
    return pairs[-1] if pairs else None


# ---------------------------------------------------------------- the node's contract

def fetch(hc):                                                                  # noqa: ARG001  (no HTTP here; the cache is local)
    """Contract: (sensors, readings). Reads what `planetai run earth change` already computed. Nothing is
    downloaded on a poll: this pack fetches on command, not on a schedule, because one year is 103 MB."""
    cs = changes()
    if not cs:
        if not _state["warned"]:
            log.info("earth: nothing cached yet — planetai run earth fetch, then planetai run earth change")
            _state["warned"] = True
        return [], []
    from datetime import datetime, timezone
    lat, lon, radius = aoi()
    ys = cached_years()
    values: dict[str, float] = {"years_cached": float(len(ys))}
    yoy = [c for c in cs if c["year_b"] - c["year_a"] == 1]
    if yoy:
        values["land_change_yoy"] = yoy[-1]["mean"]
    since = [c for c in cs if c["year_a"] == 2017]
    if since:
        values["land_change_since_2017"] = since[-1]["mean"]
    latest = (yoy or cs)[-1]
    ts = datetime(latest["year_b"], 7, 1, tzinfo=timezone.utc)                  # mid-year stamp for an annual quantity
    sensor = {"sensor_id": "earth-point", "source": "earth",
              "name": f"Land within {radius // 1000} km (AlphaEarth, {latest['year_a']}→{latest['year_b']})",
              "lat": lat, "lon": lon, "indoor": False, "local": False,
              "kind": "model", "scale": "city", "cadence": "P1Y",
              "meta": {"dataset": DATASET, "radius_m": radius, "years": ys,
                       "tiles": latest.get("tiles", []), "attribution": ATTRIBUTION}}
    readings = [(ts, "earth-point", m, v) for m, v in values.items()]
    log.info("earth: %d metrics from %d cached years", len(readings), len(ys))
    return [sensor], readings
