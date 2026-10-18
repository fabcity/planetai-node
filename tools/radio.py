#!/usr/bin/env python3
"""planetai radio — provision Meshtastic radios for a node, run the node as their gateway, federate nodes over MQTT.

    planetai radio init      [--region SG_923] [--slot N]     one fleet per node: channel keys, region, frequency slot
    planetai radio url                                        the fleet's channel URL / QR (what the phone app imports)
    planetai radio render    <role> "<long name>" <SHORT>     print the device profile that `provision` would apply
    planetai radio provision <role> "<long name>" <SHORT> --port /dev/cu.usbmodem1101 [--wifi SSID:PSK] [--fixed LAT,LON]
    planetai radio gateway   --port /dev/cu.usbmodem1101     the radio on this USB port becomes the node's gateway
    planetai radio federate  [--write]                        render (and install) the broker's bridge blocks to peer nodes
    planetai radio list                                       the fleet file and, with --port, what the radio sees
    planetai radio doctor    [--port ...]                     the usual reasons nothing arrives, checked one by one

Roles: sensor · relay · shelf · gateway-wifi (ESP32 uplinks over WiFi) · gateway-host (any board on this node's USB).

Everything a radio needs is in one DeviceProfile applied with `meshtastic --configure` in a single settings
transaction (one reboot, not six). The fleet file holds the keys, so it is a credential: config/radio/fleet.yaml,
gitignored, next to mosquitto/passwd. Python 3.9, needs `python3 -m pip install --user meshtastic paho-mqtt` on the host
(not in the container: a USB port does not reach a container on macOS, and node #1 is a Mac mini).
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("planetai.radio")
# Apple's Python 3.9 is built on LibreSSL, so urllib3 2.x warns on every run. The radio talks over USB and the LAN, and
# the warning only taught people to doubt the output under it.
import warnings  # noqa: E402
warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL")

ROOT = Path(os.getenv("PLANETAI_ROOT", Path(__file__).resolve().parent.parent))
FLEET_PATH = ROOT / "config" / "radio" / "fleet.yaml"
PROFILES_DIR = ROOT / "tools" / "radio_profiles"
MOSQ_DIR = ROOT / "config" / "mosquitto"

# ---------------------------------------------------------------- regions and the frequency slot
# Meshtastic's region table (docs/configuration/radio/lora, read 16 Oct 2026). Only the regions a Fab City node has
# asked for so far; add a line, nothing else changes. There is no Indonesia preset. Indonesia allocates 920–923 MHz
# (the AS923-2 plan), and SG_923 spans 917–925, so a slot chosen by hashing the channel name can land outside the
# allocation. `init` pins the slot inside it instead (see slot_for). KR is 920–923 exactly but carries Korean
# duty-cycle rules; staying on SG_923 with a pinned slot keeps the fleet Bali already runs.
REGIONS: Dict[str, Tuple[float, float]] = {
    "US": (902.0, 928.0), "EU_868": (869.4, 869.65), "EU_433": (433.0, 434.0), "ANZ": (915.0, 928.0),
    "SG_923": (917.0, 925.0), "TH": (920.0, 925.0), "KR": (920.0, 923.0), "MY_919": (919.0, 924.0),
    "JP": (920.5, 923.5), "IN": (865.0, 867.0), "BR_902": (902.0, 907.5), "LORA_24": (2400.0, 2483.5),
}
# What the law allows where a node lives, when it is narrower than the preset. Only entries somebody checked.
ALLOCATION: Dict[str, Tuple[float, float]] = {
    "bali": (920.0, 923.0),      # Indonesia, AS923-2. Check the Kominfo text before relying on the edges.
}
PRESET_BW_KHZ = {"LONG_FAST": 250, "LONG_SLOW": 125, "LONG_MODERATE": 125, "MEDIUM_FAST": 250, "MEDIUM_SLOW": 250,
                 "SHORT_FAST": 250, "SHORT_SLOW": 250, "SHORT_TURBO": 500, "LONG_TURBO": 500, "MEDIUM_TURBO": 500}
CITY_REGION = {"bali": "SG_923", "menorca": "EU_868", "barcelona": "EU_868", "boston": "US", "santiago": "ANZ"}


def num_slots(region: str, preset: str = "LONG_FAST") -> int:
    lo, hi = REGIONS[region]
    return int((hi - lo) / (PRESET_BW_KHZ[preset] / 1000.0))


def slot_freq(region: str, slot: int, preset: str = "LONG_FAST") -> float:
    """Centre frequency of a 1-based slot, the firmware's formula: start + bw/2 + bw*(slot-1).
    Verify against what the radio logs at boot ("freq=") the first time a region is used; this is arithmetic, not a measurement."""
    lo, _ = REGIONS[region]
    bw = PRESET_BW_KHZ[preset] / 1000.0
    return round(lo + bw / 2 + bw * (slot - 1), 4)


def slots_inside(region: str, band: Tuple[float, float], preset: str = "LONG_FAST") -> List[int]:
    """Slots whose whole bandwidth sits inside `band`."""
    bw = PRESET_BW_KHZ[preset] / 1000.0
    out = []
    for s in range(1, num_slots(region, preset) + 1):
        f = slot_freq(region, s, preset)
        if f - bw / 2 >= band[0] - 1e-9 and f + bw / 2 <= band[1] + 1e-9:
            out.append(s)
    return out


def slot_for(region: str, city: str = "", preset: str = "LONG_FAST") -> Optional[int]:
    """A slot to pin: the middle of the legal band when one is listed for the city, else None (let the name hash it)."""
    band = ALLOCATION.get(city)
    if not band:
        return None
    ok = slots_inside(region, band, preset)
    return ok[len(ok) // 2] if ok else None


# ---------------------------------------------------------------- the fleet file
def _yaml():
    import yaml  # ships with the meshtastic package; the CLI's own Python has no yaml, which is why this file is separate
    return yaml


def new_fleet(node: str, region: str, city: str = "", preset: str = "LONG_FAST", slot: Optional[int] = None) -> dict:
    if region not in REGIONS:
        raise SystemExit(f"unknown region {region!r}; one of {', '.join(sorted(REGIONS))}")
    slot = slot if slot is not None else slot_for(region, city, preset)
    return {
        "node": node, "region": region, "preset": preset, "slot": slot, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # channel 0, PRIMARY: telemetry and position travel here and only here. The key is this node's own.
        "primary": {"name": "planetai", "psk": base64.b64encode(secrets.token_bytes(32)).decode()},
        # channel 1, SECONDARY: what crosses to other nodes (text, alerts). Its own key too; federation re-sends as
        # text through the bridge, so two nodes never need to share a key. Position on it is capped coarse.
        "fabcity": {"name": "fabcity", "psk": base64.b64encode(secrets.token_bytes(32)).decode(), "position_precision": 13},
        "radios": [],
    }


def load_fleet(path: Path = FLEET_PATH) -> dict:
    if not path.exists():
        raise SystemExit(f"no fleet yet: run  planetai radio init  (looked at {path})")
    return _yaml().safe_load(path.read_text())


def save_fleet(fleet: dict, path: Path = FLEET_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_yaml().safe_dump(fleet, sort_keys=False))
    os.chmod(path, 0o600)


# ---------------------------------------------------------------- the channel URL
def channel_url(fleet: dict, gateway: bool = False) -> str:
    """One URL carrying both channels and the LoRa config (region, preset, pinned slot), the thing the phone app
    imports and `--configure` applies. Uplink/downlink flags ride inside it, so a gateway's URL differs from a
    sensor's by those two bits only."""
    from meshtastic.protobuf import apponly_pb2, channel_pb2, config_pb2
    cs = apponly_pb2.ChannelSet()
    for key, up, down in (("primary", gateway, gateway), ("fabcity", gateway, gateway)):
        ch = fleet[key]
        s = channel_pb2.ChannelSettings()
        s.name = ch["name"]
        s.psk = base64.b64decode(ch["psk"])
        s.uplink_enabled, s.downlink_enabled = up, down
        if ch.get("position_precision") is not None:
            s.module_settings.position_precision = int(ch["position_precision"])
        cs.settings.append(s)
    lora = cs.lora_config
    lora.region = config_pb2.Config.LoRaConfig.RegionCode.Value(fleet["region"])
    lora.use_preset = True
    lora.modem_preset = config_pb2.Config.LoRaConfig.ModemPreset.Value(fleet.get("preset", "LONG_FAST"))
    lora.hop_limit = 3
    lora.tx_enabled = True
    if fleet.get("slot"):
        lora.channel_num = int(fleet["slot"])
    b = base64.urlsafe_b64encode(cs.SerializeToString()).decode("ascii").rstrip("=")
    return f"https://meshtastic.org/e/#{b}"


def decode_url(url: str) -> dict:
    from meshtastic.protobuf import apponly_pb2, config_pb2
    b = url.split("/#", 1)[1]
    b += "=" * (-len(b) % 4)
    cs = apponly_pb2.ChannelSet()
    cs.ParseFromString(base64.urlsafe_b64decode(b))
    return {
        "channels": [{"name": s.name, "psk_len": len(s.psk), "uplink": s.uplink_enabled, "downlink": s.downlink_enabled,
                      "position_precision": s.module_settings.position_precision} for s in cs.settings],
        "region": config_pb2.Config.LoRaConfig.RegionCode.Name(cs.lora_config.region),
        "preset": config_pb2.Config.LoRaConfig.ModemPreset.Name(cs.lora_config.modem_preset),
        "slot": cs.lora_config.channel_num,
    }


# ---------------------------------------------------------------- roles → device profile
def load_profiles(d: Path = PROFILES_DIR) -> Dict[str, dict]:
    out = {}
    for p in sorted(d.glob("*.yaml")):
        out[p.stem] = _yaml().safe_load(p.read_text()) or {}
    return out


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def render_profile(role: str, long_name: str, short_name: str, fleet: dict, profiles: Dict[str, dict],
                   mqtt: Optional[dict] = None, wifi: Optional[Tuple[str, str]] = None,
                   fixed: Optional[Tuple[float, float, float]] = None) -> dict:
    """The DeviceProfile (meshtastic --configure format) for one radio. Pure: no radio, no network.
    `fixed` = (lat, lon, alt_m) pins the radio's position: a XIAO ESP32-S3 sensor node has no GPS, and a reading
    without a place never becomes `local` on the node. Broadcast on the primary channel only (the household's);
    the fabcity channel's precision cap still applies to anything that crosses."""
    if role not in profiles:
        raise SystemExit(f"unknown role {role!r}; one of {', '.join(sorted(profiles))}")
    if not (1 <= len(short_name) <= 4):
        raise SystemExit("short name is 1–4 characters (it is what the radio shows on screens with no room)")
    base = profiles.get("_base", {})
    spec = _deep_merge(base, {k: v for k, v in profiles[role].items() if not k.startswith("_")})
    is_gw = bool(profiles[role].get("_gateway"))
    prof: dict = {"owner": long_name, "owner_short": short_name, "channel_url": channel_url(fleet, gateway=is_gw)}
    prof["config"] = spec.get("config", {})
    prof["module_config"] = spec.get("module_config", {})
    # The URL already carries the LoRa config, but `--configure` applies the URL first and the config sections after,
    # each seeded from the radio's current state (meshtastic 2.7.11, __main__.py). A lora section seeded from a radio
    # whose region was still UNSET would put UNSET back. So the lora section says it all again, explicitly.
    prof["config"]["lora"] = {"region": fleet["region"], "usePreset": True, "modemPreset": fleet.get("preset", "LONG_FAST"),
                              "channelNum": int(fleet.get("slot") or 0), "hopLimit": 3, "txEnabled": True}
    if fixed:
        lat, lon, alt = fixed
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise SystemExit(f"--fixed {lat},{lon}: not a coordinate")
        prof["location"] = {"lat": lat, "lon": lon, "alt": int(alt)}   # the CLI reads `location:` and writes DeviceProfile.fixed_position
        prof["config"].setdefault("position", {}).update({"fixedPosition": True, "gpsMode": "NOT_PRESENT"})
    if is_gw and profiles[role].get("_uplink") == "wifi":
        if not mqtt:
            raise SystemExit("gateway-wifi needs the broker: --mqtt host:1883 user pass (planetai radio doctor prints it)")
        prof["module_config"]["mqtt"] = {
            "enabled": True, "address": mqtt["address"], "username": mqtt["username"], "password": mqtt["password"],
            "encryptionEnabled": False,   # the broker is the node's; an encrypted uplink hides readings from it
            "jsonEnabled": True,          # the node reads JSON. ESP32 only: nRF52 has no JSON, use gateway-host there
            "root": "msh",
        }
        if wifi:
            prof["config"]["network"] = {"wifiEnabled": True, "wifiSsid": wifi[0], "wifiPsk": wifi[1]}
    return prof


# ---------------------------------------------------------------- talking to a radio (thin: the meshtastic CLI does the work)
def meshtastic_cli() -> str:
    exe = shutil.which("meshtastic") or str(Path.home() / ".local" / "bin" / "meshtastic")
    if not Path(exe).exists():
        raise SystemExit("the meshtastic CLI is not installed:  pip3 install --user meshtastic")
    return exe


def run_cli(port: str, *args: str, timeout: int = 120) -> str:
    r = subprocess.run([meshtastic_cli(), "--port", port, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise SystemExit(f"meshtastic {' '.join(args)} failed:\n{(r.stdout + r.stderr).strip()[-800:]}")
    return r.stdout


def wait_ready(port: str, tries: int = 30) -> None:
    """Every settings write reboots the radio; an ESP32 takes longer than an nRF52 to come back. Poll, don't sleep."""
    for _ in range(tries):
        try:
            run_cli(port, "--info", timeout=40)
            return
        except SystemExit:
            time.sleep(2)
    raise SystemExit(f"radio on {port} did not come back after a reboot")


def verify(port: str, fleet: dict, role_spec: dict) -> List[str]:
    """What is actually on the radio after provisioning, as a list of problems (empty = good)."""
    info = run_cli(port, "--info")
    problems = []
    if f'"region": "{fleet["region"]}"' not in info and f"region: {fleet['region']}" not in info:
        problems.append(f"region is not {fleet['region']} (region 0 means the radio never transmits)")
    for ch in ("primary", "fabcity"):
        if f'"name": "{fleet[ch]["name"]}"' not in info:
            problems.append(f"channel {fleet[ch]['name']!r} is not on the radio")
    want_role = role_spec.get("config", {}).get("device", {}).get("role")
    if want_role and f'"role": "{want_role}"' not in info and want_role != "CLIENT":
        problems.append(f"device role is not {want_role}")
    return problems


def provision(port: str, role: str, long_name: str, short_name: str, fleet: dict, profiles: Dict[str, dict],
              mqtt: Optional[dict] = None, wifi: Optional[Tuple[str, str]] = None, dry_run: bool = False,
              fixed: Optional[Tuple[float, float, float]] = None) -> dict:
    prof = render_profile(role, long_name, short_name, fleet, profiles, mqtt, wifi, fixed)
    if dry_run:
        return prof
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        _yaml().safe_dump(prof, f, sort_keys=False)
        tmp = f.name
    try:
        wait_ready(port)
        print(f">> {role}: '{long_name}' ({short_name}), region {fleet['region']}, slot {fleet.get('slot') or 'by name'}")
        out = run_cli(port, "--configure", tmp, timeout=300)
        print("\n".join(l for l in out.splitlines() if l.startswith("Setting") or "Writing" in l))
        time.sleep(3)
        wait_ready(port)
        problems = verify(port, fleet, profiles[role])
    finally:
        os.unlink(tmp)
    node_id = None
    m = re.search(r'"id": "(![0-9a-f]{8})"', run_cli(port, "--info"))
    if m:
        node_id = m.group(1)
    fleet.setdefault("radios", []).append({"id": node_id, "role": role, "name": long_name, "short": short_name,
                                          "provisioned": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    save_fleet(fleet)
    if problems:
        print("!! provisioned with problems:\n   " + "\n   ".join(problems))
    else:
        print(f">> ok. {node_id or 'radio'} is on the fleet's channels; it is in {FLEET_PATH}")
        print("   Next step:  planetai radio")
    return prof


# ---------------------------------------------------------------- the host gateway: packets → the same JSON an ESP32 gateway publishes
_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


def snake(d: Any) -> Any:
    """MessageToDict gives camelCase; the firmware's MQTT JSON (what app/sources.py parses) is snake_case."""
    if isinstance(d, dict):
        return {_SNAKE.sub("_", k).lower(): snake(v) for k, v in d.items()}
    if isinstance(d, list):
        return [snake(x) for x in d]
    return d


def envelope(packet: dict, gateway_id: str) -> Optional[Tuple[str, dict]]:
    """One decoded packet from the Python API → (type, payload) in the firmware's JSON shape, or None if the node
    has no use for it. Pure, so it is tested without a radio. Field names follow firmware 2.x JSON output."""
    dec = packet.get("decoded") or {}
    port = dec.get("portnum")
    if port == "TELEMETRY_APP":
        t = dec.get("telemetry") or {}
        for block in ("deviceMetrics", "environmentMetrics", "airQualityMetrics", "powerMetrics"):
            if block in t:
                return "telemetry", snake(t[block])
        return None
    if port == "POSITION_APP":
        p = dec.get("position") or {}
        out = {"latitude_i": p.get("latitudeI"), "longitude_i": p.get("longitudeI")}
        if p.get("altitude") is not None:
            out["altitude"] = p["altitude"]
        if p.get("time"):
            out["time"] = p["time"]
        return "position", out
    if port == "NODEINFO_APP":
        u = dec.get("user") or {}
        return "nodeinfo", {"id": u.get("id"), "longname": u.get("longName"), "shortname": u.get("shortName"), "hardware": u.get("hwModel")}
    if port == "TEXT_MESSAGE_APP":
        return "text", {"text": dec.get("text", "")}
    return None


def to_mqtt(packet: dict, gateway_id: str, region: str, channel_name: str, root: str = "msh") -> Optional[Tuple[str, bytes]]:
    """(topic, payload) exactly as an ESP32 gateway with JSON on would publish, so app/main.py's MQTT thread needs no change."""
    e = envelope(packet, gateway_id)
    if not e:
        return None
    kind, payload = e
    sender = packet.get("fromId") or f"!{packet['from']:08x}"
    msg = {"channel": packet.get("channel", 0), "from": packet.get("from"), "id": packet.get("id"), "payload": payload,
           "sender": sender, "timestamp": int(packet.get("rxTime") or time.time()), "to": packet.get("to", -1), "type": kind}
    return f"{root}/{region}/2/json/{channel_name}/{gateway_id}", json.dumps(msg, separators=(",", ":")).encode()


# ---------------------------------------------------------------- federation: what may cross to another node
class Federation:
    """Decides what leaves this node for the fabcity/ topics and what comes in from them.
    Out: text on the fabcity channel, the node's alerts, a presence line. Never a reading, never a position finer
    than the channel's cap (and the cap is set so nothing finer than a resolution-8 cell leaves: the site rule).
    In: text from other nodes, re-sent on the local fabcity channel, deduplicated and rate-limited: LoRa airtime is
    the scarce thing, and a broker can deliver a thousand lines a second."""

    def __init__(self, node: str, fabcity_index: int = 1, max_per_minute: int = 6):
        self.node, self.idx, self.max_per_minute = node, fabcity_index, max_per_minute
        self.seen: Dict[str, float] = {}
        self.sent_times: List[float] = []

    def outbound(self, packet: dict) -> Optional[Tuple[str, bytes]]:
        if packet.get("channel", 0) != self.idx:
            return None                                     # channel 0 is the household's; it stays home
        e = envelope(packet, "")
        if not e or e[0] != "text":
            return None                                     # positions, telemetry: never
        text = e[1]["text"].strip()
        if not text:
            return None
        body = {"node": self.node, "from": packet.get("fromId"), "id": packet.get("id"), "text": text[:200],
                "ts": int(packet.get("rxTime") or time.time())}
        return f"fabcity/{self.node}/text", json.dumps(body, separators=(",", ":")).encode()

    def presence(self, radios: int, cell_r3: Optional[str]) -> Tuple[str, bytes]:
        body = {"node": self.node, "radios": radios, "cell": cell_r3, "ts": int(time.time())}
        return f"fabcity/{self.node}/presence", json.dumps(body, separators=(",", ":")).encode()

    def inbound(self, topic: str, payload: bytes, now: Optional[float] = None) -> Optional[str]:
        """The text to send on the local fabcity channel, or None (own echo, duplicate, rate limit, not text)."""
        now = now or time.time()
        parts = topic.split("/")
        if len(parts) != 3 or parts[0] != "fabcity" or parts[2] not in ("text", "alerts"):
            return None
        if parts[1] == self.node:
            return None
        try:
            m = json.loads(payload)
        except Exception:  # noqa: BLE001
            return None
        key = f"{parts[1]}/{m.get('id')}"
        if key in self.seen:
            return None
        self.seen = {k: v for k, v in self.seen.items() if now - v < 3600}
        self.seen[key] = now
        self.sent_times = [t for t in self.sent_times if now - t < 60]
        if len(self.sent_times) >= self.max_per_minute:
            log.warning("federation: dropping %s, more than %d lines a minute", key, self.max_per_minute)
            return None
        self.sent_times.append(now)
        text = str(m.get("text", "")).strip()
        if not text:
            return None
        return f"[{parts[1]}] {text}"[:200]


def mosquitto_bridges(node: str, peers: Dict[str, dict], user: str) -> str:
    """Bridge blocks for config/mosquitto/bridges/peers.conf. Each peer is a node on the tailnet; the connection goes
    over Tailscale, so no TLS and no open port, and a peer's password is the one `planetai radio federate` on
    that node printed. Only fabcity/ crosses. msh/ never does."""
    lines = ["# written by planetai radio federate; peers come from RADIO_PEERS in .env. Only fabcity/ crosses."]
    for name, p in sorted(peers.items()):
        u = p.get("username", user)
        lines += [
            f"connection fabcity-{name}",
            f"address {p['address']}",
            *([f"remote_username {u}", f"remote_password {p['password']}"] if u else []),   # mosquitto refuses an empty value
            f"remote_clientid planetai-{node}-to-{name}",
            "cleansession false",
            "try_private true",
            "notifications false",
            f"topic {node}/# out 0 fabcity/ fabcity/",      # mine go out
            f"topic {name}/# in 0 fabcity/ fabcity/",       # theirs come in; nothing else
            "",
        ]
    return "\n".join(lines) + "\n"


def parse_peers(s: str) -> Dict[str, dict]:
    """RADIO_PEERS=menorca=lucas-node.tailnet.ts.net:1883:<password>,boston=…"""
    out = {}
    for item in (x.strip() for x in s.split(",") if x.strip()):
        name, _, rest = item.partition("=")
        host, _, rest = rest.partition(":")
        port, _, password = rest.partition(":")
        if not (name and host and port and password):
            raise SystemExit(f"RADIO_PEERS entry {item!r} is not name=host:port:password")
        out[name.strip()] = {"address": f"{host}:{port}", "password": password}
    return out


# ---------------------------------------------------------------- the gateway process
def lan_ip() -> str:
    """The address other machines on the LAN reach this one at: the source of the route out. No packet is sent."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))      # TEST-NET-1: never routed, but connect() picks the interface
        ip = s.getsockname()[0]; s.close()
        return "" if ip.startswith("127.") else ip
    except OSError:
        return ""


def envget(key: str, default: str = "") -> str:
    env = ROOT / ".env"
    if not env.exists():
        return os.getenv(key, default)
    for line in env.read_text().splitlines():
        if line.startswith(key + "="):
            v = line.split("=", 1)[1].strip()
            if v[:1] in "\"'":                       # quoted: the value is what the quotes hold, # and all
                return v[1:].split(v[0], 1)[0]
            return re.split(r"\s+#", v, maxsplit=1)[0].strip()   # unquoted: ` # …` is a comment, as docker compose reads it
    return os.getenv(key, default)


def gateway(port: str, fleet: dict, broker: str = "127.0.0.1:1883", once: bool = False) -> None:
    """This radio, on this node's USB, is the gateway: packets go to the broker as JSON; downlink text comes back;
    the fabcity channel is federated. Runs until killed. `planetai radio gateway --install` makes it a service."""
    import paho.mqtt.client as mqtt
    from pubsub import pub
    import meshtastic.serial_interface

    user, password = envget("MQTT_USER", "planetai"), envget("MQTT_PASS")
    node = envget("NODE_NAME", fleet.get("node", "node"))
    host, _, bport = broker.partition(":")
    region, primary, fab = fleet["region"], fleet["primary"]["name"], fleet["fabcity"]["name"]
    iface = meshtastic.serial_interface.SerialInterface(port)
    me = iface.getMyNodeInfo() or {}
    gw_id = (me.get("user") or {}).get("id") or f"!{me.get('num', 0):08x}"
    root_topic = f"msh/{region}"
    # the radio's channel table decides which index is which; a phone import can land fabcity anywhere
    names = {0: primary, 1: fab}
    try:
        names = {c.index: c.settings.name for c in iface.localNode.channels if c.settings.name} or names
    except Exception:  # noqa: BLE001
        pass
    fab_idx = next((i for i, n in names.items() if n == fab), 1)
    fed = Federation(node, fabcity_index=fab_idx)
    log.info("gateway %s on %s, broker %s, node %s, fabcity is channel %d", gw_id, port, broker, node, fab_idx)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"planetai-radio-{node}")
    if user:
        c.username_pw_set(user, password)
    counts = {"up": 0, "down": 0, "fed_out": 0, "fed_in": 0}

    def on_radio(packet, interface):  # noqa: ARG001
        ch = packet.get("channel", 0)
        tp = to_mqtt(packet, gw_id, region, names.get(ch, primary))
        if tp:
            c.publish(tp[0], tp[1]); counts["up"] += 1
        fo = fed.outbound(packet)
        if fo:
            c.publish(fo[0], fo[1]); counts["fed_out"] += 1

    def on_mqtt(client, userdata, msg):  # noqa: ARG001
        if msg.topic == f"{root_topic}/2/json/mqtt/":          # app/main.py mesh_send(): the node's own alerts
            try:
                m = json.loads(msg.payload)
                if m.get("type") == "sendtext":
                    iface.sendText(str(m.get("payload", ""))[:200], channelIndex=int(m.get("channel", 0)))
                    counts["down"] += 1
                    c.publish(f"fabcity/{node}/alerts", json.dumps({"node": node, "id": int(time.time()), "text": m.get("payload", "")}).encode())
            except Exception as e:  # noqa: BLE001
                log.warning("downlink ignored: %s", e)
            return
        text = fed.inbound(msg.topic, msg.payload)
        if text:
            iface.sendText(text, channelIndex=fab_idx); counts["fed_in"] += 1

    c.on_message = on_mqtt
    c.connect(host, int(bport or 1883), keepalive=60)
    c.subscribe([(f"{root_topic}/2/json/mqtt/", 0), ("fabcity/+/text", 0), ("fabcity/+/alerts", 0)])
    c.loop_start()
    pub.subscribe(on_radio, "meshtastic.receive")

    def heartbeat():
        while True:
            t, p = fed.presence(len(fleet.get("radios", [])), None)
            c.publish(t, p, retain=True)
            log.info("up %d · down %d · federated out %d in %d", counts["up"], counts["down"], counts["fed_out"], counts["fed_in"])
            time.sleep(1800)
    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        if once:
            time.sleep(5)
        else:
            while True:
                time.sleep(60)
    finally:
        iface.close(); c.loop_stop()


SERVICE_MAC = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>city.fab.planetai.radio</string>
  <key>ProgramArguments</key><array><string>{python}</string><string>{script}</string><string>gateway</string><string>--port</string><string>{port}</string></array>
  <key>WorkingDirectory</key><string>{root}</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{root}/out/radio.log</string><key>StandardErrorPath</key><string>{root}/out/radio.log</string>
</dict></plist>
"""
SERVICE_LINUX = """[Unit]
Description=PLANETAI radio gateway
After=network.target docker.service
[Service]
WorkingDirectory={root}
ExecStart={python} {script} gateway --port {port}
Restart=always
RestartSec=10
[Install]
WantedBy=default.target
"""


def install_service(port: str) -> None:
    py, script, root = sys.executable, str(Path(__file__).resolve()), str(ROOT)
    if sys.platform == "darwin":
        p = Path.home() / "Library" / "LaunchAgents" / "city.fab.planetai.radio.plist"
        p.write_text(SERVICE_MAC.format(python=py, script=script, port=port, root=root))
        subprocess.run(["launchctl", "unload", str(p)], capture_output=True)   # a fresh load picks up a changed port
        r = subprocess.run(["launchctl", "load", str(p)], capture_output=True, text=True)
        print(f">> the gateway runs as a service now, and again after every restart ({p})" if r.returncode == 0 else
              f"!! wrote {p}, but launchctl did not load it: {(r.stderr or r.stdout).strip()}\n   by hand:  launchctl load {p}")
    else:
        p = Path.home() / ".config" / "systemd" / "user" / "planetai-radio.service"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(SERVICE_LINUX.format(python=py, script=script, port=port, root=root))
        ok = all(subprocess.run(c, capture_output=True).returncode == 0 for c in
                 (["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "--now", "planetai-radio"]))
        print(f">> the gateway runs as a service now ({p}). So it also runs while nobody is logged in:  loginctl enable-linger $USER"
              if ok else f"!! wrote {p}, but systemctl did not start it.\n   by hand:  systemctl --user daemon-reload && systemctl --user enable --now planetai-radio")


# ---------------------------------------------------------------- doctor
def doctor(port: Optional[str]) -> int:
    bad = 0

    def chk(ok: bool, what: str, fix: str) -> None:
        nonlocal bad
        print(("  ok  " if ok else "  !!  ") + what + ("" if ok else f"\n        {fix}"))
        bad += 0 if ok else 1

    chk(bool(shutil.which("meshtastic") or (Path.home() / ".local/bin/meshtastic").exists()), "meshtastic CLI on the host", "python3 -m pip install --user meshtastic")
    try:
        from importlib.metadata import version
        v = tuple(int(x) for x in version("meshtastic").split(".")[:3])
        # 2.7.11 is the version read on 16 Oct 2026, where --configure seeds each section from the radio before
        # overlaying the profile. An older CLI replaces whole sections, and a partial `device:` would reset the rest.
        chk(v >= (2, 7, 11), f"meshtastic package {'.'.join(map(str, v))} (2.7.11 or newer: --configure merges sections)", "python3 -m pip install --user -U meshtastic")
    except Exception:  # noqa: BLE001
        chk(False, "meshtastic package version readable", "python3 -m pip install --user -U meshtastic")
    try:
        import paho.mqtt  # noqa: F401
        chk(True, "paho-mqtt on the host", "")
    except ImportError:
        chk(False, "paho-mqtt on the host", "python3 -m pip install --user paho-mqtt")
    chk(FLEET_PATH.exists(), f"fleet file {FLEET_PATH.relative_to(ROOT)}", "planetai radio init")
    chk(bool(envget("MQTT_PASS")), "broker credentials in .env", "planetai meshtastic  (creates the broker and its user)")
    chk("mqtt" in envget("COMPOSE_PROFILES"), "mqtt compose profile on", "planetai meshtastic")
    if FLEET_PATH.exists():
        f = load_fleet()
        city = envget("NODE_CITY")
        band = ALLOCATION.get(city)
        if band:
            slot = f.get("slot")
            chk(bool(slot) and slot in slots_inside(f["region"], band, f.get("preset", "LONG_FAST")),
                f"frequency slot inside {city}'s allocation {band[0]}–{band[1]} MHz",
                "planetai radio init --slot N   (then re-provision every radio: the URL changed)")
    if port:
        try:
            info = run_cli(port, "--info", timeout=60)
            chk('"region": "UNSET"' not in info and "region: 0" not in info, "radio has a region", "a radio with region unset never transmits and nothing tells you")
            chk('"name": "planetai"' in info, "radio is on the planetai channel", "planetai radio provision …")
        except SystemExit as e:
            chk(False, f"radio answers on {port}", str(e).splitlines()[-1] if str(e) else "")
    print(f"\n{bad} problem(s)" if bad else "\nnothing wrong that this can see")
    return 1 if bad else 0


# ---------------------------------------------------------------- the guide
def usb_radios() -> List[Tuple[str, str]]:
    """Serial ports with a USB vendor id: what is plugged in now. macOS lists every radio twice (cu. and tty.); cu. is
    the one to use. Empty when pyserial is missing, so the guide still runs."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    out = []
    for p in list_ports.comports():
        if p.vid is None or "/dev/tty." in p.device:
            continue
        out.append((p.device, (p.description or "").strip() if p.description and p.description != "n/a" else "USB serial"))
    return out


def service_installed() -> bool:
    if sys.platform == "darwin":
        return (Path.home() / "Library" / "LaunchAgents" / "city.fab.planetai.radio.plist").exists()
    return (Path.home() / ".config" / "systemd" / "user" / "planetai-radio.service").exists()


def guide() -> int:
    """`planetai radio` on its own: where this node is in setting up its radios, step by step, and the one command
    that comes next. Read-only: it looks at .env, the fleet file and the USB ports, and never talks to a radio."""
    ports = usb_radios()
    port = ports[0][0] if len(ports) == 1 else "/dev/cu.usbmodem…"
    try:
        fleet = load_fleet() if FLEET_PATH.exists() else None
    except ImportError:   # yaml arrives with the packages; the fleet is there, its details wait for step 1
        fleet = {"region": "?", "radios": []}
    radios = (fleet or {}).get("radios", [])
    gateways = [r for r in radios if str(r.get("role", "")).startswith("gateway")]
    others = [r for r in radios if not str(r.get("role", "")).startswith("gateway")]
    steps = []   # (done, title, detail, next command when not done)
    try:
        import meshtastic  # noqa: F401
        import paho.mqtt  # noqa: F401
        pkgs = True
    except ImportError:
        pkgs = False
    pins = ('"pyobjc-core<12" "pyobjc-framework-Cocoa<12" "pyobjc-framework-CoreBluetooth<12" "pyobjc-framework-libdispatch<12" '
            if sys.platform == "darwin" and sys.version_info < (3, 10) else "")   # 12.0 does not build on Apple's 3.9
    steps.append((pkgs, "The packages", f"meshtastic and paho-mqtt for {sys.executable}",
                  f"python3 -m pip install --user {pins}meshtastic paho-mqtt"))
    broker = bool(envget("MQTT_PASS")) and "mqtt" in envget("COMPOSE_PROFILES")
    steps.append((broker, "The broker", "the node's MQTT broker, where the gateway delivers what the radios hear",
                  "planetai meshtastic"))
    if fleet:
        f = fleet
        where = f"region {f['region']}, slot {f.get('slot') or 'by channel name'}" + (
            f" ({slot_freq(f['region'], f['slot'], f.get('preset', 'LONG_FAST'))} MHz)" if f.get("slot") else "")
        steps.append((True, "The fleet", f"{where}; the household's channel keys, in {FLEET_PATH.relative_to(ROOT)}", ""))
    else:
        steps.append((False, "The fleet", "one set of channel keys, region and frequency for every radio of this node",
                      "planetai radio init"))
    steps.append((bool(gateways), "The gateway radio",
                  "one radio on this machine's USB that carries the mesh to the node" + (f": {gateways[0]['name']}" if gateways else ""),
                  f'planetai radio provision gateway-host "{envget("NODE_NAME", "node")} gateway" GATE --port {port}'))
    if gateways:
        steps.append((service_installed(), "The gateway, always on", "a service that keeps the gateway running after a restart",
                      f"planetai radio gateway --port {port} --install"))
    steps.append((bool(others), "Sensor and shelf radios",
                  (f"{len(others)} provisioned: " + ", ".join(r["name"] for r in others[:4]) + ("…" if len(others) > 4 else "")) if others
                  else "field sensors, relays, and shelf radios that receive alerts when the internet is down",
                  f'planetai radio provision sensor "<the place it stands>" ABC --port {port}'))
    print("Radios for this node, step by step\n")
    for i, (done, title, detail, _) in enumerate(steps, 1):
        print(f"  {'✓' if done else '·'} {i}. {title}: {detail}")
    print("\n  On USB now: " + ("; ".join(f"{d} ({desc})" for d, desc in ports) if ports
          else "no radio. Plug one in by USB (antenna on first), then run this again.\n"
          "    Plugged in and still nothing? The usual four, most likely first: a charge-only cable (try the one that came\n"
          "    with the radio); a Tracker's power switch is off; a XIAO needs BOOT held while it is plugged in; a hub or\n"
          "    dock in between (plug straight into this machine)."))
    todo = [st for st in steps if not st[0]]
    if todo:
        print(f"\nNext: {todo[0][3]}")
        if "/dev/cu.usbmodem…" in todo[0][3]:
            print("      (plug the radio in by USB first; this command then names its port)" if not ports else
                  "      (more than one radio is plugged in: pick its port from the list above)")
    else:
        print("\nEvery step is done. Phones join with  planetai radio url ; check a radio with  planetai radio doctor --port <port>")
    print("Step by step, with what you should see: docs/MESHTASTIC.md")
    return 0


# ---------------------------------------------------------------- CLI
def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="planetai radio", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("init"); s.add_argument("--region"); s.add_argument("--slot", type=int); s.add_argument("--preset", default="LONG_FAST"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("url"); s.add_argument("--json", action="store_true", help="the decoded settings, for a script")
    for name in ("render", "provision"):
        s = sub.add_parser(name); s.add_argument("role"); s.add_argument("long_name"); s.add_argument("short_name")
        s.add_argument("--port"); s.add_argument("--mqtt", help="host:1883 user pass, for gateway-wifi", nargs=3, metavar=("ADDR", "USER", "PASS"))
        s.add_argument("--wifi", help="SSID:PSK, gateway-wifi only")
        s.add_argument("--fixed", help="LAT,LON[,ALT_M]: pin the position of a radio with no GPS (a XIAO sensor node)")
    s = sub.add_parser("gateway"); s.add_argument("--port", required=True); s.add_argument("--broker", default="127.0.0.1:1883"); s.add_argument("--install", action="store_true"); s.add_argument("--once", action="store_true")
    s = sub.add_parser("federate"); s.add_argument("--write", action="store_true")
    s = sub.add_parser("list"); s.add_argument("--port")
    s = sub.add_parser("doctor"); s.add_argument("--port")
    a = ap.parse_args(argv)
    if not a.cmd:
        return guide()

    if a.cmd == "init":
        if FLEET_PATH.exists() and not a.force:
            raise SystemExit(f"{FLEET_PATH} exists. --force makes a new one, and every radio must then be re-provisioned (new keys).")
        city = envget("NODE_CITY")
        region = a.region or CITY_REGION.get(city)
        if not region:   # never guess: a radio on another country's band is illegal there (node #1 got EU_868 in Bali)
            raise SystemExit(f"no radio region for NODE_CITY={city!r}. Say which, e.g.  planetai radio init --region SG_923\n"
                             f"   one of {', '.join(sorted(REGIONS))}")
        f = new_fleet(envget("NODE_NAME", "node"), region, city, a.preset, a.slot)
        save_fleet(f)
        print(f">> fleet for {f['node']}: region {region}, preset {a.preset}, slot {f['slot'] or 'by channel name'}"
              + (f" ({slot_freq(region, f['slot'], a.preset)} MHz)" if f["slot"] else ""))
        print(f"   keys in {FLEET_PATH} (mode 600, gitignored). Next step:  planetai radio")
        return 0
    if a.cmd == "url":
        f = load_fleet(); u = channel_url(f)
        if a.json:
            print(json.dumps({"url": u, **decode_url(u)}, indent=1)); return 0
        print(f"This node's radio channels: region {f['region']}, slot {f.get('slot') or 'by channel name'}; "
              "two channels, planetai (the household's) and fabcity (what other nodes see).\n")
        print("To put a phone on the mesh:")
        print("  1. Install the Meshtastic app (iPhone or Android).")
        print("  2. Pair it with any radio over Bluetooth: the PIN is on the radio's screen, or 123456 on one without a screen.")
        qr = shutil.which("qrencode")
        print(f"  3. Open this link on the phone{', or scan the QR below' if qr else ''}, and accept replacing the channels:\n")
        print(f"     {u}\n")
        if qr:
            subprocess.run(["qrencode", "-t", "ansiutf8", u], check=False)
        else:
            print("     (for a QR here:  brew install qrencode  or  apt install qrencode)")
        print("Radios provisioned with  planetai radio provision  already have these channels; this link is for phones.")
        return 0
    if a.cmd in ("render", "provision"):
        f, profiles = load_fleet(), load_profiles()
        mqtt = {"address": a.mqtt[0], "username": a.mqtt[1], "password": a.mqtt[2]} if a.mqtt else None
        if a.role == "gateway-wifi" and not mqtt:
            mqtt = {"address": f"{lan_ip() or '<node LAN ip>'}:1883", "username": envget("MQTT_USER", "planetai"), "password": envget("MQTT_PASS")}
        wifi = tuple(a.wifi.split(":", 1)) if a.wifi else None
        fixed = None
        if a.fixed:
            try:
                xs = [float(x) for x in a.fixed.split(",")]
                fixed = (xs[0], xs[1], xs[2] if len(xs) > 2 else 0.0)
            except (ValueError, IndexError):
                raise SystemExit("--fixed wants LAT,LON or LAT,LON,ALT_M")
        if a.cmd == "render":
            print(_yaml().safe_dump(render_profile(a.role, a.long_name, a.short_name, f, profiles, mqtt, wifi, fixed), sort_keys=False)); return 0
        if not a.port:
            seen = usb_radios()
            raise SystemExit("--port is needed to provision. " + (
                "On USB now: " + ", ".join(d for d, _ in seen) if seen else "No radio is on USB now: plug one in (antenna on first).")
                + "\n   render shows the profile without a radio.")
        provision(a.port, a.role, a.long_name, a.short_name, f, profiles, mqtt, wifi, fixed=fixed); return 0
    if a.cmd == "gateway":
        if a.install:
            install_service(a.port); print("   Next step:  planetai radio"); return 0
        gateway(a.port, load_fleet(), a.broker, once=a.once); return 0
    if a.cmd == "federate":
        peers = parse_peers(envget("RADIO_PEERS"))
        node = envget("NODE_NAME", "node")
        if not peers:
            print("no peers. In .env:  RADIO_PEERS=menorca=<their tailnet host>:1883:<their MQTT_PASS>,…")
            print(f"what a peer puts in theirs for this node:  {node}=<this node's tailnet host>:1883:{envget('MQTT_PASS') or '<MQTT_PASS>'}")
            return 0
        conf = mosquitto_bridges(node, peers, envget("MQTT_USER", "planetai"))
        if a.write:
            # a subdirectory, because include_dir takes every *.conf in it and mosquitto.conf must not include itself
            d = MOSQ_DIR / "bridges"; d.mkdir(parents=True, exist_ok=True)
            (d / "peers.conf").write_text(conf)
            main_conf = MOSQ_DIR / "mosquitto.conf"
            if main_conf.exists() and "include_dir" not in main_conf.read_text():
                main_conf.write_text(main_conf.read_text().rstrip("\n") + "\ninclude_dir /mosquitto/config/bridges\n")
            print(f">> wrote {d / 'peers.conf'} (a credential: gitignore config/mosquitto/bridges/); restart the broker:  planetai restart")
        else:
            print(conf)
        return 0
    if a.cmd == "list":
        f = load_fleet()
        print(f"{f['node']}: region {f['region']}, slot {f.get('slot') or 'by name'}, {len(f.get('radios', []))} radio(s) provisioned")
        for r in f.get("radios", []):
            print(f"  {r.get('id') or '?':10} {r['role']:13} {r['short']:4} {r['name']}  ({r['provisioned'][:10]})")
        if a.port:
            print(run_cli(a.port, "--nodes"))
        return 0
    if a.cmd == "doctor":
        return doctor(a.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
