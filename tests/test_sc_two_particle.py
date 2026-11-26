"""packs/smartcitizen: a box with two particle sensors keeps both.

Until 22 Nov 2026 the adapter mapped a measurement by its name, so a device with a Seeed HM-3301 and a Sensirion SEN5X
wrote two rows with one key, (sc-<kit>, pm25, ts). The insert keeps the row already there, so the first one the API
listed was stored and the other dropped, with no log line. One box read 5.0 on the HM-3301 and 12.6 on the SEN5X that
afternoon, and the node showed 5.0.

What must hold now: the sensor that had `pm25` keeps it, under the same sensor id, so history, rules and the Index
cells read the series they always read; any other known particle sensor in the box is stored beside it as
`pm25_<model>` (and pm1, pm10), declared `private`; a second sensor's reading carries its own sensor's time, so one
that has gone quiet is not written again as fresh; and the adapter never hands the insert two rows with one key.

Shapes are the two devices as api.smartcitizen.me answered on 22 Nov 2026, and the DIY firmware v5 message
(makingsensebali hardware/diy-node/firmware: BME68X, then HM-3301, then SEN5X, then PMS5003).

    PACKS_DIR=packs PYTHONPATH=app python3 tests/test_sc_two_particle.py
"""
import importlib.util
import json
import os
import time
from collections import Counter

import yaml

os.environ.update(PACKS_DIR="packs", NODE_LAT="")
import settings  # noqa: E402

settings._cache = {"at": time.time() + 1e9, "rows": {"SC_FORWARD": ""}}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


sc = load("sc_adapter", "packs/smartcitizen/adapter.py")
hooks = load("sc_hooks", "packs/smartcitizen/hooks.py")

NOW, OCT = "2026-11-22T07:32:01Z", "2026-10-29T04:33:34Z"


def sensor(sid, name, measurement, value, at=NOW):
    return {"id": sid, "name": name, "measurement": {"name": measurement}, "value": value, "last_reading_at": at}


HM = [sensor(233, "Seeed HM-3301 - PM1.0", "PM1", 4.0), sensor(235, "Seeed HM-3301 - PM10.0", "PM10", 5.0),
      sensor(234, "Seeed HM-3301 - PM2.5", "PM2.5", 5.0)]
SEN = [sensor(203, "Sensirion SEN5X - Humidity", "Relative Humidity", 70.2), sensor(193, "Sensirion SEN5X - PM1", "PM1", 12.1),
       sensor(196, "Sensirion SEN5X - PM10", "PM10", 12.6), sensor(194, "Sensirion SEN5X - PM2.5", "PM2.5", 12.6),
       sensor(204, "Sensirion SEN5X - Temperature", "Air Temperature", 29.785)]
PMS = [sensor(119, "PMS5003_HUM", "Relative Humidity", 62.9), sensor(118, "PMS5003_TEMP", "Air Temperature", 25.3),
       sensor(89, "Plantower PMS5003 - PM1", "PM1", 3.0), sensor(88, "Plantower PMS5003 - PM10", "PM10", 8.0),
       sensor(87, "Plantower PMS5003 - PM2.5", "PM2.5", 7.0)]
BME = [sensor(238, "Bosch BME68X - Humidity", "Relative Humidity", 73.4), sensor(237, "Bosch BME68X - Temperature", "Air Temperature", 27.5)]


class HC:
    def __init__(s, sensors): s.sensors = sensors
    def get(s, url, timeout=None):
        return type("R", (), {"raise_for_status": lambda r: None, "json": lambda r: {
            "name": "box", "last_reading_at": NOW, "location": {"exposure": "indoor", "latitude": 0.0, "longitude": 0.0},
            "data": {"sensors": s.sensors}}})()


def read(sensors, kit=1001):
    s, r = sc.smartcitizen(HC(sensors), [kit])
    assert [x["sensor_id"] for x in s] == [f"sc-{kit}"], "one box is one sensor row, as it always was"
    keys = Counter((sid, m, ts) for ts, sid, m, _ in r)
    assert max(keys.values()) == 1, f"two rows with one key, and the insert keeps only the first: {[k for k, n in keys.items() if n > 1]}"
    return {m: (v, ts.isoformat().replace("+00:00", "Z")) for ts, _, m, v in r}


# ---- 1. a box with an HM-3301 and a SEN5X. Both kept; the HM-3301 keeps the plain names.
got = read(HM + SEN)
assert {m: v for m, (v, _) in got.items() if m.startswith("pm")} == {
    "pm1": 4.0, "pm25": 5.0, "pm10": 5.0, "pm1_sen5x": 12.1, "pm25_sen5x": 12.6, "pm10_sen5x": 12.6}, got
assert read(list(reversed(HM + SEN))) == got, "which sensor keeps pm25 must not depend on the order the API sends"
print("two particle sensors: both stored, the one that had pm25 keeps it, whatever order the API lists them in")

# ---- 2. a box with three particle sensors, one of them quiet since 29 Oct, and three thermometers.
got = read(BME + PMS + [dict(x, value=v, last_reading_at=OCT) for x, v in zip(HM, (11.0, 18.0, 16.0))] + SEN, kit=1002)
assert (got["pm25"], got["pm25_sen5x"]) == ((7.0, NOW), (12.6, NOW)), got
assert got["pm25_hm3301"] == (16.0, OCT), "a sensor that stopped on 29 Oct was written again as a reading of today"
assert (got["temp"][0], got["humidity"][0]) == (27.5, 73.4), "temperature and humidity stay the sensor they were (not in this change)"
assert not [m for m in got if m.startswith(("temp_", "humidity_"))], got
# the plain channels keep the kit's time, as they always have: trust/channel_dead (config/rules.yml) finds a dead
# channel under a live kit by the flat day that draws, and would go blind to Smart Citizen kits without it
assert read([dict(x, last_reading_at=OCT) for x in HM])["pm25"] == (5.0, NOW)
print("three particle sensors: three series; a quiet second sensor keeps its own last time, a plain channel the kit's")

# ---- 3. a box with one particle sensor is stored exactly as before, whichever sensor it is
for one in (HM, SEN, PMS):
    assert sorted(m for m in read(one) if m.startswith("pm")) == ["pm1", "pm10", "pm25"], one[0]["name"]
# and a second sensor nobody has named is dropped as before: an undeclared metric would leave the node as public
got = read(HM + [sensor(900, "Zeta X1 - PM2.5", "PM2.5", 99.0)])
assert got["pm25"][0] == 5.0 and sorted(got) == ["pm1", "pm10", "pm25"], got
print("one particle sensor: unchanged. An unknown second one: dropped, never a metric with no declared role")

# ---- 4. the direct path: a DIY node on firmware v5 publishing HM-3301 and SEN5X to this node's broker
def wire(token, *ids):
    vals = {237: 28.3, 233: 4.0, 234: 9.0, 235: 11.0, 193: 6.6, 194: 6.9, 196: 7.1, 89: 3.0, 87: 7.0, 88: 8.0}
    msg = {"data": [{"recorded_at": NOW, "sensors": [{"id": i, "value": vals[i]} for i in ids]}]}
    _, r, _ = hooks.smartcitizen_mqtt(f"device/sck/{token}/readings", json.dumps(msg).encode())
    assert len({(sid, m, ts) for ts, sid, m, _ in r}) == len(r), r
    return {m: v for _, _, m, v in r}


both = wire("tok-both", 237, 233, 234, 235, 193, 194, 196)
assert both == {"temp": 28.3, "pm1": 4.0, "pm25": 9.0, "pm10": 11.0, "pm1_sen5x": 6.6, "pm25_sen5x": 6.9, "pm10_sen5x": 7.1}, both
assert wire("tok-sen", 193, 194, 196) == {"pm1": 6.6, "pm25": 6.9, "pm10": 7.1}, "a kit with only a SEN5X keeps the plain names"
assert wire("tok-pms", 193, 194, 196, 89, 87, 88)["pm25_pms5003"] == 7.0
print("direct path: both stored, the first the firmware sends keeps the plain names")

# ---- 5. every metric this can write is declared private for both sources: stays on the node, out of the export,
#         the push to a parent, the Index counts and an agent's reads (packs.public_sql)
NEW = {f"{m}_{model}" for m in ("pm1", "pm25", "pm10") for model in ("sen5x", "hm3301", "pms5003")}
roles = {(c["source"], c["metric"]): c["role"] for c in yaml.safe_load(open("config/channels.yml"))}
for source in ("smartcitizen", "smartcitizen-direct"):
    assert {m for m in NEW if roles.get((source, m)) == "private"} == NEW, f"{source}: {sorted(NEW)} must all be private"
assert roles[("smartcitizen", "pm25")] == "ambient", "the plain channels are what they were"
assert NEW <= set(yaml.safe_load(open("packs/smartcitizen/pack.yaml"))["metrics"]), "the pack's card lists what it can write"

# ---- 6. and the page has a word for each (new features are visible)
js = open("app/static/doors-data.js").read()
assert all(f"{m}: '" in js for m in NEW), [m for m in NEW if f"{m}: '" not in js]
print("the second sensors: private on both sources, on the pack's card, named on the Data door")
print("sc two particle: every check passed")
