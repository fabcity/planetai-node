"""The vendored source registry: the file, the gate, the route and the row on a /cells line.

Runs against the files themselves — data/sources/ as committed, tools/check_registry.py as it is in
`make lint` — because a registry typed into a test is a test of the typing.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"

# ---- the snapshot itself
ver = dict(l.split("=", 1) for l in (SOURCES / "REGISTRY_VERSION").read_text().split() if "=" in l)
index = json.loads((SOURCES / "index.json").read_text())
yaml_files = sorted((SOURCES / "data").rglob("*.yaml"))

assert int(ver["entries"]) == len(index) == len(yaml_files), (
    f"REGISTRY_VERSION says {ver['entries']}, index.json has {len(index)}, "
    f"the YAML has {len(yaml_files)}")
assert len(ver["sha"]) == 40 and ver["short"] == ver["sha"][:7], "REGISTRY_VERSION: sha/short disagree"
for e in index:
    p, s, _ = e["slug"].split("/")
    assert e["cell"] == f"{p.capitalize()}|{s.capitalize()}", f"{e['slug']}: cell {e['cell']}"
print(f"  {len(index)} entries at {ver['short']}, synced {ver['synced']}")

# ---- every pack's `sources:` id resolves. The gate says so too; this says it without the gate, so a
# change to the gate cannot make both go quiet at once.
ids = {e["slug"] for e in index}
import re
named = 0
for pk in sorted(ROOT.glob("packs/*/pack.yaml")):
    m = re.search(r"^sources:\s*\[(.*?)\]", pk.read_text(), re.M | re.S)
    for sid in ([x.strip() for x in m.group(1).split(",") if x.strip()] if m else []):
        named += 1
        assert sid in ids, f"{pk.relative_to(ROOT)} names {sid}, which is not in the registry"
print(f"  {named} pack source ids resolve")

# ---- the gate names the slug it cannot resolve
tmp = tempfile.mkdtemp()
try:
    fixture = pathlib.Path(tmp) / "planetai-node"
    fixture.mkdir()
    (fixture / "tools").mkdir()
    for t in ("check_registry.py", "build_registry_index.py"):
        shutil.copy(ROOT / "tools" / t, fixture / "tools" / t)
    shutil.copytree(SOURCES, fixture / "data" / "sources")
    (fixture / "packs" / "bad").mkdir(parents=True)
    (fixture / "packs" / "bad" / "pack.yaml").write_text(
        "id: bad\nsources: [environmental/city/does-not-exist]\n")
    r = subprocess.run([sys.executable, "tools/check_registry.py"], cwd=fixture,
                       capture_output=True, text=True)
    assert r.returncode == 1, "check_registry.py passed a pack citing a slug that is not filed"
    assert "environmental/city/does-not-exist" in r.stdout, \
        f"the failure does not name the slug:\n{r.stdout}"
    print("  an unfiled slug fails the gate, by name")

    # and a hand edit to the generated index does too
    bad = fixture / "data" / "sources" / "index.json"
    d = json.loads(bad.read_text()); d[0]["license"] = "hand edited"
    bad.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    (fixture / "packs" / "bad" / "pack.yaml").write_text("id: bad\n")
    r = subprocess.run([sys.executable, "tools/check_registry.py"], cwd=fixture,
                       capture_output=True, text=True)
    assert r.returncode == 1 and "hand-edited" in r.stdout, f"a hand edit passed:\n{r.stdout}"
    print("  a hand-edited index.json fails the gate")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---- the route
os.environ.update(SOURCES_DIR=str(SOURCES), SHARE_LEVEL="open", NODE_CITY="bali", NODE_SCALE="city",
                  NODE_NAME="t", NODE_LAT="-8.8", NODE_LON="115.1",
                  PACKS_DIR=str(ROOT / "packs"),
                  DATABASE_URL="postgresql://x:x@127.0.0.1:1/x")
sys.path.insert(0, str(ROOT / "app"))
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
import index as index_mod  # noqa: E402

c = TestClient(main.app)
r = c.get("/sources", params={"pilot": "bali"})
assert r.status_code == 200, r.text
body = r.json()
assert body["registry"]["short"] == ver["short"] and body["registry"]["entries"] == len(index)
assert body["count"] == len(body["sources"]) > 0
for e in body["sources"]:
    rel = e.get("pilot_relevance") or []
    assert "bali" in rel or "global" in rel, f"{e['slug']} is neither bali nor global: {rel}"
assert len(body["sources"]) < len(index), "the pilot filter returned everything"
print(f"  /sources?pilot=bali -> {body['count']} rows, all bali or global")

# one entry, and a slug that is not in THIS pin
assert c.get("/sources/economic/community/openstreetmap").status_code == 200
assert c.get("/sources/environmental/city/nope").status_code == 404

# ---- the route's count for a cell is the number index.py puts on that cell's row
for cell in ("Governance|City", "Social|City", "Environmental|Community"):
    n = c.get("/sources", params={"cell": cell}).json()["count"]
    row = index_mod._row(cell, 1.0, "u", "src", "partial")
    assert row["registered"] == n, f"{cell}: /sources says {n}, a /cells row says {row['registered']}"
    read = any(e.get("adapter")
               for e in c.get("/sources", params={"cell": cell}).json()["sources"])
    assert row["adapter"] is read, f"{cell}: /cells adapter {row['adapter']}, /sources says {read}"
    # additive: the row still carries everything it carried before
    assert {"city", "cell", "value", "unit", "source", "observed_at", "state", "notes"} <= set(row)
print("  /cells `registered` and `adapter` agree with /sources for three cells")

# ---- no registry, no crash: 503 on /sources and /health untouched
os.environ["SOURCES_DIR"] = "/nowhere-at-all"
import registry  # noqa: E402
registry.SOURCES_DIR = pathlib.Path("/nowhere-at-all")
registry._cache.update(mtime=None, entries=[], version={})
assert c.get("/sources").status_code == 503
assert "sync_registry.sh" in c.get("/sources").json()["detail"]
assert c.get("/health").status_code == 200
print("  no registry: /sources 503s naming the sync script, /health is unaffected")

print("registry ok")
