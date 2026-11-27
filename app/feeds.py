"""A community node's feeds: the names, the fixed words, and the subscriber store.

A subscriber is a chat id, the feeds picked and a language, nothing else. The id lives in the `subscribers` table
only: it is not logged, not put in a URL, and `backup.sh` leaves the table's data out.
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
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
    outage = False
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
                    else:
                        log.warning("feeds: telegram answered %d", r.status_code)
                        outage = outage or r.status_code >= 500 or r.status_code == 429
                except Exception as e:  # noqa: BLE001 — httpx puts the URL, and so the token, in its messages
                    log.warning("feeds: a send failed: %s", type(e).__name__)
                    outage = True
                break
            _sleep(0.04)
    # Nothing got through and something failed like an outage: the lines stay open for the next pass (the 12 h drop bounds them).
    keep = outage and not n["sent"]
    done = [q["id"] for q in open_ if q not in fresh or (q in go and not keep)]
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


DAYS = {"en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "id": ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]}
MONTHS = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
          "id": ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]}
WEEK = {
    "en": {"clean": "Air was clean all week; the worst moment was {v} near {name}, {day}.",
           "mostly": "Air was mostly clean; {day} was the worst, {v} near {name}.",
           "bad": "Air was unhealthy on {k} days; {day} was the worst, {v} near {name}.",
           "heat": "The hottest afternoon was {day}, {v} °C in the shade.",
           "sea": "Swell peaked {day}, {v} m.",
           "rain": "{v} mm of rain fell, most on {day}.",
           "rhythm": "Evenings around {v}:00 are when the air is worst here.",
           "link": "The full report: {v}/ui#data/report"},
    "id": {"clean": "Udara bersih sepanjang minggu; paling buruk {v} dekat {name}, hari {day}.",
           "mostly": "Udara sebagian besar bersih; paling buruk hari {day}, {v} dekat {name}.",
           "bad": "Udara tidak sehat {k} hari; {day} paling buruk, {v} dekat {name}.",
           "heat": "Siang terpanas hari {day}, {v} °C di tempat teduh.",
           "sea": "Ombak tertinggi hari {day}, {v} m.",
           "rain": "Hujan {v} mm, paling banyak hari {day}.",
           "rhythm": "Sekitar pukul {v}.00 udara di sini paling buruk.",
           "link": "Laporan lengkap: {v}/ui#data/report"},
}
# Outdoor and public rows only: `sensors.indoor` and the channel-role predicate every road out of the house uses.
_OUT = "NOT s.indoor AND s.kind IN ('sensor','child') AND r.mean IS NOT NULL AND r.bucket >= %s AND r.bucket < %s"


def _span(a: date, lang: str) -> str:
    b = a + timedelta(days=6)
    m = MONTHS[lang]
    return f"{a.day}–{b.day} {m[b.month - 1]}" if a.month == b.month else f"{a.day} {m[a.month - 1]}–{b.day} {m[b.month - 1]}"


def _fmt(x: float, dp: int, lang: str = "en") -> str:
    out = f"{x:.{dp}f}"
    return out.replace(".", ",") if lang == "id" else out


def _name(n: str) -> str:
    """A station name without its trailing bracket: "TPA Kutuh (Smart Citizen)" is "TPA Kutuh"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", n or "")


def _rain(cur, w0: date, w1: date):
    """(mm, busiest day) for the week, or None. The first series that exists wins: an outdoor sensor's `rain` or
    `precipitation`; else the model point's `precipitation` (Open-Meteo, the only rain this node has when no sensor
    reports it); else the stored past hours of `fc_rain`, the mean of the forecast points. Hourly means, summed."""
    for metrics, extra in ((["rain", "precipitation"], "NOT s.indoor AND s.kind = 'sensor'"),
                           (["precipitation"], "true"), (["fc_rain"], "true")):
        cur.execute(
            "WITH h AS (SELECT r.bucket, avg(r.mean) AS mm FROM readings_1h r JOIN sensors s USING (sensor_id) "
            f"WHERE r.metric = ANY(%s) AND {extra} AND r.mean IS NOT NULL AND r.bucket >= %s AND r.bucket < %s "
            f"AND r.bucket < now() AND {packs.public_sql('r')} GROUP BY r.bucket), "
            "d AS (SELECT bucket::date AS day, sum(mm) AS mm FROM h GROUP BY 1) "
            "SELECT (SELECT sum(mm) FROM d) AS mm, (SELECT day FROM d ORDER BY mm DESC LIMIT 1) AS day",
            (metrics, w0, w1))
        row = cur.fetchone()
        if row and row["mm"] is not None:
            return float(row["mm"]), row["day"]
    return None


def _week(cur, week_start: date, place_name: str, public_url: str):
    """(texts, n): the weekly message for the Monday-to-Sunday before `week_start`, and how many lines besides the head
    and the link it has. Each line is left out when its rows are missing."""
    w0 = week_start - timedelta(days=7)
    w = (w0, week_start)
    lines: list[dict] = []          # {"key", "v", "day", "name", "k"} per line, in order

    cur.execute(  # the worst day by its median, and that day's highest hour
        f"WITH h AS (SELECT r.bucket, r.mean, s.name FROM readings_1h r JOIN sensors s USING (sensor_id) "
        f"WHERE r.metric = 'pm25' AND {_OUT} AND {packs.public_sql('r')}), "
        "d AS (SELECT bucket::date AS day, percentile_cont(0.5) WITHIN GROUP (ORDER BY mean) AS med FROM h GROUP BY 1), "
        "w AS (SELECT day, med FROM d ORDER BY med DESC LIMIT 1) "
        "SELECT w.day, w.med, h.name, h.mean, (SELECT count(*) FROM d WHERE med >= 35.5) AS k "
        "FROM w JOIN h ON h.bucket::date = w.day ORDER BY h.mean DESC LIMIT 1", w)
    a = cur.fetchone()
    if a:
        # the verdict is the days' medians; a worst hour over the line with no unhealthy day is "mostly clean"
        key = "bad" if a["k"] else "mostly" if a["mean"] >= 35.5 else "clean"
        lines.append({"key": key, "num": (a["mean"], 0), "day": a["day"], "name": _name(a["name"]), "k": a["k"]})

    cur.execute(  # per local hour 12:00-17:59 the median of the sensors' hourly means; the highest of those
        f"SELECT r.bucket::date AS day, percentile_cont(0.5) WITHIN GROUP (ORDER BY r.mean) AS mean "
        f"FROM readings_1h r JOIN sensors s USING (sensor_id) "
        f"WHERE r.metric = 'temp' AND {_OUT} AND extract(hour FROM r.bucket) BETWEEN 12 AND 17 "
        f"AND {packs.public_sql('r')} GROUP BY r.bucket ORDER BY 2 DESC LIMIT 1", w)
    t = cur.fetchone()
    if t:
        lines.append({"key": "heat", "num": (t["mean"], 0), "day": t["day"]})

    cur.execute(  # the sea's model point; public
        f"SELECT r.bucket::date AS day, r.mean FROM readings_1h r JOIN sensors s USING (sensor_id) "
        f"WHERE r.metric = 'swell_height_m' AND r.mean IS NOT NULL AND r.bucket >= %s AND r.bucket < %s "
        f"AND {packs.public_sql('r')} ORDER BY r.mean DESC LIMIT 1", w)
    sea = cur.fetchone()
    if sea:
        lines.append({"key": "sea", "num": (sea["mean"], 1), "day": sea["day"]})

    rain = _rain(cur, *w)
    if rain and rain[0] >= 0.1:
        lines.append({"key": "rain", "num": (rain[0], 1), "day": rain[1]})

    cur.execute(  # the rows the Wall reads: the hour the day's fine dust is usually highest
        "SELECT (numbers->>'high_hour')::int AS hour FROM learnings WHERE kind = 'usual' AND scope = 'place' "
        "AND status = 'holding' AND metric = 'pm25' AND numbers ? 'high_hour' ORDER BY n DESC, key LIMIT 1")
    rh = cur.fetchone()
    if rh and rh["hour"] is not None and rh["hour"] >= 17:   # the line says "evenings"; a morning peak is left out
        lines.append({"key": "rhythm", "v": f"{rh['hour']:02d}"})
    n = len(lines)
    if n and public_url:
        lines.append({"key": "link", "v": public_url})

    texts = {}
    for lang in LANGS:
        out = [f"📊 {place_name}, {_span(w0, lang)}."]
        for ln in lines:
            day = DAYS[lang][ln["day"].weekday()] if ln.get("day") else ""
            v = _fmt(*ln["num"], lang) if "num" in ln else ln["v"]
            out.append(WEEK[lang][ln["key"]].format(v=v, day=day, name=ln.get("name"), k=ln.get("k")))
        texts[lang] = "\n".join(out)
    return texts, n


def weekly_texts(cur, week_start: date, place: str, public_url: str) -> dict:  # noqa: A002
    """{"en","id"}: the head line, then the lines this week's rows support, then the link when `public_url` is set."""
    return _week(cur, week_start, place, public_url)[0]


def weekly_job(cur, now: datetime) -> bool:
    """On Monday from 07:00 local, queue the weekly message once: True when it did. Already queued this week is read
    from feed_queue (a 'weekly' row at or after this Monday 07:00). A week with no data lines queues nothing."""
    start = now.replace(hour=7, minute=0, second=0, microsecond=0)
    if now.weekday() != 0 or now < start:
        return False
    cur.execute("SELECT 1 FROM feed_queue WHERE feed = %s AND ts >= %s LIMIT 1", ("weekly", start))
    if cur.fetchone():
        return False
    texts, n = _week(cur, now.date(), place(), settings.get("PUBLIC_URL", ""))
    if not n:
        return False
    cur.execute("INSERT INTO feed_queue (feed, rule_id, texts, urgent) VALUES (%s, %s, %s, %s)",
                ("weekly", None, Jsonb(texts), False))
    return True
