"""The subscriber store and its routes.

    PYTHONPATH=app python3 tests/test_feeds.py
"""
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
os.environ.update(NODE_KIND="community", NODE_NAME="Ungasan", ADMIN_TOKEN="admin-tok",
                  DATABASE_URL="postgresql://unused/never-connected")

import feeds  # noqa: E402
import settings  # noqa: E402

settings._cache = {"at": time.time() + 1e9, "rows": {"SHARE_LEVEL": "open"}}
ROWS = {}
QUEUE = []
CLOCK = [datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)]
SENSORS = {"ag-in": (True, set()), "sc-private": (False, {"pm25"}), "firms-fires": (False, set())}


class _Cur:
    """The store's SQL over a dict: one statement per call, matched by its first words."""
    rowcount = 0
    _out = None

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def cursor(self): return self

    def execute(self, sql, p=()):
        sql = " ".join(sql.split())
        self._out, self.rowcount = [], 0
        if sql.startswith("INSERT INTO subscribers"):
            if p[0] not in ROWS:
                ROWS[p[0]] = {"feeds": ["weekly"], "lang": "en"}
        elif sql.startswith("SELECT feeds, lang"):
            self._out = [dict(ROWS[p[0]])] if p[0] in ROWS else []
        elif sql.startswith("UPDATE subscribers SET feeds"):
            ROWS[p[2]].update(feeds=list(p[0]), lang=p[1])
        elif sql.startswith("DELETE FROM subscribers"):
            self.rowcount = 1 if ROWS.pop(p[0], None) else 0
        elif sql.startswith("SELECT s.indoor"):
            s = SENSORS.get(p[1])
            self._out = [{"indoor": s[0], "pub": p[0] not in s[1]}] if s else []
        elif sql.startswith("SELECT 1 FROM feed_queue"):
            self._out = [{"one": 1}] if any(q["feed"] == p[0] and q["ts"] >= p[1] for q in QUEUE) else []
        elif sql.startswith("INSERT INTO feed_queue"):
            QUEUE.append({"id": len(QUEUE) + 1, "feed": p[0], "rule_id": p[1], "texts": p[2].obj, "urgent": p[3],
                          "ts": CLOCK[0], "done": False})
        elif sql.startswith("SELECT id, ts, feed"):
            self._out = [dict(q) for q in sorted(QUEUE, key=lambda q: q["ts"]) if not q["done"]]
        elif sql.startswith("SELECT chat_id, feeds"):
            self._out = [dict(chat_id=k, **v) for k, v in ROWS.items()]
        elif sql.startswith("UPDATE feed_queue SET done"):
            for q in QUEUE:
                if q["id"] in p[0]:
                    q["done"] = True
        elif sql.startswith("UPDATE subscribers SET last_sent"):
            ROWS[p[1]]["last_sent"] = p[0]
        elif sql.startswith("SELECT texts FROM feed_queue"):
            hit = [q for q in sorted(QUEUE, key=lambda q: q["ts"], reverse=True)
                   if q["feed"] == p[0] and (len(p) < 2 or q["ts"] >= p[1])]
            self._out = [{"texts": hit[0]["texts"]}] if hit else []
        elif sql.startswith("SELECT feeds FROM subscribers"):
            self._out = [{"feeds": list(r["feeds"])} for r in ROWS.values()]
        else:
            raise AssertionError(sql)

    def fetchone(self): return self._out[0] if self._out else None
    def fetchall(self): return self._out


cur = _Cur()
c = feeds.start(cur, "777")
assert c["text"].startswith("Ungasan community node") and "/stop deletes it" in c["text"], c["text"]
assert ["✓ Weekly report, Mondays", "Air", "Heat", "Waves"] == [b["text"] for b in c["keyboard"][0]]
assert [b["text"] for b in c["keyboard"][1]] == ["Fire", "Rain and floods"]
assert [b["callback_data"] for b in c["keyboard"][-1]] == ["fl:en", "fl:id"]
assert c["keyboard"][0][1]["callback_data"] == "fd:air"
assert ROWS["777"]["feeds"] == ["weekly"] and ROWS["777"]["lang"] == "en"
feeds.toggle(cur, "777", "waves"); feeds.toggle(cur, "777", "weekly")
assert ROWS["777"]["feeds"] == ["waves"]
assert feeds.toggle(cur, "777", "lang:id")["text"].startswith("Node komunitas Ungasan")
assert feeds.stop(cur, "777") and "777" not in ROWS and not feeds.stop(cur, "777")
assert feeds.card(cur, "777") is None
assert feeds.start(cur, "777") and ROWS["777"]["feeds"] == ["weekly"]   # back after /stop: a fresh row
before = dict(ROWS["777"])
feeds.toggle(cur, "777", "nonsense"); feeds.toggle(cur, "777", "lang:xx")   # unknown: unchanged, no error
assert ROWS["777"] == before
assert feeds.counts(cur) == {"total": 1, "feeds": {"weekly": 1, "air": 0, "heat": 0, "waves": 0, "fire": 0, "rain": 0}}
assert feeds.NAMES == ["weekly", "air", "heat", "waves", "fire", "rain"]
for k in feeds.WORDS["en"]:
    assert k in feeds.WORDS["id"]
print("ok  feeds store")

# the send pass, with 7-digit chat ids so a digit in a count cannot match one in the log
saved_rows, saved_queue = dict(ROWS), list(QUEUE)
T0 = datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)
SENT, STATUS, LOGS, SLEPT = [], {}, [], []


class _Resp:
    def __init__(self, code): self.status_code = code
    def json(self): return {"parameters": {"retry_after": 7}}


def fake(url, body):
    chat = body["chat_id"]
    SENT.append((chat, body["text"]))
    return _Resp(STATUS[chat].pop(0) if STATUS.get(chat) else 200)


class _Cap(logging.Handler):
    def emit(self, rec): LOGS.append(rec.getMessage())


logging.disable(logging.NOTSET)
logging.getLogger("planetai").addHandler(_Cap())
logging.getLogger("planetai").setLevel(logging.INFO)
feeds._sleep = SLEPT.append


IDS = iter(range(1000, 9999))


def line(feed, en, urgent=False, ts=T0):
    return {"id": next(IDS), "feed": feed, "rule_id": None, "texts": {"en": en, "id": en + " (id)"},
            "urgent": urgent, "ts": ts, "done": False}


def sub(picked, lang="en"):
    return {"feeds": list(picked), "lang": lang, "since": T0 - timedelta(days=1)}


QUEUE.clear(); ROWS.clear()
QUEUE[:] = [line("air", "Air line"), line("waves", "Waves line"), line("fire", "Fire upwind", urgent=True)]
ROWS.update({"5550001": sub(["air", "waves"]), "5550002": sub(["fire"], lang="id"), "5550003": sub(["weekly"])})
r = feeds.send_pass(cur, T0, quiet=False, post=fake)
assert SENT == [("5550001", "Air line\n\nWaves line"), ("5550002", "Fire upwind (id)")] and r["sent"] == 2, (SENT, r, LOGS)
assert all(q["done"] for q in QUEUE) and ROWS["5550001"]["last_sent"] == T0 and "last_sent" not in ROWS["5550003"]
SENT.clear(); assert feeds.send_pass(cur, T0, quiet=False, post=fake)["sent"] == 0 and SENT == []   # nothing open
# quiet hours hold all but urgent, which goes; the rest goes once after
NIGHT, MORNING = T0.replace(hour=23), T0 + timedelta(hours=7)
QUEUE[:] = [line("air", "Rain", ts=NIGHT), line("fire", "Fire", urgent=True, ts=NIGHT)]
ROWS.update({"5550001": sub(["air", "fire"])}); SENT.clear()
r = feeds.send_pass(cur, NIGHT, quiet=True, post=fake)
assert r["held"] == 1
assert ("5550001", "Fire") in SENT and not QUEUE[0]["done"] and QUEUE[1]["done"]
SENT.clear()
feeds.send_pass(cur, MORNING, quiet=False, post=fake); feeds.send_pass(cur, MORNING, quiet=False, post=fake)
assert [t for _, t in SENT] == ["Rain"], SENT
# a line held past 12 h is dropped, not sent late
QUEUE[:] = [line("air", "Old", ts=T0 - timedelta(hours=13))]; SENT.clear()
r = feeds.send_pass(cur, T0, quiet=False, post=fake)
assert r["dropped"] == 1 and SENT == [] and QUEUE[0]["done"]
# a line queued before someone subscribed does not reach them
QUEUE[:] = [line("air", "Before", ts=T0 - timedelta(days=2))]; SENT.clear()
assert feeds.send_pass(cur, T0 - timedelta(hours=1), quiet=False, post=fake)["sent"] == 0 and SENT == []
# 403 deletes the row, and a new start makes a fresh one with the weekly ticked
QUEUE[:] = [line("air", "Air")]; STATUS["5550001"] = [403]; SENT.clear()
r = feeds.send_pass(cur, T0, quiet=False, post=fake)
assert r["gone"] == 1 and "5550001" not in ROWS
feeds.start(cur, "5550001"); assert ROWS["5550001"]["feeds"] == ["weekly"]
# 429 waits its retry_after and tries that chat once more
ROWS["5550001"] = sub(["air"]); QUEUE[:] = [line("air", "Air")]; STATUS["5550001"] = [429, 200]; SENT.clear(); SLEPT.clear()
r = feeds.send_pass(cur, T0, quiet=False, post=fake)
assert SENT == [("5550001", "Air")] * 2 and r["sent"] == 1 and 7.0 in SLEPT, (SENT, SLEPT)
# a failure other than 403/429 is logged by type and the pass moves on
def boom(url, body): raise ConnectionError("https://api.telegram.org/botSECRET/sendMessage 5550001")
QUEUE[:] = [line("air", "Air")]; LOGS.clear()
r = feeds.send_pass(cur, T0, quiet=False, post=boom)
assert r["sent"] == 0 and any("ConnectionError" in m for m in LOGS)
assert not any(x in m for m in LOGS for x in ("5550001", "5550002", "5550003", "SECRET")), LOGS
assert any(m == "feeds: sent 0, held 0, dropped 0, gone 0" for m in LOGS)
# an outage (every send raises, or answers 502) keeps the lines open; the next pass sends each once
def down(url, body): raise ConnectionError("down")
def bad(url, body): return _Resp(502)
for failing in (down, bad):
    QUEUE[:] = [line("air", "Air")]; ROWS["5550001"] = sub(["air"]); ROWS["5550002"] = sub(["air"]); SENT.clear()
    assert feeds.send_pass(cur, T0, quiet=False, post=failing)["sent"] == 0 and not QUEUE[0]["done"]
    assert feeds.send_pass(cur, T0, quiet=False, post=fake)["sent"] == 2 and QUEUE[0]["done"]
    assert sorted(c for c, _ in SENT) == ["5550001", "5550002"]
    SENT.clear(); assert feeds.send_pass(cur, T0, quiet=False, post=fake)["sent"] == 0
# one chat 502 and another 200: the lines are done, the 200 subscriber has theirs
def mixed(url, body): return _Resp(502 if body["chat_id"] == "5550001" else 200)
QUEUE[:] = [line("air", "Air")]; LOGS.clear()
r = feeds.send_pass(cur, T0, quiet=False, post=mixed)
assert r["sent"] == 1 and QUEUE[0]["done"] and "feeds: telegram answered 502" in LOGS
# a 400 is logged by its number, never the chat id; a 429 that persists too
def refused(url, body): return _Resp(400)
def slow(url, body): return _Resp(429)
QUEUE[:] = [line("air", "Air")]; LOGS.clear(); SLEPT.clear()
feeds.send_pass(cur, T0, quiet=False, post=refused)
assert "feeds: telegram answered 400" in LOGS and QUEUE[0]["done"]
QUEUE[:] = [line("air", "Air")]; LOGS.clear()
feeds.send_pass(cur, T0, quiet=False, post=slow)
assert "feeds: telegram answered 429" in LOGS and not QUEUE[0]["done"]
assert not any(c in m for m in LOGS for c in ("5550001", "5550002")), LOGS
# /now and /week
QUEUE[:] = [line("air", "Air today", ts=T0), line("weekly", "Week en", ts=T0 - timedelta(days=3))]
ROWS["5550001"] = sub(["weekly", "air", "heat"], lang="id")
assert feeds.now_text(cur, "5550001", T0) == "Air today (id)\n\n" + feeds.WORDS["id"]["nothing_now"].format(feeds="Panas")
assert feeds.week_text(cur, "5550001") == "Week en (id)"
QUEUE.clear(); ROWS["5550001"]["lang"] = "en"
assert feeds.week_text(cur, "5550001") == feeds.WORDS["en"]["no_week"]
ROWS.clear(); ROWS.update(saved_rows); QUEUE[:] = saved_queue
logging.disable(logging.CRITICAL)
print("ok  send pass")

backup = (ROOT / "backup.sh").read_text()
assert "--exclude-table-data=subscribers" in backup and "--exclude-table-data=feed_queue" in backup
sql = (ROOT / "init.sql").read_text()
assert "CREATE TABLE IF NOT EXISTS subscribers" in sql and "('0.68')" in sql
assert "PLACE_NAME" in settings.RUNTIME and settings.RUNTIME["PLACE_NAME"][0] == "basics"
print("ok  schema, backup, setting")

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("feeds: route checks skipped (pip install -r app/requirements.txt)")
    raise SystemExit(0)

import yaml  # noqa: E402

RULES = {}
for f in sorted((ROOT / "packs").glob("*/rules.yml")):
    for r in yaml.safe_load(f.read_text()) or []:
        RULES[f"{f.parent.name}/{r['id']}"] = r
NOW = CLOCK[0]
os.environ["NODE_KIND"] = "community"
r = {"id": "fire/fire_upwind_near", "feed": RULES["fire/fire_upwind_near"]["feed"]}
assert feeds.enqueue(cur, r, {"km": 4, "dir": {"en": "north", "id": "utara"}}, "node", NOW)
assert QUEUE[-1]["texts"]["en"].startswith("\U0001F525 Fire 4 km north") and QUEUE[-1]["urgent"]
assert "di sebelah utara" in QUEUE[-1]["texts"]["id"]
assert feeds.enqueue(cur, r, {"km": 3, "dir": {"en": "north", "id": "utara"}}, "node", NOW)   # urgent: no daily cap
swell = {"id": "coast/heavy_swell", "feed": RULES["coast/heavy_swell"]["feed"]}
assert feeds.enqueue(cur, swell, {}, "node", NOW) and not feeds.enqueue(cur, swell, {}, "node", NOW)   # one a day
CLOCK[0] = NOW + timedelta(days=1)
assert feeds.enqueue(cur, swell, {}, "node", NOW + timedelta(days=1))                       # past local midnight: again
smoke = {"id": "fire/smoke_arriving", "feed": RULES["fire/smoke_arriving"]["feed"]}
assert smoke["feed"]["metric"] == "pm25"
n = len(QUEUE)
assert not feeds.enqueue(cur, smoke, {"pm25": 80}, "ag-in", NOW), "an indoor sensor never reaches a feed"
assert not feeds.enqueue(cur, smoke, {"pm25": 80}, "sc-private", NOW), "a private metric never does"
assert not feeds.enqueue(cur, smoke, {"pm25": 80}, "nobody-knows", NOW), "an unknown sensor never does"
assert len(QUEUE) == n
assert feeds.enqueue(cur, smoke, {"pm25": 80}, "firms-fires", NOW) and "air outside is 80," in QUEUE[-1]["texts"]["en"]
assert not feeds.enqueue(cur, {"id": "x/y"}, {}, "node", NOW) and not feeds.enqueue(cur, {"id": "x/y", "feed": {"name": "zzz", "en": "a"}}, {}, "node", NOW)
nid = {"id": "x/y", "feed": {"name": "heat", "en": "hot {k}"}}                              # no id template: falls back to en
assert feeds.enqueue(cur, nid, {"k": 1}, "node", NOW) and QUEUE[-1]["texts"] == {"en": "hot 1", "id": "hot 1"}
assert not feeds.enqueue(cur, {"id": "x/z", "feed": {"name": "air", "en": "{missing}"}}, {}, "node", NOW), "a hole in a line"
os.environ["NODE_KIND"] = "home"
n = len(QUEUE)
assert not feeds.enqueue(cur, swell, {}, "node", NOW + timedelta(days=5)), "a private node queues nothing"
assert len(QUEUE) == n
os.environ["NODE_KIND"] = "community"
for rid, rule in RULES.items():
    if "feed" in rule:
        assert rule["feed"]["name"] in feeds.NAMES and {"en", "id"} <= set(rule["feed"]), rid
        assert all(t.count("\n") <= 1 for t in (rule["feed"]["en"], rule["feed"]["id"])), rid
assert [k for k, v in RULES.items() if "feed" in v] == ["air-quality/air_unhealthy_around", "coast/heavy_swell", "fire/fire_near",
                                                       "fire/fire_upwind_near", "fire/smoke_arriving", "forecast/heat_ahead",
                                                       "forecast/rain_ahead"]
print("ok  feed lines")

logging.disable(logging.WARNING)
os.environ.setdefault("PACKS_DIR", str(ROOT / "packs"))
import main  # noqa: E402
import subscribers  # noqa: E402

subscribers._db = lambda: _Cur()
anon = TestClient(main.app)
H = {"Authorization": "Bearer admin-tok"}
assert anon.post("/subscribers/start", json={"chat": "777"}).status_code == 403
assert anon.get("/subscribers/counts").status_code == 403
assert anon.post("/subscribers/start", json={}, headers=H).status_code == 422, "a chat id is required"
assert anon.post("/subscribers/start", json={"chat": ""}, headers=H).status_code == 422
r = anon.post("/subscribers/start", json={"chat": "888"}, headers=H)
assert r.status_code == 200 and r.json()["keyboard"][0][0]["callback_data"] == "fd:weekly", r.text
assert anon.get("/subscribers/counts", headers=H).json()["total"] == 2
assert anon.post("/subscribers/toggle", json={"chat": "888", "what": "air"}, headers=H).json()["keyboard"][0][1]["text"] == "✓ Air"
assert anon.post("/subscribers/card", json={"chat": "888"}, headers=H).status_code == 200
assert anon.post("/subscribers/card", json={"chat": "000"}, headers=H).status_code == 404
r = anon.post("/subscribers/now", json={"chat": "888"}, headers=H); assert r.status_code == 200, (r.status_code, r.text); assert r.json()["text"].startswith("\U0001F525 Smoke")
assert anon.post("/subscribers/week", json={"chat": "888"}, headers=H).json() == {"text": feeds.WORDS["en"]["no_week"]}
assert anon.post("/subscribers/stop", json={"chat": "888"}, headers=H).json() == {"text": feeds.WORDS["en"]["stopped"]}
assert "888" not in ROWS
os.environ["NODE_KIND"] = "home"
r = anon.post("/subscribers/start", json={"chat": "777"}, headers=H)
assert r.status_code == 409 and r.json() == {"error": main.placewords.NO_ACT}, r.text
assert anon.get("/subscribers/counts", headers=H).status_code == 409
print("ok  feeds routes")

# ---- the weekly message. The SQL is stubbed per line (the fixture week is the one in the spec); a check that the
# air and heat statements read outdoor, public rows only stands in for the indoor sensor at 300 µg/m³.
from datetime import date  # noqa: E402

STUB = {}
SEEN = []


class _Wk(_Cur):
    def execute(self, sql, p=()):
        s = " ".join(sql.split())
        key = ("air" if "metric = 'pm25' AND" in s and "WITH h" in s else "heat" if "metric = 'temp'" in s else
               "sea" if "swell_height_m" in s else "rain" if "metric = ANY" in s else
               "rhythm" if "FROM learnings" in s else None)
        if key is None:
            return super().execute(sql, p)
        SEEN.append((key, s, p))
        got = STUB.get(key)
        got = got.get(tuple(p[0])[0], None) if key == "rain" and isinstance(got, dict) else got
        self._out = [got] if got else []


wk = _Wk()
FIX = {"air": {"day": date(2026, 11, 19), "med": 20.0, "name": "Jimbaran", "mean": 30.6, "k": 0},
       "heat": {"day": date(2026, 11, 21), "mean": 31.7},
       "sea": {"day": date(2026, 11, 21), "mean": 2.14},
       "rhythm": {"hour": 18}}
STUB.update(FIX)
URL = "https://x.ts.net:8443"
en = feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", URL)["en"]
assert en == ("📊 Ungasan, 17–23 Nov.\n"
              "Air was clean all week; the worst moment was 31 near Jimbaran, Thursday.\n"
              "The hottest afternoon was Saturday, 32 °C in the shade.\n"
              "Swell peaked Saturday, 2.1 m.\n"
              "Evenings around 18:00 are when the air is worst here.\n"
              "The full report: https://x.ts.net:8443/ui#data/report"), en
for key, s, p in SEEN:           # outdoor and public only, in the week Monday 17 to Sunday 23
    if key in ("air", "heat"):
        assert "NOT s.indoor" in s and "NOT EXISTS" in s and "'private'" in s, s
    assert key == "rhythm" or p[-2:] == (date(2026, 11, 17), date(2026, 11, 24)), (key, p)
idt = feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", URL)["id"]
assert idt.split("\n")[1] == "Udara bersih sepanjang minggu; paling buruk 31 dekat Jimbaran, hari Kamis.", idt
assert idt.split("\n")[2] == "Siang terpanas hari Sabtu, 32 °C di tempat teduh."
assert idt.split("\n")[-1] == "Laporan lengkap: https://x.ts.net:8443/ui#data/report"
assert "📊 Ungasan, 17–23 Nov." == idt.split("\n")[0]
assert "full report" not in feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", "")["en"]
# an unhealthy week names its days; a morning peak leaves the rhythm line out; rain falls back to the next series
# no unhealthy day but one hour at 91: mostly clean, the bracket on the station name dropped
STUB["air"] = {"day": date(2026, 11, 23), "med": 20.0, "name": "TPA Kutuh (Smart Citizen)", "mean": 91.2, "k": 0}
mc = feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", "")
assert mc["en"].split("\n")[1] == "Air was mostly clean; Monday was the worst, 91 near TPA Kutuh.", mc
assert mc["id"].split("\n")[1] == "Udara sebagian besar bersih; paling buruk hari Senin, 91 dekat TPA Kutuh.", mc
assert feeds._name("A (b) c") == "A (b) c" and feeds._name("Seminyak Beach - Hotel Indigo (IQAir)") == "Seminyak Beach - Hotel Indigo"
# the heat statement takes the median of the sensors per hour; Indonesian writes decimals with a comma
assert "percentile_cont(0.5)" in [x[1] for x in SEEN if x[0] == "heat"][0]
assert feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", "")["id"].split("\n")[3] == "Ombak tertinggi hari Sabtu, 2,1 m."
STUB["air"] = {"day": date(2026, 11, 18), "med": 60.0, "name": "Sempidi", "mean": 88.4, "k": 2}
STUB["rhythm"] = {"hour": 16}   # 16:00 is not evening: left out
STUB["rain"] = {"rain": None, "precipitation": {"mm": 12.34, "day": date(2026, 11, 20)}}
en = feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", "")["en"].split("\n")
assert en[1] == "Air was unhealthy on 2 days; Wednesday was the worst, 88 near Sempidi.", en
assert "12.3 mm of rain fell, most on Friday." in en
assert "Hujan 12,3 mm, paling banyak hari Jumat." in feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", "")["id"].split("\n") and not any("Evenings" in x for x in en), en
STUB["rain"] = {"rain": {"mm": 0.0, "day": date(2026, 11, 20)}}
assert not any("rain fell" in x for x in feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", "")["en"].split("\n"))
# a week with no rows is the head alone, and the job queues nothing for it
STUB.clear()
assert feeds.weekly_texts(wk, date(2026, 11, 24), "Ungasan", URL)["en"] == "📊 Ungasan, 17–23 Nov."
assert feeds.weekly_texts(wk, date(2026, 11, 30), "Ungasan", "")["id"] == "📊 Ungasan, 23–29 Nov."
assert feeds.weekly_texts(wk, date(2026, 12, 7), "Ungasan", "")["en"] == "📊 Ungasan, 30 Nov–6 Dec."

# weekly_job: Mondays from 07:00 local, once a week
QUEUE.clear()
settings._cache["rows"]["PUBLIC_URL"] = URL
from zoneinfo import ZoneInfo  # noqa: E402
TZ = ZoneInfo("Asia/Makassar")
mon = lambda h, m, d=23: datetime(2026, 11, d, h, m, tzinfo=TZ)  # noqa: E731
assert feeds.weekly_job(wk, mon(7, 0)) is False and not QUEUE      # no data: nothing queued, head-only never goes
STUB.update(FIX)
assert feeds.weekly_job(wk, mon(6, 59)) is False and not QUEUE
CLOCK[0] = mon(7, 0)
assert feeds.weekly_job(wk, mon(7, 0)) is True and len(QUEUE) == 1
q = QUEUE[0]
assert (q["feed"], q["rule_id"], q["urgent"]) == ("weekly", None, False)
assert q["texts"]["en"].startswith("📊 Ungasan, 16–22 Nov.\n") and q["texts"]["en"].endswith("/ui#data/report")
CLOCK[0] = mon(7, 10)
assert feeds.weekly_job(wk, mon(7, 10)) is False and len(QUEUE) == 1
CLOCK[0] = datetime(2026, 11, 30, 7, 0, tzinfo=TZ)
assert feeds.weekly_job(wk, datetime(2026, 11, 30, 7, 0, tzinfo=TZ)) is True and len(QUEUE) == 2
assert feeds.weekly_job(wk, datetime(2026, 12, 1, 9, 0, tzinfo=TZ)) is False   # Tuesday: the week is not caught up late
# PUBLIC_URL must be https:// and not end with /; the refusal comes before any database is touched
for bad in ("http://x.ts.net", "https://x.ts.net/", "x.ts.net"):
    try:
        settings.set("PUBLIC_URL", bad)
        raise AssertionError(bad)
    except ValueError:
        pass
print("ok  feeds weekly")
