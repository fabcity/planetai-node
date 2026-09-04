"""Reticulum bridge for a node. Runs in its own container (compose profile `reticulum`).

What it gives the node:
  · an LXMF address (announced on the network) so Sideband, NomadNet or another node can message it
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
reticulum = RNS.Reticulum(configdir=os.getenv("RETICULUM_CONFIGDIR", "/etc/reticulum"))
id_path = os.path.join(DATA, "identity")
identity = RNS.Identity.from_file(id_path) if os.path.exists(id_path) else RNS.Identity()
if not os.path.exists(id_path):
    identity.to_file(id_path)
router = LXMF.LXMRouter(identity=identity, storagepath=DATA)
me = router.register_delivery_identity(identity, display_name=f"planetai {NODE}")
log.info("LXMF address for %s: %s", NODE, RNS.prettyhexrep(me.hash))
with open(os.path.join(DATA, "address"), "w") as f:
    f.write(RNS.hexrep(me.hash, delimit=False))


def on_message(message):
    text = (message.content or b"").decode("utf-8", "ignore").strip()
    src = RNS.prettyhexrep(message.source_hash)
    log.info("inbox from %s: %s", src, text[:120])
    m = ACT.match(text)
    if not m:
        return
    alert_id, note = int(m.group(1)), (m.group(2).strip() or "acted (via reticulum)")
    try:
        httpx.post(f"{API}/actions", json={"alert_id": alert_id, "stage": "acted", "actor": f"lxmf:{src}", "note": note}, timeout=10).raise_for_status()
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
            self._json(200, {"ok": True, "address": RNS.hexrep(me.hash, delimit=False), "destinations": len(DESTS)})
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
        router.announce(me.hash)
        time.sleep(ANNOUNCE_S)


threading.Thread(target=announce_loop, daemon=True).start()
log.info("bridge up: http :4243, announcing every %ss, %d alert destination(s)", ANNOUNCE_S, len(DESTS))
HTTPServer(("0.0.0.0", 4243), H).serve_forever()
