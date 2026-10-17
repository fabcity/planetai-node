"""Offline tests for tools/radio.py: the slot arithmetic, the fleet file, the channel URL, the role profiles, the
host gateway's packet → JSON mapping (fed straight into app/sources.py, which must not need to change), the
federation filter and the broker bridge blocks. No radio, no broker.
Run: PYTHONPATH=/tmp/stub:app:tools python3 tests/test_radio.py   (needs the meshtastic package: it has the protobufs)"""
import base64
import json
import os
import tempfile
from pathlib import Path

try:
    import meshtastic  # noqa: F401  (the protobufs the channel URL and the profile reader need)
except ImportError:
    print("radio: skipped (no meshtastic package: pip3 install --user meshtastic)")
    raise SystemExit(0)
import radio
import sources

# ---- the frequency slot: SG_923 is 917–925, Indonesia allows 920–923, LONG_FAST is 250 kHz wide
assert radio.num_slots("SG_923") == 32
inside = radio.slots_inside("SG_923", (920.0, 923.0))
assert inside == list(range(13, 25)), inside
for s in inside:
    f = radio.slot_freq("SG_923", s)
    assert 920.0 <= f - 0.125 and f + 0.125 <= 923.0, (s, f)
assert radio.slot_freq("SG_923", 13) == 920.125 and radio.slot_freq("SG_923", 24) == 922.875
pinned = radio.slot_for("SG_923", "bali")
assert pinned in inside
assert radio.slot_for("EU_868", "menorca") is None, "no listed allocation: the channel name hashes the slot"

# ---- the fleet file: two channels, two keys, never the same, 32 bytes each, pinned for Bali
f = radio.new_fleet("bayu-ungasan", "SG_923", "bali")
assert f["primary"]["name"] == "planetai" and f["fabcity"]["name"] == "fabcity"
assert len(base64.b64decode(f["primary"]["psk"])) == 32 and len(base64.b64decode(f["fabcity"]["psk"])) == 32
assert f["primary"]["psk"] != f["fabcity"]["psk"] and f["slot"] == pinned
assert f["fabcity"]["position_precision"] == 13, "2.9 km on the shared channel: coarser than a resolution-8 cell"
g = radio.new_fleet("menorca", "EU_868", "menorca")
assert g["slot"] is None and g["primary"]["psk"] != f["primary"]["psk"]
try:
    radio.new_fleet("x", "ID_923"); raise AssertionError("unknown region must refuse")
except SystemExit:
    pass
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "fleet.yaml"
    radio.save_fleet(f, p)
    assert oct(p.stat().st_mode)[-3:] == "600", "the fleet file holds keys"
    assert radio.load_fleet(p)["primary"]["psk"] == f["primary"]["psk"]

# ---- the channel URL carries both channels and the LoRa config; the gateway's differs by the uplink bits only
u = radio.channel_url(f)
d = radio.decode_url(u)
assert d["region"] == "SG_923" and d["preset"] == "LONG_FAST" and d["slot"] == pinned
assert [c["name"] for c in d["channels"]] == ["planetai", "fabcity"]
assert all(c["psk_len"] == 32 for c in d["channels"])
assert not d["channels"][0]["uplink"] and not d["channels"][0]["downlink"]
assert d["channels"][1]["position_precision"] == 13 and d["channels"][0]["position_precision"] == 0
dg = radio.decode_url(radio.channel_url(f, gateway=True))
assert dg["channels"][0]["uplink"] and dg["channels"][0]["downlink"] and dg["channels"][1]["uplink"]
assert u.startswith("https://meshtastic.org/e/#") and "=" not in u

# ---- role profiles render to the --configure format; the base is merged under every role
profiles = radio.load_profiles(Path(__file__).resolve().parent.parent / "tools" / "radio_profiles")
assert {"sensor", "relay", "shelf", "gateway-wifi", "gateway-host"} <= set(profiles)
sp = radio.render_profile("sensor", "Subak edge", "SBK", f, profiles)
assert sp["owner"] == "Subak edge" and sp["owner_short"] == "SBK" and sp["channel_url"] == u
assert sp["config"]["device"]["role"] == "SENSOR" and sp["config"]["device"]["serialEnabled"] is True, "base merged"
assert sp["module_config"]["telemetry"]["environmentMeasurementEnabled"] is True
assert sp["module_config"]["telemetry"]["environmentUpdateInterval"] == 900 and sp["module_config"]["telemetry"]["deviceUpdateInterval"] == 900
assert sp["config"]["position"]["gpsMode"] == "ENABLED"
assert sp["config"]["lora"] == {"region": "SG_923", "usePreset": True, "modemPreset": "LONG_FAST", "channelNum": pinned, "hopLimit": 3, "txEnabled": True}, \
    "the lora section repeats the URL's region and slot: a seeded lora section must never put UNSET back"
mp = radio.render_profile("sensor", "Es Castell", "CAS", g, profiles)
assert mp["config"]["lora"]["region"] == "EU_868" and mp["config"]["lora"]["channelNum"] == 0, "no pinned slot: the name hashes it"
assert "mqtt" not in sp["module_config"]
rp = radio.render_profile("relay", "Roof", "RF", f, profiles)
assert rp["config"]["device"]["role"] == "ROUTER" and rp["config"]["position"]["gpsMode"] == "NOT_PRESENT"
try:
    radio.render_profile("gateway-wifi", "gw", "GW", f, profiles); raise AssertionError("wifi gateway without a broker must refuse")
except SystemExit:
    pass
wp = radio.render_profile("gateway-wifi", "bayu gateway", "GW", f, profiles, {"address": "192.168.4.190:1883", "username": "planetai", "password": "pw"}, ("subak", "secret"))
assert wp["module_config"]["mqtt"] == {"enabled": True, "address": "192.168.4.190:1883", "username": "planetai", "password": "pw",
                                       "encryptionEnabled": False, "jsonEnabled": True, "root": "msh"}
assert wp["config"]["network"] == {"wifiEnabled": True, "wifiSsid": "subak", "wifiPsk": "secret"}
assert radio.decode_url(wp["channel_url"])["channels"][0]["uplink"], "a gateway's URL has uplink on"
hp = radio.render_profile("gateway-host", "node radio", "NODE", f, profiles)
assert hp["module_config"]["mqtt"]["enabled"] is False and hp["config"]["bluetooth"]["enabled"] is False
assert hp["config"]["device"]["serialEnabled"] is True
# a XIAO sensor node has no GPS: --fixed pins its position in the profile and turns the GPS off
fp = radio.render_profile("sensor", "Warung roof", "WRG", f, profiles, fixed=(-8.8004527, 115.1766378, 12))
assert fp["location"] == {"lat": -8.8004527, "lon": 115.1766378, "alt": 12}, "the CLI reads location:, not fixed_position:"
assert fp["config"]["position"]["fixedPosition"] is True and fp["config"]["position"]["gpsMode"] == "NOT_PRESENT"
assert fp["config"]["position"]["positionBroadcastSecs"] == 1800, "the role's other position settings survive"
assert "location" not in sp, "no --fixed, no pin"
try:
    radio.render_profile("sensor", "x", "X", f, profiles, fixed=(91.0, 0.0, 0.0)); raise AssertionError("bad coordinate")
except SystemExit:
    pass
for bad in ("", "TOOLONG"):
    try:
        radio.render_profile("sensor", "x", bad, f, profiles); raise AssertionError("short name length")
    except SystemExit:
        pass
try:
    radio.render_profile("drone", "x", "DR", f, profiles); raise AssertionError("unknown role")
except SystemExit:
    pass

# ---- the host gateway: a decoded packet from the Python API becomes the JSON an ESP32 publishes, and
# app/sources.py reads it unchanged. Shapes as MessageToDict gives them (camelCase).
GW = "!a1b2c3d4"
def pkt(portnum, **decoded):
    return {"from": 0xDEADBEEF, "fromId": "!deadbeef", "to": 4294967295, "id": 77, "channel": 0, "rxTime": 1760600000,
            "decoded": {"portnum": portnum, **decoded}}
tp = radio.to_mqtt(pkt("TELEMETRY_APP", telemetry={"time": 1760600000, "environmentMetrics": {"temperature": 29.4, "relativeHumidity": 71.2, "barometricPressure": 1008.3, "gasResistance": 47658.0, "iaq": 52}}), GW, "SG_923", "planetai")
assert tp[0] == "msh/SG_923/2/json/planetai/!a1b2c3d4", tp[0]
m = json.loads(tp[1])
assert m["type"] == "telemetry" and m["sender"] == "!deadbeef" and m["from"] == 0xDEADBEEF and m["timestamp"] == 1760600000
assert m["payload"]["relative_humidity"] == 71.2 and m["payload"]["barometric_pressure"] == 1008.3, m["payload"]
s, r, info = sources.meshtastic_message(tp[0], tp[1])
vals = {k: v for _, _, k, v in r}
assert s[0]["sensor_id"] == "msh-deadbeef" and s[0]["local"] and vals["temp"] == 29.4 and vals["humidity"] == 71.2
assert abs(vals["pressure"] - 100.83) < 0.01 and vals["gas_resistance"] == 47658.0 and vals["iaq"] == 52
assert info["root_topic"] == "msh/SG_923" and info["gateway"] == GW, "the node learns where to send alerts back"
# air quality block → pm names; device metrics with the 101 sentinel are dropped by sources, not by us
tp = radio.to_mqtt(pkt("TELEMETRY_APP", telemetry={"airQualityMetrics": {"pm10Standard": 4, "pm25Standard": 9, "pm100Standard": 11}}), GW, "SG_923", "planetai")
s, r, _ = sources.meshtastic_message(*tp)
vals = {k: v for _, _, k, v in r}
assert vals == {"pm1": 4.0, "pm25": 9.0, "pm10": 11.0}, vals
tp = radio.to_mqtt(pkt("TELEMETRY_APP", telemetry={"deviceMetrics": {"batteryLevel": 101, "voltage": 4.9, "airUtilTx": 0.05}}), GW, "SG_923", "planetai")
s, r, _ = sources.meshtastic_message(*tp)
assert {k for _, _, k, _ in r} == {"lora_util_pct"}
# position and nodeinfo
tp = radio.to_mqtt(pkt("POSITION_APP", position={"latitudeI": -88004527, "longitudeI": 1151766378, "altitude": 42, "time": 1760600000}), GW, "SG_923", "planetai")
s, r, _ = sources.meshtastic_message(*tp)
assert abs(s[0]["lat"] + 8.8004527) < 1e-6 and abs(s[0]["lon"] - 115.1766378) < 1e-6
tp = radio.to_mqtt(pkt("NODEINFO_APP", user={"id": "!deadbeef", "longName": "Subak edge", "shortName": "SBK", "hwModel": "WIO_TRACKER_L1"}), GW, "SG_923", "planetai")
s, _, _ = sources.meshtastic_message(*tp)
assert s[0]["name"] == "Subak edge" and s[0]["meta"]["hardware"] == "WIO_TRACKER_L1"
# text; and what the node has no use for returns None rather than noise
tp = radio.to_mqtt(pkt("TEXT_MESSAGE_APP", text="smoke at the river"), GW, "SG_923", "planetai")
assert json.loads(tp[1])["payload"] == {"text": "smoke at the river"}
assert radio.to_mqtt(pkt("ROUTING_APP", routing={}), GW, "SG_923", "planetai") is None
assert radio.to_mqtt(pkt("TELEMETRY_APP", telemetry={"time": 1}), GW, "SG_923", "planetai") is None
# the node's downlink (sources.meshtastic_downlink) is what the gateway listens for: same topic, same shape
t, p = sources.meshtastic_downlink("msh/SG_923", 123456, "PM2.5 high, close windows")
assert t == "msh/SG_923/2/json/mqtt/" and json.loads(p)["type"] == "sendtext"

# ---- federation: text on channel 1 leaves; readings and positions and channel 0 never do; inbound is deduplicated,
# rate-limited and never an echo
fed = radio.Federation("bayu-ungasan", max_per_minute=3)
assert fed.outbound(pkt("TEXT_MESSAGE_APP", text="hello from the household")) is None, "channel 0 stays home"
p1 = pkt("TEXT_MESSAGE_APP", text="hello from Bali"); p1["channel"] = 1
t, body = fed.outbound(p1)
assert t == "fabcity/bayu-ungasan/text" and json.loads(body) == {"node": "bayu-ungasan", "from": "!deadbeef", "id": 77, "text": "hello from Bali", "ts": 1760600000}
pp = pkt("POSITION_APP", position={"latitudeI": -88004527, "longitudeI": 1151766378}); pp["channel"] = 1
assert fed.outbound(pp) is None, "a position never crosses, whatever the channel"
pt = pkt("TELEMETRY_APP", telemetry={"environmentMetrics": {"temperature": 30}}); pt["channel"] = 1
assert fed.outbound(pt) is None, "a reading never crosses"
msg = json.dumps({"node": "menorca", "id": 5, "text": "hola desde Menorca"}).encode()
assert fed.inbound("fabcity/menorca/text", msg, now=1000) == "[menorca] hola desde Menorca"
assert fed.inbound("fabcity/menorca/text", msg, now=1001) is None, "duplicate id"
assert fed.inbound("fabcity/bayu-ungasan/text", json.dumps({"id": 9, "text": "me"}).encode(), now=1002) is None, "own echo"
assert fed.inbound("fabcity/menorca/presence", json.dumps({"id": 9, "text": "x"}).encode(), now=1003) is None, "presence is not relayed to the air"
assert fed.inbound("msh/EU_868/2/json/planetai/!1", b"{}", now=1004) is None
assert fed.inbound("fabcity/menorca/alerts", json.dumps({"id": 6, "text": "heat alert"}).encode(), now=1005) == "[menorca] heat alert"
assert fed.inbound("fabcity/boston/text", json.dumps({"id": 1, "text": "third"}).encode(), now=1006) == "[boston] third"
assert fed.inbound("fabcity/boston/text", json.dumps({"id": 2, "text": "fourth in the same minute"}).encode(), now=1007) is None, "rate limit"
assert fed.inbound("fabcity/boston/text", json.dumps({"id": 3, "text": "a minute later"}).encode(), now=1070) == "[boston] a minute later"
long = json.dumps({"id": 4, "text": "x" * 400}).encode()
assert len(fed.inbound("fabcity/boston/text", long, now=1200)) == 200, "LoRa frames are small"
t, body = fed.presence(3, "83a5f6fffffffff")
assert t == "fabcity/bayu-ungasan/presence" and json.loads(body)["radios"] == 3

# ---- .env reading: blank, quoted, commented (a blank MQTT_PASS= is every node before `planetai meshtastic`)
import tempfile as _tf, pathlib as _pl
with _tf.TemporaryDirectory() as _d:
    _old = radio.ROOT; radio.ROOT = _pl.Path(_d)
    (_pl.Path(_d) / ".env").write_text('MQTT_PASS=\nMQTT_USER=planetai   # the broker user\nNODE_NAME="bayu # ungasan"\nNODE_CITY=bali\n')
    assert radio.envget("MQTT_PASS") == "", "a blank value is blank, not a crash"
    assert radio.envget("MQTT_USER") == "planetai" and radio.envget("NODE_NAME") == "bayu # ungasan" and radio.envget("NODE_CITY") == "bali"
    assert radio.envget("MISSING", "dflt") == "dflt"
    radio.ROOT = _old

# ---- broker bridges: only fabcity/ crosses, each direction named, over the tailnet
peers = radio.parse_peers("menorca=lucas-node.tail1234.ts.net:1883:s3cret, boston=fabhub.tail1234.ts.net:1883:pw2")
assert peers == {"menorca": {"address": "lucas-node.tail1234.ts.net:1883", "password": "s3cret"}, "boston": {"address": "fabhub.tail1234.ts.net:1883", "password": "pw2"}}
conf = radio.mosquitto_bridges("bayu-ungasan", peers, "planetai")
assert "connection fabcity-menorca" in conf and "address lucas-node.tail1234.ts.net:1883" in conf
assert "topic bayu-ungasan/# out 0 fabcity/ fabcity/" in conf and "topic menorca/# in 0 fabcity/ fabcity/" in conf
assert "msh/" not in conf, "readings never leave the node"
assert conf.count("connection ") == 2
try:
    radio.parse_peers("menorca=host"); raise AssertionError("malformed peer")
except SystemExit:
    pass
assert radio.parse_peers("") == {}

print("radio: ok")
