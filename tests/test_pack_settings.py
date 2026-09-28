"""A pack's own keys, saved from Set up, reach the node and reach the pack. No network; the database is a dict.

v0.75.3 made the packs group send MAKE_ENABLED and friends, and the test for it read what the PAGE sent. The node
answered every one of them 400 "is not a runtime setting", and had it accepted them, the make pack reads os.getenv and
would never have seen the row. So this drives the real PUT and GET /settings handlers and then asks the pack itself.
Only psycopg.connect is replaced, with a store that understands the four statements settings and the ledger use.

Run: PYTHONPATH=app python3 tests/test_pack_settings.py
"""
import logging
import os

import psycopg
from fastapi.testclient import TestClient

logging.disable(logging.WARNING)
os.environ.update(ADMIN_TOKEN="admin-tok", NODE_LAT="-8.6478291", NODE_LON="115.1385412", PACKS_DIR="packs",
                  DATABASE_URL="postgresql://unused/never-connected", MAKE_ENABLED="0")
os.environ.pop("MAKE_SNAPSHOT", None)

STORE, LEDGER = {}, []


class Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, args=()):
        self.out = []
        if sql.startswith("SELECT key, value FROM settings"):
            self.out = [{"key": k, "value": v} for k, v in STORE.items()]
        elif sql.startswith("INSERT INTO settings"):
            STORE[args[0]] = args[1]
        elif sql.startswith("DELETE FROM settings"):
            STORE.pop(args[0], None)
        elif sql.startswith("INSERT INTO actions"):
            LEDGER.append(args)
    def fetchall(self): return self.out
    def fetchone(self): return (self.out or [None])[0]


class Con(Cur):
    def cursor(self): return Cur()


psycopg.connect = lambda *a, **k: Con()

import main       # noqa: E402
import packs      # noqa: E402
import settings   # noqa: E402

node = TestClient(main.app)
ADMIN = {"Authorization": "Bearer admin-tok"}


def row(key):
    settings._cache["at"] = 0                         # the next read goes to the store, not the 20 s cache
    body = node.get("/settings", headers=ADMIN).json()
    # describe() rows, never a flat map: body["MAKE_ENABLED"] would be a KeyError, and body.get() a quiet None
    assert isinstance(body["runtime"], list) and "MAKE_ENABLED" not in body
    return next(r for r in body["runtime"] if r["key"] == key)


# the switch of a pack that is off, and one of its values: both declared in packs/make/pack.yaml, neither in RUNTIME
assert "MAKE_ENABLED" not in settings.RUNTIME and "MAKE_RADIUS_KM" not in settings.RUNTIME
r = node.put("/settings", json={"MAKE_ENABLED": "1", "MAKE_RADIUS_KM": "25", "MAKE_SNAPSHOT": "2026.07.31_labs.json"},
             headers=ADMIN)
assert r.status_code == 200, r.text
assert set(r.json()["changed"]) == {"MAKE_ENABLED", "MAKE_RADIUS_KM", "MAKE_SNAPSHOT"}
assert len(LEDGER) == 1 and LEDGER[0][0] == "gui" and "MAKE_ENABLED" in LEDGER[0][1], "a save leaves its actions row"

for k, v in (("MAKE_ENABLED", "1"), ("MAKE_RADIUS_KM", "25")):
    got = row(k)
    assert got["value"] == v and got["source"] == "gui" and got["pack"] == "make", got
    assert got["restart"] is False, "in force at the pack's next run; `planetai config get` must not say restart"

# and the pack sees it, through the os.getenv it has always used
make = packs.module("make")
assert make.enabled(), "Set up saved MAKE_ENABLED=1 and the make pack still reads the 0 in .env"
assert os.getenv("MAKE_RADIUS_KM") == "25"

# blank is back to the environment, for the pack as well as the page; a key .env never had is unset again
assert node.put("/settings", json={"MAKE_ENABLED": "", "MAKE_SNAPSHOT": ""}, headers=ADMIN).status_code == 200
got = row("MAKE_ENABLED")
assert got["value"] == "0" and got["source"] == "env", got
assert not make.enabled() and "MAKE_SNAPSHOT" not in os.environ

# a key nothing declares is still refused, and refusing it writes nothing
before = dict(STORE)
r = node.put("/settings", json={"NO_PACK_DECLARES_THIS": "1"}, headers=ADMIN)
assert r.status_code == 400 and "no installed pack declares it" in r.text, r.text
assert STORE == before and len(LEDGER) == 2
assert node.put("/settings", json={"APP_PORT": "9999"}, headers=ADMIN).status_code == 400, "bootstrap stays .env-only"

print("all pack settings tests pass")
