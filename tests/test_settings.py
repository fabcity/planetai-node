"""The settings layer: DB overlays env, blank returns to env, secrets mask, only RUNTIME keys are writable.
Run: PYTHONPATH=/tmp/stub:app python3 tests/test_settings.py"""
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
assert all(r["group"] in ("sources", "alerts", "packs", "integrations", "keys", "agent", "node") for r in d["runtime"])
assert {b["key"] for b in d["bootstrap"]} >= {"NODE_NAME", "APP_PORT", "NODE_TZ"}

# only runtime keys may be written
try:
    settings.set("APP_PORT", "9999"); raise AssertionError("bootstrap keys must not be writable")
except KeyError:
    pass
print("all settings tests pass")
