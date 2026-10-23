"""Check the pack against the bucket, the arithmetic and the node, and say which line failed.  planetai run terrain verify

Five checks: the libraries import, the node's tile answers without a key, the kept result describes this point,
every land cell in it drains (the one check that fails if the fill breaks), and the reading reached the database.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

fails = []


def step(n, ok, msg):
    print(f"  {'✓' if ok else '✗'} {n}: {msg}")
    if not ok:
        fails.append(f"{n}: {msg}")


try:
    import numpy as np
    import rasterio
    step(1, True, f"numpy {np.__version__}, rasterio {rasterio.__version__}")
except ImportError as e:
    step(1, False, f"{e}. planetai packs install, then planetai restart")
    sys.exit(1)

cov = A.coverage()
step(2, cov["kind"] != "none", f"{cov['kind']}: {cov['why']}")

r = A.result()
step(3, bool(r), "the kept result is around this point" if r else
     "nothing kept for this point and radius: planetai run terrain fetch")

if r and cov["kind"] != "none":
    z, sea, dx, dy, rc = A.read(cov)
    f = A.fill(z, sea)
    _, drop = A.steepest(f, dx, dy)
    n = A.stuck(f, sea, drop)
    step(4, n == 0, f"{n} land cells with nowhere to drain after the fill" if n else
         f"every one of {int((~sea).sum())} land cells drains to the edge or the sea")

try:
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as con, con.cursor() as cur:
        cur.execute("SELECT metric, value, ts FROM observations WHERE sensor_id = 'terrain-point' ORDER BY metric")
        rows = cur.fetchall()
    step(5, bool(rows), ", ".join(f"{m} {v:g}" for m, v, _ in rows) if rows else
         "no terrain-point rows yet: is terrain in PACKS_ENABLED, and has the node polled since the fetch?")
except Exception as e:  # noqa: BLE001
    step(5, False, f"the database did not answer ({type(e).__name__})")

print(f"\n{A.ATTRIBUTION}")
sys.exit(1 if fails else 0)
