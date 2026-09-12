"""Reticulum bridge for a node. Runs in its own container (compose profile `reticulum`).

What it gives the node:
  · an LXMF address (announced on the network) so Sideband, NomadNet or another node can message it
  · presence: a `planetai.presence` destination announcing the node's name and a COARSE map cell, and
    an announce handler collecting the same from other nodes. Neither end publishes a position: the
    cell is rounded to whatever RETICULUM_PRESENCE_RES says (default 3, about sixty kilometres), and
    the distance between two nodes is the distance between two cell centres. Off until a household
    sets RETICULUM_PRESENCE=1; the node decides, this container only asks and obeys.
  · an inbox: a message whose text is  `act <alert id> [note]`  becomes POST /actions on the node — closing the
    loop over a medium that works with no internet, exactly as a Telegram reply or `planetai act` would
  · an outbox: POST /send {"text": ...} delivers the text to every LXMF destination in RETICULUM_ALERT_DESTINATIONS

Transport is whatever config/reticulum/config enables: the TCP server always (reachable over the LAN or the
tailnet); an RNode LoRa radio when its block is uncommented and the device is passed into the container.

Identity and LXMF storage persist in /data. Deleting that volume gives the node a new address.
Written against rns/lxmf 0.9.x; the LXMF API is small and stable, but validate with a Sideband client on first run.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import LXMF
import RNS

log = logging.getLogger("planetai.reticulum")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")

NODE = os.getenv("NODE_NAME", "node")
API = os.getenv("NODE_API_URL", "http://app:8080")
DATA = os.getenv("RETICULUM_DATA", "/data")
DESTS = [d.strip().lower() for d in os.getenv("RETICULUM_ALERT_DESTINATIONS", "").split(",") if d.strip()]
ANNOUNCE_S = int(os.getenv("RETICULUM_ANNOUNCE_S", "1800"))
ACT = re.compile(r"^\s*act\s+(\d+)\s*(.*)$", re.I)

os.makedirs(DATA, exist_ok=True)
# RNS writes its own storage under configdir, and the config is mounted read-only (the container crash-looped on
# 'Read-only file system: /etc/reticulum/storage'). Run it from a copy of the config inside the writable volume.
_cfg_src = os.path.join(os.getenv("RETICULUM_CONFIGDIR", "/etc/reticulum"), "config")
_cfg_dir = os.path.join(DATA, "rns"); os.makedirs(_cfg_dir, exist_ok=True)
if os.path.exists(_cfg_src):
    shutil.copyfile(_cfg_src, os.path.join(_cfg_dir, "config"))
reticulum = RNS.Reticulum(configdir=_cfg_dir)
id_path = os.path.join(DATA, "identity")
identity = RNS.Identity.from_file(id_path) if os.path.exists(id_path) else RNS.Identity()
if not os.path.exists(id_path):
    identity.to_file(id_path)
router = LXMF.LXMRouter(identity=identity, storagepath=DATA)
me = router.register_delivery_identity(identity, display_name=f"planetai {NODE}")
log.info("LXMF address for %s: %s", NODE, RNS.prettyhexrep(me.hash))
with open(os.path.join(DATA, "address"), "w") as f:
    f.write(RNS.hexrep(me.hash, delimit=False))


# ---------------------------------------------------------------- presence: "I am here", and nothing else
#
# A destination of our own, `planetai.presence`, announced with a small JSON payload: the node's
# name, a COARSE map cell, and the version. No readings, no address, no coordinates. The node API
# decides whether to announce at all and how coarse the cell is — this container has no settings and
# no h3, and asking keeps the policy in one place (GET /presence, app/main.py).
#
# The receiving half is an announce handler on the same aspect. Every PLANETAI node with this bridge
# has been announcing its LXMF address since the bridge was written; none of them was listening, so
# no node has ever seen another this way.
PRESENCE = RNS.Destination(identity, RNS.Destination.IN, RNS.Destination.SINGLE, "planetai", "presence")
HEARD_MAX = 200
heard: dict = {}
heard_lock = threading.Lock()
announcing = False


class PresenceHandler:
    aspect_filter = "planetai.presence"

    def received_announce(self, destination_hash, announced_identity, app_data):
        h = RNS.hexrep(destination_hash, delimit=False)
        if h == RNS.hexrep(PRESENCE.hash, delimit=False):
            return                                          # our own announce, come back round
        try:
            body = json.loads((app_data or b"").decode("utf-8", "ignore"))
        except Exception:                                   # noqa: BLE001 — a stranger on the network
            return
        if not isinstance(body, dict) or not body.get("node"):
            return
        now = time.time()
        with heard_lock:
            row = heard.get(h) or {"first": now}
            row.update({"hash": h, "last": now,
                        "node": str(body.get("node"))[:64],
                        "cell": str(body.get("cell") or "")[:20] or None,
                        "res": int(body["res"]) if isinstance(body.get("res"), int) else None,
                        "version": str(body.get("version") or "")[:24] or None,
                        "kind": str(body.get("kind") or "")[:24] or None})
            heard[h] = row
            if len(heard) > HEARD_MAX:                      # a busy network must not fill this container
                for k, _ in sorted(heard.items(), key=lambda kv: kv[1]["last"])[:len(heard) - HEARD_MAX]:
                    heard.pop(k, None)
        log.info("presence: heard %s (%s)", row["node"], h[:8])


RNS.Transport.register_announce_handler(PresenceHandler())


def announce_presence() -> None:
    """Ask the node what it is willing to say, then say exactly that — or nothing."""
    global announcing
    try:
        p = httpx.get(f"{API}/presence", timeout=5).json()
    except Exception as e:                                  # noqa: BLE001
        log.debug("presence: the node did not answer (%s)", e)
        return
    if not p.get("enabled"):
        announcing = False
        return
    body = {k: p.get(k) for k in ("node", "cell", "res", "version", "kind") if p.get(k) is not None}
    PRESENCE.announce(app_data=json.dumps(body, separators=(",", ":")).encode())
    announcing = True
    log.info("presence: announced %s", body)


def on_message(message):
    text = (message.content or b"").decode("utf-8", "ignore").strip()
    src = RNS.prettyhexrep(message.source_hash)
    log.info("inbox from %s: %s", src, text[:120])
    m = ACT.match(text)
    if not m:
        return
    alert_id, note = int(m.group(1)), (m.group(2).strip() or "acted (via reticulum)")
    try:
        # ACT_TOKEN because this is another container, so the API sees a peer that is not this machine: /actions is
        # open on loopback only. It arrives here from .env via `env_file`, like every other key this service reads.
        httpx.post(f"{API}/actions", json={"alert_id": alert_id, "stage": "acted", "actor": f"lxmf:{src}", "note": note},
                   headers={"Authorization": f"Bearer {os.getenv('ACT_TOKEN', '')}"}, timeout=10).raise_for_status()
        reply(message.source_hash, f"recorded: you acted on #{alert_id}")
    except Exception as e:  # noqa: BLE001
        log.warning("could not record action: %s", e)


router.register_delivery_callback(on_message)


def deliver(dest_hex: str, text: str, title: str = "") -> bool:
    try:
        dest_hash = bytes.fromhex(dest_hex)
    except ValueError:
        log.warning("bad destination hash %r", dest_hex); return False
    if not RNS.Transport.has_path(dest_hash):
        RNS.Transport.request_path(dest_hash)
        for _ in range(30):
            if RNS.Transport.has_path(dest_hash):
                break
            time.sleep(0.5)
    ident = RNS.Identity.recall(dest_hash)
    if ident is None:
        log.warning("no path to %s yet; is that client announced and reachable?", dest_hex[:8]); return False
    dest = RNS.Destination(ident, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")
    msg = LXMF.LXMessage(dest, me, text, title=title or f"planetai {NODE}", desired_method=LXMF.LXMessage.DIRECT)
    router.handle_outbound(msg)
    return True


def reply(source_hash: bytes, text: str) -> None:
    deliver(RNS.hexrep(source_hash, delimit=False), text)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "address": RNS.hexrep(me.hash, delimit=False),
                             "destinations": len(DESTS), "announcing": announcing,
                             "presence": RNS.hexrep(PRESENCE.hash, delimit=False)})
        elif self.path == "/peers":
            with heard_lock:
                rows = sorted(heard.values(), key=lambda r: -r["last"])
            self._json(200, {"peers": [dict(r, first=int(r["first"]), last=int(r["last"])) for r in rows]})
        else:
            self._json(404, {})
    def do_POST(self):
        if self.path != "/send":
            return self._json(404, {})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0")) or b"{}"))
        text = str(body.get("text", ""))[:1000]
        sent = sum(1 for d in DESTS if deliver(d, text, body.get("title", "")))
        self._json(200, {"queued": sent, "of": len(DESTS)})


def announce_loop():
    while True:
        try:
            router.announce(me.hash)                        # the LXMF address, so a person can message it
            announce_presence()                             # and, if the node allows it, that it exists
        except Exception as e:                              # noqa: BLE001 — one bad announce is not the end
            log.warning("announce failed: %s", e)
        time.sleep(ANNOUNCE_S)


threading.Thread(target=announce_loop, daemon=True).start()
log.info("bridge up: http :4243, announcing every %ss, %d alert destination(s), presence at %s",
         ANNOUNCE_S, len(DESTS), RNS.prettyhexrep(PRESENCE.hash))
HTTPServer(("0.0.0.0", 4243), H).serve_forever()
