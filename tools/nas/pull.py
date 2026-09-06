"""Pull PLANETAI node backups and exports onto the NAS, forever.

The node makes a dump every night at 03:10 and serves the list at /backups. This runs on the NAS, asks every hour
what the node has, and fetches anything missing here. Pull, not push: the NAS holds the schedule and the copies, so
the node dying takes nothing with it, the node never needs NAS credentials or a mount, and there is no folder that
can silently turn out to be local.

It also archives what the earth pack computed: the change statistics and their maps, from /earth. Not the
embedding cache under out/earth/ — that is 64 MB a year and `planetai run earth fetch` remakes any of it in
about two and a half minutes from a public bucket. What cannot be remade once a node is gone is the record of
what that node computed and when, and that is a few hundred kB a pair.

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


def fetch(path, dest, kind, auth=True):
    """kind: 'dump' | 'json' | 'png'. Each is checked before it replaces anything, so a truncated download
    fails here rather than next year during a restore."""
    tmp = dest + ".tmp"
    with open(tmp, "wb") as f:
        f.write(get(path, auth))
    if kind == "dump":
        with gzip.open(tmp) as g:
            head = g.read(65536)
        if b"CREATE TABLE" not in head:
            raise ValueError("does not look like a database dump")
    elif kind == "png":
        with open(tmp, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                raise ValueError("does not look like a PNG")
    else:
        json.loads(open(tmp, "rb").read())
    os.replace(tmp, dest)


def earth(ddir):
    """The earth pack's results, if the node runs it. /earth is public and never errors, so a node without
    the pack costs one request and returns nothing to do."""
    try:
        e = json.loads(get("/earth", auth=False))
    except Exception as ex:  # noqa: BLE001 — an older node has no /earth at all
        log("earth: skipped -", type(ex).__name__, str(ex)[:60]); return 0
    changes = e.get("changes") or []
    if not changes:
        return 0
    edir = os.path.join(ddir, "earth"); os.makedirs(edir, exist_ok=True)
    got = 0
    for c in changes:
        stem = f"change_{c.get('year_a')}_{c.get('year_b')}"
        dest = os.path.join(edir, stem + ".json")
        if not os.path.exists(dest):
            with open(dest + ".tmp", "w") as f:
                json.dump(c, f, indent=1)
            os.replace(dest + ".tmp", dest); got += 1
            log(f"earth   {stem}.json  mean {c.get('mean')}")
        png = os.path.join(edir, stem + ".png")
        if c.get("png_url") and not os.path.exists(png):
            fetch(c["png_url"], png, kind="png", auth=False); got += 1
            log(f"earth   {stem}.png  {os.path.getsize(png)//1024} kB")
    return got


def once():
    node = json.loads(get("/health", auth=False))
    name = node.get("node", "node")
    ddir = os.path.join(DEST, name); os.makedirs(os.path.join(ddir, "exports"), exist_ok=True)
    got = 0
    for b in json.loads(get("/backups")):
        dest = os.path.join(ddir, b["name"])
        if os.path.exists(dest) and os.path.getsize(dest) == b["bytes"]:
            continue
        fetch(f"/backups/{b['name']}", dest, kind="dump"); got += 1
        log(f"backup  {b['name']}  {b['bytes']//1024} kB")
    for e in json.loads(get("/exports", auth=False)):
        dest = os.path.join(ddir, "exports", e["name"])
        if os.path.exists(dest) and os.path.getsize(dest) == e["bytes"]:
            continue
        fetch(f"/exports/{e['node']}/{e['name']}", dest, kind="json", auth=False); got += 1
        log(f"export  {e['name']}")
    got += earth(ddir)
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
