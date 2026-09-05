"""planetai-node. One process:
  poll sources → postgres   (every POLL_SECONDS)
  run rules.yml (SQL) → telegram/log   (every 60s, cooldown enforced in SQL against the alerts table)
  push hourly aggregates to PARENT_API_URL if set   (every hour)
  answer HTTP: /health /sensors /readings /stats /observations /alerts /aggregates /cells /rho /packs
              POST /aggregates (parent side, token) · POST /actions (ρ) · POST /readings (downstream contributors)
"""
from __future__ import annotations

import json
import logging
import os
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
import index
import packs
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
            with con.cursor() as cur:
                for s in sensors:
                    cur.execute(
                        """INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind, scale, cadence, meta)
                           VALUES (%(sensor_id)s, %(source)s, %(name)s, %(lat)s, %(lon)s, %(indoor)s, %(local)s,
                                   %(kind)s, %(scale)s, %(cadence)s, %(meta)s)
                           ON CONFLICT (sensor_id) DO UPDATE SET name=EXCLUDED.name, lat=EXCLUDED.lat, lon=EXCLUDED.lon,
                             indoor=EXCLUDED.indoor, kind=EXCLUDED.kind, scale=EXCLUDED.scale,
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
    with db() as con, con.cursor() as cur:
        for s in sensors:
            cur.execute("""INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind, scale, cadence, meta)
                           VALUES (%(sensor_id)s,%(source)s,%(name)s,%(lat)s,%(lon)s,%(indoor)s,%(local)s,%(kind)s,%(scale)s,%(cadence)s,%(meta)s)
                           ON CONFLICT (sensor_id) DO UPDATE SET
                             name = COALESCE(EXCLUDED.name, sensors.name),
                             lat = COALESCE(EXCLUDED.lat, sensors.lat), lon = COALESCE(EXCLUDED.lon, sensors.lon),
                             indoor = EXCLUDED.indoor, meta = sensors.meta || EXCLUDED.meta""",
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
    return core + packs.rules()


def run_rules() -> None:
    rules = load_rules()
    with db() as con, con.cursor() as cur:
        for rule in rules:
            try:
                cur.execute(rule["sql"])
                rows = cur.fetchall()
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
                notify(level, f"{text}\n\n#{alert_id}")   # the id is how a reply becomes an action
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
    if not PARENT:
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
        cur.execute("SELECT count(*) AS n FROM readings")
        if (cur.fetchone() or {}).get("n"):
            return
        log.info("first start: bootstrapping from global open data (no sensor needed)")
        state["bootstrap"] = bootstrap.run(con, hc, float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"]))
try:
    bootstrap_once()
except Exception as e:  # noqa: BLE001  — never block startup on it
    log.warning("bootstrap failed: %s", e)

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
        if not tok or auth != f"Bearer {tok}":
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
            **({"mesh": mesh_state} if MQTT_HOST else {})}


@app.get("/sensors")
def sensors_():
    return q("SELECT * FROM sensors ORDER BY local DESC, name")


@app.get("/readings")
def readings(sensor_id: str | None = None, metric: str | None = None, limit: int = Query(200, le=10000)):
    return q("SELECT ts, sensor_id, metric, value FROM readings WHERE (%s IS NULL OR sensor_id=%s) AND (%s IS NULL OR metric=%s) ORDER BY ts DESC LIMIT %s",
             sensor_id, sensor_id, metric, metric, limit)


@app.get("/stats")
def stats():
    """Rolling 15m/1h/24h — sensors only. Slow sources (portals, models, surveys) are in /observations."""
    return q("SELECT * FROM stats ORDER BY local DESC, sensor_id, metric")


@app.get("/observations")
def observations():
    """Latest value per slow-moving source: city statistics, model point samples, survey results."""
    return q("SELECT * FROM observations ORDER BY scale, sensor_id, metric")


@app.get("/alerts")
def alerts(limit: int = Query(50, le=1000)):
    """Alerts newest first, each with its id (what `planetai act <id>` and the GUI's Act button need) and whether
    anyone has already acted on it."""
    return q("""SELECT a.id, a.ts, a.rule_id, a.sensor_id, a.level, a.text,
                       (SELECT min(x.ts) FROM actions x WHERE x.alert_id = a.id AND x.stage IN ('acknowledged','acted')) AS acted_at
                FROM alerts a ORDER BY a.ts DESC LIMIT %s""", limit)


@app.get("/series")
def series(metric: str = "pm25", hours: int = Query(24, le=168)):
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
    rows = [{"t": r["bucket"].isoformat(), "sensor": name(r), "local": r["local"], "indoor": r["indoor"], "kind": r["kind"],
             "metric": r["metric"], "mean": r["mean"], "min": r["min"], "max": r["max"], "n": r["n"]} for r in hourly]
    alerts_ = q("SELECT ts, rule_id, level, text FROM alerts WHERE ts >= %s::date AND ts < %s::date + 1 ORDER BY ts", day, day)
    with db() as con, con.cursor() as cur:
        cells_ = index.cells(cur); rho_ = index.rho(cur)
    return {"node": NODE, "city": os.getenv("NODE_CITY", ""), "scale": os.getenv("NODE_SCALE", "community"),
            "lat": round(float(os.getenv("NODE_LAT", 0) or 0), 3), "lon": round(float(os.getenv("NODE_LON", 0) or 0), 3),
            "day": day, "generated": datetime.now(timezone.utc).isoformat(), "version": os.getenv("NODE_VERSION", ""),
            "licence": "CC BY 4.0", "hourly": rows,
            "alerts": [{"t": a["ts"].isoformat(), "rule": a["rule_id"], "level": a["level"], "text": a["text"].split("\n")[0]} for a in alerts_],
            "cells": cells_, "rho": rho_}


@app.get("/sparks")
def sparks(metric: str = "pm25", hours: int = Query(24, le=168)):
    """Per-sensor hourly means, aligned to the same buckets, for small traces inside the dashboard's sensor tiles."""
    rows = q("""
        WITH h AS (SELECT generate_series(date_trunc('hour', now()) - make_interval(hours => %s - 1), date_trunc('hour', now()), interval '1 hour') AS bucket),
        ids AS (SELECT DISTINCT sensor_id FROM readings_1h WHERE metric = %s AND bucket > now() - make_interval(hours => %s))
        SELECT ids.sensor_id, h.bucket, r.mean
        FROM ids CROSS JOIN h LEFT JOIN readings_1h r ON r.sensor_id = ids.sensor_id AND r.bucket = h.bucket AND r.metric = %s
        ORDER BY ids.sensor_id, h.bucket""", hours, metric, hours, metric)
    out: dict = {}
    for x in rows:
        out.setdefault(x["sensor_id"], []).append(x["mean"])
    return out


# ---------------------------------------------------------------- backups and exports, for a machine that pulls them
BACKUPS = Path("/app/backups")
EXPORTS = Path("/app/exports")


def _pull_ok(authorization: str) -> None:
    """A read-only token for whoever collects backups (a NAS), separate from the admin token. Either works."""
    tokens = {t for t in (os.getenv("ADMIN_TOKEN", "").strip(), settings.get("BACKUP_TOKEN", "").strip()) if t}
    if not tokens:
        raise HTTPException(403, "no BACKUP_TOKEN or ADMIN_TOKEN set on this node")
    if authorization.replace("Bearer ", "", 1) not in tokens:
        raise HTTPException(401, "bad or missing token")


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
    """The dashboard: one HTML file, no build step, reads the same API everything else does."""
    from fastapi.responses import HTMLResponse
    f = STATIC / "index.html"
    return HTMLResponse(f.read_text() if f.exists() else "<h1>planetai-node</h1><p>GUI not shipped in this build.</p>")


def _admin(authorization: str) -> None:
    tok = os.getenv("ADMIN_TOKEN", "").strip()
    if not tok:
        raise HTTPException(403, "ADMIN_TOKEN is not set in .env; run `planetai ui` to create one")
    if authorization != f"Bearer {tok}":
        raise HTTPException(401, "bad or missing admin token")


@app.get("/settings")
def get_settings():
    """Every runtime setting with its group, help and current value (secrets masked), plus bootstrap keys read-only."""
    return settings.describe()


@app.put("/settings")
def put_settings(body: dict, authorization: str = Header(""), x_agent: str = Header("")):
    """Change runtime settings. {"KEY": "value", ...}. Blank returns a key to its .env value. Effective within ~20 s."""
    _admin(authorization)
    changed = []
    for k, v in body.items():
        if k not in settings.RUNTIME:
            raise HTTPException(400, f"{k} is not a runtime setting")
        settings.set(k, str(v).strip())
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
    text = "Test alert from your node. If you can read this, the whole path works: rule to message to you."
    with db() as con, con.cursor() as cur:
        cur.execute("INSERT INTO alerts (ts, rule_id, sensor_id, level, text) VALUES (now(), 'gui/test', 'node', 'act', %s) RETURNING id", (text,))
        alert_id = cur.fetchone()["id"]
    notify("act", f"{text}\n\n#{alert_id}")
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
    with db() as con, con.cursor() as cur:
        cur.execute("INSERT INTO actions (alert_id, stage, actor, note) VALUES (%s,%s,%s,%s)",
                    (body.get("alert_id"), body["stage"], body.get("actor"), body.get("note")))
    return {"ok": True}


@app.post("/readings")
def post_readings(body: dict):
    """Downstream contributors (a phone, a DIY pod on the LAN) post raw readings.
    {"sensor": {"sensor_id": "phone-abc", "source": "mobile", "name": "...", "lat":..,"lon":.., "indoor": false},
     "readings": [{"ts": "...", "metric": "<name>", "value": 12.3}, ...]}   The sensor is local by definition."""
    s = body["sensor"]
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
    if authorization != f"Bearer {AGG_TOKEN()}":
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
