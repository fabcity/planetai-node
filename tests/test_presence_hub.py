"""What the node says about the hub (docs/SPEC_hub.md): /health › reticulum gains `hub`, whether this node is on it,
and `relaying`, how many nodes are on this one when it is a hub. Heard rows keep the `id` the bridge now passes on.

Runs the real poll_reticulum against a faked bridge. fastapi, channels, settings, sources and main are stubbed, since
the point is what the node does with the bridge's answer.
"""
import sys
import types

sys.path.insert(0, "app")
stub = lambda name, **kw: sys.modules.setdefault(name, types.SimpleNamespace(**kw))
stub("fastapi", APIRouter=lambda *a, **k: types.SimpleNamespace(get=lambda *a, **k: (lambda f: f)))
stub("channels", RETICULUM_TO=lambda: ["aa11"])
stub("settings"); stub("sources", km=lambda *a: 0)
stub("main", _cell=lambda: None)
answers = {}
stub("httpx", get=lambda url, timeout: types.SimpleNamespace(json=lambda: answers[url.rsplit("/", 1)[1]]))
import presence  # noqa: E402

presence.RETICULUM_URL = "http://bridge"
fails = 0
def chk(name, cond):
    global fails
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    fails += 0 if cond else 1

def poll(health, peers=()):
    answers.update(health=health, peers={"peers": list(peers)})
    presence.poll_reticulum()
    return presence.reticulum_state

server = lambda n: {"name": "TCP Server", "type": "TCPServerInterface", "online": True, "clients": n}
hub = lambda up: {"name": "Fab City hub", "type": "PipeInterface", "online": up}

s = poll({"ok": True, "transport": False, "interfaces": [server(0), hub(True)]})
chk("a node on the hub says so", s["hub"] is True and s["relaying"] is None)
s = poll({"ok": True, "transport": False, "interfaces": [server(0), hub(False)]})
chk("and says when the hub is not answering", s["hub"] is False)
s = poll({"ok": True, "transport": False, "interfaces": [server(0)]})
chk("a node that does not dial one says nothing about it", s["hub"] is None and s["relaying"] is None)
s = poll({"ok": True, "transport": True, "interfaces": [server(3)]})
chk("a hub counts the nodes on it", s["relaying"] == 3 and s["hub"] is None)
s = poll({"ok": True, "address": "1b4f"})
chk("a bridge older than the hub breaks nothing", s["ok"] is True and s["hub"] is None and s["relaying"] is None)
s = poll({"ok": True}, [{"node": "mahon1", "cell": None, "res": 3, "first": 1, "last": 2, "hash": "ab", "id": "k4xq2"}])
chk("a heard node keeps its id", s["peers"][0]["id"] == "k4xq2")

print("the hub shows on /health" if not fails else f"{fails} failed")
raise SystemExit(1 if fails else 0)
