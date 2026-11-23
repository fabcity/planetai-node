"""The models container's logic. Standard library only at the top: torch and chronos are imported inside load(),
so the test suite runs without them and a node that never starts this container never pays for them.

The server (server.py) maps problem/answer/health onto HTTP; pull.py uses pinned/verify. Nothing here touches
the network except load(), which reads weights already on disk (HF_HUB_OFFLINE=1 in compose).
"""
import hashlib
import json
import math
import os
import shutil
import threading
from pathlib import Path

CATALOGUE = "/srv/models.json"
QUANTILES = [0.1, 0.5, 0.9]
MIN_VALUES, MAX_VALUES, MAX_SERIES, MAX_HORIZON = 24, 8192, 512, 64
BATCH = 32          # series per call into the model: memory grows with the series in one call
LOCK = threading.Lock()     # one forecast at a time, so two requests cannot hold the model's memory twice

PIPE = None     # an object with quantiles(series, horizon) -> [[[p10, p50, p90] x horizon] per series]
META = None     # {"name": ..., "revision": ...} of what PIPE is
ERROR = None    # why PIPE is None, when loading was tried and failed


def problem(body):
    """The reason a request body is refused, or None."""
    if not isinstance(body, dict):
        return "body must be an object"
    s, h = body.get("series"), body.get("horizon")
    if not isinstance(s, list) or not s:
        return "series must be a non-empty list"
    if len(s) > MAX_SERIES:
        return f"at most {MAX_SERIES} series"
    if not all(isinstance(x, list) and len(x) >= MIN_VALUES for x in s):
        return f"every series needs at least {MIN_VALUES} values"
    if any(len(x) > MAX_VALUES for x in s):
        return f"a series has at most {MAX_VALUES} values"
    if isinstance(h, bool) or not isinstance(h, int) or not 1 <= h <= MAX_HORIZON:
        return f"horizon must be a whole number from 1 to {MAX_HORIZON}"
    return None


def clean(q):
    """Nested lists with every non-finite number as None, so the JSON is valid."""
    if isinstance(q, list):
        return [clean(x) for x in q]
    return float(q) if math.isfinite(q) else None


def health():
    if PIPE is None:
        return {"ready": False, "model": None, "revision": None, "error": ERROR or "no model pulled"}
    return {"ready": True, "model": META["name"], "revision": META["revision"], "error": None}


def answer(body):
    """The forecast, BATCH series at a time and one request at a time, in the order the series came."""
    s, h = body["series"], body["horizon"]
    with LOCK:
        q = [x for i in range(0, len(s), BATCH) for x in PIPE.quantiles(s[i:i + BATCH], h)]
    return {"model": META["name"], "revision": META["revision"], "quantiles": clean(q)}


class _Chronos2:
    """Chronos-2 takes a list of arrays and gives back one (1, H, 3) tensor per series."""
    def __init__(self, pipe):
        self.pipe = pipe

    def quantiles(self, series, horizon):
        import numpy
        q, _ = self.pipe.predict_quantiles([numpy.asarray(s, dtype="float32") for s in series],
                                           prediction_length=horizon, quantile_levels=QUANTILES)
        return [t[0].tolist() for t in q]


class _Bolt:
    """Bolt takes a list of tensors and gives back one (n, H, 3) tensor."""
    def __init__(self, pipe):
        self.pipe = pipe

    def quantiles(self, series, horizon):
        import torch
        q, _ = self.pipe.predict_quantiles([torch.tensor(s, dtype=torch.float32) for s in series],
                                           prediction_length=horizon, quantile_levels=QUANTILES)
        return q.tolist()


def pinned(name, cat):
    """The catalogue entry for a model, or None when the name is not in it."""
    return cat.get(name)


def load():
    """Load $MODEL from the weights on disk. A failure is kept in ERROR and the server still starts."""
    global PIPE, META, ERROR
    PIPE, META, ERROR = None, None, None
    name = os.environ.get("MODEL", "")
    if not name:
        return
    try:
        entry = pinned(name, json.load(open(CATALOGUE)))
        if entry is None:
            raise ValueError(f"unknown model {name}")
        import torch  # noqa: F401  (a failed import is a failed load, reported through /health)
        from chronos import ChronosBoltPipeline, Chronos2Pipeline
        cls, wrap = (Chronos2Pipeline, _Chronos2) if entry["kind"] == "chronos2" else (ChronosBoltPipeline, _Bolt)
        pipe = cls.from_pretrained(name, revision=entry["revision"], device_map="cpu")
        PIPE, META = wrap(pipe), {"name": name, "revision": entry["revision"]}
    except Exception as e:
        ERROR = f"{type(e).__name__}: {e}"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def cache_root(name, snapshot):
    """The hub's folder for this one model, `snapshot`'s grandparent, or None when the path is not shaped
    <cache>/models--org--name/snapshots/<rev>. Only this folder is ever removed."""
    root = Path(snapshot).parent.parent
    return root if Path(snapshot).parent.name == "snapshots" and root.name == "models--" + name.replace("/", "--") else None


def model_dir(name, cat, hf_home=None):
    """This catalogue model's own folder in the hub cache, or None for a name the catalogue does not have."""
    if pinned(name, cat) is None:
        return None
    return Path(hf_home or os.getenv("HF_HOME", "/weights")) / "hub" / ("models--" + name.replace("/", "--"))


def have(name, cat, hf_home=None):
    root = model_dir(name, cat, hf_home)
    return root is not None and (root / "snapshots").is_dir()


def remove(name, cat, hf_home=None):
    """None when the model's own folder is gone (or never was); otherwise the reason. Nothing else is touched."""
    root = model_dir(name, cat, hf_home)
    if root is None:
        return f"unknown model {name}; the catalogue has: {', '.join(cat)}"
    drop(root)
    return None


def drop(root):
    """Remove one model's folder and the files it links to in the hub's shared store (huggingface_hub 2.x keeps
    them in <hub>/blobs), unless another model's folder still links to the same file. Nothing outside the hub."""
    hub = Path(root).resolve().parent
    def links(d):
        return {p.resolve() for p in Path(d).rglob("*") if p.is_symlink()}
    mine = links(root) if Path(root).is_dir() else set()
    shutil.rmtree(root, ignore_errors=True)
    kept = set().union(*(links(d) for d in hub.glob("models--*")))
    for f in mine - kept:
        if hub in f.parents and f.is_file():
            f.unlink()


def verify(name, snapshot, cat):
    """None when the snapshot's model.safetensors is the pinned file; otherwise the reason, and the model's own
    cache folder is removed so a wrong file is never left where load() would find it. A snapshot path of any
    other shape removes nothing."""
    entry = pinned(name, cat)
    root = cache_root(name, snapshot)
    try:
        if entry is None:
            err = f"unknown model {name}"
        elif root is None:
            return f"{name}: unexpected snapshot path {snapshot}; nothing removed"
        elif sha256_of(Path(snapshot) / "model.safetensors") != entry["sha256"]:
            err = f"{name}: model.safetensors sha256 differs from the catalogue"
        else:
            return None
    except OSError as e:
        err = f"{name}: {e}"
    if root is not None:
        drop(root)
    return err
