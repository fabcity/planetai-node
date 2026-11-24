"""The models container's logic: what it refuses, what it returns, what it does when nothing is pulled.

Run: python3 tests/test_models_server.py
It imports models/core.py only, with a fake pipeline, so it needs neither torch nor fastapi. What is checked is
what fails silently: a NaN that reaches the wire as invalid JSON, a body the model should never see, a pull whose
weights are not the pinned ones, and a core.py that imports torch at the top and takes the whole suite with it.
"""
import hashlib
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
import core  # noqa: E402


class Fake:
    def quantiles(self, series, horizon):
        return [[[0.9, 1.0, 1.1]] * horizon for _ in series]


core.PIPE = Fake()
core.META = {"name": "amazon/chronos-2", "revision": "29ec3766d36d6f73f0696f85560a422f50e8498c"}

# ---- the body: what is refused before the model sees it.
ok = {"series": [[1.0] * 48, [2.0] * 100], "horizon": 48}
assert core.problem(ok) is None
r = core.answer(ok)
assert r["model"] == "amazon/chronos-2" and r["revision"].startswith("29ec3766")
assert r["quantiles"][0][0] == [0.9, 1.0, 1.1] and len(r["quantiles"]) == 2 and len(r["quantiles"][1]) == 48
assert core.problem({"series": [], "horizon": 48})
assert core.problem({"series": [[1.0] * 23], "horizon": 48})
assert core.problem({"series": [[1.0] * 24], "horizon": 48}) is None
assert core.problem({"series": [[1.0] * 48] * 512, "horizon": 48}) is None
assert core.problem({"series": [[1.0] * 48] * 513, "horizon": 48})
assert core.problem({"series": [[1.0] * 48], "horizon": 65})
assert core.problem({"series": [[1.0] * 48], "horizon": 0})
assert core.problem({"series": [[1.0] * 48], "horizon": 1.5})
assert core.problem({"series": [[1.0] * 48], "horizon": True})
assert core.problem({"series": [[1.0] * 48]})
assert core.problem({"series": "abc", "horizon": 48})
assert core.problem([1, 2])

assert core.problem({"series": [[1.0] * 8192], "horizon": 48}) is None
assert "8192" in core.problem({"series": [[1.0] * 8193], "horizon": 48}), "a series longer than 8,192 values is refused"


# ---- batches of 32, in order, one forecast at a time.
class Counting:
    def __init__(self):
        self.calls = []

    def quantiles(self, series, horizon):
        assert core.LOCK.locked(), "the model ran without the lock"
        self.calls.append(len(series))
        return [[[x[0]] * 3] * horizon for x in series]


core.PIPE = Counting()
r = core.answer({"series": [[float(i)] * 24 for i in range(70)], "horizon": 2})
assert core.PIPE.calls == [32, 32, 6], core.PIPE.calls
assert [q[0][0] for q in r["quantiles"]] == [float(i) for i in range(70)], "batches come back in order"
assert not core.LOCK.locked()
core.PIPE = Fake()
_svc = open(os.path.join(ROOT, "docker-compose.yml")).read().split("\n  models:\n")[1].split("\nvolumes:")[0]
assert "\n    mem_limit: 4g\n" in _svc, "the models service has a memory limit"

# ---- a non-finite output is null, never NaN on the wire.
assert core.clean([[float("nan"), 1.0, 2.0]]) == [[None, 1.0, 2.0]]
assert core.clean([[[float("inf"), -float("inf"), 3]]]) == [[[None, None, 3.0]]]
json.dumps(core.clean([[float("nan")]]), allow_nan=False)

# ---- nothing pulled: the server starts, says why, and answers nothing.
core.PIPE = None
assert core.health() == {"ready": False, "model": None, "revision": None, "error": "no model pulled"}
core.ERROR = "boom"
assert core.health()["error"] == "boom"
core.ERROR = None
core.PIPE = Fake()
h = core.health()
assert h["ready"] is True and h["model"] == "amazon/chronos-2" and h["error"] is None
core.PIPE = None

# ---- the weights: only the pinned file, checked before anything serves it.
cat = json.load(open(os.path.join(ROOT, "packs", "predict", "models.json")))
assert set(cat) == {"amazon/chronos-2", "amazon/chronos-bolt-tiny"}
assert core.pinned("nope/unknown", cat) is None and core.pinned("amazon/chronos-2", cat)["kind"] == "chronos2"
data = b"not the weights"
good = {"x/y": {"revision": "r", "sha256": hashlib.sha256(data).hexdigest(), "kind": "bolt"}}


def snapshot(content, folder="models--x--y"):
    """A fake hub cache: <tmp>/<folder>/snapshots/r/model.safetensors, with a sibling model beside it."""
    cache = tempfile.mkdtemp()
    os.makedirs(os.path.join(cache, "models--other--model"))
    snap = os.path.join(cache, folder, "snapshots", "r")
    os.makedirs(snap)
    with open(os.path.join(snap, "model.safetensors"), "wb") as f:
        f.write(content)
    return cache, snap


cache, snap = snapshot(data)
assert core.cache_root("x/y", snap) == core.Path(cache) / "models--x--y"
assert core.verify("x/y", snap, good) is None and os.path.isdir(snap)
cache, snap = snapshot(b"tampered")
assert "sha256" in core.verify("x/y", snap, good)
assert not os.path.exists(os.path.join(cache, "models--x--y")) and os.path.isdir(os.path.join(cache, "models--other--model"))
cache, snap = snapshot(data)
assert "unknown" in core.verify("a/b", snap, good) and os.path.isdir(snap)          # nothing was pulled for it
cache, snap = snapshot(data)
os.remove(os.path.join(snap, "model.safetensors"))
assert core.verify("x/y", snap, good) and not os.path.exists(os.path.join(cache, "models--x--y"))   # no file at all

# a path of another shape removes nothing: one level shorter, or a folder that is not this model's
cache, snap = snapshot(b"tampered")
short = os.path.join(cache, "models--x--y", "snapshots")
assert core.cache_root("x/y", short) is None
assert "nothing removed" in core.verify("x/y", short, good) and os.path.isdir(snap)
cache, snap = snapshot(b"tampered", folder="local_dir")
assert core.cache_root("x/y", snap) is None
assert "nothing removed" in core.verify("x/y", snap, good) and os.path.isdir(snap)
assert os.path.isdir(os.path.join(cache, "models--other--model"))

# ---- remove and have: one model's own folder, a name outside the catalogue refused.
hub = tempfile.mkdtemp()
cat2 = {"x/y": good["x/y"], "x/z": good["x/y"]}
for m in ("x--y", "x--z"):
    os.makedirs(os.path.join(hub, "hub", "models--" + m, "snapshots", "r"))
assert core.have("x/y", cat2, hub) and not core.have("a/b", cat2, hub)
assert core.model_dir("../../etc", cat2, hub) is None and "unknown model" in core.remove("../../etc", cat2, hub)
assert core.remove("x/y", cat2, hub) is None and not core.have("x/y", cat2, hub) and core.have("x/z", cat2, hub)
assert core.remove("x/y", cat2, hub) is None   # already gone is fine


# ---- the shared store: huggingface_hub 2.x keeps the files in <hub>/blobs and the model's folder only links into
# them (node #1, 23 Nov: rm left 456 MB there and the next pull "downloaded" it in 4 s). remove and a failed verify
# drop this model's files from the store too, and nothing another model still links to.
def shared(content):
    h = os.path.join(tempfile.mkdtemp(), "hub")
    for m, name, body in (("x--y", "ab", content), ("x--y", "cd", b"config"), ("x--z", "cd", b"config")):
        os.makedirs(os.path.join(h, "blobs", name[:1]), exist_ok=True)
        with open(os.path.join(h, "blobs", name[:1], name), "wb") as f:
            f.write(body)
        snap = os.path.join(h, "models--" + m, "snapshots", "r")
        os.makedirs(snap, exist_ok=True)
        os.symlink(os.path.join("..", "..", "..", "blobs", name[:1], name),
                   os.path.join(snap, "model.safetensors" if name == "ab" else "config.json"))
    return h, os.path.join(h, "models--x--y", "snapshots", "r")

h, snap = shared(data)
assert core.verify("x/y", snap, good) is None and os.path.isfile(os.path.join(h, "blobs", "a", "ab"))
assert core.remove("x/y", cat2, os.path.dirname(h)) is None
assert not os.path.exists(os.path.join(h, "blobs", "a", "ab"))                     # its weights are gone
assert os.path.isfile(os.path.join(h, "blobs", "c", "cd")) and core.have("x/z", cat2, os.path.dirname(h))  # x/z's stay
h, snap = shared(b"tampered")
assert "sha256" in core.verify("x/y", snap, good) and not os.path.exists(os.path.join(h, "blobs", "a", "ab"))
assert os.path.isfile(os.path.join(h, "blobs", "c", "cd"))

# ---- the seam: torch and chronos are imported inside load(), never at the top.
src = open(os.path.join(ROOT, "models", "core.py")).read()
assert "\nimport torch" not in src and "\nfrom chronos" not in src and "\nimport numpy" not in src

# ---- load() with no MODEL set stays quiet; an unknown one fails into ERROR and leaves PIPE None.
os.environ.pop("MODEL", None)
core.CATALOGUE = os.path.join(ROOT, "packs", "predict", "models.json")
core.load()
assert core.PIPE is None and core.ERROR is None and core.health()["error"] == "no model pulled"
os.environ["MODEL"] = "nope/unknown"
core.load()
assert core.PIPE is None and "unknown" in core.ERROR

print("  ok: models core (refusals, nulls, health, pinned weights, lazy imports)")
sys.exit(0)
