"""Tests for the shipped code packs' logic, without their services.
  · coast: the inland refusal and the metric mapping, against a saved Marine API payload
  · earth-engine: compute() against a fake `ee` that returns known numbers; fetch() stays idle without credentials
Run: PYTHONPATH=/tmp/stub:app python3 tests/test_packs.py"""
import importlib.util
import os
import sys
import types

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

# ---------------------------------------------------------------- coast
coast = load("packs/coast/adapter.py", "coast")
class R:
    def __init__(s, j): s.j = j
    def raise_for_status(s): pass
    def json(s): return s.j
class HC:
    def __init__(s, j): s.j = j
    def get(s, url, params=None): return R(s.j)
marine = {"latitude": -8.791664, "longitude": 115.125015, "current_units": {"wave_height": "m"},
          "current": {"time": "2026-09-05T03:45", "wave_height": 1.72, "wave_direction": 203, "wave_period": 11.75,
                      "swell_wave_height": 1.58, "swell_wave_period": 11.1, "sea_surface_temperature": 27.4}}
os.environ.update(NODE_LAT="-8.8271", NODE_LON="115.15709")
s, r = coast.fetch(HC(marine))
m = {k: v for _, _, k, v in r}
assert s[0]["kind"] == "model" and s[0]["scale"] == "bioregion" and not s[0]["local"]
assert m["wave_height_m"] == 1.72 and m["sea_surface_temp"] == 27.4 and m["swell_period_s"] == 11.1
assert 4 < s[0]["meta"]["distance_km"] < 6, "the node is ~5 km from that ocean cell"
os.environ.update(NODE_LAT="-8.5069", NODE_LON="115.2625", COAST_MAX_KM="10")     # Ubud
try:
    coast.fetch(HC(marine)); raise AssertionError("an inland node must be refused")
except RuntimeError:
    pass
os.environ.update(NODE_LAT="-8.8271", NODE_LON="115.15709"); os.environ.pop("COAST_MAX_KM", None)

# ---------------------------------------------------------------- earth-engine, with a fake ee
eepack = load("packs/earth-engine/adapter.py", "eepack")

class FakeVal:
    def __init__(s, v): s.v = v
    def getInfo(s): return s.v
class FakeImage:
    def __init__(s, data): s.data = data
    def select(s, *a): return s
    def updateMask(s, *a): return s
    def rename(s, *a): return s
    def normalizedDifference(s, *a): return s
    def neq(s, *a): return s
    def And(s, *a): return s
    def reduceRegion(s, **kw): return FakeDict(s.data)
class FakeDict:
    def __init__(s, d): s.d = d
    def get(s, k): return FakeVal(s.d.get(k))
    def getInfo(s): return s.d
class FakeIC:
    def __init__(s, cid): s.cid = cid
    def filterBounds(s, *a): return s
    def filterDate(s, a, b): s.year = int(a[:4]); return s
    def select(s, *a): return s
    def sort(s, *a): return s
    def map(s, fn): return s
    def mode(s): return FakeImage({"label": {"1": 60, "6": 30, "4": 10}})                      # 60% trees, 30% built, 10% crops
    def median(s): return FakeImage({"ndvi": 0.42})
    def first(s):
        if s.cid == eepack.VIIRS: return FakeImage({"avg_rad": 3.7})
        vec = {f"A{i:02d}": (1.0 if s.year == 2025 else (1.0 if i < 60 else -1.0)) for i in range(64)}   # 4 of 64 dims flipped
        return FakeImage(vec)
class FakeReducer:
    @staticmethod
    def frequencyHistogram(): return "hist"
    @staticmethod
    def mean(): return "mean"
class FakeGeom:
    @staticmethod
    def Point(c):
        class P:
            def buffer(s, m): return "aoi"
        return P()
fake_ee = types.SimpleNamespace(ImageCollection=FakeIC, Reducer=FakeReducer, Geometry=FakeGeom)

out = eepack.compute(fake_ee, -8.8271, 115.15709, 2025)
assert abs(out["tree_frac"] - 0.6) < 1e-9 and abs(out["built_frac"] - 0.3) < 1e-9 and abs(out["crop_frac"] - 0.1) < 1e-9
assert out["water_frac"] == 0.0, "an absent class is 0, not missing"
assert out["ndvi_median"] == 0.42 and out["night_lights"] == 3.7
# 4 of 64 dims flipped sign: cosine = (60-4)/64 = 0.875 -> change score 0.125
assert abs(out["land_change_score"] - 0.125) < 1e-9, out["land_change_score"]

# without credentials the pack must stay idle, not raise, and must not retry every poll
for k in ("EE_PROJECT", "EE_SERVICE_ACCOUNT", "EE_KEY_FILE"): os.environ.pop(k, None)
sys.modules["ee"] = types.ModuleType("ee")     # importable, but _init will fail on missing config
eepack._state["last"] = 0
assert eepack.fetch(None) == ([], []) and eepack._state["warned"]

print("all pack tests pass")
