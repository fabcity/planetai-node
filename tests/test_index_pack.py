"""The index pack's place list and the nearest-place suggestion.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_index_pack.py
What is checked is what fails silently: a list that lost a place, a centre in the wrong order (the registry's are
[lat, lng]; swap them and Bali lands in the Indian Ocean without an error), a node in Menorca told it is in
Barcelona, and the two command-line entry points the `planetai place` command calls instead of redoing the sums.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packs", "index"))
import place as PL  # noqa: E402

PY = os.path.join(ROOT, "packs", "index", "place.py")
P = PL.load()

# ---- the list: the registry's 61, each with a centre.
assert len(P) == 61, len(P)
assert [p["slug"] for p in P] == sorted(p["slug"] for p in P)
assert all(set(p) == {"slug", "name", "country", "lat", "lon"} for p in P)
assert sum(1 for p in P if p["lat"] is not None) == 61

# ---- nearest, by where the place is rather than by which list it is in.
assert PL.nearest(41.39, 2.17, P)["slug"] == "barcelona"
assert PL.nearest(-8.8271, 115.15709, P)["slug"] == "bali"        # node #1: 66 km from Bali's centre
# Menorca is 240 km from Barcelona and has no place of its own: a suggestion that far would be a guess.
assert PL.nearest(39.89, 4.26, P) is None
# a place with no centre can never be the nearest, and a list of only those is None, not an error
blank = [{"slug": "x", "name": "X", "country": "Y", "lat": None, "lon": None}]
assert PL.nearest(0, 0, blank) is None
assert PL.nearest(41.39, 2.17, blank + P)["slug"] == "barcelona"
# the antimeridian: Fiji-side longitudes must not read as the far side of the world
wrap = [{"slug": "w", "name": "W", "country": "Z", "lat": 0.0, "lon": -179.9}]
assert PL.nearest(0.0, 179.9, wrap)["slug"] == "w"

# ---- known
assert PL.known("barcelona", P) and not PL.known("barcelone", P) and not PL.known("", P)

# ---- the entry points `planetai place` calls
def run(*a):
    return subprocess.run([sys.executable, PY, *a], capture_output=True, text=True)

r = run("--nearest", "41.39", "2.17")
assert r.returncode == 0 and json.loads(r.stdout)["slug"] == "barcelona", (r.stdout, r.stderr)
assert len(r.stdout.strip().splitlines()) == 1
r = run("--nearest", "39.89", "4.26")
assert r.returncode == 0 and r.stdout.strip() == "null", r.stdout
assert run("--known", "bali").returncode == 0
assert run("--known", "bali-ish").returncode == 2
assert run().returncode not in (0, 2)

print("  ok: test_index_pack")
sys.exit(0)
