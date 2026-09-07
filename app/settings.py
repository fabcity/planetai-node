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
    "REPORT_EVERY":       ("alerts", "Report every", False, False, "Hours between reports: 3, 4, 6, 8, 12 or 24. Default 6, which is four a day."),
    "REPORT_ANCHOR":      ("alerts", "First report of the day", False, False, "The local hour the rhythm starts from, 0-23. Default 6: with a 6-hour interval that is 06, 12, 18 and 00."),
    "REPORT_DEPTH":       ("alerts", "How much the report says", False, False, "auto, brief, standard or deep. auto lets the strongest model the node can reach decide. Until a model is in the path every report is the node's own, and this changes nothing."),
    "ALERT_LEVEL":        ("alerts", "Interrupt me for", False, False, "act = only when something needs doing (default) · warn = also when something changed · info = everything. Everything is recorded, on the dashboard, and in the next report."),
    "QUIET_HOURS":        ("alerts", "Quiet hours", False, False, "1 = between the hours below, only act-level alerts are sent; the rest wait for the morning report."),
    "QUIET_FROM":         ("alerts", "Quiet from", False, False, "Local hour, default 22."),
    "QUIET_TO":           ("alerts", "Quiet until", False, False, "Local hour, default 6."),
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
    "AGENT_PREFER":       ("agent", "Model preference", False, True, "strongest tries online, remote, local; private never uses online."),
    "AGENT_REMOTE_URL":   ("agent", "Remote model URL", False, True, "A bigger local model on your tailnet, OpenAI-compatible: http://<host>:8082/v1"),
    "AGENT_REMOTE_MODEL": ("agent", "Remote model", False, True, "e.g. gpt-oss-120b or qwen3:8b"),
    "AGENT_REMOTE_KEY":   ("agent", "Remote model key", True, True, "If that server asks for one."),
    "AGENT_ONLINE_URL":   ("agent", "Online model URL", False, True, "https://api.anthropic.com/v1 or https://api.openai.com/v1"),
    "AGENT_ONLINE_MODEL": ("agent", "Online model", False, True, "e.g. claude-sonnet-4-6"),
    "AGENT_ONLINE_KEY":   ("agent", "Online model key", True, True, "The only thing that lets household data leave your network. Your choice."),
    "UI_LAYOUT":          ("node", "Dashboard layout", False, False, "Order and visibility of the dashboard's cards, as JSON. Managed by the dashboard's Arrange mode; blank restores the default."),
    "AGGREGATE_TOKEN":    ("node", "Token children must present", True, False, "Set this before pointing another node at this one."),
    "BACKUP_TOKEN":       ("node", "Token for collecting backups", True, False, "Read-only: lets a NAS fetch /backups. Separate from the admin token."),
    "PARENT_API_URL":     ("node", "Parent node", False, False, "http://<district>:8080 — hourly means go here. Empty = none."),
    "PARENT_TOKEN":       ("node", "Token for the parent", True, False, ""),
    "NODE_KIND":          ("node", "Kind", False, False, "home | business | community | district."),
}
# What an anonymous reader on the LAN may see the value of. Everything else shows as "•••• set" until the admin token is
# presented (the dashboard's Set up view sends it once unlocked). Chat ids, sensor hosts, account names and remote URLs
# are not secrets, but they are the household's, and GET /settings answers anyone on the WiFi (found 6 Sep 2026).
PUBLIC = {"REPORT_EVERY", "REPORT_ANCHOR", "REPORT_DEPTH", "ALERT_LEVEL", "QUIET_HOURS", "QUIET_FROM", "QUIET_TO", "ALERT_LOCALE",
          "MESH_ALERTS", "HA_DISCOVERY", "PACKS_ENABLED", "PACKS_ALLOW_CODE", "OPENMETEO_ENABLED", "BAD_ENABLED", "BAD_RADIUS_KM",
          "SENSOR_INDOOR", "COAST_MAX_KM", "AGENT_PREFER", "AGENT_REMOTE_MODEL", "AGENT_ONLINE_MODEL", "UI_LAYOUT", "NODE_KIND"}
BOOTSTRAP = {
    "NODE_NAME": "Name", "NODE_CITY": "City key", "NODE_LAT": "Latitude", "NODE_LON": "Longitude", "NODE_TZ": "Time zone",
    "NODE_SCALE": "Scale", "APP_PORT": "Port", "COMPOSE_PROFILES": "Extra containers", "MQTT_HOST": "Broker",
    "BACKUP_DIR": "Backups", "BACKUP_REMOTE": "Off-machine copy", "BACKUP_KEEP": "Days of backups kept", "DATA_DIR": "Database location", "EXPORT_ENABLED": "Daily export", "IPFS_PUBLISH": "IPFS", "POLL_SECONDS": "Poll interval",
}

# Values a key refuses. Most settings are free text on purpose — a node has to keep running through a typo — but a
# report interval the scheduler cannot honour would make the node silent instead of wrong, which is worse. The help
# text above is where the accepted values are written; the refusal quotes it rather than keeping a second copy.
CHOICES = {
    "REPORT_EVERY":  ("3", "4", "6", "8", "12", "24"),      # each divides 24, so the rhythm does not walk round the clock
    "REPORT_ANCHOR": tuple(str(h) for h in range(24)),
    "REPORT_DEPTH":  ("auto", "brief", "standard", "deep"),
}

# Keys the reports release retired. Rows for them are left in `settings` and in .env, and nothing reads them: a
# household that updates does not have a value it chose deleted out from under it. BRIEF_HOUR was the agent
# container's own third clock and is gone from the compose file.
RETIRED = ("BRIEFINGS", "BRIEF_MORNING", "BRIEF_EVENING", "BRIEF_HOUR")


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
    if value and key in CHOICES and value not in CHOICES[key]:
        raise ValueError(f"{value!r} is not a value {key} accepts. {RUNTIME[key][4]}")
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(DB, row_factory=dict_row, autocommit=True) as con, con.cursor() as cur:
        if value == "":
            cur.execute("DELETE FROM settings WHERE key = %s", (key,))       # blank = back to the environment
        else:
            cur.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (key, value))
    _cache["at"] = 0.0


def num(key: str, default: int) -> int:
    """A setting that has to be a number, where the default survives a key that is present but empty. `update.sh`
    merges new keys from `.env.example` with whatever value they carry there, and the REPORT_* keys ship blank so
    that an updating node keeps the rhythm it had instead of silently taking the new default."""
    v = (get(key, "") or "").strip()
    return int(v) if v.isdigit() else default


def brief_migration(current: dict) -> dict:
    """What a node on the old two-briefings schedule should be set to when it updates: the REPORT_* rows to write,
    or nothing at all. Pure, so the test can run this function rather than a copy of its rule.

    A node with BRIEF_MORNING=7 keeps seven o'clock and keeps speaking twice a day; it does not start speaking four
    times a day because someone ran an update. A fresh install has none of the old keys, gets nothing written here,
    and takes 6 and 6 from the defaults."""
    if any((current.get(k) or "").strip() in CHOICES[k] for k in ("REPORT_EVERY", "REPORT_ANCHOR")):
        return {}
    if not any((current.get(k) or "").strip() for k in RETIRED[:3]):
        return {}
    anchor = (current.get("BRIEF_MORNING") or "").strip()
    return {"REPORT_EVERY": "12", "REPORT_ANCHOR": anchor if anchor in CHOICES["REPORT_ANCHOR"] else "6"}


def migrate_briefings() -> dict:
    """Run brief_migration against this node and write what it says. Returns what was written, for the log."""
    current = {k: get(k, "") for k in (*RETIRED, "REPORT_EVERY", "REPORT_ANCHOR")}
    writes = brief_migration(current)
    for k, v in writes.items():
        set(k, v)
    return writes


def _mask(v: str) -> str:
    return ("•••• set" if v else "") if v is not None else ""


def describe(unlocked: bool = False) -> dict:
    """unlocked=False is what an anonymous GET /settings gets: secrets masked, and every value outside PUBLIC masked too.
    unlocked=True (admin token presented, or an MCP call, which is behind the token already) shows all but the secrets."""
    db = _rows()
    out = {"unlocked": unlocked, "runtime": [], "bootstrap": []}
    for k, (group, label, secret, restart, help_) in RUNTIME.items():
        v = get(k, "")
        hide = secret or (not unlocked and k not in PUBLIC)
        out["runtime"].append({"key": k, "group": group, "label": label, "secret": secret, "restart": restart, "help": help_,
                               "value": _mask(v) if hide else v, "set": bool(v), "source": "gui" if k in db else ("env" if os.getenv(k) else "default")})
    for k, label in BOOTSTRAP.items():
        out["bootstrap"].append({"key": k, "label": label, "value": os.getenv(k, "")})
    return out
