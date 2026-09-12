"""The engine: SQL and arithmetic, and nothing from a model.

`compute()` reads five tables once and answers, for every issue the node declares: which state it is
in and why, the four distances with their values and provenance, the line, the attribution class, the
open asks, twenty-four hours of series at each distance, and one sentence in each of three locales.

Every sentence is a template over numbers this file worked out. There is no prompt anywhere in it: a
node with no agent container, no network and no model reachable produces exactly the same page as one
with all three, which is the invariant the whole dashboard rests on.

Three pieces of arithmetic are worth reading before changing anything:

  · `apparent()` is Steadman's no-wind form, the same expression `packs/heat/rules.yml` evaluates in
    SQL. It is applied PER SENSOR and the results are then aggregated — not the other way round.
    Apparent temperature is not linear in its inputs, so the median of four sensors' apparent
    temperatures is not the apparent temperature of their median temperature and median humidity.
    On node #1's 6 September capture the four indoor units give 30.8 the first way and 30.5 the
    second; 30.8 is what the room felt like.

  · `fenced_median()` trims with median absolute deviation, not with Tukey's fence. A ring is often
    three or four stations, and at three the outlier IS the upper quartile, so 1.5 x IQR calls
    nothing odd. Six MADs above the median, with a floor, so a ring that agrees exactly does not
    collapse onto itself. Lifted from the dashboard (index.html:761) where it was drawing an axis.

  · `_classify()` is the attribution classifier: clear · inside · everywhere · outside_worse ·
    mixed · unknown. It compares by the mode the issue declares, because a concentration compares by
    ratio and a temperature has to compare by difference. The place prompt's own release will
    replace this with the version that also reads wind direction; until then this is the shipped
    dashboard's `why()` logic, moved here and given the six names.
"""
from __future__ import annotations

import logging
import math
import os
import statistics
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import datetime, timezone

import packs

from . import (CMP_WORDS, DISTANCES, JOIN_WORDS, LABEL_WORDS, LOCALES, NOUN_WORDS, REASON_WORDS,
               SPAN_WORDS, WHERE_WORDS, order)
from .schema import is_open, is_seen, place_of, stage_of

log = logging.getLogger("planetai.issues")

# A device that has said nothing for two hours is not reporting. Same number as the rules and the
# shipped page used, so the stack and the alerts cannot disagree about who is awake.
FRESH_MINUTES = 120
# An act-level ask whose reading has come back is still an ask, but it stops being *now* after this.
ASK_CURRENT_HOURS = 2
# "a warn in the last 24 h" — the window `notable` is measured over.
NOTABLE_HOURS = 24
# An ask is an alert somebody is expected to answer, and ρ is the share of them that got an answer
# (app/index.py:105 counts level='act' and nothing else). So `open_asks` holds act-level alerts only:
# an `info` note was never an ask, and saying "still open, the reading came back" about a digest is
# both untrue and a way to make the strip look busy when nothing is being asked of anyone.
ASK_LEVEL = "act"


# ---------------------------------------------------------------------------------------- arithmetic
def apparent(t: float | None, rh: float | None) -> float | None:
    """Steadman apparent temperature, no-wind form: AT = T + 0.33e - 4.0, e the vapour pressure in
    hPa from T and RH. The expression is character-for-character the one in packs/heat/rules.yml."""
    if t is None or rh is None:
        return None
    return t + 0.33 * (rh / 100.0 * 6.105 * math.exp(17.27 * t / (237.7 + t))) - 4.0


FUNCTIONS = {"apparent": apparent}


def fenced_median(values: list[float]) -> tuple[float | None, list[float]]:
    """The median of the values inside a median-absolute-deviation fence, and the ones outside it.

    Returns (median, outliers). One station reading 152 while the rest read 5 to 12 is either a fire
    in that lane or a broken sensor; either way it is not the neighbourhood, and it is worth naming
    rather than averaging away. The floor on the MAD keeps a ring that agrees exactly from fencing
    itself down to a single value.
    """
    if not values:
        return None, []
    m0 = statistics.median(values)
    mad = statistics.median([abs(v - m0) for v in values])
    fence = m0 + 6 * max(mad, 5 / 6)
    inside = [v for v in values if v <= fence]
    return (statistics.median(inside) if inside else m0), [v for v in values if v > fence]


def _aggregate(values: list[float], how: str) -> tuple[float | None, list[float]]:
    if not values:
        return None, []
    if how == "mean":
        return statistics.fmean(values), []
    if how == "median":
        return statistics.median(values), []
    if how == "fenced_median":
        return fenced_median(values)
    log.warning("unknown aggregate %r — treating it as a mean", how)
    return statistics.fmean(values), []


def _combine(per_sensor: dict[str, dict[str, float | None]], metrics: list[str],
             function: str | None, how: str) -> tuple[float | None, int, list[float]]:
    """One value from many sensors: the function per sensor, then the aggregate over the results.

    A sensor missing any of the metrics is left out entirely rather than half-counted — which is how
    "public sensors carrying both channels" is enforced without a separate query for it.
    """
    fn = FUNCTIONS.get(function) if function else None
    out = []
    for vals in per_sensor.values():
        got = [vals.get(m) for m in metrics]
        if any(v is None for v in got):
            continue
        out.append(fn(*got) if fn else got[0])
    value, outliers = _aggregate(out, how)
    return value, len(out), outliers


def _worse(a: float | None, b: float | None, compare: dict) -> str | None:
    """Where a stands against b: over · under · level. None when either side is missing."""
    if a is None or b is None:
        return None
    margin = float(compare.get("margin", 1.5))
    if compare.get("mode") == "difference":
        if a - b > margin:
            return "over"
        return "under" if b - a > margin else "level"
    hi = b * margin if b else None
    if hi is not None and a > hi:
        return "over"
    if a and b > a * margin:
        return "under"
    return "level"


def _ambient(row: dict, place: str) -> bool:
    """Whether this row may enter this distance's number.

    SPEC.md §1: "Indoor sensors never enter an ambient average." `place_of` answers geography —
    somebody else's kit indoors is still in the ring — so the ambient rule lives here, once, where no
    issue's .yml can forget it and where the stack and the series cannot disagree about it. Node #1's
    own capture is why: two of its eleven ring stations are other people's indoor kits, one reading
    0.3 µg/m³, and leaving them in moved the street from 7.0 to 6.1.
    """
    return place_of(row) == place and (place == "room" or not row.get("indoor"))


# ------------------------------------------------------------------------------------------ the stack
def _cell(value, n, source, provenance, age_min, sensors, outliers=()) -> dict:
    return {"value": None if value is None else round(value, 6), "n": n, "source": source,
            "provenance": provenance, "age_minutes": None if age_min is None else round(age_min),
            "sensors": sensors, "outliers": len(outliers)}


def _from_stats(spec: dict, stats: list[dict], names: dict) -> dict | None:
    """One distance's value from the rolling means. See `_ambient` for the indoor rule."""
    place, field = spec["place"], spec["field"]
    rows = [r for r in stats
            if _ambient(r, place) and r.get("metric") in spec["metrics"]
            and (r.get("silent_minutes") is None or r["silent_minutes"] < FRESH_MINUTES)]
    if not rows:
        return None
    per: dict[str, dict] = {}
    for r in rows:
        per.setdefault(r["sensor_id"], {})[r["metric"]] = r.get(field)
    value, n, outliers = _combine(per, spec["metrics"], spec.get("function"), spec["aggregate"])
    if value is None:
        return None
    used = sorted(s for s in per if all(per[s].get(m) is not None for m in spec["metrics"]))
    age = min((r["silent_minutes"] for r in rows if r.get("silent_minutes") is not None), default=None)
    # ours is measured here; somebody else's is theirs, which is a different word whatever its quality
    word = "live" if place in ("room", "yard") else "partial"
    if len(used) == 1:
        source = names.get(used[0]) or used[0]
    else:
        source = f"{len(used)} sensors"
    return _cell(value, n, source, word, age, used, outliers)


def _from_observations(spec: dict, obs: list[dict], now: datetime) -> dict | None:
    sid = spec["sensor_id"]
    rows = {r["metric"]: r for r in obs if r["sensor_id"] == sid and r["metric"] in spec["metrics"]}
    if len(rows) < len(spec["metrics"]):
        return None
    per = {sid: {m: r["value"] for m, r in rows.items()}}
    value, n, _ = _combine(per, spec["metrics"], spec.get("function"), "mean")
    if value is None:
        return None
    first = next(iter(rows.values()))
    age = _age_minutes(first.get("ts"), now)
    # SPEC.md §1: a model or a portal is partial, whatever its quality. The layer's provenance
    # vocabulary is finer than that — `model` says which kind of partial — so a model row gets
    # `model` and a portal row keeps `partial`.
    word = "model" if first.get("kind") == "model" else "partial"
    return _cell(value, n, first.get("name") or sid, word, age, [sid])


def _from_earth(spec: dict, earth: dict | None, obs: list[dict], now: datetime) -> dict | None:
    """The node's own AlphaEarth record: what packs/earth computed here, from files it downloaded.

    No fallback, on purpose. See the comment on land.yml's region column: the candidate metric was
    retired in v0.33.1 as a second number for one idea, and `observations` would still be holding a
    stale row for it on any node that ran the pack before then. With no record this returns None, the
    issue is `none`, and the page says how to fetch one.
    """
    latest = (earth or {}).get("latest") or {}
    if latest.get("share_over_threshold") is None:
        return None
    over = latest.get("threshold")
    cell = _cell(latest["share_over_threshold"] * 100, 1,
                 f"this node's own AlphaEarth comparison, {latest.get('year_a')}"
                 f"\u2013{latest.get('year_b')}"
                 + (f", pixels that moved more than {over}" if over is not None else ""),
                 "model", _age_minutes(latest.get("computed_at"), now), ["earth"])
    # The share is the statistic the sentence uses because it accumulates the way a reader expects:
    # on node #1, 2024-2025 is 1.3 % and 2017-2025 is 8.5 %. `mean` does not — its 2017-2025 figure
    # (0.027) is SMALLER than one year's (0.043), because it is a mean per-pixel distance in
    # embedding space and not a quantity of change. Both travel in `extra` so the band can draw the
    # span without a second request, and so Figures can name the one the Index cell uses.
    cell["extra"] = {k: latest.get(k) for k in
                     ("mean", "median", "p95", "threshold", "hectares_over_threshold",
                      "year_a", "year_b", "metres_per_pixel", "radius_m")}
    # The longest span the pack has computed to the same end year: on node #1, 2017-2025 at 8.5 %.
    # That is the sentence's history — one year is a number, eight years is a direction.
    spans = [c for c in (earth or {}).get("changes") or []
             if c.get("year_b") == latest.get("year_b") and c.get("share_over_threshold") is not None
             and (c.get("year_b") or 0) - (c.get("year_a") or 0) > 1]
    if spans:
        first = min(spans, key=lambda c: c.get("year_a") or 9999)
        cell["extra"]["since_year"] = first["year_a"]
        cell["extra"]["since_pct"] = round(first["share_over_threshold"] * 100, 1)
    return cell


def _age_minutes(ts, now: datetime) -> float | None:
    if not ts:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() / 60


def _stack(d: dict, stats, obs, earth, names, now) -> dict:
    out = {}
    for dist in DISTANCES:
        spec = (d.get("distances") or {}).get(dist)
        if not spec:
            out[dist] = None
            continue
        src = spec.get("from")
        if src == "stats":
            out[dist] = _from_stats(spec, stats, names)
        elif src == "observations":
            out[dist] = _from_observations(spec, obs, now)
        elif src == "earth":
            out[dist] = _from_earth(spec, earth, obs, now)
        else:
            out[dist] = None
    return out


# ------------------------------------------------------------------------------------- attribution
def _classify(stack: dict, line: dict | None, compare: dict) -> str:
    """Which of the six stories the stack tells.

    `outside` is the yard if the node has one and the ring if it does not — the same order as
    everywhere else in this repo ("the person's own outdoor sensors, else the nearest public
    references, else the model", AGENTS.md).
    """
    room = (stack.get("room") or {}).get("value")
    outside = (stack.get("yard") or {}).get("value")
    if outside is None:
        outside = (stack.get("ring") or {}).get("value")
    if room is None:
        return "unknown"
    over = line is not None and room > float(line["value"])
    out_over = line is not None and outside is not None and outside > float(line["value"])
    if not over and not out_over:
        return "clear"
    rel = _worse(room, outside, compare)
    if rel == "over" and over:
        return "inside"
    if rel == "under" and out_over:
        return "outside_worse"
    if rel == "level" and over and out_over:
        return "everywhere"
    return "mixed"


# ------------------------------------------------------------------------------------------ the asks
def _mine(d: dict, rule_id: str, domain_of: dict) -> bool:
    """Whether an alert belongs to this issue: its pack's domain, or the rule named by hand."""
    if not rule_id or "/" not in rule_id:
        return False                       # a core rule is domain-blind and belongs to no issue
    pack = rule_id.split("/", 1)[0]
    return domain_of.get(pack) in (d["packs"]["domains"] or []) or rule_id in (d["packs"]["rules"] or [])


def _asks(d, alerts, actions, stack, line, domain_of, now) -> tuple[list[dict], list[dict]]:
    """(the open asks, every alert of this issue's in the last 24 h), newest first.

    An open act-level ask is `current` only while its condition still holds: the room is over the
    issue's line, or the alert is under two hours old. On the 6 September capture six act alerts were
    open across twelve hours and one of them (#53, cooking, 14:30) was still open at 22:08 with the
    room at 5 µg/m³. It is still an open ask — ρ counts it — but it is not what is happening now, and
    a page that headlines it is lying about the present.
    """
    room = (stack.get("room") or {}).get("value")
    over = line is not None and room is not None and room > float(line["value"])
    mine = [a for a in alerts if _mine(d, a.get("rule_id", ""), domain_of)]
    recent = [a for a in mine if (_age_minutes(a.get("ts"), now) or 1e9) < NOTABLE_HOURS * 60]
    open_asks = []
    for a in mine:
        if a.get("level") != ASK_LEVEL or not is_open(a, actions):
            continue
        age = _age_minutes(a.get("ts"), now)
        open_asks.append({
            "id": a.get("id"), "ts": a.get("ts"), "rule_id": a.get("rule_id"),
            "sensor_id": a.get("sensor_id"), "level": a.get("level"), "text": a.get("text"),
            "age_minutes": None if age is None else round(age),
            "stage": stage_of(a, actions), "seen": is_seen(a, actions),
            "current": bool(over or (age is not None and age < ASK_CURRENT_HOURS * 60)),
        })
    open_asks.sort(key=lambda a: (not a["current"], -(a["id"] or 0)))
    # Each ask carries its own two sentences in every locale — what it is, and how to close it — so a
    # phone, a wall screen and Telegram all say the same thing and none of them writes it themselves.
    for a in open_asks:
        code = "open_ask_current" if a["current"] else "open_ask_stale"
        a["says"] = {loc: _reason_text({"code": code, "at": a["ts"]}, loc) for loc in LOCALES}
        a["how"] = {loc: _reason_text({"code": "ask_how", "alert_id": a["id"]}, loc) for loc in LOCALES}
    return open_asks, recent


# ------------------------------------------------------------------------------------------ the state
def _state(d, stack, open_asks, recent, line) -> tuple[str, dict]:
    """One of act · notable · quiet · context · none, and the reason, as a code plus its parts."""
    if not any(stack.values()):
        return "none", {"code": "no_source"}
    if d["kind"] == "context":
        return "context", {"code": "context_only"}

    current = [a for a in open_asks if a["current"]]
    if current:
        a = current[0]
        return "act", {"code": "open_ask_current", "at": a["ts"], "alert_id": a["id"]}

    room = (stack.get("room") or {}).get("value")
    over = line is not None and room is not None and room > float(line["value"])
    loud = [a for a in recent if a.get("level") in ("act", "warn")]
    if open_asks:                          # act-level by construction, and none of them current
        a = open_asks[0]
        return "notable", {"code": "open_ask_stale", "at": a["ts"], "alert_id": a["id"]}
    if loud:
        a = loud[0]
        return "notable", {"code": "alert_today", "at": a.get("ts"), "level": a.get("level"),
                           "alert_id": a.get("id")}
    if over and not open_asks:
        return "notable", {"code": "over_line"}
    return "quiet", {"code": "no_alert"}


# --------------------------------------------------------------------------------------- the sentence
def _hhmm(ts) -> str:
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return ""
    return ts.strftime("%H:%M") if isinstance(ts, datetime) else ""


def _reason_text(reason: dict, loc: str) -> str:
    """One line of why, in one language. Every word comes from REASON_WORDS; nothing is typed here.

    A reason that knows the day's high (`peak`, `peak_at`) takes the `_peak` form of its line where
    one exists. On a quiet evening that is the whole of what there is to say, and "nothing to say"
    was leaving it out.
    """
    words = REASON_WORDS.get(loc, REASON_WORDS["en"])
    code = reason["code"]
    if reason.get("peak_at") and code + "_peak" in words:
        code += "_peak"
    return words.get(code, "").format(when=_hhmm(reason.get("at")), level=reason.get("level", ""),
                                      id=reason.get("alert_id", ""), peak=reason.get("peak", ""),
                                      peak_at=reason.get("peak_at", ""))


def _clock(data: dict):
    """The zone every hour on the page is printed in.

    On a node it is NODE_TZ: Postgres runs the session in it (app/main.py), so buckets and alert
    times arrive in one zone already. A snapshot is the case that needs this — `planetai snapshot`
    wrote node #1's hourly buckets in UTC and its alerts in +08:00, and without a rule the quiet line
    said "the day's high was at 06:00" beside an ask "at 14:30" on the same evening. The alerts' own
    zone is the one the household already reads its times in, so it wins when NODE_TZ is not set.
    """
    name = os.getenv("NODE_TZ", "").strip()
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    for a in data.get("alerts") or []:
        ts = a.get("ts")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
        if isinstance(ts, datetime) and ts.tzinfo is not None:
            return ts.tzinfo
    return None


def _peak(series: list[float | None] | None, buckets: list, dp: int, unit: str = "", tz=None) -> dict:
    """The day's high and the hour it landed in, from the 24 hourly values the page already draws.

    History, not statistics: the largest of 24 numbers and its position. Empty with fewer than six
    hours, because "the day's high" of a sensor that came online at lunch is not a day."""
    vals = list(series or [])
    have = [(v, i) for i, v in enumerate(vals) if v is not None]
    if len(have) < 6 or len(buckets) != len(vals):
        return {}
    v, i = max(have)
    at = buckets[i]
    if tz is not None and isinstance(at, datetime) and at.tzinfo is not None:
        at = at.astimezone(tz)
    return {"peak": f"{v:.{dp}f} {unit}".strip(), "peak_at": _hhmm(at)}


def _trend(series: list[float | None], compare: dict) -> str:
    """Which way the room's last three hours went against the three before them."""
    v = [x for x in (series or []) if x is not None]
    if len(v) < 6:
        return "steady"
    a, b = statistics.fmean(v[-3:]), statistics.fmean(v[-6:-3])
    rel = _worse(a, b, compare)
    return {"over": "rising", "under": "falling"}.get(rel, "steady")


def _where(d: dict, dist: str, loc: str) -> str:
    override = ((d.get("where") or {}).get(loc) or {}).get(dist)
    return override or WHERE_WORDS.get(loc, WHERE_WORDS["en"]).get(dist, dist)


def _join(items: list[str], word: str) -> str:
    """a, b and c."""
    if len(items) < 2:
        return "".join(items)
    return f"{', '.join(items[:-1])} {word} {items[-1]}"


def _cmp(d, stack, headline_dist, loc, compare) -> str:
    """{cmp}: where the headline number stands against every other distance that has one.

    A sensed issue compares. A context issue has nothing to compare against — one model row and no
    line — so its {cmp} is its readouts, which is what the review gives a context band instead of a
    stack strip.
    """
    if d["kind"] == "context":
        parts = [r["_text"][loc] for r in (d.get("_readouts") or []) if r.get("_text")]
    else:
        head = (stack.get(headline_dist) or {}).get("value")
        words = CMP_WORDS.get(loc, CMP_WORDS["en"])
        nouns = NOUN_WORDS.get(loc, NOUN_WORDS["en"])
        # One clause per RELATION, not one per distance. Node #1 has a yard, so three distances all
        # answered "level" and the hero read "Level with the wall outside, level with the street,
        # level with the model" — the same three words three times, five lines of headline on a
        # screen budgeted for two. Grouped, that is "Level with the wall outside, the street and the
        # model", and a household reads one comparison instead of counting three.
        grouped: dict[str, list[str]] = {}
        for dist in DISTANCES:
            if dist == headline_dist or not stack.get(dist):
                continue
            rel = _worse(head, stack[dist]["value"], compare)
            if rel:
                grouped.setdefault(rel, []).append(nouns.get(dist, dist))
        join = JOIN_WORDS.get(loc, JOIN_WORDS["en"])
        parts = [words[rel].format(noun=_join(ns, join)) for rel, ns in grouped.items()]
    if not parts:
        return ""
    s = ", ".join(parts)
    return s[0].upper() + s[1:] + "."


def _sentence(d, stack, state, headline_dist, verb_key, loc, compare, attribution) -> str:
    block = (d.get("sentences") or {}).get(loc) or {}
    if state in ("none", "context"):
        tpl = (block.get("state") or {}).get(state)
        if not tpl and state == "none":
            return (d.get("empty") or {}).get(loc, "")
    else:
        tpl = (block.get("state") or {}).get(state) or (block.get("attribution") or {}).get(attribution)
    if not tpl:
        return (d.get("empty") or {}).get(loc, "")
    cell = stack.get(headline_dist) or {}
    n = cell.get("value")
    extra = cell.get("extra") or {}
    sw = SPAN_WORDS.get(loc, SPAN_WORDS["en"])
    span = sw["between"].format(a=extra["year_a"], b=extra["year_b"]) \
        if extra.get("year_a") and extra.get("year_b") else ""
    since = sw["since"].format(pct=f"{extra['since_pct']:.1f}", year=extra["since_year"]) \
        if extra.get("since_year") and extra.get("since_pct") is not None else ""
    return " ".join(tpl.format(
        verb=(block.get("verbs") or {}).get(verb_key, ""),
        n="" if n is None else f"{n:.{d['dp']}f}",
        unit=d["unit"],
        where=_where(d, headline_dist, loc),
        cmp=_cmp(d, stack, headline_dist, loc, compare),
        span=span, since=since,
    ).split()).replace(" ,", ",").replace(" .", ".")


# ------------------------------------------------------------------------------------------- readouts
def _readouts(d, obs, loc_all=LOCALES) -> list[dict]:
    out = []
    for r in d.get("readouts") or []:
        row = next((o for o in obs if o["sensor_id"] == r["sensor_id"] and o["metric"] == r["metric"]), None)
        if not row or row.get("value") is None:
            continue
        dp = int(r.get("dp", 0))
        v = round(row["value"] * float(r.get("scale", 1)), dp)
        shown = f"{v:.{dp}f}"
        out.append({"metric": r["metric"], "value": v, "dp": dp, "unit": r["unit"],
                    "label": r["label"], "source": row.get("name") or r["sensor_id"],
                    "provenance": "model" if row.get("kind") == "model" else "partial",
                    "_text": {loc: f"{r['label'][loc]} {shown} {r['unit']}" for loc in loc_all}})
    return out


# --------------------------------------------------------------------------------------------- series
def _series(d, hourly, buckets, names) -> dict:
    """Twenty-four hourly values at each distance, on the same buckets, so the traces line up."""
    out = {}
    for dist in DISTANCES:
        spec = (d.get("distances") or {}).get(dist)
        if not spec or spec.get("from") != "stats":
            out[dist] = None
            continue
        vals = []
        for b in buckets:
            per: dict[str, dict] = {}
            for r in hourly.get(b, []):
                if not _ambient(r, spec["place"]) or r["metric"] not in spec["metrics"]:
                    continue
                per.setdefault(r["sensor_id"], {})[r["metric"]] = r.get("mean")
            v, _, _ = _combine(per, spec["metrics"], spec.get("function"), spec["aggregate"])
            vals.append(None if v is None else round(v, 6))
        out[dist] = vals if any(v is not None for v in vals) else None
    return out


# ----------------------------------------------------------------------------------------------- read
def _rows(cur, sql, *args) -> list[dict]:
    cur.execute(sql, args)
    return [dict(r) for r in cur.fetchall()]


def _read(cur) -> dict:
    """Five reads, once, for every issue. Nothing here is per-issue: an eighth issue costs no query."""
    return {
        "stats": _rows(cur, "SELECT sensor_id, metric, indoor, local, kind, scale, lat, lon, name, "
                            "last, last_ts, silent_minutes, mean_15m, mean_1h, mean_24h FROM stats"),
        "obs": _rows(cur, "SELECT sensor_id, metric, value, ts, name, kind, scale, local, cadence, "
                          "meta FROM observations"),
        "alerts": _rows(cur, "SELECT id, ts, rule_id, sensor_id, level, text FROM alerts "
                             "ORDER BY ts DESC LIMIT 200"),
        "actions": _rows(cur, "SELECT ts, alert_id, stage, actor, note FROM actions "
                              "WHERE alert_id IS NOT NULL"),
        "hourly": _rows(cur, "SELECT h.bucket, h.sensor_id, h.metric, h.mean, s.indoor, s.local, "
                             "s.kind FROM readings_1h h JOIN sensors s USING (sensor_id) "
                             "WHERE h.bucket > now() - interval '24 hours'"),
    }


class Replay:
    """A cursor that answers `_read`'s five queries from a snapshot instead of from Postgres.

    This is what makes `?fixture=<name>` worth having: a fixture is rendered through the real engine,
    at the hour it was captured, so a design round and a wall screen are looking at the same code. A
    fixture with a baked-in `issues` block would go stale the first time the state machine changed
    and nothing would say so.

    It matches on the table name rather than the whole statement, so a whitespace change in the SQL
    does not break every fixture and every test.
    """
    TABLES = (("FROM stats", "stats"), ("FROM observations", "observations"),
              ("FROM alerts", "alerts"), ("FROM actions", "actions"),
              ("FROM readings_1h", "readings_1h"))

    def __init__(self, snapshot: dict):
        self.snapshot, self.rows = snapshot, []

    def execute(self, sql: str, args=()):
        for needle, key in self.TABLES:
            if needle in sql:
                self.rows = [dict(r) for r in (self.snapshot.get(key) or [])]
                if key == "actions":
                    self.rows = [r for r in self.rows if r.get("alert_id") is not None]
                if key == "readings_1h":
                    for r in self.rows:
                        if isinstance(r.get("bucket"), str):
                            r["bucket"] = datetime.fromisoformat(r["bucket"])
                return
        raise LookupError(f"a snapshot cannot answer this query: {sql[:80]}")

    def fetchall(self):
        return self.rows


def replay(snapshot: dict, settings, decl: dict) -> dict:
    """A snapshot's own issues, computed at the hour it was captured.

    `now` comes from the snapshot: a stack computed against today's wall clock would report every
    figure in a week-old capture as hours stale, which is true of the clock and false of the data.
    """
    now = snapshot.get("as_of")
    if isinstance(now, str):
        now = datetime.fromisoformat(now)
    return compute(Replay(snapshot), settings, decl, earth=snapshot.get("earth"), now=now)


def compute(cur, settings, decl: dict, earth: dict | None = None, now: datetime | None = None) -> dict:
    """Every declared issue, computed. See the module docstring for what is arithmetic and what is not.

    `earth` is `/earth`'s body, passed in rather than re-read here so that the earth pack's record has
    exactly one reader in this repo. `now` is injectable so a fixture can be replayed at the hour it
    was captured; a stack computed against the wall clock of a different day is all `cached`.
    """
    now = now or datetime.now(timezone.utc)
    data = _read(cur)
    declared, dropped = order(settings.get("NODE_ISSUES", ""), decl)
    undeclared = [k for k in sorted(decl) if k not in declared]
    domain_of = {m["id"]: m.get("domain") for m in packs.manifests()}
    names = {r["sensor_id"]: r.get("name") for r in data["stats"]}
    clock = _clock(data)

    buckets = sorted({r["bucket"] for r in data["hourly"]})[-24:]
    hourly: dict = {b: [] for b in buckets}
    for r in data["hourly"]:
        if r["bucket"] in hourly:
            hourly[r["bucket"]].append(r)

    out = {}
    for key in declared + undeclared:
        d = dict(decl[key])
        if key in undeclared:
            # Still shown, at the foot of the index, so a stranger sees what this node could do.
            out[key] = {"state": "none", "watched": False,
                        "reason": {"code": "not_watched"},
                        "reason_text": {loc: _reason_text({"code": "not_watched"}, loc) for loc in LOCALES},
                        "name": d["name"], "kind": d["kind"], "unit": d["unit"], "dp": d["dp"],
                        "stack": {dist: None for dist in DISTANCES}, "line": d.get("line"),
                        "attribution": None, "open_asks": [], "series": {dist: None for dist in DISTANCES},
                        "readouts": [], "provenance": [],
                        # "not watched here", not "no source". The node may well have a source for
                        # this — coast has a marine model wherever there is a sea — and telling a
                        # stranger there is none would be false. The row is greyed and says the
                        # true thing: nobody here asked for it.
                        "sentence": {loc: _reason_text({"code": "not_watched"}, loc)[0].upper()
                                          + _reason_text({"code": "not_watched"}, loc)[1:] + "."
                                     for loc in LOCALES}}
            continue

        compare = d.get("compare") or {"mode": "ratio", "margin": 1.5}
        line = d.get("line")
        stack = _stack(d, data["stats"], data["obs"], earth, names, now)
        d["_readouts"] = _readouts(d, data["obs"])
        open_asks, recent = _asks(d, data["alerts"], data["actions"], stack, line, domain_of, now)
        state, reason = _state(d, stack, open_asks, recent, line)
        series = _series(d, hourly, buckets, names)
        # the headline number is the nearest distance that has one: the room if there is one, else
        # the yard, else the ring, else the model. Same order as every other answer in this repo.
        headline = next((x for x in DISTANCES if stack.get(x)), DISTANCES[0])
        attribution = _classify(stack, line, compare) if d["kind"] == "sensed" else None
        verb_key = _trend(series.get("room") or series.get(headline), compare)
        if reason.get("code") in ("no_alert", "over_line"):
            reason = {**reason, **_peak(series.get("room") or series.get(headline), buckets, d["dp"], d["unit"], clock)}
        out[key] = {
            "state": state, "watched": True,
            "reason": reason,
            "reason_text": {loc: _reason_text(reason, loc) for loc in LOCALES},
            "name": d["name"], "kind": d["kind"], "metric": d["metric"], "unit": d["unit"], "dp": d["dp"],
            "headline": headline, "stack": stack, "line": line, "attribution": attribution,
            "trend": verb_key,
            "open_asks": open_asks,
            "series": series, "buckets": [b.isoformat() if hasattr(b, "isoformat") else b for b in buckets],
            "readouts": [{k: v for k, v in r.items() if k != "_text"} for r in d["_readouts"]],
            "provenance": _provenance(d, stack, earth),
            "sentence": {loc: _sentence(d, stack, state, headline, verb_key, loc, compare, attribution)
                         for loc in LOCALES},
        }

    headline_issue = _headline(out, declared)
    return {"order": declared, "undeclared": undeclared, "dropped": dropped,
            "headline": headline_issue, "as_of": now.isoformat(),
            # the column headings, so the page and Telegram both take their words from the node
            "distances": list(DISTANCES), "labels": LABEL_WORDS,
            "issues": out}


STATE_RANK = {"act": 4, "notable": 3, "quiet": 2, "context": 1, "none": 0}


def _headline(out: dict, declared: list[str]) -> str | None:
    """The issue with the highest state present; ties go to the declared order.

    Deterministic, and printable under the index in one sentence, which is the point of it.
    """
    best = None
    for key in declared:                                   # declared order IS the tie-break
        rank = STATE_RANK.get(out[key]["state"], 0)
        if best is None or rank > STATE_RANK.get(out[best]["state"], 0):
            best = key
    return best


def _provenance(d: dict, stack: dict, earth: dict | None) -> list[dict]:
    """Every figure this issue puts on the page, with where it came from and its word.

    This is what makes `live` an earned word rather than a decoration: the Figures band is generated
    from this list, so a number with no row here cannot be drawn.
    """
    rows = []
    for dist in DISTANCES:
        cell = stack.get(dist)
        if not cell:
            continue
        rows.append({"figure": f"{d['key']}.{dist}", "value": cell["value"], "unit": d["unit"],
                     "source": cell["source"], "provenance": cell["provenance"],
                     "age_minutes": cell["age_minutes"], "n": cell["n"]})
    for r in d.get("_readouts") or []:
        rows.append({"figure": f"{d['key']}.{r['metric']}", "value": r["value"], "unit": r["unit"],
                     "source": r["source"], "provenance": r["provenance"], "age_minutes": None,
                     "n": 1})
    if d.get("line"):
        rows.append({"figure": f"{d['key']}.line", "value": d["line"]["value"],
                     "unit": d["line"].get("unit", d["unit"]), "source": d["line"]["source"],
                     "provenance": "reference", "age_minutes": None, "n": 1})
    if (d.get("distances") or {}).get("region", {}) and \
            ((d.get("distances") or {}).get("region") or {}).get("from") == "earth" and earth:
        rows.append({"figure": f"{d['key']}.square", "value": earth.get("radius_m"), "unit": "m",
                     "source": earth.get("attribution", ""), "provenance": "model",
                     "age_minutes": None, "n": 1})
    return rows
