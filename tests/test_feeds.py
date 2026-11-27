"""The subscriber store and its routes.

    PYTHONPATH=app python3 tests/test_feeds.py
"""
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
os.environ.update(NODE_KIND="community", NODE_NAME="Ungasan", ADMIN_TOKEN="admin-tok",
                  DATABASE_URL="postgresql://unused/never-connected")

import feeds  # noqa: E402
import settings  # noqa: E402

settings._cache = {"at": time.time() + 1e9, "rows": {"SHARE_LEVEL": "open"}}
ROWS = {}


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
        elif sql.startswith("UPDATE subscribers"):
            ROWS[p[2]].update(feeds=list(p[0]), lang=p[1])
        elif sql.startswith("DELETE FROM subscribers"):
            self.rowcount = 1 if ROWS.pop(p[0], None) else 0
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
logging.disable(logging.WARNING)
os.environ.setdefault("PACKS_DIR", str(ROOT / "packs"))
import main  # noqa: E402
import subscribers  # noqa: E402

subscribers._db = lambda: _Cur()
anon = TestClient(main.app)
H = {"Authorization": "Bearer admin-tok"}
assert anon.post("/subscribers/start", json={"chat": "777"}).status_code == 403
assert anon.get("/subscribers/counts").status_code == 403
r = anon.post("/subscribers/start", json={"chat": "888"}, headers=H)
assert r.status_code == 200 and r.json()["keyboard"][0][0]["callback_data"] == "fd:weekly", r.text
assert anon.get("/subscribers/counts", headers=H).json()["total"] == 2
assert anon.post("/subscribers/toggle", json={"chat": "888", "what": "air"}, headers=H).json()["keyboard"][0][1]["text"] == "✓ Air"
assert anon.post("/subscribers/card", json={"chat": "888"}, headers=H).status_code == 200
assert anon.post("/subscribers/card", json={"chat": "000"}, headers=H).status_code == 404
assert anon.post("/subscribers/now", json={"chat": "888"}, headers=H).status_code == 501
assert anon.post("/subscribers/week", json={"chat": "888"}, headers=H).status_code == 501
assert anon.post("/subscribers/stop", json={"chat": "888"}, headers=H).json() == {"text": feeds.WORDS["en"]["stopped"]}
assert "888" not in ROWS
os.environ["NODE_KIND"] = "home"
r = anon.post("/subscribers/start", json={"chat": "777"}, headers=H)
assert r.status_code == 409 and r.json() == {"error": main.placewords.NO_ACT}, r.text
assert anon.get("/subscribers/counts", headers=H).status_code == 409
print("ok  feeds routes")
