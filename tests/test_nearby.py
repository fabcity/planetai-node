"""The ring: which Bali Air Dispatch stations are this node's neighbours, and which are its own kit read twice.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_nearby.py
Against tests/data/bad_*_2026-09-07.json — the archive as it answered on 7 September 2026, saved whole, not
numbers typed into a test. Every exclusion below fires on a real station; none of them needed a crafted case.
"""
import json
import os

import sources

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAT, LON = -8.8271, 115.15709          # node #1, bayu-2, Ungasan
# the Smart Citizen kits node #1 polls itself: SC_USER=tomasdiez, state has_published, seen in the last 3 days
POLLED = {"sc-19898", "sc-19880", "sc-19849", "sc-19874", "sc-19897", "sc-19236"}


def fixture(name):
    with open(os.path.join(ROOT, "tests/data", name)) as f:
        return json.load(f)


latest = fixture("bad_latest_2026-09-07.json")["readings"]
stations = {s["station_id"]: s for s in fixture("bad_stations_2026-09-07.json")["stations"]}
assert len(latest) == 84 and len(stations) == 87, "the fixture is the archive as it stood, 84 of 87 with a reading"

v = dict((r["station_id"], w) for r, w in sources.bad_verdicts(latest, LAT, LON, 15.0, POLLED))

# ---- identity. sc-19236 is "Ungasan Kit", 1.3 km away: no distance rule would ever catch it, and the node reads
# it directly, so the ring would be this node arguing with itself.
assert v["sc-19236"].startswith("excluded: identity"), v["sc-19236"]
assert v["sc-19898"].startswith("excluded: identity"), "a kit of ours 7 km away is still a kit we read twice"

# ---- proximity. sc-19835 ("Bayu Kit") sits 10 m from the node and is NOT on the account the node polls, so
# identity misses it entirely. This is the rule that catches it, and it is why identity alone is not enough.
assert v["sc-19835"].startswith("excluded: proximity"), v["sc-19835"]
assert "sc-19835" not in POLLED, "the case only means something while this kit is not one we poll"

# ---- by hand
byhand = dict((r["station_id"], w) for r, w in sources.bad_verdicts(latest, LAT, LON, 15.0, POLLED, {"sc-19760"}))
assert byhand["sc-19760"] == "excluded: by hand (BAD_EXCLUDE)", byhand["sc-19760"]
assert v["sc-19760"] == "included", "and without the hand list it is a neighbour, not a duplicate"

# ---- quality flags, each on the station that actually carries it. Ownership and radius are decided first, so
# the only station flagged malfunctioning (33 km away) is read from the wide view.
wide = dict((r["station_id"], w) for r, w in sources.bad_verdicts(latest, LAT, LON, 50.0, POLLED))
assert wide["iq-kopernik"] == "excluded: suspected_malfunctioning", wide["iq-kopernik"]
assert v["iqs-jimbaran-s"] == "excluded: suspected_indoor", v["iqs-jimbaran-s"]
assert v["sc-19618"].startswith("excluded: stale"), v["sc-19618"]
assert v["pa-46949"] == "excluded: beyond the radius", "42 km is not this node's ring"

# ---- one device, one row. The archive does NOT dedupe OpenAQ against AirGradient: 23 units appear twice, same
# coordinates, same name. A ring median over both rows weights those devices double.
assert wide["ag-197980"] == "included", "keep the direct network"
assert wide["oq-6432409"] == "excluded: same device as ag-197980", wide["oq-6432409"]
mirrors = [k for k, w in wide.items() if w.startswith("excluded: same device")]
assert len(mirrors) >= 20, f"only {len(mirrors)} mirrors collapsed; the archive had 23 on 7 Sep"
assert all(m.startswith(sources.BAD_MIRROR_PREFIXES) for m in mirrors), "the mirror is dropped, never the direct row"
# not only OpenAQ: AQICN republishes an IQAir station at Sempidi under its own id.
assert wide["aq--519205"] == "excluded: same device as iqs-kabupaten-badung-sempidi", wide["aq--519205"]

# three Smart Citizen kits sit 25 m apart at Kios Utak Atik under different names. Same place, different devices:
# collapsing them would delete real sensors, which is why the rule needs the name and not just the distance.
assert not wide["sc-19762"].startswith("excluded: same device"), wide["sc-19762"]

# ---- an external station is never `local`, at any distance. sc-19835 ("Bayu Kit") sits at node #1's exact
# coordinates and stopped reporting on 16 August; whatever it is, the node must never count it as its own
# measurement. Pinned where `local` is actually decided: stamp_local only ever narrows, so a row the adapter
# did not claim cannot be widened into the house by being close.
ring = {"station_id": "x-40m", "name": "forty metres away", "source": "IQAir",
        "latitude": LAT + 40 / 111_320.0, "longitude": LON,
        "observed_at": "2026-09-07T13:00:00Z", "stale": False, "pm25": 9.1}


class _R:
    def __init__(self, j): self.j = j
    def raise_for_status(self): pass
    def json(self): return self.j


class _HC:
    def __init__(self, j): self.j = j
    def get(self, url, timeout=None): return _R(self.j)


s, r = sources.baliairdispatch(_HC({"readings": [ring]}), LAT, LON, 15.0, min_separation_m=10.0)
assert len(s) == 1 and s[0]["local"] is False, "a station 40 m away is a neighbour, not this node's own kit"
assert 39 < sources.metres(LAT, LON, ring["latitude"], ring["longitude"]) < 41
sources.stamp_local(s, LAT, LON, 500.0)
assert s[0]["local"] is False, "stamp_local only ever narrows: an unclaimed sensor never becomes local"
assert [m for _, _, m, _ in r] == ["pm25"] and s[0]["meta"]["attribution"].startswith("Bali Air Dispatch")

# ---- what the ring at node #1 actually is. This is the finding, pinned so it cannot quietly change.
inc = [k for k, w in v.items() if w == "included"]
assert len(inc) == 6, f"node #1 had 6 real neighbours at 15 km on 7 Sep, got {len(inc)}"
near = min(sources.km(LAT, LON, stations[k]["latitude"], stations[k]["longitude"]) for k in inc)
assert 3.7 < near < 3.9, f"the nearest neighbour was 3.81 km, got {near:.2f}"

print("test_nearby: ok —", len(inc), "included,", len(latest) - len(inc), "excluded at 15 km")
