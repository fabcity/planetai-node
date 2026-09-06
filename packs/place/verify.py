"""Check the place pack end to end on this node: PostGIS, OpenStreetMap, Earth Engine + Open Buildings.  planetai run place verify"""
import os, sys, time
import httpx, psycopg
sys.path.insert(0, os.path.dirname(__file__))
import adapter as A
lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"]); radius = int(os.getenv("PLACE_RADIUS_M", "1000"))
def step(n, ok, msg): print(f"  {'✓' if ok else '✗'} {n}: {msg}")
try:
    con = psycopg.connect(os.environ["DATABASE_URL"]); cur = con.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis"); con.commit(); cur.execute("SELECT PostGIS_Version()"); step(1, True, f"PostGIS {cur.fetchone()[0]}")
except Exception as e:
    step(1, False, f"PostGIS: {e}. Did planetai update switch the database image? docker compose ps"); sys.exit(1)
try:
    t0 = time.time(); n = A.refresh(con, httpx.Client(), lat, lon, radius); step(2, True, f"OpenStreetMap: {n} features within {radius} m in {time.time()-t0:.0f}s")
except Exception as e:
    step(2, False, f"OpenStreetMap via Overpass: {e}")
try:
    import satellite as S
    ee = S.init_ee(); step(3, True, "Earth Engine credentials accepted")
    t0 = time.time(); n, conf = S.footprints(ee, con, lat, lon, radius); step(4, True, f"Open Buildings V3: {n} footprints, mean confidence {conf:.2f}, {time.time()-t0:.0f}s")
    t0 = time.time(); ys = S.yearly(ee, lat, lon, radius); step(5, True, f"Open Buildings Temporal: {', '.join(f'{y}: {round(c)} bld, {h:.1f} m' if h else f'{y}: {round(c)} bld' for y, c, h in ys)} ({time.time()-t0:.0f}s)")
except Exception as e:
    step(3, False, f"Earth Engine / Open Buildings: {type(e).__name__}: {str(e)[:160]}. Configure the earth-engine pack first; the place pack reuses its key.")
print("\nNext: planetai run place gaps  — the mapping briefing.")
