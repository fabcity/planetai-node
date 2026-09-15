"""Peers heard over Reticulum must outlive the container that heard them.

`heard` was a plain dict in memory. `planetai update` recreates containers, so a node forgot every peer
it knew on every update and showed "alone" on the Network tab until each one announced again — up to
RETICULUM_ANNOUNCE_S (30 minutes) later. Watched happen four times on 14 September while verifying the
presence fixes; the peer table was empty after every single update.

Runs the bridge's real _load_heard/_save_heard, lifted out of the module, against a temp directory. The
bridge itself imports RNS and LXMF, which this test has no business needing, so the two functions and
the constants they close over are exec'd on their own.
"""
import json
import logging
import os
import pathlib
import tempfile
import threading

src = pathlib.Path("app/reticulum_bridge.py").read_text()

# the two functions plus PEERS_FILE, out of the real file. Never a retyped copy.
assert "PEERS_FILE = os.path.join(DATA" in src, (
    "app/reticulum_bridge.py has no PEERS_FILE — peers are back to memory only, so every restart "
    "empties the Network tab until each peer announces again (up to RETICULUM_ANNOUNCE_S later)")
start = src.index("PEERS_FILE = os.path.join(DATA")
end = src.index("\n_load_heard()", start)   # the bare call at column 0, not the def line
block = src[start:end]
assert "def _load_heard" in block and "def _save_heard" in block, "could not lift the peer store out of the bridge"

d = tempfile.mkdtemp()
ns = {"os": os, "json": json, "threading": threading, "DATA": d,
      "log": logging.getLogger("t"), "heard": {}}
exec(compile(block, "bridge-peers", "exec"), ns)          # noqa: S102 — the point is to run the real code

fails = 0
def chk(name, cond):
    global fails
    print(f"  {'ok  ' if cond else 'FAIL'} {name}")
    fails += 0 if cond else 1

# nothing written yet: a first run is not an error
ns["_load_heard"]()
chk("a first run with no file starts empty", ns["heard"] == {})

# one peer, saved and read back by a fresh 'container'
ns["heard"]["ab12"] = {"hash": "ab12", "node": "dieznode", "cell": "838db5fffffffff",
                       "res": 3, "first": 1, "last": 2, "version": "v0.53", "kind": "home"}
ns["_save_heard"]()
chk("the file lands in DATA, not the cwd", os.path.isfile(os.path.join(d, "peers.json")))

ns2 = dict(ns); ns2["heard"] = {}
exec(compile(block, "bridge-peers", "exec"), ns2)          # noqa: S102
ns2["_load_heard"]()
chk("a restart remembers the peer", ns2["heard"].get("ab12", {}).get("node") == "dieznode")
chk("and its cell, so the tab can still place it", ns2["heard"]["ab12"]["cell"] == "838db5fffffffff")

# the write is atomic: no .tmp is left behind for the next run to trip over
chk("no .tmp left behind", not os.path.exists(os.path.join(d, "peers.json.tmp")))

# a corrupt file must not kill the bridge — the next announce rebuilds the list anyway
pathlib.Path(d, "peers.json").write_text("{ this is not json")
ns3 = dict(ns); ns3["heard"] = {}
exec(compile(block, "bridge-peers", "exec"), ns3)          # noqa: S102
try:
    ns3["_load_heard"]()
    chk("a corrupt file is survivable", ns3["heard"] == {})
except Exception as e:                                     # noqa: BLE001
    chk(f"a corrupt file is survivable (raised {type(e).__name__})", False)

# a row with no node name is a stranger's malformed announce, not a peer
pathlib.Path(d, "peers.json").write_text(json.dumps({"cd34": {"hash": "cd34"}, "ef56": "not a dict"}))
ns4 = dict(ns); ns4["heard"] = {}
exec(compile(block, "bridge-peers", "exec"), ns4)          # noqa: S102
ns4["_load_heard"]()
chk("malformed rows are dropped on load", ns4["heard"] == {})

print("peers survive a restart" if not fails else f"{fails} failed")
raise SystemExit(1 if fails else 0)
