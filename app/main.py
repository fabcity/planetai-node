"""planetai-node. One process:
  poll sources → postgres   (every POLL_SECONDS)
  run rules.yml (SQL) → telegram/log   (every 60s, cooldown enforced in SQL against the alerts table)
  push hourly aggregates to PARENT_API_URL if set   (every hour)
  answer HTTP: /health /sensors /readings /stats /alerts /aggregates /cells /rho
              POST /aggregates (parent side) · POST /actions (ρ) · POST /readings (downstream contributors)
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
from fastapi import FastAPI, Query
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

import index
import sources

log = logging.getLogger("planetai")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")

DB = os.environ["DATABASE_URL"]
NODE = os.getenv("NODE_NAME", "node")
POLL = int(os.getenv("POLL_SECONDS", "300"))
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHATS = [c for c in os.getenv("TELEGRAM_CHAT_IDS", "").replace(" ", "").split(",") if c]
LOCALE = os.getenv("ALERT_LOCALE", "en")
PARENT = os.getenv("PARENT_API_URL", "").strip()
if PARENT and not PARENT.startswith(("http://", "https://")):
    log.warning("PARENT_API_URL %r has no http(s):// — ignoring", PARENT); PARENT = ""
RULES = Path(os.getenv("RULES_PATH", "/app/config/rules.yml"))
STARTED = time.time()
state = {"polls": 0, "last_poll": None, "last_error": None, "ingested": 0}


def db():
    return psycopg.connect(DB, row_factory=dict_row, autocommit=True)


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
                        """INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, meta)
                           VALUES (%(sensor_id)s, %(source)s, %(name)s, %(lat)s, %(lon)s, %(indoor)s, %(local)s, %(meta)s)
                           ON CONFLICT (sensor_id) DO UPDATE SET name=EXCLUDED.name, lat=EXCLUDED.lat, lon=EXCLUDED.lon,
                             indoor=EXCLUDED.indoor, meta=EXCLUDED.meta""",
                        {**s, "meta": Jsonb(s.get("meta") or {})},
                    )
                if readings:
                    cur.executemany(
                        "INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        readings,
                    )
                    state["ingested"] += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            log.info("%s: %d sensors, %d readings", name, len(sensors), len(readings))
    state["polls"] += 1
    state["last_poll"] = datetime.now(timezone.utc).isoformat()
    state["last_error"] = " | ".join(errors) if errors else None   # clears when every source succeeds


# ---------------------------------------------------------------- rules → alerts
def load_rules() -> list[dict]:
    try:
        return yaml.safe_load(RULES.read_text()) or []
    except FileNotFoundError:
        return []


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
                tmpl = msg.get(LOCALE) or msg.get("en") if isinstance(msg, dict) else str(msg)
                try:
                    text = tmpl.format(**{k: ("—" if v is None else v) for k, v in row.items()})
                except (KeyError, ValueError, TypeError):
                    text = tmpl
                level = rule.get("level", "info")
                cur.execute("INSERT INTO alerts (rule_id, sensor_id, level, text) VALUES (%s,%s,%s,%s) RETURNING id", (rule["id"], sid, level, text))
                alert_id = cur.fetchone()["id"]
                notify(level, f"{text}\n\n#{alert_id}")   # the id is how a reply becomes an action


def notify(level: str, text: str) -> None:
    icon = {"info": "ℹ️", "warn": "⚠️", "act": "🔴"}.get(level, "")
    log.info("ALERT [%s] %s", level, text)
    if not TG_TOKEN or not TG_CHATS:
        return
    for chat in TG_CHATS:
        try:
            httpx.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                       json={"chat_id": chat, "text": f"{icon} {text}".strip()}, timeout=15).raise_for_status()
        except Exception as e:  # noqa: BLE001
            log.warning("telegram %s: %s", chat, e)


# ---------------------------------------------------------------- hourly push (child → parent)
def push_aggregates() -> None:
    if not PARENT:
        return
    with db() as con, con.cursor() as cur:
        cur.execute("SELECT bucket, sensor_id, metric, mean, min, max, n FROM readings_1h WHERE bucket > now() - interval '2 hours'")
        rows = [{**r, "bucket": r["bucket"].isoformat()} for r in cur.fetchall()]
    try:
        httpx.post(f"{PARENT}/aggregates", json={"node": NODE, "rows": rows}, timeout=30).raise_for_status()
        log.info("pushed %d hourly rows to parent", len(rows))
    except Exception as e:  # noqa: BLE001
        log.warning("push to parent failed: %s", e)


# ---------------------------------------------------------------- loops
def loop(fn, every: int, delay: int = 0):
    def run():
        time.sleep(delay)
        while True:
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                state["last_error"] = str(e)
                log.exception("%s: %s", fn.__name__, e)
            time.sleep(every)
    threading.Thread(target=run, daemon=True, name=fn.__name__).start()


hc = httpx.Client(timeout=30, headers={"User-Agent": f"planetai-node/{NODE}"})
loop(lambda: poll_once(hc), POLL, delay=2)
loop(run_rules, 60, delay=30)
loop(push_aggregates, 3600, delay=120)

# ---------------------------------------------------------------- http
app = FastAPI(title="planetai-node")


def q(sql: str, *args):
    with db() as con, con.cursor() as cur:
        cur.execute(sql, args)
        return [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in cur.fetchall()]


@app.get("/health")
def health():
    return {"ok": state["last_poll"] is not None, "node": NODE, "uptime_s": int(time.time() - STARTED), **state}


@app.get("/sensors")
def sensors_():
    return q("SELECT * FROM sensors ORDER BY local DESC, name")


@app.get("/readings")
def readings(sensor_id: str | None = None, metric: str | None = None, limit: int = Query(200, le=10000)):
    return q("SELECT ts, sensor_id, metric, value FROM readings WHERE (%s IS NULL OR sensor_id=%s) AND (%s IS NULL OR metric=%s) ORDER BY ts DESC LIMIT %s",
             sensor_id, sensor_id, metric, metric, limit)


@app.get("/stats")
def stats():
    return q("SELECT * FROM stats ORDER BY local DESC, sensor_id, metric")


@app.get("/alerts")
def alerts(limit: int = Query(50, le=1000)):
    return q("SELECT ts, rule_id, sensor_id, level, text FROM alerts ORDER BY ts DESC LIMIT %s", limit)


# ---- Index contract (fci-cells-v0) and ρ ------------------------------------------------------
@app.get("/cells")
def cells():
    """Index cells this node can honestly compute. Same row shape as the FCI Observations base."""
    with db() as con, con.cursor() as cur:
        return index.cells(cur)


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
     "readings": [{"ts": "...", "metric": "pm25", "value": 12.3}, ...]}   The sensor is local by definition."""
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
def receive_aggregates(body: dict):
    """Parent side. Children push hourly means; stored as readings under metric '<metric>_1h' with the child's sensor ids.
    Raw readings never travel this path."""
    rows = body.get("rows", [])
    child = body.get("node", "?")
    with db() as con, con.cursor() as cur:
        for r in rows:
            sid = f"{child}/{r['sensor_id']}"
            cur.execute("INSERT INTO sensors (sensor_id, source, name, local) VALUES (%s,'child',%s,FALSE) ON CONFLICT DO NOTHING", (sid, sid))
            cur.execute("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (r["bucket"], sid, f"{r['metric']}_1h", float(r["mean"])))
    return {"accepted": len(rows)}
