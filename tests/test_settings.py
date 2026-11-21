"""The settings layer: DB overlays env, blank returns to env, secrets mask, only RUNTIME keys are writable.
Run: PYTHONPATH=/tmp/stub:app python3 tests/test_settings.py"""
import re
import json
import os
import sys

os.environ["TELEGRAM_BOT_TOKEN"] = "env-token"
os.environ["SC_USER"] = "env-user"
import settings  # noqa: E402

# no database reachable: everything falls through to the environment, nothing raises
settings._cache["at"] = 0
assert settings.get("SC_USER") == "env-user"
assert settings.get("MISSING_KEY", "dflt") == "dflt"

# simulate the DB having rows
settings._cache.update(at=9e12, rows={"SC_USER": "gui-user", "MESH_ALERTS": "1"})
assert settings.get("SC_USER") == "gui-user", "a GUI value wins over the environment"
assert settings.get("MESH_ALERTS") == "1"
assert settings.get("TELEGRAM_BOT_TOKEN") == "env-token", "keys the GUI never touched still come from .env"

d = settings.describe(unlocked=True)
tok = next(r for r in d["runtime"] if r["key"] == "TELEGRAM_BOT_TOKEN")
assert tok["secret"] and tok["value"] == "•••• set" and tok["set"], "secrets are masked, presence is shown"
sc = next(r for r in d["runtime"] if r["key"] == "SC_USER")
assert sc["source"] == "gui" and sc["value"] == "gui-user"
assert d["unlocked"] is True

# anonymous GET /settings (no admin token): the household's values are masked too, the node's own stay readable.
# GET /settings answers anyone on the WiFi; chat ids and sensor hosts were visible to them until v0.32.
a = settings.describe()
assert a["unlocked"] is False
row = {r["key"]: r for r in a["runtime"]}
assert row["SC_USER"]["value"] == "•••• set" and row["SC_USER"]["set"], "an account name is the household's: masked without the token"
assert row["MESH_ALERTS"]["value"] == "1", "a node setting stays readable: the dashboard reads UI_LAYOUT and the alert level without a token"
assert row["TELEGRAM_BOT_TOKEN"]["value"] == "•••• set"
for k in ("TELEGRAM_CHAT_IDS", "AIRGRADIENT_HOSTS", "PURPLEAIR_HOSTS", "SC_DEVICES", "CKAN_PORTALS", "AGENT_REMOTE_URL", "PARENT_API_URL", "EE_PROJECT"):
    assert k not in settings.PUBLIC, f"{k} names a host, an account or an address; it must not be public"
assert "UI_LAYOUT" in settings.PUBLIC and "ALERT_LOCALE" in settings.PUBLIC
# Every group a setting claims must have a pane in the dashboard's Set up view, or a household cannot
# reach the setting at all. The list is read out of the page rather than retyped here, so the two
# cannot drift. NO_PANE_YET is for a group whose setting has shipped ahead of its pane; an entry there
# needs the reason, and the release that adds the pane deletes the entry.
NO_PANE_YET: set = set()   # NODE_ISSUES's entry went when the groups became tasks (28 Sep): it leads Basics
panes = set(re.findall(r"(\w+):\s*\['", re.search(r"const GROUPS\s*=\s*\{(.*?)\n\};", 
            open("app/static/dashboard.js").read(), re.S).group(1)))
for r in d["runtime"]:
    assert r["group"] in panes | NO_PANE_YET, \
        f"{r['key']} is in group {r['group']!r}, which has no pane in the dashboard's Set up view"
assert NO_PANE_YET <= {r["group"] for r in d["runtime"]}, \
    "NO_PANE_YET names a group no setting uses any more — delete the entry"
assert {b["key"] for b in d["bootstrap"]} >= {"NODE_NAME", "APP_PORT", "NODE_TZ"}

# only runtime keys may be written
try:
    settings.set("APP_PORT", "9999"); raise AssertionError("bootstrap keys must not be writable")
except KeyError:
    pass

# PREDICT_MODEL is .env's alone: the models container can only follow .env. It is a read-only row in group model, with
# its help, refused on save like COMPOSE_PROFILES, and every reader sees the environment.
os.environ["PREDICT_MODEL"] = "amazon/chronos-2"
_b = {b["key"]: b for b in settings.describe(unlocked=True)["bootstrap"]}
assert "PREDICT_MODEL" not in settings.RUNTIME and "PREDICT_MODEL" in _b and "COMPOSE_PROFILES" in _b
assert _b["PREDICT_MODEL"]["group"] == "model" and _b["PREDICT_MODEL"]["label"] == "Forecast model" and _b["PREDICT_MODEL"]["value"] == "amazon/chronos-2"
assert _b["PREDICT_MODEL"]["help"].startswith("A time-series model that forecasts this node's own readings") and "planetai models pull <name>" in _b["PREDICT_MODEL"]["help"]
assert "help" not in _b["COMPOSE_PROFILES"], "a row with no help carries none"
for _k in ("PREDICT_MODEL", "COMPOSE_PROFILES"):
    try:
        settings.set(_k, "amazon/chronos-bolt-tiny"); raise AssertionError(_k + " must refuse a save")
    except KeyError:
        pass
_real_rows = settings._rows
settings._rows = lambda: {"PREDICT_MODEL": "a row that must never be read"}
assert settings.get("PREDICT_MODEL") == os.getenv("PREDICT_MODEL") == "amazon/chronos-2", "one source: the environment"
settings._rows = _real_rows
os.environ.pop("PREDICT_MODEL")
_ds = open("app/static/doors-setup.js").read(); _dj = open("app/static/dashboard.js").read()
assert "b.help ?" in _ds and "b.help ?" in _dj, "Set up draws a read-only row's help only when it has one"

# --- MAP_TILES: live tiles leave the house, so they are off until a keeper says otherwise --------------------
assert "MAP_TILES" in settings.PUBLIC, "MAP_TILES is a public setting, so the page can read it"
try:
    settings.set("MAP_TILES", "sometimes")
    raise AssertionError("MAP_TILES accepted 'sometimes'; it is off or on")
except (ValueError, KeyError):
    pass
# get() with a fallback proves nothing: assert the shipped default is in .env.example, the real source
assert "MAP_TILES=off" in open(".env.example").read(), "MAP_TILES defaults to off in the shipped .env.example"

# --- STATIONS_SHOWN: the list's display cap. Nothing here changes what the node collects ---------------------
assert "STATIONS_SHOWN" in settings.PUBLIC, \
    "STATIONS_SHOWN is a public setting, or a reader with no token gets the default and the keeper's choice is lost"
assert "STATIONS_SHOWN" not in settings.OUTWARD, \
    "a display cap decides what this house looks at, never what leaves it; BAD_RADIUS_KM is the one that collects"
assert "STATIONS_SHOWN=3" in open(".env.example").read(), \
    "STATIONS_SHOWN defaults to 3 in the shipped .env.example"

# --- AGENT_PREFER: the household's own sentences stay home until somebody here says otherwise ----------------
# get() with a fallback proves nothing about what ships; assert the shipped default, the way MAP_TILES does.
assert "AGENT_PREFER=private" in open(".env.example").read(), \
    "AGENT_PREFER ships as private: a fresh node sends nothing off the network before anyone has chosen"
assert settings.CHOICES["AGENT_PREFER"][0] == "private", \
    "private is offered first, on the Model page and in `planetai config` — both walk CHOICES as given"
assert "AGENT_PREFER" in settings.OUTWARD, "it decides whether the online path is used at all"
assert settings.RUNTIME["AGENT_PREFER"][4].startswith("private"), \
    "the help is the one line each surface shows and the one the refusal quotes; the consequences are in it"

# Grafana's keys are read at start and shown in Set up › System; its password only ever as "set" (24 Oct 2026)
os.environ.update(GRAFANA_ADMIN_PASSWORD="hunter2-not-shown", GRAFANA_BIND="127.0.0.1")
for _unlocked in (False, True):
    _b = {b["key"]: b for b in settings.describe(unlocked=_unlocked)["bootstrap"]}
    assert _b["GRAFANA_ADMIN_PASSWORD"]["value"] == "set" and _b["GRAFANA_ADMIN_PASSWORD"]["secret"], _b["GRAFANA_ADMIN_PASSWORD"]
    assert "hunter2" not in json.dumps(settings.describe(unlocked=_unlocked)), "the Grafana password reached /settings"
    assert _b["GRAFANA_BIND"]["value"] == "127.0.0.1" and not _b["GRAFANA_BIND"]["secret"]
os.environ.pop("GRAFANA_ADMIN_PASSWORD")
assert {b["key"]: b for b in settings.describe()["bootstrap"]}["GRAFANA_ADMIN_PASSWORD"]["value"] == ""
print("settings: Grafana's address and port are shown, its password only as set or not")

# --- LOCAL_RADIUS_M is retired: own cells in node_cells replace the circle (SPEC_eyes §5) --------------------
assert "LOCAL_RADIUS_M" not in settings.RUNTIME, "LOCAL_RADIUS_M must leave settings.RUNTIME"
assert "LOCAL_RADIUS_M" not in settings.PUBLIC, "LOCAL_RADIUS_M must leave settings.PUBLIC"
assert "LOCAL_RADIUS_M" in settings.RETIRED, "LOCAL_RADIUS_M is recorded in settings.RETIRED"
assert "LOCAL_RADIUS_M" not in open(".env.example").read(), "LOCAL_RADIUS_M must leave .env.example"
os.environ["LOCAL_RADIUS_M"] = "500"
settings._cache["rows"]["LOCAL_RADIUS_M"] = "750"
for _unlocked in (False, True):
    _desc = settings.describe(unlocked=_unlocked)
    _keys = {r["key"] for r in _desc["runtime"]} | {r["key"] for r in _desc["bootstrap"]}
    assert "LOCAL_RADIUS_M" not in _keys, "a node whose .env or DB still sets LOCAL_RADIUS_M ignores it"
assert not settings.writable("LOCAL_RADIUS_M"), "retired LOCAL_RADIUS_M is not writable"
os.environ.pop("LOCAL_RADIUS_M", None)
settings._cache["rows"].pop("LOCAL_RADIUS_M", None)
print("settings: LOCAL_RADIUS_M is retired and ignored when still present in .env or settings table")

print("all settings tests pass")
