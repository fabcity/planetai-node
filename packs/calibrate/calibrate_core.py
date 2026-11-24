"""The arithmetic of the calibrate pack: one sensor corrected against a better one a keeper names beside it.

A straight line is fitted on the 14 days before a day, scored on that day (which the line never saw), and shown
only while the newest scored days say it is at least a tenth closer. An hour where either side has read one value
for 24 hourly readings in a row is not paired. Pure, stdlib only.
"""
import statistics as st
from datetime import date, datetime, timedelta
from itertools import groupby
from typing import NamedTuple
from zoneinfo import ZoneInfo

FIT_DAYS, MIN_FIT_HOURS, MIN_DAY_HOURS = 14, 168, 12
WINDOW, MAX_AGE_DAYS, MIN_SCORED, MARGIN = 14, 28, 7, 0.9
KEEP_DAYS, MAX_METRES, READ_DAYS, STUCK_HOURS = 7, 50, 42, 24


class Pair(NamedTuple):
    sensor: str
    reference: str
    metric: str
    since: date
    until: date | None


def parse_pairs(text, today):
    out, seen = [], set()
    for entry in (e.strip() for e in text.split(";")):
        if not entry:
            continue
        f, pair, problem = entry.split(), None, None
        if len(f) not in (4, 5):
            problem = "fields"
        else:
            try:
                since = date.fromisoformat(f[3])
                until = date.fromisoformat(f[4]) if len(f) == 5 else None
            except ValueError:
                problem = "date"
            if problem is None:
                if until and until < since:
                    problem = "until-before-since"
                elif since > today:
                    problem = "since-in-future"
                elif f[0] == f[1]:
                    problem = "same"
                elif (f[0], f[2]) in seen:
                    problem = "duplicate"
            if problem is None:
                pair = Pair(f[0], f[1], f[2], since, until if until and until <= today else None)
            seen.add((f[0], f[2]))
        out.append({"entry": entry, "pair": pair, "problem": problem})
    return out


def refuse(pair, sensor, reference, station_sources, roles, metres):
    for side, row in (("sensor", sensor), ("reference", reference)):
        if row is None:
            return {"test": "unknown", "side": side}
    for side, row in (("sensor", sensor), ("reference", reference)):
        if row.get("kind") != "sensor":
            return {"test": "not-a-sensor", "side": side}
    if sensor["source"] in station_sources:
        return {"test": "sensor-is-station"}
    for side, row in (("sensor", sensor), ("reference", reference)):
        if (row["source"], pair.metric) not in roles:
            return {"test": "no-channel", "side": side}
    # a station's indoor flag is the archive's guess; the keeper who named the pair vouches for where the two stand
    if reference["source"] not in station_sources and bool(sensor.get("indoor")) != bool(reference.get("indoor")):
        return {"test": "indoor-outdoor"}
    if metres is not None and metres > MAX_METRES:
        return {"test": "apart", "metres": max(round(metres), MAX_METRES + 1)}
    return None


def _day(hour, tz):
    return hour.astimezone(ZoneInfo(tz)).date()


def _stuck(series):
    """The hours of every run of one value at least STUCK_HOURS readings long: a dead channel stored again under
    fresh hours (docs/sensors.md, gotcha 2), which a line would follow down to the frozen number."""
    out = set()
    for _, run in groupby(sorted(series), key=series.get):
        run = list(run)
        if len(run) >= STUCK_HOURS:
            out.update(run)
    return out


def paired(x, y, pair, tz):
    stuck = _stuck(x) | _stuck(y)
    return [(t, x[t], y[t]) for t in sorted((x.keys() & y.keys()) - stuck)
            if pair.since <= _day(t, tz) and (pair.until is None or _day(t, tz) <= pair.until)]


def line(points):
    if len(points) < MIN_FIT_HOURS or len({p[2] for p in points}) < 2:  # a reference frozen on one value
        return None
    try:
        b, a = st.linear_regression([p[1] for p in points], [p[2] for p in points])
    except st.StatisticsError:  # the sensor never varied
        return None
    return a, b


def correct(a, b, value, floor0):
    v = a + b * value
    return max(0.0, v) if floor0 else v


def _no_negatives(points):
    return not any(p[2] < 0 for p in points)


def scored_days(points, tz, today):
    by_day = {}
    for p in points:
        by_day.setdefault(_day(p[0], tz), []).append(p)
    out = []
    for d in sorted(by_day):
        if d >= today or len(by_day[d]) < MIN_DAY_HOURS:
            continue
        fit = [p for k in range(1, FIT_DAYS + 1) for p in by_day.get(d - timedelta(days=k), [])]
        ab = line(fit)
        if ab is None:
            continue
        f0, n = _no_negatives(fit), len(by_day[d])
        out.append((d, sum(abs(s - r) for _, s, r in by_day[d]) / n,
                    sum(abs(correct(*ab, s, f0) - r) for _, s, r in by_day[d]) / n))
    return out


def verdict(scored, last_day):
    recent = [s for s in scored if s[0] >= last_day - timedelta(days=MAX_AGE_DAYS)][-WINDOW:]
    if len(recent) < MIN_SCORED:
        return None, {"reason": "young", "days": len(recent), "need_days": MIN_SCORED}
    m, c = st.mean(s[1] for s in recent), st.mean(s[2] for s in recent)
    checked = {"days": len(recent), "measured": m, "corrected": c}
    if c >= m:
        return checked, {"reason": "measured-closer"}
    if c > MARGIN * m:
        return checked, {"reason": "not-a-tenth"}
    return checked, None


def work(pair, x, y, now, tz):
    pts = paired(x, y, pair, tz)
    # the side stuck right now, while the pair is open: why nothing is being paired, for the page to say
    stuck = None if pair.until else next((side for side, s in (("sensor", x), ("reference", y)) if s and max(s) in _stuck(s)), None)
    out = {"paired_hours": len(pts), "last_paired": None, "line": None, "floor0": True, "stuck": stuck,
           "checked": None, "shown": False, "why": {"reason": "no-hours"}}
    if not pts:
        return out
    last = out["last_paired"] = pts[-1][0]
    win = [p for p in pts if p[0] > last - timedelta(days=FIT_DAYS)]
    ab, out["floor0"] = line(win), _no_negatives(win)
    if ab:
        out["line"] = {"a": ab[0], "b": ab[1], "hours": len(win)}
    if now - last > timedelta(days=KEEP_DAYS):
        out["why"] = {"reason": "withdrawn", "since": _day(last, tz)}
    elif ab is None and len(win) >= MIN_FIT_HOURS:
        out["why"] = {"reason": "flat"}
    elif ab is None:
        out["why"] = {"reason": "young", "hours": len(win), "need_hours": MIN_FIT_HOURS, "days": 0, "need_days": MIN_SCORED}
    else:
        out["checked"], out["why"] = verdict(scored_days(pts, tz, _day(now, tz)), _day(last, tz))
        if out["why"] and out["why"]["reason"] == "young":
            out["why"].update(hours=len(win), need_hours=MIN_FIT_HOURS)
    out["shown"] = out["why"] is None
    return out
