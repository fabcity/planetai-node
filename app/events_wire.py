"""The alert events as GET /issues carries them (docs/SPEC_dashboard_events.md §3.1).

`build` is pure, so a live node (datetimes) and a capture (ISO strings) go through the same code and are tested apart.
`live` (Task 3) is the reads, on the cursor the /issues route already has open. The page computes nothing from this
block: every number and sentence the event card draws is here.
"""
from __future__ import annotations

import datetime as dt

import actions as A

ENGINES = ("rules", "shadow", "events")
ORDER = ("danger", "sustained", "unusual", "spike", "ahead")   # which open event leads (§3.1)
HOLD = dt.timedelta(hours=3)                                   # Not now: docs/SPEC_alerts.md §7
RECENT = dt.timedelta(days=7)                                  # Act's record (§4.3)
OUTSIDE = {"apparent": "temp", "temp": "temp", "pm25": "pm25"}  # an issue's metric -> events_pg.context's outside_*
SENT_ACTION = "\n\n👉 "                                         # how actions.render puts the action under the story


def engine_of(value) -> str:
    """run_rules' own reading of ALERT_ENGINE: anything else behaves as rules."""
    return value if value in ENGINES else "rules"


def _t(v):
    if v is None or isinstance(v, dt.datetime):
        return v
    return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def _iso(v):
    v = _t(v)
    return v.isoformat() if v else None


def _latest(rows: list[dict]) -> dict:
    out = {}
    for r in rows:
        k = r["event_id"]
        if k not in out or _t(r["ts"]) > _t(out[k]["ts"]):
            out[k] = r
    return out


def rank(row: dict) -> tuple:
    """Lower sorts first: the most serious kind, then the one open longest."""
    k = row["kind"]
    return (ORDER.index(k) if k in ORDER else len(ORDER), _t(row["opened_at"]))


def _answer(a: dict | None, kind: str) -> dict | None:
    if not a:
        return None
    held = _t(a["ts"]) + HOLD if a["stage"] == "acknowledged" and kind != "danger" else None
    return {"stage": a["stage"], "actor": a.get("actor"), "ts": _iso(a["ts"]), "held_until": _iso(held)}


def build(engine, events, messages, answers, covered, contexts, decl, locale, now, tz=None) -> dict:
    tz = tz or now.tzinfo or dt.timezone.utc
    last_msg = _latest(messages)
    last_act = _latest([m for m in messages if m.get("action_id")])
    last_ans = _latest(answers)
    opened, recent, cleared_today, last = [], [], 0, None
    for e in events:
        eid, cleared = e["id"], _t(e.get("cleared_at"))
        if cleared is not None and now - cleared > RECENT:
            continue
        if cleared is None and engine == "rules":
            continue                     # the engine is not running: an event a shadow spell left open is not open
        issue = decl.get(e["issue"]) or {}
        m, am, a = last_msg.get(eid), last_act.get(eid), last_ans.get(eid)
        said = (am.get("text") or "") if am else ""
        row = {"id": eid, "issue": e["issue"], "kind": e["kind"], "level": e["level"],
               "opened_at": _iso(e["opened_at"]), "last_seen_at": _iso(e["last_seen_at"]), "cleared_at": _iso(cleared),
               "peak": e.get("peak"), "line": (issue.get("line") or {}).get("value"),
               "rooms": sorted(e.get("rooms") or []), "places": sorted(e.get("places") or []),
               "action": ({"id": am["action_id"], "text": said.split(SENT_ACTION, 1)[1] if SENT_ACTION in said else None}
                          if am else None),
               "message": {"text": m.get("text"), "ts": _iso(m["ts"]), "sent": bool(m.get("sent"))} if m else None,
               "alerts": sorted(covered.get(eid) or []),
               "answer": _answer(a, e["kind"])}
        if cleared is None:
            ctx, key = contexts.get(eid) or {}, OUTSIDE.get(issue.get("metric"))
            row["context"] = {"usual": ctx.get("usual"), "outside": ctx.get(f"outside_{key}") if key else None,
                              "outside_metric": key, "outside_from": ctx.get("outside_source")}
            opened.append(row)
            continue
        if a and a["stage"] == "acted" and cleared > _t(a["ts"]):
            row["cleared_after_min"] = round((cleared - _t(a["ts"])).total_seconds() / 60)
        recent.append(row)
        if cleared.astimezone(tz).date() == now.astimezone(tz).date():
            cleared_today += 1
            if last is None or cleared > _t(last["ts"]):
                last = {"issue": e["issue"], "ts": cleared.isoformat()}
    opened.sort(key=rank)
    recent.sort(key=lambda r: _t(r["opened_at"]), reverse=True)
    return {"engine": engine, "buttons": A.BUTTONS.get(locale) or A.BUTTONS["en"],
            "open": opened, "recent": recent, "cleared_today": cleared_today, "last_cleared": last}
