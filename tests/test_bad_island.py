"""packs/bali-air-dispatch: the island's stations, kept beside the ring for the Wall's city scale.

Run: PACKS_DIR=packs PYTHONPATH=/tmp/stub:app python3 tests/test_bad_island.py
island() is pure; write_island() keeps out/wall/island.json whole each poll and reads /stations at most once a day.
"""
import importlib.util
import json
import os
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = tempfile.mkdtemp()
os.environ["PACK_OUT"] = OUT
_spec = importlib.util.spec_from_file_location("bad_adapter", ROOT / "packs/bali-air-dispatch/adapter.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def row(sid, name, pm25=20.0, **kw):
    r = {"station_id": sid, "name": name, "source": "IQAir", "latitude": -8.6512345, "longitude": 115.2166789,
         "observed_at": "2026-11-18T03:00:00.000Z", "age_hours": 0.5, "stale": False, "pm25": pm25,
         "suspected_indoor": False, "suspected_malfunctioning": False}
    r.update(kw)
    return r


rows = [
    row("ok-1", "Sanur", latitude=-8.6789012, longitude=115.2634567),
    row("old", "Stale one", stale=True),
    row("in", "Indoor one", suspected_indoor=True),
    row("bad", "Broken one", suspected_malfunctioning=True),
    row("none", "No pm25", pm25=None),
    row("aq--519205", "Kabupaten Badung Sempidi", source="AQICN"),
    row("iqs-kabupaten-badung-sempidi", "Kabupaten Badung Sempidi"),
]
stations = {
    "aq--519205": {"type": "Government (KLHK)", "same_device_as": ["iqs-kabupaten-badung-sempidi"]},
    "iqs-kabupaten-badung-sempidi": {"type": "Scraped station", "same_device_as": ["aq--519205"]},
    "ok-1": {"type": "Community", "same_device_as": []},
}
items = B.island(rows, stations)
assert len(items) == 2, items                       # ok-1, and Sempidi once
by = {i["network"]: i for i in items}
sem = by["AQICN"]                                    # the official row is the one kept
assert sem["official"] is True and sem["place"] == "Kabupaten Badung Sempidi"
ok = [i for i in items if not i["official"]][0]
assert ok["place"] is None and ok["pm25"] == 20.0 and ok["at"].startswith("2026-11-18T03:00:00")
for i in items:
    assert set(i) == {"lat", "lon", "pm25", "at", "network", "official", "place"}
    for k in ("lat", "lon"):
        assert round(i[k], 3) == i[k], i
# the same pair named only from one side still gives one item; no /stations at all marks nothing official
one_sided = {"aq--519205": {"type": "Government (KLHK)", "same_device_as": []},
             "iqs-kabupaten-badung-sempidi": {"type": "Scraped station", "same_device_as": ["aq--519205"]}}
assert len(B.island(rows, one_sided)) == 2
assert not any(i["official"] for i in B.island(rows, {}))

# ---- the file: written whole, /stations read at most once a day, a failed read keeps yesterday's
class R:
    def __init__(s, j): s.j = j
    def raise_for_status(s): pass
    def json(s): return s.j


class HC:
    def __init__(s, fail=False): s.calls, s.fail = [], fail
    def get(s, url, **kw):
        s.calls.append(url)
        if s.fail and url == B.STATIONS:
            raise RuntimeError("down")
        return R({"stations": [dict(station_id=k, **v) for k, v in stations.items()]})


hc = HC()
B.write_island(hc, rows)
f = Path(OUT) / "wall" / "island.json"
d = json.loads(f.read_text())
assert len(d["items"]) == 2 and d["at"] and any(i["official"] for i in d["items"])
assert not list((Path(OUT) / "wall").glob("*.part")), "tmp file replaced, not left"
B.write_island(hc, rows)
assert hc.calls.count(B.STATIONS) == 1, "/stations is read at most once a day"
old = time.time() - 2 * 86400
cache = Path(OUT) / "wall" / "bad-stations.json"
os.utime(cache, (old, old))
down = HC(fail=True)
B.write_island(down, rows)
assert down.calls.count(B.STATIONS) == 1
assert any(i["official"] for i in json.loads(f.read_text())["items"]), "yesterday's stations still stand"
cache.unlink()
B.write_island(down, rows)
assert not any(i["official"] for i in json.loads(f.read_text())["items"]), "nothing official without a list"
print("test_bad_island: ok")
