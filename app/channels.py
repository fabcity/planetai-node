"""Where an alert goes: Telegram, the LoRa mesh, the Reticulum bridge (LXMF), and Home Assistant over MQTT.

Moved out of app/main.py unchanged (22 Oct 2026). `notify()` is the one call a rule, the report or a route makes; the
mesh and Reticulum get act-level alerts only, Telegram gets everything, and Home Assistant is told separately
(`ha_alert`) and fed readings (`ha_publish`) by the ingest. `mesh_state` is written by the MQTT thread in main, the
same dict, because a downlink needs the root topic an uplink taught it. Home Assistant becomes a pack
(docs/decisions/2026-10-21-core-and-packs.md); until then it lives here with the other ways out.
"""
import json
import logging
import os
import time
import unicodedata
from datetime import datetime, timezone

import httpx

import settings
import sources

log = logging.getLogger("planetai")

NODE = os.getenv("NODE_NAME", "node")
MQTT_HOST = os.getenv("MQTT_HOST", "").strip()
MQTT_USER, MQTT_PASS = os.getenv("MQTT_USER", ""), os.getenv("MQTT_PASS", "")
RETICULUM_URL = os.getenv("RETICULUM_URL", "").strip()


def TG():
    """Token and chat ids, read at send time so the GUI can change them without a restart."""
    return settings.get("TELEGRAM_BOT_TOKEN", "").strip(), [c for c in settings.get("TELEGRAM_CHAT_IDS", "").replace(" ", "").split(",") if c]
def MESH_ALERTS():
    return settings.get("MESH_ALERTS", "0") == "1"
def MESH_GATEWAY_NUM():
    return int(settings.get("MESH_GATEWAY_NODE_NUM", "0") or 0)
def HA_DISCOVERY():
    return settings.get("HA_DISCOVERY", "0") == "1" and bool(os.getenv("MQTT_HOST", "").strip())
_ha_announced: set = set()
mesh_state = {"root_topic": None, "gateway": None, "packets": 0, "last": None}

# Whether the last message to Telegram went through, for GET /health/sources. Kept apart from `state`, which /health
# once spread to every reader at every share level: whether this house's alerts reach it is not theirs to read.
tg_state: dict = {"ok": None, "at": None}


def mesh_send(text: str) -> None:
    """Send `text` over the LoRa mesh via the gateway's MQTT downlink. Needs a root topic learned from an uplink."""
    if not (MQTT_HOST and MESH_ALERTS() and mesh_state["root_topic"]):
        return
    try:
        import paho.mqtt.publish as publish
        topic, payload = sources.meshtastic_downlink(mesh_state["root_topic"], MESH_GATEWAY_NUM(), text)
        publish.single(topic, payload, hostname=MQTT_HOST, auth={"username": MQTT_USER, "password": MQTT_PASS} if MQTT_USER else None)
        log.info("mesh -> sent %d bytes on %s", len(payload), topic)
    except Exception as e:  # noqa: BLE001
        log.warning("mesh send failed: %s", type(e).__name__)


# ---------------------------------------------------------------- Home Assistant (MQTT discovery)
# HA's MQTT integration watches homeassistant/<component>/<id>/config. Publish one config per sensor metric and
# HA creates the entity, grouped under a device per physical sensor. Then publish states. Retained, so HA sees
# them on restart. We publish; HA automates. The node never addresses a device.
HA_UNITS = {"pm25": ("µg/m³", "pm25"), "pm10": ("µg/m³", "pm10"), "pm1": ("µg/m³", "pm1"), "pm25_model": ("µg/m³", "pm25"),
            "temp": ("°C", "temperature"), "temp_model": ("°C", "temperature"), "humidity": ("%", "humidity"),
            "humidity_model": ("%", "humidity"), "pressure": ("kPa", "atmospheric_pressure"), "co2": ("ppm", "carbon_dioxide"),
            "battery_pct": ("%", "battery"), "battery_v": ("V", "voltage"), "aqi": (None, "aqi"),
            "wind_speed": ("km/h", "wind_speed"), "precipitation": ("mm", "precipitation"), "uv_index": (None, None)}


def ha_publish(sensors: list[dict], readings: list[tuple]) -> None:
    if not HA_DISCOVERY() or not readings:
        return
    try:
        import paho.mqtt.publish as publish
        auth = {"username": MQTT_USER, "password": MQTT_PASS} if MQTT_USER else None
        by_id = {s["sensor_id"]: s for s in sensors}
        latest: dict[tuple, tuple] = {}
        for ts, sid, metric, value in readings:
            if (sid, metric) not in latest or ts > latest[(sid, metric)][0]:
                latest[(sid, metric)] = (ts, value)
        msgs = []
        for (sid, metric), (ts, value) in latest.items():
            s = by_id.get(sid, {})
            if not s.get("local", False) and s.get("kind", "sensor") == "sensor":
                continue                                # reference stations are not this house's entities
            uid = f"planetai_{NODE}_{sid}_{metric}".replace("-", "_").replace("/", "_")
            state_topic = f"planetai/{NODE}/{sid}/{metric}"
            if uid not in _ha_announced:
                unit, dclass = HA_UNITS.get(metric, (None, None))
                cfg = {"name": metric.replace("_", " "), "unique_id": uid, "state_topic": state_topic,
                       "state_class": "measurement", "expire_after": 3600,
                       "device": {"identifiers": [f"planetai_{NODE}_{sid}"], "name": s.get("name") or s.get("default_name") or sid,
                                  "manufacturer": "PLANETAI node", "model": s.get("source", "sensor"),
                                  "suggested_area": "Indoor" if s.get("indoor") else "Outdoor"}}
                if unit: cfg["unit_of_measurement"] = unit
                if dclass: cfg["device_class"] = dclass
                msgs.append({"topic": f"homeassistant/sensor/{uid}/config", "payload": json.dumps(cfg), "retain": True})
                _ha_announced.add(uid)
            msgs.append({"topic": state_topic, "payload": f"{value:g}", "retain": True})
        if msgs:
            publish.multiple(msgs, hostname=MQTT_HOST, auth=auth)
    except Exception as e:  # noqa: BLE001
        log.warning("home assistant publish failed: %s", type(e).__name__)


def ha_alert(level: str, text: str, alert_id: int | None) -> None:
    """One text sensor per node carrying the latest alert, with level and id as attributes."""
    if not HA_DISCOVERY():
        return
    try:
        import paho.mqtt.publish as publish
        auth = {"username": MQTT_USER, "password": MQTT_PASS} if MQTT_USER else None
        uid = f"planetai_{NODE}_alert".replace("-", "_")
        msgs = []
        if uid not in _ha_announced:
            msgs.append({"topic": f"homeassistant/sensor/{uid}/config", "retain": True, "payload": json.dumps({
                "name": "latest alert", "unique_id": uid, "state_topic": f"planetai/{NODE}/alert",
                "json_attributes_topic": f"planetai/{NODE}/alert/attributes", "icon": "mdi:bell-alert",
                "device": {"identifiers": [f"planetai_{NODE}"], "name": f"PLANETAI {NODE}", "manufacturer": "PLANETAI node"}})})
            _ha_announced.add(uid)
        msgs.append({"topic": f"planetai/{NODE}/alert", "payload": text.split("\n")[0][:255], "retain": True})
        msgs.append({"topic": f"planetai/{NODE}/alert/attributes", "retain": True,
                     "payload": json.dumps({"level": level, "alert_id": alert_id, "ts": datetime.now(timezone.utc).isoformat()})})
        publish.multiple(msgs, hostname=MQTT_HOST, auth=auth)
    except Exception as e:  # noqa: BLE001
        log.warning("home assistant alert publish failed: %s", type(e).__name__)


def notify(level: str, text: str, keyboard: list | None = None, home: str = "", home_before_last: bool = False) -> None:
    """Send an alert. `home` is a line for the household's own Telegram only (who in this house it matters to,
    learn.alert_line; the report's morning memory): never the mesh, Reticulum or the log, which other people and
    machines can read. It goes at the end, or above the last paragraph with `home_before_last` (the report's
    invitation stays its last line)."""
    # One sign per message (design review, 14 Oct): a text that opens with its own (📈, ✅, the report's 🌡️) is not
    # given the level's as well; node #1 sent "ℹ️ 🌡️ It is hot inside".
    icon = "" if text[:1] and unicodedata.category(text[0]) == "So" else {"info": "ℹ️", "warn": "⚠️", "act": "🔴"}.get(level, "")
    log.info("ALERT [%s] %s", level, text)
    if level == "act":
        mesh_send(text.split("\n")[0])            # the mesh gets the first line only: LoRa frames are small
        if RETICULUM_URL:
            try:
                httpx.post(f"{RETICULUM_URL}/send", json={"text": text}, timeout=10)
            except Exception as e:  # noqa: BLE001
                log.warning("reticulum send failed: %s", type(e).__name__)
    tok, chats = TG()
    if not tok or not chats:
        return
    for chat in chats:
        try:
            said = f"{icon} {text}".strip()
            head, sep, last = said.rpartition("\n\n") if home and home_before_last else ("", "", said)
            body = {"chat_id": chat, "text": f"{head}\n\n{home}\n\n{last}" if sep else said + (f"\n\n{home}" if home else "")}
            if keyboard:
                body["reply_markup"] = {"inline_keyboard": keyboard}
            httpx.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                       json=body, timeout=15).raise_for_status()
            log.info("telegram -> %s ok", chat)
            tg_state.update(ok=True, at=time.time())
        except Exception as e:  # noqa: BLE001
            # never interpolate the exception's URL: httpx puts the token in it
            log.warning("telegram -> %s failed: %s", chat, type(e).__name__)
            tg_state.update(ok=False, at=time.time())
