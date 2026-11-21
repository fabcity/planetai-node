"""Once per local day, asks the models container to forecast this node's own ambient series, and stores the rows.

For every origin (local day) of the last SCORED_DAYS + 1 that has no rows for the running model, one POST carries the
contexts of every eligible series and the answer lands in `predictions`, each origin in one transaction, so an origin
is all there or not there. One fetch() works for at most BUDGET_SECONDS, oldest origin first, and the next poll carries
on where it stopped: the poll thread also reads the household's sensors. Nothing here writes a reading: a prediction
is never a measurement. fetch() returns no readings, and one sensor ("predict") whose meta feeds the Next days line.
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
import predict_core as core  # noqa: E402

log = logging.getLogger("planetai.predict")
HERE = os.path.dirname(os.path.abspath(__file__))
RETRY_MINUTES = 60                     # at most one attempt an hour until today's origin is stored
BUDGET_SECONDS = 60                    # one fetch() works this long at most; the next poll carries on
MODELS_URL = os.getenv("MODELS_URL", "http://models:8080")    # the environment only: no pack key, no Set up row

SERIES_SQL = """SELECT r.sensor_id, r.metric, r.bucket, r.mean FROM readings_1h r
  JOIN sensors s ON s.sensor_id = r.sensor_id
  JOIN channel_roles c ON c.source = s.source AND c.metric = r.metric AND c.role = 'ambient'
  WHERE s.local AND s.kind <> 'peer' AND r.metric NOT LIKE 'fc\\_%%' AND r.mean IS NOT NULL
    AND r.bucket >= %s AND r.bucket < now() ORDER BY r.sensor_id, r.metric, r.bucket"""
OUTDOOR_SQL = """SELECT r.sensor_id, r.metric FROM readings_1h r
  JOIN sensors s ON s.sensor_id = r.sensor_id
  JOIN channel_roles c ON c.source = s.source AND c.metric = r.metric AND c.role = 'ambient'
  WHERE s.local AND s.kind <> 'peer' AND r.metric = 'pm25' AND NOT s.indoor AND r.mean IS NOT NULL
    AND r.bucket < now() GROUP BY r.sensor_id, r.metric ORDER BY count(*) DESC LIMIT 1"""


@contextlib.contextmanager
def _cursor():
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as con:
        with con.cursor() as cur:
            yield cur


def _now():
    return datetime.now(timezone.utc)


_clock = time.monotonic


def series(cur, since: datetime) -> dict:
    out = defaultdict(dict)
    cur.execute(SERIES_SQL, (since,))
    for sid, metric, bucket, mean in cur.fetchall():
        out[(sid, metric)][bucket] = float(mean)
    return dict(out)


def outdoor_pm25(cur):
    cur.execute(OUTDOOR_SQL)
    row = cur.fetchone()
    return (row[0], row[1]) if row else None


def _since(today: date) -> datetime:
    return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) - timedelta(
        days=core.SCORED_DAYS + 1, hours=core.CONTEXT_HOURS)


def _due(cur, model_id: str, today: date, now: datetime) -> bool:
    """One read: today's origin is not stored for this model, and the last attempt is not within RETRY_MINUTES."""
    cur.execute("SELECT NOT EXISTS (SELECT 1 FROM predictions WHERE model_id = %s AND origin = %s) "
                "AND COALESCE((SELECT last_try FROM models WHERE model_id = %s) < %s, TRUE)",
                (model_id, today, model_id, now - timedelta(minutes=RETRY_MINUTES)))
    return bool(cur.fetchone()[0])


def run(cur, hc, today: date, tz: str, expect: str | None = None, until: float | None = None) -> dict:
    """Fills the missing origins oldest first. With `until` (a _clock() time) it stops after the origin that passes it,
    with state "cut"; at least one origin is always done, so a slow machine still moves on."""
    try:
        h = hc.get(MODELS_URL + "/health", timeout=5).json()
    except Exception as e:  # noqa: BLE001
        log.warning("predict: models container not answering (%s)", e)
        return {"state": "no-answer", "model_id": None, "filled": 0}
    if not h.get("ready"):
        return {"state": "no-model", "model_id": None, "filled": 0}
    model_id = f"{h['model']}@{h['revision']}"
    if expect and model_id != expect:
        return {"state": "no-model", "model_id": None, "filled": 0}
    cur.execute("INSERT INTO models (model_id, name, revision) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (model_id, h["model"], h["revision"]))
    pts = series(cur, _since(today))
    keys = sorted(pts)
    if not any(core.context(pts[k], core.origin_utc(today, tz)) for k in keys):
        return {"state": "young", "model_id": model_id, "filled": 0}
    cur.execute("SELECT DISTINCT origin FROM predictions WHERE model_id = %s AND origin >= %s",
                (model_id, today - timedelta(days=core.SCORED_DAYS)))
    done = {r[0] for r in cur.fetchall()}
    filled = 0
    for day in (today - timedelta(days=k) for k in range(core.SCORED_DAYS, -1, -1)):
        if day in done:
            continue
        origin = core.origin_utc(day, tz)
        ctx = [(k, c) for k in keys if (c := core.context(pts[k], origin))]
        if not ctx:
            continue
        if filled and until is not None and _clock() >= until:
            return {"state": "cut", "model_id": model_id, "filled": filled}
        r = hc.post(MODELS_URL + "/forecast", json={"series": [c for _, c in ctx], "horizon": core.HORIZON}, timeout=120)
        r.raise_for_status()
        qss = r.json()["quantiles"]
        if len(qss) != len(ctx):
            raise ValueError(f"the models container answered {len(qss)} series for {len(ctx)}")
        rows = [(model_id, sid, metric, day, origin + timedelta(hours=i), p10, p50, p90)
                for ((sid, metric), _), qs in zip(ctx, qss) for i, (p10, p50, p90) in enumerate(qs) if p50 is not None]
        with cur.connection.transaction():
            cur.executemany("INSERT INTO predictions (model_id, sensor_id, metric, origin, ts, p10, p50, p90) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", rows)
        filled += 1
    cur.execute("DELETE FROM predictions WHERE origin < %s", (today - timedelta(days=core.KEEP_DAYS),))
    return {"state": "ok", "model_id": model_id, "filled": filled}


def _stored(cur, model_id: str, since: date) -> dict:
    """(sensor, metric) -> origin -> {ts: p50}"""
    cur.execute("SELECT sensor_id, metric, origin, ts, p50 FROM predictions WHERE model_id = %s AND origin >= %s",
                (model_id, since))
    out = defaultdict(lambda: defaultdict(dict))
    for s, m, o, ts, p50 in cur.fetchall():
        out[(s, m)][o][ts] = p50
    return out


def scores(cur, model_id: str, today: date, tz: str) -> dict:
    """(sensor, metric) -> {"d1": score, "d2": score}, over the last SCORED_DAYS scored origins (core.score)."""
    stored = _stored(cur, model_id, today - timedelta(days=core.KEEP_DAYS))
    if not stored:
        return {}
    first = min(o for by in stored.values() for o in by)
    truth = series(cur, core.origin_utc(first, tz) - timedelta(hours=24))
    out = {}
    for key, by in stored.items():
        days = [core.day_errors(by[o], truth.get(key, {}), core.origin_utc(o, tz)) for o in sorted(by)]
        out[key] = {d: core.score([x[d] for x in days]) for d in ("d1", "d2")}
    return out


def _meta(cur, model_id: str, today: date, tz: str) -> dict:
    rng, unit = None, "µg/m³"
    key = outdoor_pm25(cur)
    sc = scores(cur, model_id, today, tz).get(key, {}).get("d2") if key else None
    if sc and sc["shown"]:
        pred = _stored(cur, model_id, today).get(key, {}).get(today, {})
        rng = core.day_range(pred, core.origin_utc(today, tz), 2)
        cur.execute("SELECT c.unit FROM channel_roles c JOIN sensors s ON s.source = c.source "
                    "WHERE s.sensor_id = %s AND c.metric = 'pm25'", (key[0],))
        row = cur.fetchone()
        unit = row[0] if row and row[0] else unit
    return core.ahead_meta(today, rng, unit, sc)


def fetch(hc):
    try:
        until = _clock() + BUDGET_SECONDS
        tz = os.getenv("NODE_TZ") or "UTC"
        now = _now().astimezone(ZoneInfo(tz))
        name = (os.getenv("PREDICT_MODEL") or "").strip()
        with open(os.path.join(HERE, "models.json")) as f:
            entry = json.load(f).get(name)
        if not entry or now.strftime("%H:%M") < core.RUN_AFTER:
            return [], []
        today = now.date()
        with _cursor() as cur:
            gate = f"{name}@{entry['revision']}"
            if not _due(cur, gate, today, now):
                return [], []
            cur.execute("INSERT INTO models (model_id, name, revision, last_try) VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (model_id) DO UPDATE SET last_try = EXCLUDED.last_try",
                        (gate, name, entry["revision"], now))
            r = run(cur, hc, today, tz, expect=gate, until=until)
            if r["state"] == "cut":
                # the budget ran out between origins: not a failure, so the next poll may carry on at once
                cur.execute("UPDATE models SET last_try = NULL WHERE model_id = %s", (gate,))
                log.info("predict: %d origins stored, the rest at the next poll", r["filled"])
                return [], []
            if r["state"] != "ok":
                if r["state"] == "no-model":
                    log.warning("predict: the container has no %s ready", gate)
                return [], []
            meta = _meta(cur, r["model_id"], today, tz)
        return [{"sensor_id": "predict", "source": "predict", "name": "Modelled here", "lat": None, "lon": None,
                 "indoor": False, "local": False, "kind": "model", "meta": meta}], []
    except Exception as e:  # noqa: BLE001
        log.warning("predict: nightly run stopped (%s)", e)
        return [], []
