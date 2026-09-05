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
print(f"ok  {key}")

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
try:
    lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
    v = ee.Image("COPERNICUS/DEM/GLO30").select("DEM").reduceRegion(
        reducer=ee.Reducer.first(), geometry=ee.Geometry.Point([lon, lat]), scale=30).getInfo()
    print(f"ok  ground elevation at this node: {list(v.values())[0]} m")
except Exception as e:
    print(f"FAILED — {e}"); sys.exit(1)

print("\nSetup is good. The pack fetches once a day; to see it now:")
print("  docker compose exec -T app python -c \"import sys; sys.path.insert(0,'/app/packs/earth-engine'); "
      "import adapter; s,r=adapter.fetch(None); print(s); [print(x) for x in r]\"")
