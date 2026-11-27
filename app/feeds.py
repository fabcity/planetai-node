"""A community node's feeds: the names, the fixed words, and the subscriber store.

A subscriber is a chat id, the feeds picked and a language, nothing else. The id lives in the `subscribers` table
only: it is not logged, not put in a URL, and `backup.sh` leaves the table's data out.
"""
from __future__ import annotations

import os
from datetime import datetime

from psycopg.types.json import Jsonb

import packs
import placewords
import settings

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
