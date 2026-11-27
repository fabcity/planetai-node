"""The node's role is a bootstrap key: fixed at install, read at start, never a settings row.

    PYTHONPATH=app python3 tests/test_roles.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
os.environ.pop("NODE_KIND", None)

import placewords  # noqa: E402
import settings  # noqa: E402

# the four kinds fold to two roles
for k, want in [("home", "private"), ("business", "private"), ("", "private"),
                ("community", "community"), ("district", "community"), (" Community ", "community")]:
    assert placewords.role(k) == want, (k, placewords.role(k))
os.environ["NODE_KIND"] = "district"
assert placewords.role() == "community" and not placewords.is_house()
os.environ["NODE_KIND"] = "home"
assert placewords.role() == "private" and placewords.is_house()

# NODE_KIND is a bootstrap key, not a runtime one
assert "NODE_KIND" not in settings.RUNTIME
assert not settings.writable("NODE_KIND")
assert settings.BOOTSTRAP_GROUP["NODE_KIND"] == "basics"
os.environ["NODE_KIND"] = "community"
row = next(r for r in settings.describe(unlocked=False)["bootstrap"] if r["key"] == "NODE_KIND")
assert "planetai role private" in row["help"] and "Community node" in row["help"], row

# a stale settings row never wins over the environment
real = settings.get
settings.get = lambda k, d="": "home"
try:
    assert placewords.kind() == "community"
finally:
    settings.get = real

# update moves a stray row into .env and deletes it
src = (ROOT / "update.sh").read_text()
assert "NODE_KIND" in src and "DELETE FROM settings WHERE key = 'NODE_KIND'" in src
print("ok  roles")

# ---------------------------------------------------------------- a community node shows no indoor sensor without a token
# Driven as tests/test_share.py drives it: TestClient's peer is not loopback, so a request with no token is a stranger.
try:
    from fastapi.testclient import TestClient
except ImportError:
    print("roles: request checks skipped (pip install -r app/requirements.txt)")
    raise SystemExit(0)
import logging  # noqa: E402
import time  # noqa: E402
logging.disable(logging.WARNING)
os.environ.update(ADMIN_TOKEN="admin-tok", NODE_LAT="-8.6478291", NODE_LON="115.1385412", NODE_NAME="bayu-2",
                  DATABASE_URL="postgresql://unused/never-connected")
settings._cache = {"at": time.time() + 1e9, "rows": {"SHARE_LEVEL": "open"}}
import main  # noqa: E402

assert main._drop_indoor({"sensors": [{"sensor_id": "sc-1"}, {"sensor_id": "sc-2"}],
                          "stats": {"sc-1": {"pm25": 1}, "sc-2": {}}}, {"sc-1"}) == \
    {"sensors": [{"sensor_id": "sc-2"}], "stats": {"sc-2": {}}}
assert main._drop_indoor([{"a": [{"sensor_id": "sc-1"}]}, 3, "x"], {"sc-1"}) == [{"a": []}, 3, "x"]

_IN = {"sensor_id": "ag-in", "source": "airgradient", "name": "Kids", "lat": -8.6, "lon": 115.1, "indoor": True,
       "local": True, "custody": True, "kind": "sensor", "scale": "community", "cadence": "PT5M", "meta": None}
_OUT = dict(_IN, sensor_id="ag-out", name="Garden", indoor=False)
_HOURLY = [{"bucket": "2026-11-25T10:00:00+08:00", "sensor_id": s["sensor_id"], "local": True, "indoor": s["indoor"],
            "kind": "sensor", "scale": "community", "metric": "pm25", "mean": 1.0, "min": 1.0, "max": 1.0, "n": 12}
           for s in (_IN, _OUT)]
main.q = lambda sql, *a: ([dict(r) for r in _HOURLY] if "FROM readings_1h" in sql else
                          [dict(_IN), dict(_OUT)] if "FROM sensors" in sql else [])


class _Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, *a): self.sql = sql
    def fetchall(self): return [{"sensor_id": "ag-in"}] if "indoor" in self.sql else []


class _Con(_Cur):
    def cursor(self): return _Cur()


main.db = lambda: _Con()
main.index.cells = lambda cur: []
main.index.rho = lambda cur: None
client = TestClient(main.app)


def _reset():
    main._INDOOR.update(at=0.0, ids=set()); main._HOUSE.update(at=0.0, map=[])


os.environ["NODE_KIND"] = "community"; _reset()
r = client.get("/sensors")
assert r.status_code == 200 and [s["sensor_id"] for s in r.json()] == ["ag-out"], r.text
assert all(not s.get("indoor") for s in r.json())
assert len(client.get("/sensors", headers={"Authorization": "Bearer admin-tok"}).json()) == 2, "a token reads them all"
assert TestClient(main.app, client=("127.0.0.1", 51000)).get("/sensors").json()[0]["indoor"], "this machine reads them all"
ex = client.get("/export?day=2026-11-25").json()["hourly"]
assert ex and not any(r["sensor"].startswith("indoor-") or r["indoor"] for r in ex), ex
ex = client.get("/export?day=2026-11-25", headers={"Authorization": "Bearer admin-tok"}).json()["hourly"]
assert not any(r["indoor"] for r in ex), "the export travels whoever asked: no indoor row even with a token"

os.environ["NODE_KIND"] = "home"; _reset()
assert any(s.get("indoor") for s in client.get("/sensors").json()), "a private node is unchanged"
assert any(r["sensor"] == "indoor-1" for r in client.get("/export?day=2026-11-25").json()["hourly"])
print("ok  community: no indoor sensor without a token, none in the export; private unchanged")
