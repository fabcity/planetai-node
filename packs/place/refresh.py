"""Force a fetch from Overpass now, instead of waiting for the monthly refresh. planetai run place refresh"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import httpx, psycopg
import adapter as A
with psycopg.connect(os.environ["DATABASE_URL"]) as con:
    with con.cursor() as cur: cur.execute(A.DDL); con.commit()
    n = A.refresh(con, httpx.Client(timeout=120), float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"]), int(os.getenv("PLACE_RADIUS_M", "1000")))
print(f"place: {n} features stored. The next poll turns them into readings.")
