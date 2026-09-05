"""Offline adapter tests against saved payload shapes. Run: PYTHONPATH=/tmp/stub:app python3 tests/test_sources.py
(stub httpx first: mkdir -p /tmp/stub && echo "class Client: pass" > /tmp/stub/httpx.py)"""
import sources

class R:
    def __init__(s, j): s.j = j
    def raise_for_status(s): pass
    def json(s): return s.j
class HC:
    def __init__(s, j): s.j = j
    def get(s, url, timeout=None): return R(s.j)

sc = {"name": "Bayu 2 - Indoor", "state": "has_published", "last_reading_at": "2026-09-02T03:11:31Z", "hardware": {"name": "Unknown"},
      "location": {"exposure": "indoor", "latitude": -8.8271, "longitude": 115.15709},
      "data": {"recorded_at": "2026-09-02T03:11:31Z", "sensors": [
          {"id": 234, "measurement": {"name": "PM2.5"}, "value": 7.0}, {"id": 237, "measurement": {"name": "Air Temperature"}, "value": 30.4},
          {"id": 238, "measurement": {"name": "Relative Humidity"}, "value": 63.5}, {"id": 999, "measurement": {"name": "Unknown"}, "value": 1}]}}
s, r = sources.smartcitizen(HC(sc), [19880])
assert s[0]["sensor_id"] == "sc-19880" and s[0]["indoor"] and s[0]["local"]
assert {m for _, _, m, _ in r} == {"pm25", "temp", "humidity"}

bad = {"readings": [
    {"station_id": "pa-46949", "name": "Klungkung", "source": "PurpleAir", "latitude": -8.533623, "longitude": 115.39973, "observed_at": "2026-08-01T20:15:11.000Z", "stale": False, "pm25": 36.6, "pm25_raw": 47.8},
    {"station_id": "aq-1", "name": "Denpasar", "source": "AQICN", "latitude": -8.63, "longitude": 115.21, "observed_at": "2026-06-03T08:45:39.000Z", "stale": True, "pm25": 168},
    {"station_id": "iqs-x", "name": "Jimbaran villa", "source": "IQAir", "latitude": -8.79, "longitude": 115.16, "observed_at": "2026-09-02T02:00:00Z", "stale": False, "pm25": 22.0, "suspected_indoor": True}]}
s, r = sources.baliairdispatch(HC(bad), -8.8271, 115.15709, 15)
ids = {x["sensor_id"] for x in s}
assert "bad-aq-1" not in ids, "stale must be dropped"
assert "bad-pa-46949" not in ids, "42 km away must be outside a 15 km radius"
assert "bad-iqs-x" in ids and [x for x in s if x["sensor_id"] == "bad-iqs-x"][0]["indoor"]

# a Smart Citizen kit the node polls itself must not come back a second time via BAD (it was: sc-19236 and
# bad-sc-19236 were both counted in the ambient average, with BAD's indoor flag disagreeing with Smart Citizen's)
bad2 = {"readings": [
    {"station_id": "sc-19236", "name": "Ungasan Kit", "source": "Smart Citizen", "latitude": -8.8198, "longitude": 115.1666, "observed_at": "2026-09-05T02:00:00Z", "stale": False, "pm25": 7.0},
    {"station_id": "sc-19760", "name": "Bayu Sensor", "source": "Smart Citizen", "latitude": -8.8100, "longitude": 115.1600, "observed_at": "2026-09-05T02:00:00Z", "stale": False, "pm25": 8.0}]}
s, r = sources.baliairdispatch(HC(bad2), -8.8271, 115.15709, 15, skip_station_ids={"sc-19236"})
ids = {x["sensor_id"] for x in s}
assert "bad-sc-19236" not in ids, "a kit this node reads directly must be skipped from BAD"
assert "bad-sc-19760" in ids, "someone else's kit still comes through BAD"

ag = {"serialno": "84fce612a5b4", "rco2": 612, "pm01": 4, "pm02": 9, "pm10": 11, "atmp": 29.4, "rhum": 61, "tvocIndex": 98, "noxIndex": 1, "firmware": "3.1.9", "model": "I-9PSL"}
s, r = sources.airgradient(HC(ag), ["airgradient_84fce6.local"], -8.65, 115.22, False)
m = {k: v for _, _, k, v in r}
assert s[0]["sensor_id"] == "ag-84fce612a5b4" and m["pm25_raw"] == 9.0 and 4 < m["pm25"] < 7 and m["co2"] == 612

pa = {"SensorId": "84:f3:eb:12:34:56", "Geo": "PurpleAir-3456", "lat": -8.53, "lon": 115.40, "pm2_5_cf_1": 47.8, "pm2_5_cf_1_b": 46.9, "pm10_0_cf_1": 52.1, "current_humidity": 62, "current_temp_f": 94, "pressure": 1006.2}
s, r = sources.purpleair(HC(pa), ["192.168.1.60"], None, None, False)
m = {k: v for _, _, k, v in r}
assert s[0]["sensor_id"] == "pa-84f3eb123456" and 34 < m["pm25"] < 38, "EPA correction of ~47 raw @62% RH should land ~36 (BAD's Klungkung row)"
assert abs(m["temp"] - 34.4) < 0.1 and abs(m["pressure"] - 100.62) < 0.01

assert round(sources.epa_2021_correct(28, 65), 1) == 14.8   # BAD's worked example: raw 28 -> ~15
print("all adapter tests pass")
