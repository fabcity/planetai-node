"""A community node's feeds: the names, the fixed words, and the subscriber store.

A subscriber is a chat id, the feeds picked and a language, nothing else. The id lives in the `subscribers` table
only: it is not logged, not put in a URL, and `backup.sh` leaves the table's data out.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

import packs
import placewords
import settings

log = logging.getLogger("planetai")
STALE = timedelta(hours=12)   # a held line older than this is dropped, never sent late
_sleep = time.sleep

FEEDS = [
    {"name": "weekly", "en": "Weekly report, Mondays", "id": "Laporan mingguan, tiap Senin", "urgent": set()},
    {"name": "air", "en": "Air", "id": "Udara", "urgent": set()},
    {"name": "heat", "en": "Heat", "id": "Panas", "urgent": set()},
    {"name": "waves", "en": "Waves", "id": "Ombak", "urgent": set()},
    {"name": "fire", "en": "Fire", "id": "Api", "urgent": {"fire/fire_upwind_near"}},
    {"name": "rain", "en": "Rain and floods", "id": "Hujan dan banjir", "urgent": set()},
]
NAMES = [f["name"] for f in FEEDS]
LANGS = ("en", "id")

WORDS = {
    "en": {
        "title": "{place} community node",
        "pick": "Pick what you want to get. /feeds changes it any time.",
        "keeps": "This node keeps your chat number and what you picked, nothing else. /stop deletes it.",
        "other": "I send what you picked here. /feeds changes it, /stop ends it.",
        "stopped": "Done. This node no longer keeps your chat. /start to come back.",
        "nothing_now": "Nothing new today for {feeds}.",
        "no_week": "The first weekly message comes on Monday at 07:00.",
    },
    "id": {
        "title": "Node komunitas {place}",
        "pick": "Pilih yang ingin kamu terima. /feeds untuk mengubahnya kapan saja.",
        "keeps": "Node ini hanya menyimpan nomor chat kamu dan pilihanmu. /stop menghapusnya.",
        "other": "Saya mengirim yang kamu pilih di sini. /feeds untuk mengubah, /stop untuk berhenti.",
        "stopped": "Selesai. Node ini tidak lagi menyimpan chat kamu. /start untuk kembali.",
        "nothing_now": "Belum ada kabar hari ini untuk {feeds}.",
        "no_week": "Pesan mingguan pertama datang Senin pukul 07.00.",
    },
}


def place() -> str:
    return settings.get("PLACE_NAME", "").strip() or os.getenv("NODE_NAME", "").strip()


def _row(cur, chat: str):
    cur.execute("SELECT feeds, lang FROM subscribers WHERE chat_id = %s", (chat,))
    return cur.fetchone()


def card(cur, chat: str) -> dict | None:
    """The subscribe card for this chat, or None when it is not a subscriber."""
    row = _row(cur, chat)
    if not row:
        return None
    lang, picked = row["lang"], row["feeds"]
    w = WORDS[lang]
    btn = [{"text": ("✓ " if f["name"] in picked else "") + f[lang], "callback_data": "fd:" + f["name"]} for f in FEEDS]
    langs = [{"text": ("✓ " if lang == code else "") + label, "callback_data": "fl:" + code}
             for code, label in (("en", "English"), ("id", "Bahasa Indonesia"))]
    return {"text": f"{w['title'].format(place=place())}\n{w['pick']}\n\n{w['keeps']}",
            "keyboard": [btn[:4], btn[4:], langs], "lang": lang}


def start(cur, chat: str) -> dict:
    cur.execute("INSERT INTO subscribers (chat_id) VALUES (%s) ON CONFLICT DO NOTHING", (chat,))
    return card(cur, chat)


def toggle(cur, chat: str, what: str) -> dict:
    """Flip a feed or set the language; anything else leaves the row as it is."""
    row = _row(cur, chat)
    if not row:
        return start(cur, chat)
    feeds, lang = list(row["feeds"]), row["lang"]
    if what.startswith("lang:") and what[5:] in LANGS:
        lang = what[5:]
    elif what in NAMES:
        feeds = [n for n in NAMES if (n in feeds) != (n == what)]
    else:
        return card(cur, chat)
    cur.execute("UPDATE subscribers SET feeds = %s, lang = %s WHERE chat_id = %s", (feeds, lang, chat))
    return card(cur, chat)


def stop(cur, chat: str) -> bool:
    cur.execute("DELETE FROM subscribers WHERE chat_id = %s", (chat,))
    return cur.rowcount > 0


def counts(cur) -> dict:
    cur.execute("SELECT feeds FROM subscribers")
    rows = cur.fetchall()
    return {"total": len(rows), "feeds": {n: sum(n in r["feeds"] for r in rows) for n in NAMES}}


def allowed(cur, sensor_id: str, metric: str | None) -> bool:
    """May a reading of this sensor reach a subscriber: the node's own (`node` or none), or a sensor that is outdoors
    and, for `metric`, not marked private. Same predicate as packs.public_sql. An unknown sensor is not allowed."""
    if sensor_id in ("", "node", None):
        return True
    cur.execute(f"SELECT s.indoor, {packs.public_sql('m')} AS pub FROM sensors s "
                "CROSS JOIN LATERAL (SELECT s.sensor_id AS sensor_id, %s::text AS metric) m WHERE s.sensor_id = %s",
                (metric, sensor_id))
    row = cur.fetchone()
    return bool(row) and not row["indoor"] and bool(row["pub"])


def _fill(tmpl: str, row: dict) -> str:
    return tmpl.format(**{k: ("—" if v is None else v) for k, v in row.items()})


def enqueue(cur, rule: dict, row: dict, sensor_id: str, now: datetime) -> bool:
    """Queue the rule's feed line (its `feed:` block) for the next send pass. True when a row was queued. One line a
    feed per local day, except for the feed's urgent rules; indoor and private readings never get here."""
    block = rule.get("feed")
    feed = next((f for f in FEEDS if block and f["name"] == block.get("name")), None)
    if placewords.is_house() or not feed:
        return False
    metric = block.get("metric") or (rule.get("watch") or {}).get("metric")
    if not allowed(cur, sensor_id, metric):
        return False
    urgent = rule["id"] in feed["urgent"]
    if not urgent:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cur.execute("SELECT 1 FROM feed_queue WHERE feed = %s AND ts >= %s LIMIT 1", (feed["name"], midnight))
        if cur.fetchone():
            return False
    try:
        en = _fill(block["en"], row)
        texts = {"en": en, "id": _fill(block["id"], row) if block.get("id") else en}
    except (KeyError, IndexError, ValueError, TypeError):
        return False                      # a line with a hole in it is never sent
    cur.execute("INSERT INTO feed_queue (feed, rule_id, texts, urgent) VALUES (%s, %s, %s, %s)",
                (feed["name"], rule["id"], Jsonb(texts), urgent))
    return True


def _local_midnight(now: datetime | None = None) -> datetime:
    try:
        now = now or datetime.now(ZoneInfo(os.getenv("NODE_TZ", "").strip() or "UTC"))
    except Exception:  # noqa: BLE001
        now = now or datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _text(texts: dict, lang: str) -> str:
    return texts.get(lang) or texts["en"]


def _default_post(url: str, body: dict):
    import channels  # noqa: PLC0415 — channels pulls in the sources; the pass needs it only to send
    return channels._tg_post(url, body, waits=())


def send_pass(cur, now: datetime, quiet: bool, post=None) -> dict:
    """Turn the open queue lines into one message per subscriber. Lines older than 12 h are dropped; in quiet hours
    only urgent lines go and the rest stay open. 403 deletes the subscriber, 429 waits its retry_after and tries that
    chat once more. No chat id, token or URL is logged."""
    n = {"sent": 0, "held": 0, "dropped": 0, "gone": 0}
    cur.execute("SELECT id, ts, feed, texts, urgent FROM feed_queue WHERE done = false ORDER BY ts, id")
    open_ = cur.fetchall()
    fresh = [q for q in open_ if now - q["ts"] <= STALE]
    n["dropped"] = len(open_) - len(fresh)
    go = [q for q in fresh if q["urgent"] or not quiet]
    n["held"] = len(fresh) - len(go)
    tok = ""
    if post is None:
        import channels  # noqa: PLC0415
        tok = channels.TG()[0]
        if not tok and go:
            go = []                       # no bot token: nothing can be sent, so nothing is marked done
            n["held"] = len(fresh)
        post = _default_post
    if go:
        cur.execute("SELECT chat_id, feeds, lang, since FROM subscribers")
        for s in cur.fetchall():
            mine = [q for q in go if q["feed"] in s["feeds"] and q["ts"] > s["since"]]
            if not mine:
                continue
            body = {"chat_id": s["chat_id"], "text": "\n\n".join(_text(q["texts"], s["lang"]) for q in mine)}
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            for attempt in (0, 1):
                try:
                    r = post(url, body)
                    if r.status_code == 429 and attempt == 0:
                        try:
                            wait = float(r.json()["parameters"]["retry_after"])
                        except Exception:  # noqa: BLE001
                            wait = 1.0
                        _sleep(min(wait, 60.0))
                        continue
                    if r.status_code == 403:
                        stop(cur, s["chat_id"])
                        n["gone"] += 1
                    elif r.status_code == 200:
                        cur.execute("UPDATE subscribers SET last_sent = %s WHERE chat_id = %s", (now, s["chat_id"]))
                        n["sent"] += 1
                except Exception as e:  # noqa: BLE001 — httpx puts the URL, and so the token, in its messages
                    log.warning("feeds: a send failed: %s", type(e).__name__)
                break
            _sleep(0.04)
    done = [q["id"] for q in open_ if q not in fresh or q in go]
    if done:
        cur.execute("UPDATE feed_queue SET done = true WHERE id = ANY(%s)", (done,))
    log.info("feeds: sent %d, held %d, dropped %d, gone %d", n["sent"], n["held"], n["dropped"], n["gone"])
    return n


def now_text(cur, chat: str, now: datetime | None = None) -> str:
    """What this subscriber's feeds said today (the newest line of each, never the weekly), or the fixed line."""
    row = _row(cur, chat)
    lang = row["lang"] if row else "en"
    midnight = _local_midnight(now)
    out, quiet = [], []
    for f in FEEDS:
        if f["name"] == "weekly" or (row and f["name"] not in row["feeds"]):
            continue
        cur.execute("SELECT texts FROM feed_queue WHERE feed = %s AND ts >= %s ORDER BY ts DESC LIMIT 1",
                    (f["name"], midnight))
        got = cur.fetchone()
        (out if got else quiet).append(_text(got["texts"], lang) if got else f[lang])
    if quiet:
        out.append(WORDS[lang]["nothing_now"].format(feeds=", ".join(quiet)))
    return "\n\n".join(out)


def week_text(cur, chat: str) -> str:
    """The newest weekly message in this subscriber's language, or the fixed line before the first Monday."""
    row = _row(cur, chat)
    lang = row["lang"] if row else "en"
    cur.execute("SELECT texts FROM feed_queue WHERE feed = %s ORDER BY ts DESC LIMIT 1", ("weekly",))
    got = cur.fetchone()
    return _text(got["texts"], lang) if got else WORDS[lang]["no_week"]
