"""Check the Earth Engine setup without waiting for the daily fetch.

    docker compose exec -T app python /app/packs/earth-engine/verify.py

Tells you which of the five steps is not done, in order, rather than one opaque failure.
"""
import os
import sys

sys.path.insert(0, "/app/packs/earth-engine")

print("1. library      ", end="")
try:
    import ee
    print("ok")
except ImportError:
    print("MISSING — run `planetai packs` on the host to install earthengine-api into the image"); sys.exit(1)

print("2. settings     ", end="")
missing = [k for k in ("EE_PROJECT", "EE_SERVICE_ACCOUNT", "EE_KEY_FILE") if not os.getenv(k)]
if missing:
    print(f"MISSING {', '.join(missing)} in .env"); sys.exit(1)
print(f"ok  project={os.environ['EE_PROJECT']}")

print("3. key file     ", end="")
key = os.environ["EE_KEY_FILE"]
if not os.path.exists(key):
    print(f"NOT FOUND at {key} — copy it to config/ee-key.json on the host"); sys.exit(1)
import json
try:
    kj = json.load(open(key))
except Exception as e:
    print(f"NOT VALID JSON ({e})"); sys.exit(1)
print(f"ok  {key}  (service account {kj.get('client_email','?')})")

# The key file states its own project. EE_PROJECT is often filled in with the service account's 21-digit unique id
# or its numeric client id, which Earth Engine rejects with "project not found" — a confusing error for a wrong field.
key_project = kj.get("project_id")
if key_project and os.environ["EE_PROJECT"] != key_project:
    print(f"   ! EE_PROJECT is '{os.environ['EE_PROJECT']}' but the key belongs to project '{key_project}'.")
    if os.environ["EE_PROJECT"].isdigit():
        print("     That looks like the service account's unique id, not a project id.")
    print(f"     Using '{key_project}' for this check. Set EE_PROJECT={key_project} in .env to make it permanent.")
    os.environ["EE_PROJECT"] = key_project

print("4. credentials  ", end="")
try:
    ee.Initialize(ee.ServiceAccountCredentials(os.environ["EE_SERVICE_ACCOUNT"], key), project=os.environ["EE_PROJECT"])
    print("ok")
except Exception as e:
    print(f"REJECTED — {e}")
    print("     · is the project registered for Earth Engine (code.earthengine.google.com/register)?")
    print("     · does the service account have the Earth Engine Resource Viewer role on it?")
    print("     · does the key belong to that same service account?")
    sys.exit(1)

print("5. a real query ", end="")
# A single-image dataset with a long life and no deprecation history. (COPERNICUS/DEM/GLO30 is an ImageCollection,
# not an Image, and is superseded — using it here failed for two unrelated reasons at once.)
try:
    lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
    v = ee.Image("USGS/SRTMGL1_003").select("elevation").reduceRegion(
        reducer=ee.Reducer.first(), geometry=ee.Geometry.Point([lon, lat]), scale=30).getInfo()
    print(f"ok  ground elevation at this node: {list(v.values())[0]} m")
except Exception as e:
    print(f"FAILED — {e}"); sys.exit(1)

print("6. the pack's own datasets")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapter  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
year = datetime.now(timezone.utc).year - 1
for name, cid in (("Dynamic World", adapter.DW), ("Sentinel-2", adapter.S2),
                  ("VIIRS night lights", adapter.VIIRS), ("AlphaEarth embeddings", adapter.EMB)):
    try:
        n = ee.ImageCollection(cid).filterDate(f"{year}-01-01", f"{year}-12-31").limit(1).size().getInfo()
        print(f"   {name:24} {'ok' if n else 'reachable but empty for ' + str(year)}   {cid}")
    except Exception as e:
        print(f"   {name:24} FAILED — {str(e)[:70]}   {cid}")

print("\nSetup is good. The pack fetches once a day; to see it now:")
print("  docker compose exec -T app python -c \"import sys; sys.path.insert(0,'/app/packs/earth-engine'); "
      "import adapter; s,r=adapter.fetch(None); print(s); [print(x) for x in r]\"")
