"""A room marked `secondary` is read and drawn but is not the house's number.
Run: PACKS_DIR=packs PYTHONPATH=app python3 tests/test_room_role.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("PACKS_DIR", "packs")
sys.path.insert(0, str(ROOT / "app"))
from issues import engine  # noqa: E402


def row(sid, metric, mean, role=None, indoor=True, local=True):
    return {"sensor_id": sid, "metric": metric, "indoor": indoor, "local": local, "kind": "sensor", "role": role,
            "name": sid, "mean_15m": mean, "silent_minutes": 3}


living = [row("living", "temp", 24.0, "reference"), row("living", "humidity", 55.0, "reference")]
workshop = [row("workshop", "temp", 36.0, "secondary"), row("workshop", "humidity", 70.0, "secondary")]
spec = {"place": "room", "field": "mean_15m", "metrics": ["temp", "humidity"], "aggregate": "median", "function": "apparent"}

# the predicate
assert engine._ambient(living[0], "room") and not engine._ambient(workshop[0], "room")
assert engine._ambient(row("w", "temp", 30.0), "room"), "a sensor with no role is an ordinary room"
assert engine._ambient(row("y", "temp", 30.0, "secondary", indoor=False), "yard"), "the role is about rooms only"

# the number: the living room alone, the same with or without the workshop beside it
alone = engine._from_stats(spec, living, {})
both = engine._from_stats(spec, living + workshop, {})
assert alone and both and alone["value"] == both["value"] and both["sensors"] == ["living"], both
# the workshop on its own is not "the house": no room number at all
assert engine._from_stats(spec, workshop, {}) is None
# unmarked, the two rooms are blended (the behaviour this exists to avoid)
plain = [dict(r, role=None) for r in living + workshop]
assert engine._from_stats(spec, plain, {})["value"] != alone["value"]
print("room role: ok")
