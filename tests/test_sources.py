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
          {"id": 238, "measurement": {"name": "Relative Humidity"}, "value": 63.5}, {"id": 241, "measurement": {"name": "AQI"}, "value": 55},
          {"id": 999, "measurement": {"name": "Unknown"}, "value": 1}]}}
s, r = sources.smartcitizen(HC(sc), [19880])
assert s[0]["sensor_id"] == "sc-19880" and s[0]["indoor"] and s[0]["local"]
# the Smart Citizen "AQI" channel is `Bosch BME68X - AQI`, the BME680's own gas index, not an air quality index.
# Stored as `aqi` it sat in the same column as IQAir's real AQI from Bali Air Dispatch.
assert {m for _, _, m, _ in r} == {"pm25", "temp", "humidity", "bme_iaq"}
assert "aqi" not in {m for _, _, m, _ in r}, "our kits must not publish a metric named aqi"

bad = {"readings": [
    {"station_id": "pa-46949", "name": "Klungkung", "source": "PurpleAir", "latitude": -8.533623, "longitude": 115.39973, "observed_at": "2026-08-01T20:15:11.000Z", "stale": False, "pm25": 36.6, "pm25_raw": 47.8},
    {"station_id": "aq-1", "name": "Denpasar", "source": "AQICN", "latitude": -8.63, "longitude": 115.21, "observed_at": "2026-06-03T08:45:39.000Z", "stale": True, "pm25": 168},
    {"station_id": "iqs-x", "name": "Jimbaran villa", "source": "IQAir", "latitude": -8.79, "longitude": 115.16, "observed_at": "2026-09-02T02:00:00Z", "stale": False, "pm25": 22.0, "suspected_indoor": True}]}
s, r = sources.baliairdispatch(HC(bad), -8.8271, 115.15709, 15)
ids = {x["sensor_id"] for x in s}
assert "bad-aq-1" not in ids, "stale must be dropped"
assert "bad-pa-46949" not in ids, "42 km away must be outside a 15 km radius"
# a station the archive suspects is indoors is not the street, so it is dropped by default. It is still a real
# station someone may want, so BAD_INCLUDE_INDOOR=1 brings it back with the flag intact.
assert "bad-iqs-x" not in ids, "suspected_indoor is dropped by default"
s2, _ = sources.baliairdispatch(HC(bad), -8.8271, 115.15709, 15, include_indoor=True)
assert [x for x in s2 if x["sensor_id"] == "bad-iqs-x"][0]["indoor"]

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

# `local` is ours AND here. An adapter says whether a sensor is ours; distance says whether it is at this node.
# Node #1 moved to Ungasan and kept three kits 1.2 km away marked local, so its "house" was three kits in
# another building and it had no local outdoor sensor at all.
assert round(sources.metres(-8.8190516, 115.1644423, -8.81983, 115.16657)) == 250, "sc-19236 is 250 m from node #1"
assert round(sources.metres(-8.8190516, 115.1644423, -8.8271, 115.15709)) == 1207, "the indoor cluster is 1.2 km away"
assert sources.metres(-8.8190516, 115.1644423, -8.8190516, 115.1644423) == 0.0

NODE = (-8.8190516, 115.1644423)
here     = {"sensor_id": "sc-19236", "local": True,  "lat": -8.81983, "lon": 115.16657}
far      = {"sensor_id": "sc-19880", "local": True,  "lat": -8.8271,  "lon": 115.15709}
theirs   = {"sensor_id": "bad-x",    "local": False, "lat": -8.81985, "lon": 115.16650}
nocoords = {"sensor_id": "msh-abc",  "local": True,  "lat": None,     "lon": None}
sources.stamp_local([here, far, theirs, nocoords], *NODE, 500)
assert here["local"] is True,  "250 m inside a 500 m radius stays local"
assert far["local"] is False,  "1.2 km away is ours but not here"
assert theirs["local"] is False, "a public station next door is still not ours"
assert nocoords["local"] is True, "a mesh pod on our own gateway has no coordinates and stays local"

# A node that does not know where it is must not decide that nothing is local. With no coordinates stamp_local
# leaves every claim alone: blanking the fleet on a half-configured node is worse than trusting the adapter.
unset = [{"sensor_id": "sc-19236", "local": True, "lat": -8.81983, "lon": 115.16657}]
sources.stamp_local(unset, None, None, 500)
assert unset[0]["local"] is True, "no node coordinates means no narrowing, not narrowing everything away"

print("all adapter tests pass")
