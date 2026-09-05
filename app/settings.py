"""Runtime settings: the database overlays the environment.

  get(key, default)   the DB value if the GUI set one, else the environment, else default. Cached 20 s.
  set(key, value)     write; the next get() sees it within 20 s. No restart for anything in RUNTIME.
  describe()          what the GUI shows: every editable key with its group, label, whether it is a secret,
                      whether it needs a restart, and its current (masked) value.

Two classes of key, and the distinction is the whole design:
  RUNTIME   read through get() by the code, so a change takes effect on the next poll or rule pass.
  BOOTSTRAP read once by Docker or the process at start (ports, database, compose profiles). The GUI shows
            them read-only with the instruction to edit .env and run `planetai restart`.
"""
from __future__ import annotations

import os
import time

DB = os.getenv("DATABASE_URL", "postgresql://planetai:planetai@db:5432/planetai")
_cache: dict = {"at": 0.0, "rows": {}}
TTL = 20

# key -> (group, label, secret?, restart?, help)
RUNTIME = {
    # sources
    "SC_USER":            ("sources", "Smart Citizen username", False, False, "Every kit on the account is read as yours, indoor or outdoor from each kit's own setting."),
    "SC_DEVICES":         ("sources", "Smart Citizen kit ids", False, False, "Comma-separated. Always treated as yours, at this address."),
    "SC_EXCLUDE":         ("sources", "Smart Citizen kits to leave out", False, False, "Comma-separated ids of account kits that belong to another site."),
    "AIRGRADIENT_HOSTS":  ("sources", "AirGradient hosts", False, False, "Hostnames or IPs on your WiFi, comma-separated. Read directly, no cloud."),
    "PURPLEAIR_HOSTS":    ("sources", "PurpleAir hosts", False, False, "IP addresses on your WiFi."),
    "SENSOR_INDOOR":      ("sources", "LAN sensors are indoors", False, False, "1 if the AirGradient/PurpleAir units are inside."),
    "BAD_ENABLED":        ("sources", "Bali Air Dispatch", False, False, "Bali only: the island's public stations as outdoor reference. 1 or 0."),
    "BAD_RADIUS_KM":      ("sources", "Bali Air Dispatch radius, km", False, False, ""),
    "OPENMETEO_ENABLED":  ("sources", "Global models (Open-Meteo, CAMS)", False, False, "Free, key-free, anywhere. 1 or 0."),
    "CKAN_PORTALS":       ("sources", "Open-data portals", False, False, "slug=url pairs, comma-separated. Feeds Governance|City."),
    "MESH_INDOOR_NODES":  ("sources", "Indoor mesh radios", False, False, "Meshtastic node ids that are inside, e.g. !8f491db0,!64e0bfd1."),
    # alerts
    "TELEGRAM_BOT_TOKEN": ("alerts", "Telegram bot token", True, False, "From @BotFather. Never shown again once saved."),
    "TELEGRAM_CHAT_IDS":  ("alerts", "Telegram chat ids", False, False, "Comma-separated. planetai telegram finds yours."),
    "ALERT_LOCALE":       ("alerts", "Alert language", False, False, "en or id."),
    "MESH_ALERTS":        ("alerts", "Alerts over the LoRa mesh", False, False, "1 to send act-level alerts through the gateway radio."),
    "MESH_GATEWAY_NODE_NUM": ("alerts", "Gateway node number", False, False, "Decimal, for mesh downlink."),
    # integrations
    "HA_DISCOVERY":       ("integrations", "Home Assistant", False, False, "1 publishes sensors and alerts as HA entities over MQTT (needs the broker)."),
    "RETICULUM_ALERT_DESTINATIONS": ("integrations", "Reticulum alert addresses", False, False, "LXMF hashes, comma-separated."),
    "PACKS_ENABLED":      ("packs", "Enabled packs", False, False, "Empty = every pack in packs/. Or a comma-separated list of ids."),
    "PACKS_ALLOW_CODE":   ("packs", "Allow code packs", False, False, "1 lets packs with adapter.py run. Read them first."),
    # pack keys
    "EE_PROJECT":         ("keys", "Earth Engine project", False, False, "Project id, not the service account number. Blank reads it from the key file."),
    "EE_KEY_FILE":        ("keys", "Earth Engine key file", False, False, "Path inside the container; the file goes in config/."),
    "COAST_MAX_KM":       ("keys", "Coast: max distance to sea, km", False, False, ""),
    "AGGREGATE_TOKEN":    ("node", "Token children must present", True, False, "Set this before pointing another node at this one."),
    "PARENT_API_URL":     ("node", "Parent node", False, False, "http://<district>:8080 — hourly means go here. Empty = none."),
    "PARENT_TOKEN":       ("node", "Token for the parent", True, False, ""),
    "NODE_KIND":          ("node", "Kind", False, False, "home | business | community | district."),
}
BOOTSTRAP = {
    "NODE_NAME": "Name", "NODE_CITY": "City key", "NODE_LAT": "Latitude", "NODE_LON": "Longitude", "NODE_TZ": "Time zone",
    "NODE_SCALE": "Scale", "APP_PORT": "Port", "COMPOSE_PROFILES": "Extra containers", "MQTT_HOST": "Broker",
    "BACKUP_DIR": "Backups", "POLL_SECONDS": "Poll interval",
}


def _rows() -> dict:
    if time.time() - _cache["at"] < TTL:
        return _cache["rows"]
    try:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(DB, row_factory=dict_row, autocommit=True) as con, con.cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            _cache["rows"] = {r["key"]: r["value"] for r in cur.fetchall()}
    except Exception:  # noqa: BLE001 — before the table exists, or db down: fall through to the environment
        pass
    _cache["at"] = time.time()
    return _cache["rows"]


def get(key: str, default: str = "") -> str:
    v = _rows().get(key)
    if v is not None:
        return v
    return os.getenv(key, default)


def set(key: str, value: str) -> None:  # noqa: A001
    if key not in RUNTIME:
        raise KeyError(f"{key} is not a runtime setting")
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(DB, row_factory=dict_row, autocommit=True) as con, con.cursor() as cur:
        if value == "":
            cur.execute("DELETE FROM settings WHERE key = %s", (key,))       # blank = back to the environment
        else:
            cur.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (key, value))
    _cache["at"] = 0.0


def _mask(v: str) -> str:
    return ("•••• set" if v else "") if v is not None else ""


def describe() -> dict:
    db = _rows()
    out = {"runtime": [], "bootstrap": []}
    for k, (group, label, secret, restart, help_) in RUNTIME.items():
        v = get(k, "")
        out["runtime"].append({"key": k, "group": group, "label": label, "secret": secret, "restart": restart, "help": help_,
                               "value": _mask(v) if secret else v, "set": bool(v), "source": "gui" if k in db else ("env" if os.getenv(k) else "default")})
    for k, label in BOOTSTRAP.items():
        out["bootstrap"].append({"key": k, "label": label, "value": os.getenv(k, "")})
    return out
