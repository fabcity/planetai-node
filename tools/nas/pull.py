"""Pull PLANETAI node backups and exports onto the NAS, forever.

The node makes a dump every night at 03:10 and serves the list at /backups. This runs on the NAS, asks every hour
what the node has, and fetches anything missing here. Pull, not push: the NAS holds the schedule and the copies, so
the node dying takes nothing with it, the node never needs NAS credentials or a mount, and there is no folder that
can silently turn out to be local.

    PLANETAI_URL    http://192.168.4.190:8081
    PLANETAI_TOKEN  the node's BACKUP_TOKEN (read-only; `planetai storage` prints it)
    DEST            /data (mounted from the NAS's backups folder)
    EVERY           seconds between runs, default 3600

Nothing here is ever deleted by this script. Dumps are small (hundreds of kB a day); a decade is a few GB.
"""
import gzip
import json
import os
import sys
import time
import urllib.request

URL = os.environ["PLANETAI_URL"].rstrip("/")
TOKEN = os.environ.get("PLANETAI_TOKEN", "")
DEST = os.environ.get("DEST", "/data")
EVERY = int(os.environ.get("EVERY", "3600"))
HDR = {"Authorization": f"Bearer {TOKEN}", "User-Agent": "planetai-nas-pull/1"}


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M"), *a, flush=True)


def get(path, auth=True):
    req = urllib.request.Request(URL + path, headers=HDR if auth else {"User-Agent": HDR["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch(path, dest, check_gzip, auth=True):
    tmp = dest + ".tmp"
    with open(tmp, "wb") as f:
        f.write(get(path, auth))
    if check_gzip:
        with gzip.open(tmp) as g:          # a truncated download fails here, not next year during a restore
            head = g.read(65536)
        if b"CREATE TABLE" not in head:
            raise ValueError("does not look like a database dump")
    else:
        json.loads(open(tmp, "rb").read())
    os.replace(tmp, dest)


def once():
    node = json.loads(get("/health", auth=False))
    name = node.get("node", "node")
    ddir = os.path.join(DEST, name); os.makedirs(os.path.join(ddir, "exports"), exist_ok=True)
    got = 0
    for b in json.loads(get("/backups")):
        dest = os.path.join(ddir, b["name"])
        if os.path.exists(dest) and os.path.getsize(dest) == b["bytes"]:
            continue
        fetch(f"/backups/{b['name']}", dest, check_gzip=True); got += 1
        log(f"backup  {b['name']}  {b['bytes']//1024} kB")
    for e in json.loads(get("/exports", auth=False)):
        dest = os.path.join(ddir, "exports", e["name"])
        if os.path.exists(dest) and os.path.getsize(dest) == e["bytes"]:
            continue
        fetch(f"/exports/{e['node']}/{e['name']}", dest, check_gzip=False, auth=False); got += 1
        log(f"export  {e['name']}")
    have = len([f for f in os.listdir(ddir) if f.endswith(".sql.gz")])
    with open(os.path.join(ddir, "LAST_PULL"), "w") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + f"  {have} dumps\n")
    log(f"{name}: {got} new, {have} dumps held")


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("PLANETAI_TOKEN is empty: put the node's BACKUP_TOKEN in planetai-backup/.env")
    while True:
        try:
            once()
        except Exception as e:  # noqa: BLE001 — the node may be down; try again next hour
            log("pull failed:", type(e).__name__, str(e)[:120])
        time.sleep(EVERY)
