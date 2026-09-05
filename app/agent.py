"""The node as a set of tools for an AI agent, over MCP.

Mounted on the API at /mcp (streamable HTTP). A remote Claude reaches it over Tailscale; a local model on the same
machine reaches it on localhost. Reads are what the API already gives; writes need the admin token and record which
agent did them (the X-Agent header, default "agent").

What an agent can do here: read the node, act on an alert, change runtime settings, enable packs, run a pack's
scripts, get one day as open data. What it cannot do from here: anything that needs Docker or git on the host
(update, backup, restart). For those, `maintenance` returns the exact command to run on the node; an agent with a
shell runs it, an agent without one tells the person.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

import settings

API = f"http://127.0.0.1:{os.getenv('PORT', '8080')}"
NODE = os.getenv("NODE_NAME", "node")

mcp = MCPServer(
    "planetai-node",
    instructions=(
        f"You are operating PLANETAI node '{NODE}': a small computer that reads environmental sensors at one place, "
        "decides locally, and tells the people there what to do. Raw readings never leave it. Your job is to keep it "
        "healthy and useful: read status, check alerts, record actions people took (that is how the node measures "
        "itself), adjust settings when asked, and report plainly. Never expose tokens. Prefer one clear sentence to a list."
    ),
)


def _get(path: str):
    r = httpx.get(API + path, timeout=30)
    r.raise_for_status()
    return r.json()


def _admin_headers(agent: str) -> dict:
    return {"Authorization": f"Bearer {os.getenv('ADMIN_TOKEN', '')}", "X-Agent": agent}


@mcp.tool()
def status() -> dict:
    """Is the node alive, what has it read, what fired, and its rho (share of alerts that led to an action)."""
    h = _get("/health"); rho = _get("/rho")
    backups = Path("/app/backups")
    last_ok = (backups / "LAST_OK").read_text().strip() if (backups / "LAST_OK").exists() else None
    return {"node": h.get("node"), "version": h.get("version"), "schema": h.get("schema"), "uptime_s": h.get("uptime_s"),
            "last_poll": h.get("last_poll"), "readings": h.get("ingested"), "polls": h.get("polls"),
            "errors": h.get("errors") or {}, "mesh": h.get("mesh"), "rho": rho, "last_backup_ok": last_ok}


@mcp.tool()
def health_check() -> dict:
    """Checks with the fix named next to each failure: polling recent, sources without errors, a backup in the last two days,
    the database reachable, the mesh alive if configured."""
    h = _get("/health"); checks = []
    def chk(name, ok, fix): checks.append({"check": name, "ok": bool(ok), "fix": None if ok else fix})
    age = None
    if h.get("last_poll"):
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(h["last_poll"])).total_seconds() / 60
    chk("polled in the last 15 min", age is not None and age < 15, "the poll loop is stuck or the node just started; check `planetai logs`")
    chk("no source errors", not h.get("last_error") and not (h.get("errors") or {}), f"errors: {h.get('last_error') or h.get('errors')}")
    backups = Path("/app/backups")
    dumps = sorted(backups.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime) if backups.exists() else []
    fresh = dumps and (datetime.now(timezone.utc) - datetime.fromtimestamp(dumps[-1].stat().st_mtime, timezone.utc)) < timedelta(days=2)
    chk("a backup in the last 2 days", fresh, "run `planetai backup` on the node and check `crontab -l | grep backup`")
    if os.getenv("MQTT_HOST"):
        # judge the radios by their readings, not by in-memory packet counters that reset on every restart
        mesh = [r for r in _get("/stats") if r["sensor_id"].startswith("msh-")]
        quiet = sorted({r["sensor_id"] for r in mesh if r["silent_minutes"] > 60})
        heard = sorted({r["sensor_id"] for r in mesh if r["silent_minutes"] <= 60})
        chk("LoRa radios heard in the last hour", bool(heard) or not mesh,
            f"radio(s) {', '.join(quiet)} have been silent for hours. What this means: readings and alerts that travel over LoRa have "
            f"stopped; everything else (the WiFi sensors, Telegram, the dashboard) is unaffected. Most often the gateway radio (the XIAO) "
            f"lost WiFi or its MQTT session: check its power light, open its web page at its IP, or power-cycle it. `planetai logs mosquitto` shows whether the broker hears it.")
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


@mcp.tool()
def sensors() -> list:
    """Every sensor the node knows: yours (local) and public references, indoor or outdoor, with the latest PM2.5, temperature and
    humidity and how long since each spoke."""
    stats = _get("/stats"); by = {}
    for r in stats:
        by.setdefault(r["sensor_id"], {"sensor_id": r["sensor_id"], "name": r["name"], "local": r["local"], "indoor": r["indoor"], "kind": r["kind"]})
        if r["metric"] in ("pm25", "temp", "humidity"):
            by[r["sensor_id"]][r["metric"]] = r["mean_15m"]
            by[r["sensor_id"]]["silent_minutes"] = round(r["silent_minutes"])
    return sorted(by.values(), key=lambda s: (not s["local"], s["sensor_id"]))


@mcp.tool()
def alerts(limit: int = 10) -> list:
    """Recent alerts, newest first, each with its id, level (info/warn/act) and whether anyone acted on it."""
    return _get(f"/alerts?limit={min(limit, 100)}")


@mcp.tool()
def act(alert_id: int, note: str = "acted", agent: str = "agent") -> dict:
    """Record that a person acted on an alert. This is the node's own measurement: rho is the share of act-level alerts that
    led to an action. Use the person's words in `note` when you have them."""
    r = httpx.post(API + "/actions", json={"alert_id": alert_id, "stage": "acted", "actor": agent, "note": note}, timeout=30)
    r.raise_for_status()
    return {"recorded": True, "alert_id": alert_id, "by": agent}


@mcp.tool()
def settings_get() -> dict:
    """Every runtime setting with its group, help and current value. Secrets are masked. Bootstrap settings (ports, database)
    are shown read-only; they change only in .env on the node."""
    return settings.describe()


@mcp.tool()
def settings_set(changes: dict, agent: str = "agent") -> dict:
    """Change runtime settings, e.g. {"SC_USER": "tomasdiez", "MESH_ALERTS": "1"}. Live within ~20 s, no restart. Blank returns a
    key to its .env value. Only keys listed by settings_get under `runtime` are allowed."""
    r = httpx.put(API + "/settings", json=changes, headers=_admin_headers(agent), timeout=30)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def packs() -> list:
    """The packs loaded on this node: id, kind (data/code), description. Enable or disable with settings_set PACKS_ENABLED."""
    return _get("/packs")


@mcp.tool()
def cells() -> list:
    """The Fab City Index cells this node computes, with value, unit and provenance state (live = measured here, partial = derived
    or modelled)."""
    return _get("/cells")


@mcp.tool()
def series(metric: str = "pm25", hours: int = 24) -> dict:
    """Hourly means for the last N hours: indoor (yours), outdoor (yours and references), and the model, as aligned arrays."""
    return _get(f"/series?metric={metric}&hours={min(hours, 168)}")


@mcp.tool()
def export_day(day: str | None = None) -> dict:
    """One day as open data: hourly means per sensor, cells, alerts, rho. Default yesterday. What a parent node or a researcher receives."""
    day = day or (date.today() - timedelta(days=1)).isoformat()
    return _get(f"/export?day={day}")


@mcp.tool()
def run_pack_script(pack: str, script: str, args: list[str] | None = None, agent: str = "agent") -> dict:
    """Run a script a pack ships (e.g. earth-engine verify, earth-engine timelapse). Runs in the app container; output files land in out/.
    Returns stdout/stderr and the exit code."""
    p = Path("/app/packs") / Path(pack).name / (Path(script).name + ".py")
    if not p.exists():
        return {"error": f"no such script: {pack}/{script}", "available": [f"{q.parent.name}/{q.stem}" for q in Path("/app/packs").glob("*/*.py") if q.stem != "adapter"]}
    r = subprocess.run(["python", str(p), *(args or [])], capture_output=True, text=True, timeout=900, env={**os.environ, "PACK_OUT": "/app/out"})
    return {"exit": r.returncode, "stdout": r.stdout[-6000:], "stderr": r.stderr[-2000:], "by": agent}


@mcp.tool()
def maintenance(task: str) -> dict:
    """Host-side tasks this server cannot run itself because they need Docker or git on the node's machine: update, backup, restore,
    restart, logs, doctor, storage, ui, telegram. Returns the exact command and what it does, so an agent with a shell on the node runs
    it, and an agent without one tells the person."""
    cmds = {
        "update": ("planetai update", "backs up, fetches the current version, migrates the database, rebuilds, verifies"),
        "backup": ("planetai backup", "dumps the database now, writes the daily export, copies off-machine if configured"),
        "restore": ("planetai restore <backups/file.sql.gz>", "replaces the live database with a dump; takes a safety backup first"),
        "restart": ("planetai restart", "restarts the containers; needed after editing .env"),
        "logs": ("planetai logs", "follows the app log; `planetai logs mosquitto` for the broker"),
        "doctor": ("planetai doctor --json", "every check with the fix named for each failure, as JSON"),
        "storage": ("planetai storage", "database size, backup destination and freshness, remote, exports, IPFS, the NAS token"),
        "ui": ("planetai ui", "dashboard URLs and the admin token"),
        "telegram": ("planetai telegram", "connects the Telegram bot"),
    }
    if task not in cmds:
        return {"error": f"unknown task; one of {sorted(cmds)}"}
    c, what = cmds[task]
    return {"run_on_the_node": c, "does": what, "where": "a shell on the node's machine (ssh, or the local agent). Not from here."}


def http_routes():
    """Routes serving MCP at exactly /mcp, to append to the main app. The caller runs session_manager in its lifespan.
    DNS-rebinding protection is off: the node is reached by many names (LAN IP, .local, the tailnet name) and the
    admin token, not the Host header, is the access control."""
    from mcp.server.transport_security import TransportSecuritySettings
    inner = mcp.streamable_http_app(streamable_http_path="/mcp",
                                    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    return inner.routes
