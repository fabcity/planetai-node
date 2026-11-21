"""The arithmetic of the predict pack: pure, stdlib only. No database, no network, no model.

A forecast starts at a local midnight (the origin) and runs HORIZON hours: day one is hours 0-23, day two 24-47.
It is scored against what was measured, and shown only once it has beaten "tomorrow looks like today" on enough days.
"""
import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

HORIZON = 48
SCORED_DAYS = 28
MIN_DAYS = 14
MIN_PRESENT = 0.90
MIN_CONTEXT_DAYS = 7
MIN_SCORED = 7
KEEP_DAYS = 35
CONTEXT_HOURS = 4096
RUN_AFTER = "00:10"

_HOUR = timedelta(hours=1)


def origin_utc(day: date, tz: str) -> datetime:
    """That local day's midnight, as an aware UTC datetime."""
    return datetime.combine(day, time(0), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def context(points: dict, origin: datetime):
    """Hourly values before `origin`, oldest first, gaps filled linearly, cut to the last CONTEXT_HOURS.
    None when the series is younger than MIN_CONTEXT_DAYS or under MIN_PRESENT measured in its last MIN_DAYS."""
    pts = {t: v for t, v in points.items() if t < origin}
    if not pts:
        return None
    first = min(pts)
    n = int((origin - first) / _HOUR)
    if n < MIN_CONTEXT_DAYS * 24:
        return None
    window = min(n, MIN_DAYS * 24)
    if sum(1 for i in range(n - window, n) if first + i * _HOUR in pts) < MIN_PRESENT * window:
        return None
    known = [i for i in range(n) if first + i * _HOUR in pts]
    out, j = [], 0
    for i in range(n):
        while known[j] < i and j + 1 < len(known):
            j += 1
        hi = known[j]
        lo = known[j - 1] if hi > i and j else hi
        vlo, vhi = pts[first + lo * _HOUR], pts[first + hi * _HOUR]
        out.append(vlo if hi == lo else vlo + (vhi - vlo) * (i - lo) / (hi - lo))
    return out[-CONTEXT_HOURS:]


def day_errors(pred: dict, truth: dict, origin: datetime) -> dict:
    """{"d1": (model_mae, naive_mae, hours) | None, "d2": ...}. The naive forecast for both days is the same clock hour
    of the 24 hours before the origin; an hour counts only when the model, the truth and the naive value all exist."""
    out = {}
    for d in (0, 1):
        m = n = k = 0
        for h in range(24):
            t = origin + timedelta(hours=24 * d + h)
            base = truth.get(origin + timedelta(hours=h - 24))
            if t in pred and t in truth and base is not None:
                m += abs(pred[t] - truth[t])
                n += abs(base - truth[t])
                k += 1
        out[f"d{d + 1}"] = (m / k, n / k, k) if k else None
    return out


def score(days: list) -> dict:
    """Means over the scored origins; `shown` only with MIN_SCORED of them and a model strictly closer than naive."""
    if not days:
        return {"model": 0.0, "naive": 0.0, "days": 0, "shown": False}
    model = sum(d[0] for d in days) / len(days)
    naive = sum(d[1] for d in days) / len(days)
    return {"model": model, "naive": naive, "days": len(days), "shown": len(days) >= MIN_SCORED and model < naive}


def day_range(pred: dict, origin: datetime, day: int):
    """Lowest and highest p50 over that day (1 or 2), or None."""
    vals = [pred[t] for h in range(24) if (t := origin + timedelta(hours=24 * (day - 1) + h)) in pred]
    return (min(vals), max(vals)) if vals else None


def ahead_meta(today: date, rng, unit: str) -> dict:
    """The sensor meta the Next days line reads: the day it was made and, with a range, tomorrow's text in en, es, id."""
    meta = {"fetched": today.isoformat()}
    if rng:
        a, b = (math.floor(x + 0.5) for x in rng)
        span = f"{a}–{b} {unit}"
        meta["ahead_en_d1"] = f"PM2.5 outside: {span} (modelled here)"
        meta["ahead_es_d1"] = f"PM2.5 fuera: {span} (modelado aquí)"
        meta["ahead_id_d1"] = f"PM2.5 di luar: {span} (dimodelkan di sini)"
    return meta
