"""What worked here (docs/SPEC_learn.md step 1): the household's own evidence, from the actions ledger.

For every act-level alert on one sensor that somebody acted on, or that nobody answered at all, the node takes the
metric the rule watches on that sensor in the hour before (the act, or the alert when unanswered) and its mean over a
window after, and the same two numbers on the street (every outdoor sensor). Per rule it keeps the medians as one row
of `learnings`, with its cases, so the page can show the proof.

WHAT IT DOES NOT CLAIM, AND THE ROW SAYS SO: a cause. GET /effect already warns that air clearing at 03:00 may be the
window or the night. Here the street's change is beside the house's, and the unanswered alerts beside the acted ones,
which is more than a before and after; it is still not an experiment.

Hourly, because readings_1h is what a node keeps for every sensor; the hour before the act ends up to 59 minutes
before it. Code proves, a model only words (SPEC_learn §2): the statement is a template over the numbers.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone

# The metric a rule is judged on, when its own `watch` does not name one, by pack. inside_worse_ventilate fires on a
# relation (inside worse than outside) and has no line, but what it asks you to change is still PM2.5.
# ponytail: two issues; a pack that wants its own declares `watch: {metric}` on its rules
PACK_METRIC = {"air-quality": "pm25", "heat": "apparent"}
# Hours after the act that make "after": air changes within the hour, a room's heat over several.
AFTER = {"pm25": (1, 2), "apparent": (3, 6), "temp": (3, 6)}
UNIT = {"pm25": "µg/m³", "apparent": "°C", "temp": "°C"}
WORDS = {"pm25": "PM2.5", "apparent": "the feels-like temperature", "temp": "the temperature"}
EARLY = 5          # fewer acted cases than this and the row says "too early to say", with its count


def apparent(t: float, rh: float) -> float:
    """The node's own Steadman form, as packs/heat/rules.yml and usual_by_hour write it."""
    return t + 0.33 * (rh / 100.0 * 6.105 * math.exp(17.27 * t / (237.7 + t))) - 4.0


def series(rows: list[dict]) -> dict:
    """Hourly means as {(sensor_id, metric): {bucket: value}}, with `apparent` derived where temp and humidity meet."""
    out: dict = {}
    for r in rows:
        out.setdefault((r["sensor_id"], r["metric"]), {})[r["bucket"]] = r["mean"]
    for (sid, m), temps in list(out.items()):
        if m == "temp" and (sid, "humidity") in out:
            hum = out[(sid, "humidity")]
            out[(sid, "apparent")] = {b: apparent(t, hum[b]) for b, t in temps.items() if b in hum}
    return out


def _mean(s: dict, start: datetime, hours: range):
    vals = [s[start + timedelta(hours=h)] for h in hours if start + timedelta(hours=h) in s]
    return sum(vals) / len(vals) if vals else None


def case(s: dict, outdoor: list[dict], h: datetime, after: tuple[int, int]) -> dict | None:
    """One alert's numbers: before and after on its own sensor, and on the street. None when the house has no reading
    on either side; the street may be missing, and then only the house's change is kept."""
    before, aft = _mean(s, h, range(-1, 0)), _mean(s, h, range(after[0], after[1] + 1))
    if before is None or aft is None:
        return None
    ob = [x for x in (_mean(o, h, range(-1, 0)) for o in outdoor) if x is not None]
    oa = [x for x in (_mean(o, h, range(after[0], after[1] + 1)) for o in outdoor) if x is not None]
    street = (sum(oa) / len(oa) - sum(ob) / len(ob)) if ob and oa else None
    return {"at": h.isoformat(), "before": round(before, 1), "after": round(aft, 1),
            "change": round(aft - before, 1), "street": None if street is None else round(street, 1)}


def _med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def summarise(rule: str, metric: str, acted: list[dict], unanswered: list[dict], was: dict | None, live: bool) -> dict:
    """One learning row from the cases, with the statement written from its own numbers."""
    a = {"n": len(acted), "change": _med(c["change"] for c in acted), "street": _med(c["street"] for c in acted)}
    u = {"n": len(unanswered), "change": _med(c["change"] for c in unanswered),
         "street": _med(c["street"] for c in unanswered)}
    w, unit, lo, hi = WORDS[metric], UNIT[metric], *AFTER[metric]
    if not live:
        status = "gone"
    elif a["n"] < EARLY:
        status = "too_early"
    else:
        net = a["change"] - (a["street"] or 0)
        old = ((was or {}).get("numbers") or {}).get("acted") or {}
        old_net = (old.get("change") or 0) - (old.get("street") or 0) if old.get("n", 0) >= EARLY else None
        status = "weakening" if old_net is not None and (old_net < 0) != (net < 0) else "holding"

    def says(x, who):
        street = f", while on the street it changed {x['street']:+.1f} {unit}" if x["street"] is not None else ""
        return f"{who} {x['n']} times: {w} inside changed {x['change']:+.1f} {unit} in the {lo}–{hi} h after{street}."
    if status == "too_early":
        text = f"Acted on {a['n']} times so far: too early to say."
    else:
        text = says(a, "Acted on") if a["n"] else "Nobody has acted on it yet."
        if u["n"]:
            text += " " + says(u, "Left unanswered")
    return {"kind": "worked", "key": rule, "issue": rule.split("/")[0], "metric": metric, "status": status,
            "statement": text, "n": a["n"], "scope": "house",
            "numbers": {"acted": a, "unanswered": u, "after_hours": [lo, hi], "unit": unit,
                        "cases": {"acted": acted[-30:], "unanswered": unanswered[-30:]}}}


def learn_worked(q, rules: list[dict], live: set, was: dict) -> list[dict]:
    """Every rule's row, for each rule with at least one case. `q` reads the database (main.q), `rules` are
    packs.load_rules(), `live` the rules that can still fire, `was` the previous rows by key (for `weakening`). A rule
    no longer loaded still gets its row, marked `gone`, from its alerts: retiring a rule does not unlearn it."""
    watch = {r["id"]: (r.get("watch") or {}).get("metric") for r in rules if isinstance(r, dict) and r.get("id")}
    alerts = q("""SELECT l.id, l.ts, l.rule_id, l.sensor_id,
                         (SELECT min(x.ts) FROM actions x WHERE x.alert_id = l.id AND x.stage = 'acted') AS acted_at,
                         EXISTS (SELECT 1 FROM actions x WHERE x.alert_id = l.id) AS answered,
                         (SELECT string_agg(x.note, ' · ') FROM actions x
                           WHERE x.alert_id = l.id AND x.stage = 'acted' AND coalesce(x.note, '') <> '') AS note
                  FROM alerts l
                  WHERE l.level = 'act' AND l.sensor_id IS NOT NULL
                  ORDER BY l.ts""")
    want = {}
    for rid in dict.fromkeys(a["rule_id"] for a in alerts):
        metric = watch.get(rid) or PACK_METRIC.get(rid.split("/")[0] if "/" in rid else "")
        if metric in AFTER:
            want[rid] = metric
    if not want:
        return []
    since = min(_aware(a["ts"]) for a in alerts) - timedelta(hours=2)
    rows = q("""SELECT date_trunc('hour', r.ts) AS bucket, r.sensor_id, r.metric, avg(r.value) AS mean, bool_or(s.indoor) AS indoor
                FROM readings r JOIN sensors s USING (sensor_id)
                WHERE s.kind = 'sensor' AND r.metric IN ('pm25', 'temp', 'humidity') AND r.ts >= %s AND r.ts <= now()
                GROUP BY 1, 2, 3""", since)
    for r in rows:
        r["bucket"] = _aware(r["bucket"])
    s = series(rows)
    indoor = {r["sensor_id"]: r["indoor"] for r in rows}
    now = datetime.now(timezone.utc)
    out = []
    for rule, metric in want.items():
        street = [v for (sid, m), v in s.items() if m == metric and indoor.get(sid) is False]
        acted, unanswered = [], []
        for a in (x for x in alerts if x["rule_id"] == rule):
            h = _aware(a["acted_at"] or a["ts"]).replace(minute=0, second=0, microsecond=0)
            if a["acted_at"] is None and a["answered"]:
                continue                     # seen or dismissed, but not acted on: neither group
            if now < h + timedelta(hours=AFTER[metric][1] + 1):
                continue                     # its after-window has not passed yet
            c = case(s.get((a["sensor_id"], metric), {}), street, h, AFTER[metric])
            if c:
                (acted if a["acted_at"] else unanswered).append({**c, "note": a["note"] or ""} if a["acted_at"] else c)
        if acted or unanswered:
            out.append(summarise(rule, metric, acted, unanswered, was.get(rule), rule in live))
    return out




def _aware(t) -> datetime:
    t = datetime.fromisoformat(t) if isinstance(t, str) else t
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
