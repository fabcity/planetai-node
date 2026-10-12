"""The capture tier (SPEC_eyes step 1): the schema, the routes, the cleaning, the privacy.

Structural half reads init.sql and app/main.py the way test_share.py does, because the invariants are
structural: the exact point is kept but the FILE is cleaned, captures are on no SHARE_LEVEL list, and no
export, aggregate, readings or parent-push path may ever name them.

Request half drives FastAPI's TestClient with the database stubbed (a stranger's peer is "testclient";
the node's own machine is loopback), CAPTURES_DIR pointed at a tmp folder via PLANETAI_CAPTURES.

Run: PYTHONPATH=app python3 tests/test_captures.py
"""
import ast
import os
import re
import sys

SQL = open("init.sql").read()
SRC = open("app/main.py").read()

# ---------------------------------------------------------------- the schema
m = re.search(r"CREATE TABLE IF NOT EXISTS captures \((.*?)\n\);", SQL, re.S)
assert m, "init.sql: no captures table"
cols = m.group(1)
for c in ("id", "ts", "received_at", "kind", "cell", "lat", "lon", "outside", "at_home", "actor", "note",
          "file", "sha256", "bytes", "mime"):
    assert re.search(rf"^\s*{c}\s", cols, re.M), f"captures.{c} missing"
assert "CHECK (kind IN ('microscope','phone','camera','drone','balloon'))" in cols, "the kinds are a CHECK"
for c in ("lat", "lon"):
    line = re.search(rf"^\s*{c}\s.*$", cols, re.M).group(0)
    assert "NOT NULL" not in line, f"captures.{c} must be nullable: a person may give no point"
assert "UNIQUE" in re.search(r"^\s*sha256\s.*$", cols, re.M).group(0), "sha256 is the dedupe key, so UNIQUE"
assert SQL.count("IF NOT EXISTS") >= SQL.count("CREATE TABLE"), "every statement stays safe to run twice"
assert "REVOKE ALL ON captures FROM planetai_ro" in SQL, \
    "pack SQL must not read captures: a rule's text reaches /alerts, and the exact point would ride out in it"
print("schema: captures table, the point nullable, sha256 unique, additive")

# ---------------------------------------------------------------- the structural half
tree = ast.parse(SRC)
funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

def code_of(name):
    fn = funcs[name]
    stmts = fn.body[1:] if ast.get_docstring(fn) else fn.body
    return "\n".join(ast.get_source_segment(SRC, st) for st in stmts)

# on no SHARE_LEVEL list, at any level — the middleware must refuse a stranger before any route runs
allow = SRC[SRC.index("_SHARE_OFF = ("):SRC.index("_SHARE = {")]
assert '"/captures"' not in allow and "captures/" not in allow, "/captures crept onto a SHARE_LEVEL allowlist"

# and nothing named captures may appear in the paths that leave the node: the exports, the readings a parent
# pulls, the aggregates and events a child pushes. The grep finds each route by its decorator — a route it
# cannot find fails the test, so a renamed function cannot quietly take the protection with it.
def route_fn(path, method):
    for n in tree.body:
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            if (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == method
                    and d.args and getattr(d.args[0], "value", None) == path):
                return n
    return None
for path, meth in (("/export", "get"), ("/exports", "get"), ("/readings", "get"),
                   ("/readings", "post"), ("/aggregates", "post"), ("/events", "post")):
    n = route_fn(path, meth)
    assert n, f"no {meth.upper()} {path} route found — the grep cannot protect a road it cannot find"
    seg = ast.get_source_segment(SRC, n)
    assert "captures" not in seg, f"{meth.upper()} {path} names captures: a picture must never travel that road"
# and no module but main.py holds SQL against the table at all in step 1
import glob
for py in glob.glob("app/**/*.py", recursive=True):
    if py != "app/main.py":
        assert "FROM captures" not in open(py).read() and "captures" not in open(py).read(), \
            f"{py} names captures: in step 1 the table is main.py's alone"

assert "_admin(" in code_of("capture_delete"), "only the admin token deletes an image"
for route in ("capture_post", "captures_list", "capture_file", "capture_patch"):
    assert route in funcs, f"{route} missing"
    assert "_captures_auth" in code_of(route), f"{route} must check the token itself, like /actions"
body = code_of("capture_post")
assert "exif_transpose" in SRC and "_clean_picture" in body, "the POST must clean the file on arrival"
assert "cell_to_parent" in body and "grid_disk" in SRC, "outside is measured against the node's seven res-8 cells"
assert "at_home" in body, "at_home is computed on arrival"
assert "sha256" in body and "duplicate" in body, "a duplicate hash answers the existing row"
assert "INSERT INTO captures" in body, "the row is written"
assert "os.path.basename" in code_of("capture_file"), "the file route never trusts a path"
print("routes: token-checked, cleaned on arrival, no export or push path names captures")

# ---------------------------------------------------------------- the request half
try:
    from fastapi.testclient import TestClient
    from PIL import Image
except ImportError:
    print("captures: request checks skipped (pip install -r app/requirements.txt)  (skipped)")
    raise SystemExit(0)

import hashlib
import io
import logging
import tempfile
import time
logging.disable(logging.WARNING)
TMP = tempfile.mkdtemp(prefix="captures-test-")
os.environ.update(ADMIN_TOKEN="admin-tok", ACT_TOKEN="act-tok", BACKUP_TOKEN="backup-tok",
                  NODE_LAT="-8.6478291", NODE_LON="115.1385412", NODE_NAME="bayu-2",
                  DATABASE_URL="postgresql://unused/never-connected", PLANETAI_CAPTURES=TMP)
import settings                                    # noqa: E402
settings._cache = {"at": time.time() + 1e9, "rows": {}}
import main                                       # noqa: E402
assert main.CAPTURES_DIR == TMP, "PLANETAI_CAPTURES must steer the folder in tests"

def level(v):
    settings._cache["rows"]["SHARE_LEVEL"] = v

lan = TestClient(main.app)
local = TestClient(main.app, client=("127.0.0.1", 51000))
ADMIN, ACT, BACKUP = ({"Authorization": f"Bearer {t}"} for t in ("admin-tok", "act-tok", "backup-tok"))

# the database, faked: q for the SELECTs, a capturing cursor for the INSERT … RETURNING *
DUPROWS, LISTROWS = [], []
def qstub(sql, *a):
    if "WHERE sha256" in sql:
        return list(DUPROWS)
    if "FROM captures WHERE id" in sql:
        return [{"file": ROW["file"], "mime": ROW["mime"]}] if ROW else []
    rows = list(LISTROWS)
    if "WHERE kind" in sql and a:                       # the route filters kind in SQL; the stub plays the db
        rows = [r for r in rows if r["kind"] == a[0]]
    return rows
main.q = qstub

class FakeCur:
    def __init__(self):
        self.sql = self.params = None
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def execute(self, sql, params=()):
        self.sql, self.params = sql, params
    def fetchone(self):
        p = self.params
        if self.sql.startswith("UPDATE"):
            return {"id": p[-1], "sets": self.sql} if p[-1] == 7 else None
        if self.sql.startswith("DELETE"):
            return {"file": DELFILE} if p[0] == 7 else None
        return {"id": 7, "ts": p[0] or "2026-10-12T01:00:00+00:00", "received_at": "2026-10-12T01:00:01+00:00",
                "kind": p[1], "cell": p[2], "lat": p[3], "lon": p[4], "outside": p[5], "at_home": p[6],
                "actor": p[7], "note": p[8], "file": p[9], "sha256": p[10], "bytes": p[11], "mime": p[12]}
CUR = FakeCur()
class FakeCon:
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def cursor(self):
        return CUR
main.db = lambda: FakeCon()

def jpeg(with_gps=True):
    im = Image.new("RGB", (64, 64), (200, 30, 30))
    exif = Image.Exif()
    exif[306] = "2026:10:01 10:11:12"                       # DateTime → the capture's ts
    exif[0x8769] = {36867: "2026:10:01 10:11:12"}           # DateTimeOriginal
    if with_gps:
        exif[0x8825] = {1: "S", 2: (8.0, 38.0, 52.18476), 3: "E", 4: (115.0, 8.0, 18.74832)}  # the node's own point
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    return buf.getvalue()

PIC = jpeg()
SHA = hashlib.sha256(PIC).hexdigest()
HERE = {"lat": "-8.6478291", "lon": "115.1385412"}          # the node's own point
AWAY = {"lat": "0.5", "lon": "100.0"}                       # far outside the seven res-8 cells

# ---- the POST: kept, pointed, cleaned
level("off")
r = lan.post("/captures", files={"photo": ("p.jpg", PIC, "image/jpeg")},
             data={"kind": "phone", "actor": "tomas", "note": "the frangipani", **AWAY}, headers=ACT)
assert r.status_code == 200, r.text
cap = r.json()["capture"]
import h3
home10 = h3.latlng_to_cell(-8.6478291, 115.1385412, 10)
assert cap["cell"] == home10, f"the cell is the point's res-10: {cap['cell']}"
assert abs(cap["lat"] + 8.6478291) < 1e-6 and abs(cap["lon"] - 115.1385412) < 1e-6, \
    "the picture's own GPS is the point, and beats where the phone is now (a gallery pick); kept, token only"
assert cap["at_home"] is True and cap["outside"] is False, "at the node's own res-10 cell"
assert cap["ts"].startswith("2026-10-01T10:11:12"), f"ts is the picture's own date: {cap['ts']}"
assert cap["actor"] == "tomas" and cap["kind"] == "phone"
kept = os.path.join(TMP, cap["file"])
assert os.path.basename(cap["file"]) == cap["file"] and os.path.isfile(kept), "a name in the folder, never a path"
ex = Image.open(kept).getexif()
assert not dict(ex), f"EXIF survived the cleaning: {dict(ex)}"
try:
    assert not ex.get_ifd(0x8825), "GPS survived the cleaning"
except Exception:
    pass
assert open(kept, "rb").read() != PIC, "the file on disk is the re-encode, not the upload"
print("POST: kept with the exact point, res-10 cell, at_home, the picture's date — and no EXIF or GPS in the file")

# away point: outside the seven cells, not at home; no point at all: the node's own cell
r = lan.post("/captures", files={"photo": ("q.jpg", jpeg(False), "image/jpeg")},
             data={"kind": "drone", **AWAY}, headers=ACT)
c2 = r.json()["capture"]
assert c2["outside"] is True and c2["at_home"] is False and c2["lat"] == 0.5, c2
r = lan.post("/captures", files={"photo": ("n.jpg", jpeg(False), "image/jpeg")}, data={"kind": "camera"}, headers=ACT)
c3 = r.json()["capture"]
assert c3["cell"] == home10 and c3["lat"] is None and c3["at_home"] is True and c3["outside"] is False, \
    "no point given: the node's own cell, and the point stays null"
# a res-10 cell instead of a point; a res-9 cell refused
r = lan.post("/captures", files={"photo": ("c.jpg", jpeg(False), "image/jpeg")}, data={"kind": "phone", "cell": home10}, headers=ACT)
assert r.json()["capture"]["cell"] == home10, "a res-10 cell is taken as given"
cell9 = h3.cell_to_parent(home10, 9)
r = lan.post("/captures", files={"photo": ("d.jpg", jpeg(False), "image/jpeg")}, data={"kind": "phone", "cell": cell9}, headers=ACT)
assert r.status_code == 422 and "res 10" in r.json()["detail"], r.text
print("POST: outside and at_home honest; no point falls back to the node's cell; a coarse cell is refused")

# a duplicate hash answers the existing row and writes nothing new
DUPROWS.append({"id": 3, "sha256": SHA, "file": "old.jpg", "kind": "phone", "cell": home10})
r = lan.post("/captures", files={"photo": ("p2.jpg", PIC, "image/jpeg")}, data={"kind": "phone"}, headers=ACT)
assert r.json().get("duplicate") and r.json()["capture"]["id"] == 3, "the duplicate answers the existing row"
DUPROWS.clear()

# not a picture; one lat without its lon; a kind that is none
r = lan.post("/captures", files={"photo": ("x.txt", b"not a picture", "text/plain")}, data={"kind": "phone"}, headers=ACT)
assert r.status_code == 415, r.text
r = lan.post("/captures", files={"photo": ("p.jpg", jpeg(False), "image/jpeg")}, data={"kind": "phone", "lat": "-8.6"}, headers=ACT)
assert r.status_code == 422 and "together" in r.json()["detail"]
r = lan.post("/captures", files={"photo": ("p.jpg", jpeg(False), "image/jpeg")}, data={"kind": "satellite"}, headers=ACT)
assert r.status_code == 422, r.text
print("POST: refuses a non-picture, a half point, a made-up kind")

# ---- who may ask
for lv in ("off", "open"):
    level(lv)
    assert lan.get("/captures").status_code == 403, f"{lv}: a stranger must not list the captures"
    assert lan.get("/captures/7/file").status_code == 403, f"{lv}: a stranger must not fetch a picture"
    assert lan.post("/captures", files={"photo": ("p.jpg", PIC, "image/jpeg")}, data={"kind": "phone"}).status_code == 403, \
        f"{lv}: a stranger must not add one"
    r = lan.get("/captures", headers=BACKUP)
    assert r.status_code == 401, f"{lv}: the read-only backup token passes the gate but must not read pictures"
level("open")
assert lan.get("/captures", headers=ACT).status_code == 200, "the act token lists"
assert local.get("/captures").status_code == 200, "this machine lists with no token (F10)"
assert local.post("/captures", files={"photo": ("l.jpg", jpeg(False), "image/jpeg")}, data={"kind": "phone"}).status_code == 200, \
    "this machine adds with no token"
print("privacy: a stranger is refused at off and at open; the backup token cannot read pictures; the act token and this machine can")

# ---- the list and its cell filter, at any resolution
LISTROWS.extend([
    {"id": 11, "ts": "2026-10-12T01:00:00+00:00", "kind": "phone", "cell": home10, "note": "a", "lat": -8.6478, "lon": 115.1385},
    {"id": 10, "ts": "2026-10-11T01:00:00+00:00", "kind": "drone", "cell": h3.latlng_to_cell(0.5, 100.0, 10), "note": "b"},
])
rows = lan.get("/captures", headers=ACT).json()
assert [r["id"] for r in rows] == [11, 10], "newest first"
assert rows[0]["at"] == [-8.6478, 115.1385], "a map draws a capture at its exact point"
assert h3.latlng_to_cell(*rows[1]["at"], 10) == rows[1]["cell"], "with no point, at its cell's centre"
rows = lan.get("/captures", params={"cell": cell9}, headers=ACT).json()
assert [r["id"] for r in rows] == [11], "a res-9 cell asks for everything inside it"
rows = lan.get("/captures", params={"cell": home10}, headers=ACT).json()
assert [r["id"] for r in rows] == [11], "a res-10 cell asks for its own"
rows = lan.get("/captures", params={"kind": "drone"}, headers=ACT).json()
assert [r["id"] for r in rows] == [10], "the kind filter"
r = lan.get("/captures", params={"cell": "not-a-cell"}, headers=ACT)
assert r.status_code == 422, r.text
print("GET: newest first, a cell at any resolution, the kind filter, a bad cell refused")

# ---- the file
ROW = {"file": f"{SHA}.jpg", "mime": "image/jpeg"}
r = lan.get("/captures/7/file", headers=ACT)
assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and len(r.content) > 100, "the picture answers a token"
r = lan.get("/captures/7/file", headers=BACKUP)
assert r.status_code == 401, "the backup token cannot fetch the file either"
ROW.clear() if isinstance(ROW, dict) else None
ROW = {}
r = lan.get("/captures/999/file", headers=ACT)
assert r.status_code == 404, "no such capture"
print("GET file: the picture to a token, 401 to the backup token, 404 when there is none")

# ---- the folder gone: a clear 503, never a quiet loss
main.CAPTURES_DIR = os.path.join(TMP, "gone")
r = local.post("/captures", files={"photo": ("p.jpg", jpeg(False), "image/jpeg")}, data={"kind": "phone"})
assert r.status_code == 503 and "CAPTURES_DIR" in r.json()["detail"], r.text
main.CAPTURES_DIR = TMP
print("folder: missing or unwritable is a clear 503 that names CAPTURES_DIR")

# ---- the cleaning keeps HEIC showable, when the install can read one
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (30, 30, 200)).save(buf, "HEIF")
    cleaned, mime, _, _ = main._clean_picture(buf.getvalue())
    assert mime == "image/jpeg" and Image.open(io.BytesIO(cleaned)).format == "JPEG", "HEIC becomes JPEG"
    print("cleaning: a HEIC becomes a JPEG any screen can show")
except Exception as e:
    print(f"cleaning: HEIC check skipped ({type(e).__name__})  (skipped)")

# ---- the Data door edits an image's words, and the admin token deletes one
DELFILE = "gone.jpg"
level("open")
r = lan.patch("/captures/7", json={"note": "the frangipani", "kind": "camera", "meta": {"species": "Plumeria"}}, headers=ACT)
assert r.status_code == 200 and "note = %s" in r.json()["capture"]["sets"] and "meta = %s" in r.json()["capture"]["sets"], r.text
assert lan.patch("/captures/7", json={"kind": "satellite"}, headers=ACT).status_code == 422, "a made-up kind"
assert lan.patch("/captures/7", json={"lat": 1}, headers=ACT).status_code == 422, "the point is not edited"
assert lan.patch("/captures/8", json={"note": "x"}, headers=ACT).status_code == 404
assert lan.patch("/captures/7", json={"note": "x"}).status_code == 403, "a stranger edits nothing"
open(os.path.join(TMP, DELFILE), "wb").write(b"x")
assert lan.delete("/captures/7", headers=ACT).status_code == 401, "the act token adds and edits, never deletes"
r = lan.delete("/captures/7", headers=ADMIN)
assert r.status_code == 200 and not os.path.exists(os.path.join(TMP, DELFILE)), "delete takes the file with the row"
assert lan.delete("/captures/8", headers=ADMIN).status_code == 404
print("edit and delete: note, kind and meta by the act token; delete by the admin token only, file and row")

print("captures: every check passed")
