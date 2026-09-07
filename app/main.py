"""planetai-node. One process:
  poll sources → postgres   (every POLL_SECONDS)
  run rules.yml (SQL) → telegram/log   (every 60s, cooldown enforced in SQL against the alerts table)
  write one report every REPORT_EVERY hours from REPORT_ANCHOR, in local time; the `reports` row is the lock
  push hourly aggregates to PARENT_API_URL if set   (every hour)
  answer HTTP: /health /sensors /readings /stats /observations /alerts /aggregates /cells /rho /packs
              /report/latest · /report/bundle (read-only token) · POST /report/now (admin token)
              POST /aggregates (parent side, token) · POST /actions (ρ) · POST /readings (downstream contributors, admin token)
"""
from __future__ import annotations

import json
from zoneinfo import ZoneInfo
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psycopg
import yaml
from fastapi import FastAPI, Header, HTTPException, Query
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import bootstrap
import agent
import ground
import index
import packs
import report
import settings
import sources

log = logging.getLogger("planetai")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
# httpx logs every request URL at INFO. Telegram carries the bot token IN THE URL, so that would put a live
# credential in the logs, in `docker compose logs`, and in every screenshot anyone pastes for support. Off.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

DB = os.environ["DATABASE_URL"]
NODE = os.getenv("NODE_NAME", "node")
POLL = int(os.getenv("POLL_SECONDS", "300"))
def TG():
    """Token and chat ids, read at send time so the GUI can change them without a restart."""
    return settings.get("TELEGRAM_BOT_TOKEN", "").strip(), [c for c in settings.get("TELEGRAM_CHAT_IDS", "").replace(" ", "").split(",") if c]
def LOCALE():
    return settings.get("ALERT_LOCALE", "en")
def PARENT():
    return settings.get("PARENT_API_URL", "").strip()
MQTT_HOST = os.getenv("MQTT_HOST", "").strip()                 # set by `planetai meshtastic`; empty = no MQTT thread
MQTT_USER, MQTT_PASS = os.getenv("MQTT_USER", ""), os.getenv("MQTT_PASS", "")
def MESH_INDOOR():
    return {x.strip() for x in settings.get("MESH_INDOOR_NODES", "").split(",") if x.strip()}
def MESH_ALERTS():
    return settings.get("MESH_ALERTS", "0") == "1"
def MESH_GATEWAY_NUM():
    return int(settings.get("MESH_GATEWAY_NODE_NUM", "0") or 0)
def AGG_TOKEN():
    return settings.get("AGGREGATE_TOKEN", "").strip()
def PARENT_TOKEN():
    return settings.get("PARENT_TOKEN", "").strip()
def HA_DISCOVERY():
    return settings.get("HA_DISCOVERY", "0") == "1" and bool(os.getenv("MQTT_HOST", "").strip())
_ha_announced: set = set()
RETICULUM_URL = os.getenv("RETICULUM_URL", "").strip()       # the reticulum bridge, e.g. http://reticulum:4243
mesh_state = {"root_topic": None, "gateway": None, "packets": 0, "last": None}
RULES = Path(os.getenv("RULES_PATH", "/app/config/rules.yml"))
STARTED = time.time()
state = {"polls": 0, "last_poll": None, "last_error": None, "ingested": 0}


NODE_TZ = os.getenv("NODE_TZ", "").strip() or "UTC"


def db():
    # Rules and cells use `current_setting('TimeZone')` to find local midnight and local hours. Postgres defaults
    # to UTC, which put day boundaries and "evening" eight hours out in Bali. Set the session timezone from
    # NODE_TZ, in the connection options so it costs no extra round trip.
    # also hand the node's coordinates to SQL as custom settings, so rules can rank references by distance
    lat, lon = os.getenv("NODE_LAT", "0") or "0", os.getenv("NODE_LON", "0") or "0"
    return psycopg.connect(DB, row_factory=dict_row, autocommit=True,
                           options=f"-c timezone={NODE_TZ} -c planetai.lat={lat} -c planetai.lon={lon}")


# ---------------------------------------------------------------- ingest
def poll_once(hc: httpx.Client) -> None:
    errors: list[str] = []
    with db() as con:
        for name, fn in sources.enabled(hc):
            try:
                sensors, readings = fn()
            except Exception as e:  # noqa: BLE001
                errors.append(f"{name}: {str(e).splitlines()[0]}")
                log.warning("source %s failed: %s", name, e)
                continue
            lat_env, lon_env = os.getenv("NODE_LAT"), os.getenv("NODE_LON")
            sources.stamp_local(sensors, float(lat_env) if lat_env else None, float(lon_env) if lon_env else None,
                                 float(settings.get("LOCAL_RADIUS_M") or 500))
            with con.cursor() as cur:
                for s in sensors:
                    cur.execute(
                        """INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind, scale, cadence, meta)
                           VALUES (%(sensor_id)s, %(source)s, %(name)s, %(lat)s, %(lon)s, %(indoor)s, %(local)s,
                                   %(kind)s, %(scale)s, %(cadence)s, %(meta)s)
                           ON CONFLICT (sensor_id) DO UPDATE SET name=EXCLUDED.name, lat=EXCLUDED.lat, lon=EXCLUDED.lon,
                             indoor=EXCLUDED.indoor, local=EXCLUDED.local, kind=EXCLUDED.kind, scale=EXCLUDED.scale,
                             cadence=EXCLUDED.cadence, meta=EXCLUDED.meta""",
                        {"kind": "sensor", "scale": os.getenv("NODE_SCALE", "community"), "cadence": None,
                         **s, "meta": Jsonb(s.get("meta") or {})},
                    )
                if readings:
                    cur.executemany(
                        "INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        readings,
                    )
                    state["ingested"] += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            log.info("%s: %d sensors, %d readings", name, len(sensors), len(readings))
            ha_publish(sensors, readings)
    state["polls"] += 1
    state["last_poll"] = datetime.now(timezone.utc).isoformat()
    state["last_error"] = " | ".join(errors) if errors else None   # clears when every source succeeds


# ---------------------------------------------------------------- MQTT ingest (Meshtastic gateway, DIY pods)
def _store(sensors, readings) -> None:
    lat_env, lon_env = os.getenv("NODE_LAT"), os.getenv("NODE_LON")
    sources.stamp_local(sensors, float(lat_env) if lat_env else None, float(lon_env) if lon_env else None,
                         float(settings.get("LOCAL_RADIUS_M") or 500))
    with db() as con, con.cursor() as cur:
        for s in sensors:
            cur.execute("""INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind, scale, cadence, meta)
                           VALUES (%(sensor_id)s,%(source)s,%(name)s,%(lat)s,%(lon)s,%(indoor)s,%(local)s,%(kind)s,%(scale)s,%(cadence)s,%(meta)s)
                           ON CONFLICT (sensor_id) DO UPDATE SET
                             name = COALESCE(EXCLUDED.name, sensors.name),
                             lat = COALESCE(EXCLUDED.lat, sensors.lat), lon = COALESCE(EXCLUDED.lon, sensors.lon),
                             indoor = EXCLUDED.indoor, local = EXCLUDED.local, meta = sensors.meta || EXCLUDED.meta""",
                        {**s, "meta": Jsonb(s.get("meta") or {})})
        if readings:
            cur.executemany("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", readings)
            state["ingested"] += max(cur.rowcount or 0, 0)      # rowcount, not len: duplicates are dropped
    ha_publish(sensors, readings)


def mqtt_thread() -> None:
    """Subscribe to everything under msh/ (Meshtastic) and planetai/ (DIY pods) and store what parses."""
    import paho.mqtt.client as mqtt

    def on_connect(c, u, flags, rc, props=None):
        c.subscribe([("msh/#", 0), ("planetai/sensors/#", 0)])
        log.info("mqtt: connected to %s, subscribed msh/# and planetai/sensors/#", MQTT_HOST)

    def on_message(c, u, msg):
        try:
            if msg.topic.startswith("msh/"):
                sensors, readings, info = sources.meshtastic_message(msg.topic, msg.payload, MESH_INDOOR())
                if info.get("root_topic"):
                    mesh_state.update({"root_topic": info["root_topic"], "gateway": info.get("gateway"),
                                       "packets": mesh_state["packets"] + 1, "last": datetime.now(timezone.utc).isoformat()})
                if sensors or readings:
                    _store(sensors, readings)
            elif msg.topic.startswith("planetai/sensors/"):
                # planetai/sensors/<id>/<metric>  {"value": 12.3, "ts": "...", "indoor": false}
                _, _, sid, metric = msg.topic.split("/", 3)
                body = json.loads(msg.payload)
                ts = datetime.fromisoformat(str(body["ts"]).replace("Z", "+00:00")) if body.get("ts") else datetime.now(timezone.utc)
                _store([{"sensor_id": f"pod-{sid}", "source": "mqtt", "name": f"pod {sid}", "lat": None, "lon": None,
                         "indoor": bool(body.get("indoor", False)), "local": True, "kind": "sensor", "scale": "community",
                         "cadence": None, "meta": {"topic": msg.topic}}],
                       [(ts, f"pod-{sid}", metric, float(body["value"]))])
        except Exception as e:  # noqa: BLE001
            log.debug("mqtt message on %s ignored: %s", msg.topic, e)

    while True:
        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"planetai-{NODE}")
            if MQTT_USER:
                c.username_pw_set(MQTT_USER, MQTT_PASS)
            c.on_connect, c.on_message = on_connect, on_message
            c.connect(MQTT_HOST, 1883, keepalive=60)
            c.loop_forever(retry_first_connection=True)
        except Exception as e:  # noqa: BLE001
            log.warning("mqtt: %s — retrying in 15s", e)
            time.sleep(15)


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
                       "device": {"identifiers": [f"planetai_{NODE}_{sid}"], "name": s.get("name") or sid,
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


# ---------------------------------------------------------------- rules → alerts
def load_rules() -> list[dict]:
    try:
        core = yaml.safe_load(RULES.read_text()) or []
    except FileNotFoundError:
        core = []
    return core + packs.alerts()      # a pack rule with `contributes:` is part of the report, not an alert


def _local_now() -> datetime:
    """The node's own clock. Everything a person is told about time uses this, never UTC: a 'good morning' that arrives
    at one in the afternoon is the bug this exists to prevent."""
    try:
        return datetime.now(ZoneInfo(NODE_TZ))
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _hours(key: str, default: str) -> list[int]:
    return [int(x) for x in (settings.get(key, default) or default).replace(" ", "").split(",") if x.strip().isdigit()]


def _quiet(level: str) -> bool:
    """During quiet hours only act-level alerts go out; the rest wait for the next briefing. 22:00-06:00 by default."""
    if settings.get("QUIET_HOURS", "1") != "1" or level == "act":
        return False
    h = _local_now().hour
    a, b = _hours("QUIET_FROM", "22")[0], _hours("QUIET_TO", "6")[0]
    return (a <= h or h < b) if a > b else (a <= h < b)


def act_hint(alert_id) -> str:
    """How this household closes the loop on alert N. `/act N` is a reply to the Telegram bot, which exists only when the
    agent container runs (planetai agent local); on every other node the words are `planetai act N`. A tester who
    replied /act to a bot that was not there heard nothing back (BETA review, 8.2)."""
    bot = "agent" in os.getenv("COMPOSE_PROFILES", "")
    return f"/act {alert_id}" if bot else f"planetai act {alert_id}"


def _report_every() -> int:
    """Hours between reports. A value the scheduler cannot honour (one that does not divide 24, so the rhythm walks
    round the clock) falls back to six rather than making the node quiet: settings.set refuses those, but .env is
    edited by hand."""
    v = str(settings.num("REPORT_EVERY", 6))
    return int(v) if v in settings.CHOICES["REPORT_EVERY"] else 6


def _report_hours() -> list[int]:
    return report.due_hours(_report_every(), settings.num("REPORT_ANCHOR", 6))


def _held_hours(cur, due, every: int) -> int:
    """How many hours of held reports this one has to fold in. The window a household last actually read ended at
    the newest sent report; if none was ever sent, at the start of the oldest held one."""
    # coalesce(due_local, ts): a report written on request has no due hour, but it did go out and it did cover a
    # window, so it ends the held stretch. Without this a forced report at two in the morning left the night to be
    # folded into the six o'clock one as well, and the household read it twice.
    cur.execute("""SELECT coalesce(max(coalesce(due_local, ts)) FILTER (WHERE sent),
                            min(coalesce(due_local, ts)) FILTER (WHERE held_quiet) - make_interval(hours => %(every)s)) AS since
                     FROM reports""", {"every": every})
    return report.held_hours((cur.fetchone() or {}).get("since"), due, every)


def run_report(cur) -> None:
    """The node's one scheduled message. Called from run_rules, before the rules, every 60 seconds.

    The `reports` row is the lock, not a timer in memory: the node writes the row for this local hour and will not
    write a second one for the same hour, so a container that restarts inside the twenty-minute window does not
    send the report twice. That is what the old briefings got wrong in the other direction — they asked `alerts`,
    where every rule also writes.

    A report due inside quiet hours is written and stored and not sent. The next one covers both windows, so the
    night is in the morning's report rather than lost."""
    now = _local_now()
    if now.hour not in _report_hours() or now.minute >= 20:
        return
    due = now.replace(minute=0, second=0, microsecond=0)
    cur.execute("SELECT 1 FROM reports WHERE due_local = %s LIMIT 1", (due,))
    if cur.fetchone():
        return

    every = _report_every()
    held = _held_hours(cur, due, every)
    b = report.bundle(cur, every, held_hours=held)
    text = report.sheet(b, LOCALE())
    quiet = _quiet("info")
    cur.execute("""INSERT INTO reports (due_local, window_hours, depth, rung, text, sheet, sent, held_quiet, cells)
                   VALUES (%s, %s, 'sheet', 'node', %s, %s, %s, %s, %s) RETURNING id""",
                (due, every + held, text, text, not quiet, quiet, Jsonb(b.get("cells") or [])))
    rid = cur.fetchone()["id"]
    if quiet:
        log.info("report %d written and held for quiet hours: %d hours will be folded into the next one", rid, every + held)
        return
    notify("info", text)          # Telegram and Home Assistant. The mesh and Reticulum carry act alerts only.
    ha_alert("info", text, None)
    log.info("report %d sent: %d hours, %d words", rid, every + held, len(text.split()))


def run_rules() -> None:
    rules = load_rules()
    with db() as con, con.cursor() as cur:
        try:
            run_report(cur)
        except Exception as e:  # noqa: BLE001
            log.warning("report failed: %s", e)
        for rule in rules:
            try:
                rows = index.run_ro(cur, rule["sql"])      # as planetai_ro: a rule can read everything but settings, and write nothing
            except Exception as e:  # noqa: BLE001
                log.warning("rule %s failed: %s", rule.get("id"), e)
                continue
            for row in rows:
                sid = str(row.get("sensor_id", "node"))
                cur.execute(
                    "SELECT 1 FROM alerts WHERE rule_id=%s AND sensor_id=%s AND ts > now() - make_interval(mins => %s) LIMIT 1",
                    (rule["id"], sid, int(rule.get("cooldown_minutes", 60))),
                )
                if cur.fetchone():
                    continue
                msg = rule["message"]
                tmpl = msg.get(LOCALE()) or msg.get("en") if isinstance(msg, dict) else str(msg)
                try:
                    text = tmpl.format(**{k: ("—" if v is None else v) for k, v in row.items()})
                except (KeyError, ValueError, TypeError):
                    text = tmpl
                level = rule.get("level", "info")
                cur.execute("INSERT INTO alerts (rule_id, sensor_id, level, text) VALUES (%s,%s,%s,%s) RETURNING id", (rule["id"], sid, level, text))
                alert_id = cur.fetchone()["id"]
                # what interrupts a person: act always; warn if ALERT_LEVEL allows; info only in a briefing (it is
                # recorded either way, and appears on the dashboard). Quiet hours hold everything but act.
                floor = {"act": 2, "warn": 1, "info": 0}
                send = floor.get(level, 0) >= floor.get(settings.get("ALERT_LEVEL", "act"), floor["act"]) and not _quiet(level)
                if send:
                    # No id, and nothing asking to be told. The node watches what happens next (v0.39) instead of
                    # asking; a number a household is expected to quote back was a chore, and 15 of node #1's 37
                    # act alerts got an answer, nine of them in two dashboard batch-clicks a day later.
                    notify(level, text)
                ha_alert(level, text, alert_id)


def notify(level: str, text: str) -> None:
    icon = {"info": "ℹ️", "warn": "⚠️", "act": "🔴"}.get(level, "")
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
            httpx.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                       json={"chat_id": chat, "text": f"{icon} {text}".strip()}, timeout=15).raise_for_status()
            log.info("telegram -> %s ok", chat)
        except Exception as e:  # noqa: BLE001
            # never interpolate the exception's URL: httpx puts the token in it
            log.warning("telegram -> %s failed: %s", chat, type(e).__name__)


# ---------------------------------------------------------------- hourly push (child → parent)
def push_aggregates() -> None:
    if not PARENT():          # the function, not the setting: a bare PARENT is always truthy
        return
    with db() as con, con.cursor() as cur:
        cur.execute("SELECT bucket, sensor_id, metric, mean, min, max, n FROM readings_1h WHERE bucket > now() - interval '2 hours'")
        rows = [{**r, "bucket": r["bucket"].isoformat()} for r in cur.fetchall()]
    try:
        httpx.post(f"{PARENT()}/aggregates", json={"node": NODE, "rows": rows, "scale": os.getenv("NODE_SCALE", "community")},
                   headers={"Authorization": f"Bearer {PARENT_TOKEN()}"} if PARENT_TOKEN() else {},
                   timeout=30).raise_for_status()
        log.info("pushed %d hourly rows to parent", len(rows))
    except Exception as e:  # noqa: BLE001
        log.warning("push to parent failed: %s", e)


# ---------------------------------------------------------------- loops
def loop(fn, every: int, delay: int = 0):
    """Run fn forever. Each loop records its own last error under its own name: poll_once clears `last_error`
    when every source succeeds, so sharing that key would let a permanently broken rules thread look healthy."""
    name = getattr(fn, "__name__", "loop")
    state.setdefault("errors", {})

    def run():
        time.sleep(delay)
        while True:
            try:
                fn()
                state["errors"].pop(name, None)
            except Exception as e:  # noqa: BLE001
                state["errors"][name] = str(e).splitlines()[0]
                log.exception("%s failed: %s", name, e)
            time.sleep(every)

    threading.Thread(target=run, daemon=True, name=name).start()


hc = httpx.Client(timeout=60, headers={"User-Agent": f"planetai-node/{NODE}"})


def bootstrap_once() -> None:
    """Fill the database from free global sources the first time this node starts. See app/bootstrap.py."""
    if os.getenv("BOOTSTRAP", "1") != "1" or not os.getenv("NODE_LAT"):
        return
    with db() as con, con.cursor() as cur:
        # "already bootstrapped" means model history exists, not "any row": the wizard recreates the app container
        # seconds after the first start, and a poll that landed before the kill left 14 rows that skipped this forever
        cur.execute("SELECT count(*) AS n FROM readings WHERE sensor_id='cams-point' AND ts < now() - interval '2 days'")
        if (cur.fetchone() or {}).get("n"):
            return
        log.info("first start: bootstrapping from global open data (no sensor needed)")
        state["bootstrap"] = bootstrap.run(con, hc, float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"]))
try:
    bootstrap_once()
except Exception as e:  # noqa: BLE001  — never block startup on it
    log.warning("bootstrap failed: %s", e)

try:
    _moved = settings.migrate_briefings()
    if _moved:
        log.info("moved off the old briefing settings: %s. BRIEFINGS, BRIEF_MORNING and BRIEF_EVENING stay in place and are ignored",
                 ", ".join(f"{k}={v}" for k, v in sorted(_moved.items())))
        # ALERT_LEVEL is not moved. An update adds keys a .env is missing and never overwrites one it has, which is
        # why nothing a household chose has ever changed underneath it — and it means the new `act` default reaches
        # only a fresh install. Say so once, with the one command, rather than deciding for them.
        if settings.get("ALERT_LEVEL", "act") == "warn":
            log.info("ALERT_LEVEL is still warn, so warn-level alerts still reach the phone between reports. "
                     "`planetai report level act` leaves them to the report; nothing is lost either way")
except Exception as e:  # noqa: BLE001  — never block startup on it
    log.warning("could not move off the old briefing settings: %s", e)

def load_channel_roles() -> int:
    """Declarations are the file's, not the database's: replace the table on every start so a removed pack's
    claims go with it."""
    rows = packs.channels()
    with db() as con, con.cursor() as cur:
        # db() is autocommit, so the delete and the reinsert must share one explicit transaction block —
        # otherwise the DELETE commits alone and a concurrent reader can see an empty table mid-restart.
        with con.transaction():
            cur.execute("DELETE FROM channel_roles")
            cur.executemany(
                """INSERT INTO channel_roles (source, metric, role, comparable, unit, reference, declared_by)
                   VALUES (%(source)s,%(metric)s,%(role)s,%(comparable)s,%(unit)s,%(reference)s,%(declared_by)s)""",
                rows)
    log.info("channel roles: %d declared", len(rows))
    return len(rows)


try:
    load_channel_roles()
except Exception as e:  # noqa: BLE001  — a node whose schema predates 0.22 has no channel_roles table yet
    log.warning("channel roles: %s", e)

if MQTT_HOST:
    threading.Thread(target=mqtt_thread, daemon=True, name="mqtt").start()

def poll_sources() -> None:
    poll_once(hc)


loop(poll_sources, POLL, delay=2)
loop(run_rules, 60, delay=30)
loop(push_aggregates, 3600, delay=120)

# ---------------------------------------------------------------- http
from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(app):
    # the MCP session manager must run for the life of the process
    async with agent.mcp.session_manager.run():
        yield


app = FastAPI(title="planetai-node", lifespan=_lifespan)


@app.middleware("http")
async def _mcp_auth(request, call_next):
    """/mcp is the agent surface. Reads through it are the same data the open API serves, but the tools can also write,
    so the whole surface needs the admin token. X-Agent names the caller for the audit trail."""
    if request.url.path.startswith("/mcp"):
        tok = os.getenv("ADMIN_TOKEN", "").strip()
        auth = request.headers.get("authorization", "")
        if not tok or not _bearer_ok(auth, tok):
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "the agent surface needs Authorization: Bearer <ADMIN_TOKEN>"}, status_code=401)
    return await call_next(request)


for _r in agent.http_routes():        # MCP at exactly /mcp, no trailing-slash redirect
    app.router.routes.append(_r)


def q(sql: str, *args):
    with db() as con, con.cursor() as cur:
        cur.execute(sql, args)
        return [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in cur.fetchall()]


@app.get("/health")
def health():
    schema = None
    try:
        with db() as con, con.cursor() as cur:
            # latest applied, not the lexically largest: '0.4' > '0.14' as text
            cur.execute("SELECT version AS v FROM schema_version ORDER BY applied_at DESC, string_to_array(version,'.')::int[] DESC LIMIT 1")
            schema = (cur.fetchone() or {}).get("v")
    except Exception:  # noqa: BLE001 — a pre-0.4 node has no schema_version table until it updates
        schema = "pre-0.4 (run ./update.sh)"
    return {"ok": state["last_poll"] is not None, "node": NODE, "version": os.getenv("NODE_VERSION", "?"),
            "schema": schema, "uptime_s": int(time.time() - STARTED), "lat": float(os.getenv("NODE_LAT", 0) or 0), "lon": float(os.getenv("NODE_LON", 0) or 0), "city": os.getenv("NODE_CITY", ""), **state,
            "cell": _cell(), **({"mesh": mesh_state} if MQTT_HOST else {})}


def _cell() -> dict | None:
    """The H3 cell this node stands in: id, resolution, the mean edge of this cell in metres, and the
    line the dashboard prints under the hero. None before setup, when there is no place to name."""
    lat, lon = os.getenv("NODE_LAT", ""), os.getenv("NODE_LON", "")
    if not lat or not lon:
        return None
    try:
        return ground.facts(float(lat), float(lon))
    except Exception as e:  # noqa: BLE001
        log.warning("cell: %s: %s", type(e).__name__, e)
        return None


@app.get("/sensors")
def sensors_():
    return q("SELECT * FROM sensors ORDER BY local DESC, name")


@app.get("/readings")
def readings(sensor_id: str | None = None, metric: str | None = None, limit: int = Query(200, ge=1, le=10000)):
    # the NULL parameters need a type or Postgres cannot plan the query (500 on every call since psycopg 3)
    return q("SELECT ts, sensor_id, metric, value FROM readings WHERE (%s::text IS NULL OR sensor_id=%s::text) AND (%s::text IS NULL OR metric=%s::text) ORDER BY ts DESC LIMIT %s",
             sensor_id, sensor_id, metric, metric, limit)


@app.get("/stats")
def stats():
    """Rolling 15m/1h/24h — sensors only. Slow sources (portals, models, surveys) are in /observations."""
    return q("SELECT * FROM stats ORDER BY local DESC, sensor_id, metric")


@app.get("/trust")
def trust():
    """One row per local sensor, for the dashboard's trust card and the agent's health check — never both computing
    it themselves and drifting apart from packs/trust/rules.yml. coverage_7d is the percentage of the last 168
    hourly buckets its ambient channels reported in, same arithmetic as the coverage_low rule. frozen_channels
    counts its ambient/enclosure channels that match all three of channel_dead's conditions: flat for 6+ hours in
    the last 24, still flat in the latest bucket, AND the kit itself still producing raw readings in the last 2
    hours (the `alive` CTE below) — a channel whose kit has gone dark entirely is not "frozen", it is offline, and
    channel_dead would never fire for it. age_hours is how long since its first ever reading: under 168, the
    sensor has not lived a full week yet, so a low coverage_7d there is not a fault, just an incomplete week."""
    return q("""
        WITH ours AS (
          SELECT r.sensor_id, r.metric
          FROM readings_1h r JOIN sensors s USING (sensor_id)
          JOIN channel_roles c ON c.source = s.source AND c.metric = r.metric
          WHERE s.local AND s.kind = 'sensor' AND c.role IN ('ambient', 'enclosure')
          GROUP BY 1, 2),
        frozen_stat AS (
          SELECT o.sensor_id, o.metric,
                 max(r.bucket) AS last_bucket,
                 max(r.bucket) FILTER (WHERE r.max - r.min = 0) AS last_flat_bucket,
                 count(*) FILTER (WHERE r.max - r.min = 0) AS flat_hours
          FROM ours o JOIN readings_1h r ON r.sensor_id = o.sensor_id AND r.metric = o.metric
          WHERE r.bucket > now() - interval '24 hours'
          GROUP BY 1, 2),
        alive AS (
          SELECT sensor_id, max(ts) AS kit_ts FROM readings
          WHERE ts > now() - interval '2 hours' GROUP BY 1),
        frozen AS (
          SELECT fs.sensor_id, count(*) AS frozen_channels
          FROM frozen_stat fs JOIN alive a USING (sensor_id)
          WHERE fs.flat_hours >= 6 AND fs.last_bucket = fs.last_flat_bucket
          GROUP BY 1),
        have AS (
          SELECT r.sensor_id, count(DISTINCT r.bucket) AS hours
          FROM readings_1h r JOIN sensors s USING (sensor_id)
          JOIN channel_roles c ON c.source = s.source AND c.metric = r.metric
          WHERE s.local AND s.kind = 'sensor' AND c.role = 'ambient' AND c.comparable
            AND r.bucket > now() - interval '7 days'
          GROUP BY 1),
        age AS (SELECT sensor_id, extract(epoch FROM now() - min(ts)) / 3600 AS age_hours FROM readings GROUP BY 1)
        SELECT s.sensor_id, s.name,
               round(100.0 * coalesce(h.hours, 0) / 168) AS coverage_7d,
               coalesce(f.frozen_channels, 0) AS frozen_channels,
               round(coalesce(a.age_hours, 0)) AS age_hours
        FROM sensors s LEFT JOIN have h USING (sensor_id) LEFT JOIN frozen f USING (sensor_id) LEFT JOIN age a USING (sensor_id)
        WHERE s.local AND s.kind = 'sensor'
        ORDER BY s.name
    """)


@app.get("/nearby")
def nearby(audit: bool = False):
    """The ring: other people's stations around this node, and where this node sits inside it.

    `?audit=1` calls the archive and returns a verdict for every station it lists, which is the same answer
    `planetai run nearby stations` prints. Without it this reads only what is already stored, so the dashboard
    never waits on someone else's server.

    A station excluded after it was already stored keeps its row and stops getting readings, so `reporting` goes
    false and it leaves the ring's numbers within two hours on its own. The row is left alone rather than deleted:
    what it measured while it was in the ring was still measured.
    """
    ring = q("""
        SELECT s.sensor_id, s.name, s.lat, s.lon, s.indoor, s.meta->>'network' AS network,
               round((s.meta->>'km')::numeric, 2) AS km,
               round(st.mean_1h::numeric, 1) AS pm25,
               round(st.silent_minutes::numeric) AS silent_minutes, st.last_ts,
               (st.silent_minutes IS NOT NULL AND st.silent_minutes < 120) AS reporting
        FROM sensors s LEFT JOIN stats st
          ON st.sensor_id = s.sensor_id AND st.metric = 'pm25'
        WHERE s.source = 'baliairdispatch' AND NOT s.local
          -- a station excluded after it was stored keeps its row but stops getting readings. Drop it from the
          -- list after a day rather than leaving it on the card as a neighbour that never answers.
          AND st.last_ts > now() - interval '24 hours'
        ORDER BY (s.meta->>'km')::numeric NULLS LAST""")
    shape = q("""
        WITH ring AS (
          SELECT st.mean_1h AS pm,
                 sqrt(power((st.lat - current_setting('planetai.lat')::float) * 111320, 2)
                    + power((st.lon - current_setting('planetai.lon')::float) * 111320
                            * cos(radians(current_setting('planetai.lat')::float)), 2)) / 1000 AS km
          FROM stats st JOIN sensors sn USING (sensor_id)
          WHERE sn.source = 'baliairdispatch' AND NOT st.local AND NOT st.indoor AND st.kind = 'sensor' AND st.metric = 'pm25'
            AND st.mean_1h IS NOT NULL AND st.silent_minutes < 120 AND st.lat IS NOT NULL),
        mine AS (
          SELECT avg(mean_1h) AS pm, count(*) AS n FROM stats
          WHERE local AND NOT indoor AND kind = 'sensor' AND metric = 'pm25'
            AND mean_1h IS NOT NULL AND silent_minutes < 120)
        SELECT (SELECT count(*) FROM ring)                                                        AS stations,
               (SELECT round(min(pm)::numeric, 1) FROM ring)                                      AS lowest,
               (SELECT round(percentile_cont(0.25) WITHIN GROUP (ORDER BY pm)::numeric, 1) FROM ring) AS p25,
               (SELECT round(percentile_cont(0.5)  WITHIN GROUP (ORDER BY pm)::numeric, 1) FROM ring) AS median,
               (SELECT round(percentile_cont(0.75) WITHIN GROUP (ORDER BY pm)::numeric, 1) FROM ring) AS p75,
               (SELECT round(max(pm)::numeric, 1) FROM ring)                                      AS highest,
               (SELECT round(min(km)::numeric, 1) FROM ring)                                      AS nearest_km,
               (SELECT round(pm::numeric, 1) FROM mine)                                           AS mine,
               (SELECT n FROM mine)                                                               AS mine_sensors""")
    out = {"ring": ring, **(shape[0] if shape else {}),
           "radius_km": float(settings.get("BAD_RADIUS_KM", "15")),
           "attribution": ["Bali Air Dispatch, baliairdispatch.com",
                           "and the network named in each station's `network` field"]}
    m, med = out.get("mine"), out.get("median")
    out["mine_minus_ring"] = None if m is None or med is None else round(float(m) - float(med), 1)
    if audit:
        try:
            import sources
            hc = httpx.Client(timeout=30, headers={"user-agent": "planetai-node"})
            rows = hc.get(sources.BAD_LATEST).json().get("readings", [])
            ids = {int(x) for x in settings.get("SC_DEVICES", "").replace(" ", "").split(",") if x}
            if settings.get("SC_USER", "").strip():
                ids |= set(sources.smartcitizen_account(hc, settings.get("SC_USER").strip()))
            own = {f"sc-{i}" for i in ids}
            own |= {f"ag-{h.replace('.local', '').replace('airgradient_', '')}"
                    for h in settings.get("AIRGRADIENT_HOSTS", "").replace(" ", "").split(",") if h}
            byhand = {x for x in settings.get("BAD_EXCLUDE", "").replace(" ", "").split(",") if x}
            lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
            out["audit"] = [{"station_id": r["station_id"], "name": r.get("name"), "network": r.get("source"),
                             "km": None if r.get("latitude") is None else round(sources.km(lat, lon, r["latitude"], r["longitude"]), 2),
                             "verdict": v}
                            for r, v in sources.bad_verdicts(rows, lat, lon, out["radius_km"], own, byhand,
                                                             float(settings.get("BAD_MIN_SEPARATION_M", "150")),
                                                             settings.get("BAD_INCLUDE_INDOOR", "0") == "1")]
        except Exception as e:  # noqa: BLE001  — a source that is down must not take the endpoint down
            out["audit_error"] = f"{type(e).__name__}: {str(e)[:160]}"
    return out


@app.get("/forecast")
def forecast(hours: int = Query(24, ge=1, le=72)):
    """Official and model weather for this point: where the wind comes from, when rain is expected, and when the
    forecast was issued. Context for reading this node's own air. The node fetches it; it does not predict."""
    who = q("""SELECT sensor_id, name, lat, lon, meta FROM sensors
               WHERE source IN ('forecast-bmkg','forecast-om','forecast-gap') ORDER BY sensor_id""")
    rows = q("""SELECT sensor_id, ts, metric, value FROM readings
                WHERE sensor_id IN ('forecast-bmkg','forecast-om','forecast-gap')
                  AND ts > now() - interval '3 hours' AND ts < now() + make_interval(hours => %s)
                ORDER BY ts, sensor_id, metric""", hours)
    steps: dict = {}
    for r in rows:
        steps.setdefault((str(r["ts"]), r["sensor_id"]), {})[r["metric"]] = r["value"]
    lat, lon = float(os.getenv("NODE_LAT", 0) or 0), float(os.getenv("NODE_LON", 0) or 0)
    out = {"point": {"lat": lat, "lon": lon},
           "sources": [{"sensor_id": w["sensor_id"], "name": w["name"], "lat": w["lat"], "lon": w["lon"],
                        "issued": (w["meta"] or {}).get("issued"), "fetched": (w["meta"] or {}).get("fetched"),
                        "km_from_node": (w["meta"] or {}).get("km_from_node")} for w in who],
           "hours": [{"ts": k[0], "source": k[1], **v} for k, v in sorted(steps.items())],
           "attribution": ["BMKG (Badan Meteorologi, Klimatologi, dan Geofisika), api.bmkg.go.id",
                           "Open-Meteo, open-meteo.com, CC-BY 4.0 (free tier: non-commercial use only)"]}
    # a forecast for somewhere else is still a forecast, but the card has to say so rather than imply this point
    far = [w for w in out["sources"] if (w.get("km_from_node") or 0) > 10]
    out["far_from_node"] = [{"sensor_id": w["sensor_id"], "km": w["km_from_node"]} for w in far] or None
    return out


@app.get("/observations")
def observations():
    """Latest value per slow-moving source: city statistics, model point samples, survey results."""
    return q("SELECT * FROM observations ORDER BY scale, sensor_id, metric")


@app.get("/alerts")
def alerts(limit: int = Query(50, ge=0, le=1000)):
    """Alerts newest first, each with its id (what `planetai act <id>` and the GUI's Act button need) and whether
    anyone has already acted on it."""
    return q("""SELECT a.id, a.ts, a.rule_id, a.sensor_id, a.level, a.text,
                       (SELECT min(x.ts) FROM actions x WHERE x.alert_id = a.id AND x.stage IN ('acknowledged','acted')) AS acted_at
                FROM alerts a ORDER BY a.ts DESC LIMIT %s""", limit)


@app.get("/series")
def series(metric: str = "pm25", hours: int = Query(24, ge=1, le=168)):
    """Hourly means for the dashboard's strip: local indoor, everything outdoor (yours and references), and the
    model, as three aligned arrays. What readings_1h already knows, shaped for a chart."""
    rows = q("""
        WITH h AS (SELECT generate_series(date_trunc('hour', now()) - make_interval(hours => %s - 1), date_trunc('hour', now()), interval '1 hour') AS bucket),
        r AS (SELECT r.bucket,
                     avg(r.mean) FILTER (WHERE s.local AND s.indoor) AS indoor,
                     avg(r.mean) FILTER (WHERE NOT s.indoor AND s.kind = 'sensor') AS outdoor
              FROM readings_1h r JOIN sensors s USING (sensor_id)
              WHERE r.metric = %s AND r.bucket > now() - make_interval(hours => %s) GROUP BY r.bucket),
        m AS (SELECT date_trunc('hour', ts) AS bucket, avg(value) AS model FROM readings
              WHERE sensor_id = 'cams-point' AND metric = %s || '_model' AND ts > now() - make_interval(hours => %s) GROUP BY 1)
        SELECT h.bucket, r.indoor, r.outdoor, m.model FROM h LEFT JOIN r USING (bucket) LEFT JOIN m USING (bucket) ORDER BY h.bucket""",
        hours, metric, hours, metric, hours)
    return {"metric": metric, "hours": hours, "buckets": [x["bucket"] for x in rows],
            "indoor": [x["indoor"] for x in rows], "outdoor": [x["outdoor"] for x in rows], "model": [x["model"] for x in rows]}


@app.get("/export")
def export(day: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$")):
    """One day of this node as open data: hourly means per sensor and metric, the Index cells, the alerts, rho.
    What a parent node, the Index, a researcher or IPFS should receive. Never raw readings, never secrets.
    Your own sensors are named by role (indoor-1, outdoor-1), not by their device id."""
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(422, "day must be a real date, YYYY-MM-DD")
    hourly = q("""SELECT r.bucket, r.sensor_id, s.local, s.indoor, s.kind, s.scale, r.metric, r.mean, r.min, r.max, r.n
                  FROM readings_1h r JOIN sensors s USING (sensor_id)
                  WHERE r.bucket >= %s::date AND r.bucket < %s::date + 1 ORDER BY r.bucket, r.sensor_id, r.metric""", day, day)
    alias, counts = {}, {"indoor": 0, "outdoor": 0}
    def name(row):
        if not row["local"]:
            return row["sensor_id"]                      # public references and models are public already
        if row["sensor_id"] not in alias:
            k = "indoor" if row["indoor"] else "outdoor"; counts[k] += 1; alias[row["sensor_id"]] = f"{k}-{counts[k]}"
        return alias[row["sensor_id"]]
    rows = [{"t": r["bucket"], "sensor": name(r),                      # q() already renders timestamps as ISO strings "local": r["local"], "indoor": r["indoor"], "kind": r["kind"],
             "metric": r["metric"], "mean": r["mean"], "min": r["min"], "max": r["max"], "n": r["n"]} for r in hourly]
    alerts_ = q("SELECT ts, rule_id, level, text FROM alerts WHERE ts >= %s::date AND ts < %s::date + 1 ORDER BY ts", day, day)
    with db() as con, con.cursor() as cur:
        cells_ = index.cells(cur); rho_ = index.rho(cur)
    return {"node": NODE, "city": os.getenv("NODE_CITY", ""), "scale": os.getenv("NODE_SCALE", "community"),
            "lat": round(float(os.getenv("NODE_LAT", 0) or 0), 3), "lon": round(float(os.getenv("NODE_LON", 0) or 0), 3),
            "day": day, "generated": datetime.now(timezone.utc).isoformat(), "version": os.getenv("NODE_VERSION", ""),
            "licence": "CC BY 4.0", "hourly": rows,
            "alerts": [{"t": a["ts"], "rule": a["rule_id"], "level": a["level"], "text": a["text"].split("\n")[0]} for a in alerts_],
            "cells": cells_, "rho": rho_}


@app.get("/place/geojson")
def place_geojson(kinds: str = "building,poi,green,road,sat", tolerance: float = 0.00002):
    """The geometry the place pack stored: OpenStreetMap buildings, uses, green, roads, and the satellite's buildings
    (`sat`), as one GeoJSON FeatureCollection for the dashboard's plan. Simplified so a kilometre is a few hundred KB.
    Empty until the place pack has run; never an error."""
    want = {k.strip() for k in kinds.split(",") if k.strip()}
    feats: list = []
    diag: dict = {"tables": {}, "rows": {}}
    try:
        with db() as con, con.cursor() as cur:
            one = lambda: next(iter(cur.fetchone().values()))        # rows are dicts in this app; take the single column  # noqa: E731
            for t in ("place_features", "place_buildings_sat", "place_runs"):
                cur.execute(f"SELECT to_regclass('{t}') IS NOT NULL AS ok"); diag["tables"][t] = bool(one())
                if diag["tables"][t]:
                    cur.execute(f"SELECT count(*) AS n FROM {t}"); diag["rows"][t] = one()
            if diag["tables"]["place_features"] and want - {"sat"}:
                cur.execute("""SELECT kind, category, name, tags->>'building' AS btype, tags->>'highway' AS hw,
                                      ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, %s), 6) AS g
                               FROM place_features WHERE kind = ANY(%s)""", (tolerance, list(want - {"sat"})))
                for r in cur.fetchall():
                    feats.append({"type": "Feature", "properties": {"kind": r["kind"], "category": r["category"], "name": r["name"], "building": r["btype"], "highway": r["hw"]}, "geometry": json.loads(r["g"])})
            if diag["tables"]["place_buildings_sat"] and "sat" in want:
                # only the satellite footprints with no mapped building within 3 m: the gap, drawn
                cur.execute("""SELECT ST_AsGeoJSON(ST_SimplifyPreserveTopology(s.geom, %s), 6) AS g, s.confidence FROM place_buildings_sat s
                               WHERE s.source='open_buildings_v3' AND NOT EXISTS (
                                 SELECT 1 FROM place_features f WHERE f.kind='building' AND ST_DWithin(f.geom, s.geom, 0.00003))""", (tolerance,))   # geometry: uses the GiST index
                for r in cur.fetchall():
                    feats.append({"type": "Feature", "properties": {"kind": "sat", "confidence": r["confidence"]}, "geometry": json.loads(r["g"])})
    except Exception as e:  # noqa: BLE001
        log.warning("place/geojson: %s", e)
        diag["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    if not feats:
        diag["hint"] = ("the place pack has not stored anything yet: enable it (PACKS_ALLOW_CODE=1, planetai packs install, planetai restart) and let it poll, or planetai run place refresh"
                        if not diag["rows"].get("place_features") else "features exist but none matched; see error")
    return {"type": "FeatureCollection", "features": feats, "diag": diag,
            "center": [float(os.getenv("NODE_LON", 0) or 0), float(os.getenv("NODE_LAT", 0) or 0)],
            "radius_m": int(settings.get("PLACE_RADIUS_M", "1000") or 1000)}


def _earth_dir() -> Path:
    return OUT / "earth" / NODE


def _earth_changes() -> list[dict]:
    """Every comparison the earth pack computed here, oldest pair first. Small: about a kilobyte each, and a
    node has at most eight of them."""
    d = _earth_dir()
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("change_*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except Exception as e:  # noqa: BLE001
            log.warning("earth: %s is not readable json (%s)", f.name, e)
    return sorted(out, key=lambda c: (c.get("year_b", 0), c.get("year_a", 0)))


def _earth_latest() -> dict | None:
    """The newest comparison, preferring a year-over-year pair over a longer span."""
    out = _earth_changes()
    if not out:
        return None
    yoy = [c for c in out if c.get("year_b", 0) - c.get("year_a", 0) == 1]
    return (yoy or out)[-1]


@app.get("/earth")
def earth():
    """What the earth pack has: the years of AlphaEarth embeddings cached for this node's square, and the
    latest year-over-year comparison it computed from them. Empty until `planetai run earth fetch`; never an
    error, so the dashboard card can say what is missing instead of showing a blank box."""
    d = _earth_dir()
    years = sorted(int(p.stem) for p in d.glob("*.npy") if p.stem.isdigit()) if d.is_dir() else []
    size = sum(p.stat().st_size for p in d.glob("*")) if d.is_dir() else 0
    frames = sorted(int(f.stem[5:]) for f in d.glob("year_*.png") if f.stem[5:].isdigit()) if d.is_dir() else []
    changes = _earth_changes()
    latest = _earth_latest()
    enabled = "earth" in [m.get("id") for m in packs.manifests()]
    for c in changes:                       # so a NAS, or anything else, can fetch each map without guessing
        c["png_url"] = f"/earth/change.png?pair={c['year_a']}_{c['year_b']}"
    body = {"node": NODE, "enabled": enabled, "years": years, "bytes": size, "latest": latest,
            "changes": changes, "frames": frames, "dir": str(d),
            "png": "/earth/change.png" if latest and (d / str(latest.get("png", ""))).is_file() else None,
            "lat": float(os.getenv("NODE_LAT", 0) or 0), "lon": float(os.getenv("NODE_LON", 0) or 0),
            "radius_m": int(settings.get("EARTH_RADIUS_M", "5000") or 5000),
            "attribution": "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and "
                           "Google DeepMind. CC BY 4.0."}
    if not enabled:
        body["hint"] = "the earth pack is not loaded; see docs/PACKS.md"
    elif not years:
        body["hint"] = "no satellite record yet: planetai run earth fetch"
    elif not latest:
        body["hint"] = f"{len(years)} year(s) cached, nothing compared yet: planetai run earth change"
    elif not frames:
        body["hint"] = f"{len(years)} year(s) cached; for the year-by-year pictures: planetai run earth frames"
    return body


@app.get("/earth/change.png")
def earth_change_png(pair: str = Query("", pattern=r"^(\d{4}_\d{4})?$")):
    """A land-change map the earth pack drew: the latest, or `?pair=2023_2025`. The file name always comes
    from the pack's own JSON, never from the request — the pair only chooses among the comparisons this node
    actually computed — and only a .png inside this node's own earth directory is served."""
    from fastapi.responses import FileResponse
    want = _earth_latest() if not pair else next(
        (c for c in _earth_changes() if f"{c.get('year_a')}_{c.get('year_b')}" == pair), None)
    name = Path(str((want or {}).get("png", ""))).name
    p = _earth_dir() / name
    if not (name.endswith(".png") and p.is_file()):
        raise HTTPException(404, "no such land-change map: planetai run earth change")
    return FileResponse(p, media_type="image/png", filename=name)


@app.get("/earth/year.png")
def earth_year_png(year: int = Query(..., ge=1900, le=2200)):
    """One year of the square as the earth pack drew it. The year is an integer and the name is built here,
    so nothing from the request reaches the filesystem as a path."""
    from fastapi.responses import FileResponse
    p = _earth_dir() / f"year_{year}.png"
    if not p.is_file():
        raise HTTPException(404, f"no frame for {year}: planetai run earth frames")
    return FileResponse(p, media_type="image/png", filename=p.name)


@app.get("/report/latest")
def report_latest():
    """The last report this node wrote, sent or held. What the dashboard's Here band shows, and what the MCP tool
    `report_latest` returns. Open, like /alerts: it is the same sentences the household already received."""
    # by ts, not by due_local: a report written on request has no due hour, and ordering by that hid it here and
    # in `planetai report last` — the button said "sent" and the page went on showing the one before it.
    rows = q("""SELECT id, ts, due_local, window_hours, depth, rung, text, sent, held_quiet, fallback_reason
                  FROM reports ORDER BY ts DESC LIMIT 1""")
    return rows[0] if rows else {"text": None, "ts": None, "depth": None, "rung": None, "held_quiet": None,
                                 "note": "no report yet; the first one lands at the next due hour"}


@app.get("/report/bundle")
def report_bundle(hours: int = Query(0, ge=0, le=168), authorization: str = Header("")):
    """Every number the node has about a window, as one document — what a report is written from. Behind the
    read-only token: this is more of the household's own data in one place than any other endpoint returns."""
    _pull_ok(authorization)
    with db() as con, con.cursor() as cur:
        return report.bundle(cur, hours or _report_every())


@app.post("/report/now")
def report_now(authorization: str = Header("")):
    """Write and send a report immediately, whatever the hour. `planetai report` and /report in Telegram call this.
    It does not take the scheduled hour's place: no `due_local`, so the next due report still happens."""
    _admin(authorization)
    with db() as con, con.cursor() as cur:
        every = _report_every()
        b = report.bundle(cur, every)
        text = report.sheet(b, LOCALE())
        cur.execute("""INSERT INTO reports (window_hours, depth, rung, text, sheet, sent, held_quiet, cells)
                       VALUES (%s, 'sheet', 'node', %s, %s, TRUE, FALSE, %s) RETURNING id""",
                    (every, text, text, Jsonb(b.get("cells") or [])))
        rid = cur.fetchone()["id"]
    notify("info", text)
    ha_alert("info", text, None)
    log.info("report %d sent on request: %d hours, %d words", rid, every, len(text.split()))
    return {"id": rid, "text": text, "depth": "sheet", "rung": "node", "sent": True}


@app.get("/briefing", include_in_schema=False)
def briefing_moved(kind: str = "morning"):
    """Gone in v0.38. A dashboard left open in a browser through the update still asks for this; answer it with
    where the report lives now rather than a 404 in a screen nobody is looking at."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/report/latest", status_code=301)


@app.get("/history")
def history(sensor_id: str, metric: str, limit: int = Query(500, ge=1, le=5000)):
    """Every reading of one metric from one sensor, oldest first. For series that are not hourly: a yearly building count,
    a monthly refresh. `/sparks` is the hourly view; this is the raw one."""
    return [{"ts": r["ts"], "value": r["value"]} for r in            # q() already renders timestamps as ISO strings
            q("SELECT ts, value FROM readings WHERE sensor_id=%s AND metric=%s ORDER BY ts LIMIT %s", sensor_id, metric, limit)]


@app.get("/sparks")
def sparks(metric: str = "pm25", hours: int = Query(24, ge=1, le=168)):
    """Per-sensor hourly means, aligned to the same buckets, for small traces inside the dashboard's sensor tiles."""
    rows = q("""
        WITH h AS (SELECT generate_series(date_trunc('hour', now()) - make_interval(hours => %s - 1), date_trunc('hour', now()), interval '1 hour') AS bucket),
        ids AS (SELECT DISTINCT sensor_id FROM readings_1h WHERE metric = %s AND bucket > now() - make_interval(hours => %s))
        SELECT ids.sensor_id, h.bucket, r.mean
        FROM ids CROSS JOIN h LEFT JOIN readings_1h r ON r.sensor_id = ids.sensor_id AND r.bucket = h.bucket AND r.metric = %s
        ORDER BY ids.sensor_id, h.bucket""", hours, metric, hours, metric)
    # The buckets travel with the values. Without them a trace cannot draw its own time axis or say which hour
    # the reader is hovering over, and the dashboard was guessing the hours from the array's length.
    out: dict = {}
    hours: list = []
    seen = set()
    for x in rows:
        out.setdefault(x["sensor_id"], []).append(x["mean"])
        b = str(x["bucket"])
        if b not in seen:
            seen.add(b); hours.append(b)
    return {"hours": hours, "series": out}


# ---------------------------------------------------------------- backups and exports, for a machine that pulls them
BACKUPS = Path("/app/backups")
EXPORTS = Path("/app/exports")
OUT = Path(os.getenv("PACK_OUT", "/app/out"))      # the one writable mount; packs put their artifacts here


def _bearer_ok(authorization: str, *tokens: str) -> bool:
    """True when the Authorization header carries one of `tokens`. Compared in constant time: `!=` returns at the first
    differing byte, which lets a caller on the LAN measure its way to a token one character at a time."""
    given = authorization.replace("Bearer ", "", 1).strip().encode()
    ok = False
    for t in tokens:
        if t and secrets.compare_digest(given, t.encode()):
            ok = True          # no early return: the time taken must not say which token matched
    return ok


def _pull_ok(authorization: str) -> None:
    """A read-only token for whoever collects backups (a NAS), separate from the admin token. Either works."""
    tokens = [t for t in (os.getenv("ADMIN_TOKEN", "").strip(), settings.get("BACKUP_TOKEN", "").strip()) if t]
    if not tokens:
        raise HTTPException(403, "no BACKUP_TOKEN or ADMIN_TOKEN set on this node")
    if not _bearer_ok(authorization, *tokens):
        raise HTTPException(401, "bad or missing token")


@app.get("/settings/raw")
def settings_raw(authorization: str = Header("")):
    """Runtime settings unmasked, for the node's own processes (the agent loop reads its model ladder here every minute,
    so the dashboard's Model page changes it live). Admin token required; never call this from a browser."""
    _admin(authorization)       # not _pull_ok: the NAS's read-only BACKUP_TOKEN must not unmask the Telegram token and the AI keys
    return {k: settings.get(k, "") for k in settings.RUNTIME}


@app.get("/backups")
def list_backups(authorization: str = Header("")):
    """Dumps this node has made, newest first, so a NAS can fetch the ones it lacks. Token required."""
    _pull_ok(authorization)
    if not BACKUPS.exists():
        return []
    files = sorted(BACKUPS.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "bytes": p.stat().st_size, "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()} for p in files]


@app.get("/backups/{name}")
def get_backup(name: str, authorization: str = Header("")):
    _pull_ok(authorization)
    from fastapi.responses import FileResponse
    p = BACKUPS / Path(name).name           # no path components, ever
    if not (p.exists() and p.suffix == ".gz" and p.name.endswith(".sql.gz")):
        raise HTTPException(404, "no such backup")
    return FileResponse(p, media_type="application/gzip", filename=p.name)


@app.get("/exports")
def list_exports():
    """The daily open-data exports. Public: they are CC BY 4.0 and contain nothing raw or secret."""
    if not EXPORTS.exists():
        return []
    return [{"node": p.parent.name, "name": p.name, "bytes": p.stat().st_size}
            for p in sorted(EXPORTS.glob("*/*.json"), key=lambda p: p.name, reverse=True)]


@app.get("/exports/{node}/{name}")
def get_export(node: str, name: str):
    from fastapi.responses import FileResponse
    p = EXPORTS / Path(node).name / Path(name).name
    if not (p.exists() and p.suffix == ".json"):
        raise HTTPException(404, "no such export")
    return FileResponse(p, media_type="application/json", filename=p.name)


# ---------------------------------------------------------------- the GUI and its settings
STATIC = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
def ui():
    """The dashboard: one HTML file, no build step, reads the same API everything else does.

    Sent with `cache-control: no-cache`. Without any cache header a browser is free to reuse this document for as
    long as it likes, and an ordinary reload does not always ask: after `planetai update` a screen kept running the
    previous dashboard, with the previous bugs, until someone thought to hard-reload. The node's whole update story
    depends on the page following the version."""
    from fastapi.responses import HTMLResponse
    f = STATIC / "index.html"
    body = f.read_text() if f.exists() else "<h1>planetai-node</h1><p>GUI not shipped in this build.</p>"
    return HTMLResponse(body, headers={"cache-control": "no-cache, must-revalidate"})


# The two files index.html cannot hold. The dashboard is still one HTML document with no build step: the
# ground is an SVG whose own `:root` block would leak its paper variables into the page if it were inlined,
# and the mono is a font. Named one by one rather than served from a directory — this port is open to a
# household LAN, and a path parameter that reaches the filesystem is the usual way that ends badly.
COMPANIONS = {
    "node-ground.svg": (STATIC / "node-ground.svg", "image/svg+xml"),
    "jetbrains-mono-latin.woff2": (STATIC / "fonts" / "jetbrains-mono-latin.woff2", "font/woff2"),
}
NO_CACHE = {"cache-control": "no-cache, must-revalidate"}


@app.get("/static/{name}", include_in_schema=False)
def static_file(name: str):
    """The dashboard's ground and its data face.

    Same `no-cache, must-revalidate` as index.html, and for the same reason: a wall screen that keeps the
    previous design after `planetai update` is the bug that header exists to stop, and a stale ground is that
    bug again. FileResponse sends an ETag, so revalidating costs a 304 and nothing on the wire.

    The ground is drawn here from NODE_LAT / NODE_LON rather than served from disk, so it is this
    node's own cell and the caption naming that cell is true. The file on disk is what a node with
    no coordinates yet gets: node #1's cell, with no caption, standing in for a place the node has
    not been told about."""
    from fastapi.responses import FileResponse, Response
    if name == "node-ground.svg":
        svg = _ground_svg()
        if svg:
            return Response(svg, media_type="image/svg+xml", headers=NO_CACHE)
    hit = COMPANIONS.get(name)
    if not hit or not hit[0].exists():
        raise HTTPException(404, "no such asset")
    return FileResponse(hit[0], media_type=hit[1], headers=NO_CACHE)


def _ground_svg() -> str | None:
    """This node's ground, or None to fall back to the file: before setup there are no coordinates
    to draw, and an image built before h3 was a dependency has no h3. Neither is a reason to serve
    an empty hero."""
    lat, lon = os.getenv("NODE_LAT", ""), os.getenv("NODE_LON", "")
    if not lat or not lon:
        return None
    try:
        return ground.svg(float(lat), float(lon))
    except Exception as e:  # noqa: BLE001
        log.warning("node-ground: %s: %s — serving the shipped file", type(e).__name__, e)
        return None


def _admin(authorization: str) -> None:
    tok = os.getenv("ADMIN_TOKEN", "").strip()
    if not tok:
        raise HTTPException(403, "ADMIN_TOKEN is not set in .env; run `planetai ui` to create one")
    if not _bearer_ok(authorization, tok):
        raise HTTPException(401, "bad or missing admin token")


@app.get("/settings")
def get_settings(authorization: str = Header("")):
    """Every runtime setting with its group, help and current value, plus bootstrap keys read-only. Secrets are always
    masked. Without the admin token, so is everything that is the household's rather than the node's (chat ids, sensor
    hosts, account names, remote URLs; see settings.PUBLIC). A wrong token reads as no token: the dashboard's layout
    read must keep working for every screen in the house."""
    tok = os.getenv("ADMIN_TOKEN", "").strip()
    return settings.describe(unlocked=bool(tok) and _bearer_ok(authorization, tok))


@app.put("/settings")
def put_settings(body: dict, authorization: str = Header(""), x_agent: str = Header("")):
    """Change runtime settings. {"KEY": "value", ...}. Blank returns a key to its .env value. Effective within ~20 s."""
    _admin(authorization)
    changed = []
    for k, v in body.items():
        if k not in settings.RUNTIME:
            raise HTTPException(400, f"{k} is not a runtime setting")
        try:
            settings.set(k, str(v).strip())
        except ValueError as e:            # a key with a fixed set of values says so; a 500 would read as the node's fault
            raise HTTPException(400, str(e)) from None
        changed.append(k)
    who = x_agent or "gui"
    log.info("settings changed by %s: %s", who, ", ".join(changed))
    with db() as con, con.cursor() as cur:
        cur.execute("INSERT INTO actions (alert_id, stage, actor, note) VALUES (NULL, 'settings', %s, %s)", (who, ", ".join(changed)))
    return {"changed": changed, "by": who, "effective_within_s": settings.TTL}


@app.post("/test-alert")
def test_alert(authorization: str = Header("")):
    """Fire one act-level alert now, through every configured channel. Same as `planetai test-alert`."""
    _admin(authorization)
    text = "🔔 A test from your node.\n\nIf you can read this, the whole path works: a rule fired, the node wrote a message, and it reached you here. Real alerts will look like this, with what is happening, what it means, and what to do."
    with db() as con, con.cursor() as cur:
        cur.execute("INSERT INTO alerts (ts, rule_id, sensor_id, level, text) VALUES (now(), 'gui/test', 'node', 'act', %s) RETURNING id", (text,))
        alert_id = cur.fetchone()["id"]
    how = act_hint(alert_id)
    closing = f"👉 Reply {how} to show me how you close the loop." if how.startswith("/") else f"👉 In the terminal, {how} records that you closed the loop."
    notify("act", f"{text}\n\n{closing}")      # the hint already carries the number; a bare #id on the end taught nothing
    ha_alert("act", text, alert_id)
    return {"ok": True, "alert_id": alert_id}


# ---- Index contract (fci-cells-v0) and ρ ------------------------------------------------------
@app.get("/cells")
def cells():
    """Index cells this node can honestly compute. Same row shape as the FCI Observations base."""
    with db() as con, con.cursor() as cur:
        return index.cells(cur)


@app.get("/packs")
def packs_():
    """What this node has loaded beyond the core. data packs are rules/cells only; code packs run Python."""
    return packs.manifests()


@app.get("/rho")
def rho():
    with db() as con, con.cursor() as cur:
        return index.rho(cur)


@app.post("/actions")
def action(body: dict):
    """A human closes the loop: {"alert_id": 12, "stage": "acted", "actor": "ibu wayan", "note": "closed windows"}.
    A mobile app, a Telegram reply handler, or curl — all the same call."""
    stage = body.get("stage")
    if stage not in ("acknowledged", "acted"):            # 'settings' rows are written by the node itself, never posted
        raise HTTPException(400, "stage must be acknowledged or acted")
    with db() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM alerts WHERE id = %s", (body.get("alert_id"),))
        if not cur.fetchone():
            raise HTTPException(404, "no such alert")
        cur.execute("INSERT INTO actions (alert_id, stage, actor, note) VALUES (%s,%s,%s,%s)",
                    (body.get("alert_id"), stage, str(body.get("actor") or "")[:80], str(body.get("note") or "")[:500]))
    return {"ok": True}


@app.post("/readings")
def post_readings(body: dict, authorization: str = Header("")):
    """Downstream contributors (a phone, a DIY pod on the LAN) post raw readings. Admin token required: a posted
    reading becomes a *local, indoor* sensor whose values fire act-level alerts and enter live cells, so anyone on the
    WiFi could otherwise wake the household with 999 µg/m³ from a curl (found on the clean node, 6 Sep 2026).
    {"sensor": {"sensor_id": "phone-abc", "source": "mobile", "name": "...", "lat":..,"lon":.., "indoor": false},
     "readings": [{"ts": "...", "metric": "<name>", "value": 12.3}, ...]}   The sensor is local by definition."""
    _admin(authorization)
    s = body.get("sensor") or {}
    if not s.get("sensor_id"):
        raise HTTPException(422, "sensor.sensor_id is required")
    with db() as con, con.cursor() as cur:
        cur.execute("""INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, meta)
                       VALUES (%s,%s,%s,%s,%s,%s,TRUE,%s) ON CONFLICT (sensor_id) DO UPDATE SET lat=EXCLUDED.lat, lon=EXCLUDED.lon, indoor=EXCLUDED.indoor""",
                    (s["sensor_id"], s.get("source", "contributor"), s.get("name", s["sensor_id"]), s.get("lat"), s.get("lon"),
                     bool(s.get("indoor", False)), Jsonb(s.get("meta") or {})))
        cur.executemany("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        [(r.get("ts") or datetime.now(timezone.utc), s["sensor_id"], r["metric"], float(r["value"])) for r in body.get("readings", [])])
    return {"accepted": len(body.get("readings", []))}


@app.get("/aggregates")
def aggregates(hours: int = Query(24, le=24 * 90)):
    return q("SELECT bucket, sensor_id, metric, mean, min, max, n FROM readings_1h WHERE bucket > now() - make_interval(hours => %s) ORDER BY bucket DESC", hours)


@app.post("/aggregates")
def receive_aggregates(body: dict, authorization: str = Header("")):
    """Parent side. Children push hourly means; stored as readings under metric '<metric>_1h' with the child's sensor ids.
    Raw readings never travel this path."""
    if not AGG_TOKEN():
        raise HTTPException(403, "this node accepts no children: set AGGREGATE_TOKEN in .env and give it to them")
    if not _bearer_ok(authorization, AGG_TOKEN()):
        raise HTTPException(401, "bad or missing Authorization: Bearer <AGGREGATE_TOKEN>")
    rows = body.get("rows", [])
    child = body.get("node", "?")
    with db() as con, con.cursor() as cur:
        for r in rows:
            sid = f"{child}/{r['sensor_id']}"
            cur.execute("""INSERT INTO sensors (sensor_id, source, name, local, kind, scale, cadence)
                           VALUES (%s,'child',%s,FALSE,'child',%s,'PT1H')
                           ON CONFLICT (sensor_id) DO UPDATE SET kind='child', scale=EXCLUDED.scale""",
                        (sid, sid, body.get("scale", "community")))
            cur.execute("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (r["bucket"], sid, f"{r['metric']}_1h", float(r["mean"])))
    return {"accepted": len(rows)}
