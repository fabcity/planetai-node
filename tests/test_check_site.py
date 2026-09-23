"""tools/check_site.py passes on a page that matches, and fails on each kind of drift it exists for."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = [sys.executable, str(ROOT / "tools/check_site.py")]
PURPOSE = ("Its purpose is fixed: clean air, water and soil for the people and the other living things "
           "around each node.")
GOOD = f"""export const PURPOSE = '{PURPOSE}';
export const RHO = {{
  asked: 137, answered: 29, rho: 0.212, medianMinutes: 112,
  window: '30 days', asOf: '{{asof}}', prov: 'cached',
  label: 'share of act-level alerts answered',
}};
export const RELEASE = {{
  tag: 'v0.73', count: 87,
  packs: {{ total: {{packs}}, data: {{data}}, code: {{code}} }}, languages: ['English', 'Bahasa Indonesia', 'Spanish'], docsPages: {{docs}},
}};
"""
sys.path.insert(0, str(ROOT / "tools"))
import check_site  # noqa: E402
import datetime as dt  # noqa: E402

f = check_site.node_facts()
today = dt.date.today().isoformat()


def run(js, *extra):
    d = Path(tempfile.mkdtemp())
    (d / "web/src").mkdir(parents=True)
    (d / "web/src/data.js").write_text(js)
    r = subprocess.run(TOOL + ["--site", str(d), *extra], capture_output=True, text=True, cwd=ROOT)
    shutil.rmtree(d)
    return r.returncode, r.stdout + r.stderr


good = GOOD.replace("{asof}", today).replace("{packs}", str(f["packs"])).replace(
    "{data}", str(f["data"])).replace("{code}", str(f["code"])).replace("{docs}", str(f["docs"]))
rc, out = run(good, "--version", "v0.73")
assert rc == 0, out
print("a page that matches passes")
for what, js, extra, needle in [
    ("another release", good, ["--version", "v0.74"], "says v0.73"),
    ("a pack count", good.replace(f"total: {f['packs']}", f"total: {f['packs'] + 1}"), [], "packs"),
    ("a language", good.replace(", 'Spanish'", ""), [], "languages"),
    ("the docs count", good.replace(f"docsPages: {f['docs']}", "docsPages: 40"), [], "documentation pages"),
    ("the purpose", good.replace("clean air, water and soil", "clean air"), [], "PURPOSE"),
    ("a stale rho at release", good.replace(today, "2026-01-01"), ["--version", "v0.73"], "days ago"),
    ("rho's name", good.replace("alerts answered", "alerts acted on"), [], "answered"),
]:
    rc, out = run(js, *extra)
    assert rc != 0 and needle in out, f"{what}: expected a failure naming '{needle}', got rc={rc}\n{out}"
    print(f"fails on {what}")
rc, out = run("export const X = 1;")
assert rc != 0 and "could not find" in out, out
print("a page whose shape changed is reported, not guessed")
