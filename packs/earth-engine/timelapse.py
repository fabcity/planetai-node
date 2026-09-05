"""A series of satellite images of the same place, years apart, written to out/.

    planetai run earth-engine timelapse                       four images, five years apart, ending last year
    planetai run earth-engine timelapse --years 2010,2015,2020,2025 --km 2
    planetai run earth-engine timelapse --n 6 --gap 3 --km 1 --source sentinel

Landsat by default, because it is the only archive that reaches back far enough for a fifteen-year comparison and
the same instrument family across all four frames: a like-for-like series matters more than resolution when the
question is "what changed". Sentinel-2 (`--source sentinel`, 2016 onward) is three times sharper for recent years.

Each frame is the median of a whole year of clear pixels, which removes clouds and any single day's haze. What you
see is the year, not a date.
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import ee

OUT = os.getenv("PACK_OUT", "/app/out")

# Landsat Collection 2 Level-2 surface reflectance. Which satellite was flying decides the collection and the
# band names: TM/ETM+ put red-green-blue in B3/B2/B1, OLI shifted them to B4/B3/B2.
LANDSAT = [
    (1984, 2011, "LANDSAT/LT05/C02/T1_L2", ["SR_B3", "SR_B2", "SR_B1"]),   # Landsat 5 TM
    (2012, 2013, "LANDSAT/LE07/C02/T1_L2", ["SR_B3", "SR_B2", "SR_B1"]),   # Landsat 7 ETM+ (gap-filled era)
    (2013, 2021, "LANDSAT/LC08/C02/T1_L2", ["SR_B4", "SR_B3", "SR_B2"]),   # Landsat 8 OLI
    (2022, 2100, "LANDSAT/LC09/C02/T1_L2", ["SR_B4", "SR_B3", "SR_B2"]),   # Landsat 9 OLI-2
]


def _init():
    key = os.getenv("EE_KEY_FILE")
    if not (key and os.path.exists(key)):
        sys.exit("EE_KEY_FILE must point at a readable service-account key. See packs/earth-engine/README.md")
    kj = json.load(open(key))
    proj = os.getenv("EE_PROJECT") or ""
    if not proj or proj.isdigit():
        proj = kj["project_id"]
    ee.Initialize(ee.ServiceAccountCredentials(os.getenv("EE_SERVICE_ACCOUNT") or kj["client_email"], key), project=proj)
    return proj


def landsat_rgb(year, aoi):
    """A cloud-free median RGB composite for one year, from whichever Landsat was flying."""
    for lo, hi, cid, bands in LANDSAT:
        if lo <= year <= hi:
            def prep(img):
                qa = img.select("QA_PIXEL")
                clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))   # cloud, cloud shadow
                sr = img.select(bands).multiply(0.0000275).add(-0.2)                    # C2 L2 scaling to reflectance
                return sr.updateMask(clear).rename(["R", "G", "B"])
            col = ee.ImageCollection(cid).filterBounds(aoi).filterDate(f"{year}-01-01", f"{year}-12-31").map(prep)
            return col.median(), cid, col.size()
    sys.exit(f"no Landsat mission covers {year}")


def sentinel_rgb(year, aoi):
    def prep(img):
        scl = img.select("SCL")
        clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))            # shadow, cloud med/high, cirrus
        return img.select(["B4", "B3", "B2"]).divide(10000).updateMask(clear).rename(["R", "G", "B"])
    cid = "COPERNICUS/S2_SR_HARMONIZED"
    col = ee.ImageCollection(cid).filterBounds(aoi).filterDate(f"{year}-01-01", f"{year}-12-31").map(prep)
    return col.median(), cid, col.size()


def _nearest_with_imagery(year, aoi, source, span=3):
    """Landsat 5's coverage over parts of Asia is sparse and this coast is cloudy, so a requested year can be
    genuinely empty. Look outward a year at a time rather than leaving a gap in the series."""
    for d in range(1, span + 1):
        for y in (year - d, year + d):
            if y > datetime.now(timezone.utc).year:
                continue
            try:
                _, _, size = (sentinel_rgb if source == "sentinel" else landsat_rgb)(y, aoi)
                if size.getInfo():
                    return y
            except SystemExit:
                continue
            except Exception:  # noqa: BLE001
                continue
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", help="comma-separated, e.g. 2010,2015,2020,2025")
    p.add_argument("--n", type=int, default=4, help="how many frames (default 4)")
    p.add_argument("--gap", type=int, default=5, help="years between frames (default 5)")
    p.add_argument("--km", type=float, default=2.0, help="width of the square, in km (default 2)")
    p.add_argument("--px", type=int, default=1024, help="image size in pixels (default 1024)")
    p.add_argument("--source", choices=("landsat", "sentinel"), default="landsat")
    p.add_argument("--lat", type=float, default=None)
    p.add_argument("--lon", type=float, default=None)
    p.add_argument("--dry-run", action="store_true", help="say what would be fetched, fetch nothing")
    a = p.parse_args()

    last = datetime.now(timezone.utc).year - 1
    years = [int(y) for y in a.years.split(",")] if a.years else sorted(last - a.gap * i for i in range(a.n))
    lat = a.lat if a.lat is not None else float(os.environ["NODE_LAT"])
    lon = a.lon if a.lon is not None else float(os.environ["NODE_LON"])
    node = os.getenv("NODE_NAME", "node")

    if a.source == "sentinel" and min(years) < 2016:
        sys.exit(f"Sentinel-2 starts in 2015 (usable from 2016); {min(years)} needs --source landsat")

    print(f"{len(years)} frames of {a.km} km around {lat}, {lon} — {', '.join(map(str, years))}  [{a.source}]")
    if a.dry_run:
        return
    _init()
    os.makedirs(OUT, exist_ok=True)
    half = a.km * 1000 / 2
    aoi = ee.Geometry.Point([lon, lat]).buffer(half).bounds()
    vis = {"min": 0.0, "max": 0.3, "bands": ["R", "G", "B"], "gamma": 1.3}
    written = []
    for y in years:
        img, cid, size = (sentinel_rgb if a.source == "sentinel" else landsat_rgb)(y, aoi)
        try:
            n = size.getInfo()
        except Exception as e:  # noqa: BLE001
            print(f"  {y}  FAILED to query {cid}: {str(e)[:80]}"); continue
        if not n:
            alt = _nearest_with_imagery(y, aoi, a.source)
            if alt:
                print(f"  {y}  no clear imagery in {cid} — using {alt} instead (the archive is thin here)")
                y = alt
                img, cid, size = (sentinel_rgb if a.source == "sentinel" else landsat_rgb)(y, aoi)
                n = size.getInfo()
            else:
                print(f"  {y}  no clear imagery within 3 years in {cid}"); continue
        try:
            url = img.visualize(**vis).getThumbURL({"region": aoi, "dimensions": a.px, "format": "png"})
        except Exception as e:  # noqa: BLE001
            if "thumbnails.create" in str(e) or "permission" in str(e).lower():
                sys.exit("\nEarth Engine refused to render an image: the service account can read but not draw.\n"
                         "  Cloud Console -> IAM & Admin -> IAM -> " + (os.getenv("EE_SERVICE_ACCOUNT") or "your service account") + "\n"
                         "  add the role  Earth Engine Resource Writer  (keep Resource Viewer), then run this again.\n"
                         "  Reading numbers needs Viewer; making pictures needs Writer.")
            raise
        path = os.path.join(OUT, f"{node}-{y}-{a.source}-{a.km:g}km.png")
        urllib.request.urlretrieve(url, path)
        kb = os.path.getsize(path) // 1024
        print(f"  {y}  {n:4d} scenes → {os.path.basename(path)}  ({kb} kB)")
        written.append((y, os.path.basename(path)))

    if len(written) > 1:
        html = os.path.join(OUT, f"{node}-timelapse-{a.source}.html")
        with open(html, "w") as f:
            f.write(f"<!doctype html><meta charset=utf-8><title>{node} {years[0]}–{years[-1]}</title>"
                    "<style>body{background:#171717;color:#f7f5f1;font:14px/1.5 system-ui;margin:0;padding:24px}"
                    "h1{font-weight:800;letter-spacing:-.02em}.g{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}"
                    "figure{margin:0}img{width:100%;display:block;border:1px solid #333}figcaption{padding:8px 0;color:#b3ada0;font-variant-numeric:tabular-nums}</style>"
                    f"<h1>{node} · {a.km:g} km · {a.source}</h1><div class=g>"
                    + "".join(f"<figure><img src='{fn}' loading=lazy><figcaption>{yr}</figcaption></figure>" for yr, fn in written)
                    + "</div><p style='color:#8b857a;margin-top:24px'>Annual median of clear pixels. "
                      "Landsat Collection 2 Level-2 / Copernicus Sentinel-2 via Google Earth Engine.</p>")
        print(f"\nside by side: out/{os.path.basename(html)}")
    print(f"\n{len(written)} image(s) in out/ — they are on the host, next to your .env")


if __name__ == "__main__":
    main()
