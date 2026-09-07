"""The GUI is one HTML file with no build step, so nothing catches a typo until someone opens it. This does:
  · the script parses (node, if present)
  · every element id the script references exists in the markup
  · every API path the page calls exists in app/main.py
  · every field it reads off /stats rows is a column of the stats view
  · anything the script hides with .hidden is not un-hidden by a display rule
Run: python3 tools/check_ui.py"""
import re
import shutil
import subprocess
import sys

h = open("app/static/index.html").read()
js = h[h.rindex("<script>") + 8: h.rindex("</script>")]
errs = []

if shutil.which("node"):
    r = subprocess.run(["node", "-e", "new Function(require('fs').readFileSync(0,'utf8'))"], input=js, capture_output=True, text=True)
    if r.returncode:
        errs.append("script does not parse: " + r.stderr.strip().splitlines()[-1][:120])

used = set(re.findall(r"\$\('#([a-zA-Z0-9_-]+)'\)", js)) | set(re.findall(r"getElementById\('([^']+)'\)", js))
have = set(re.findall(r'\bid="([a-zA-Z0-9_-]+)"', h))
for i in sorted(used - have):
    errs.append(f"script references #{i}, which is not in the markup")

main = open("app/main.py").read()
routes = set(re.findall(r'@app\.(?:get|post|put)\("(/[a-z_/-]*)"', main))   # paths may nest: /place/geojson
for p in sorted(set(re.findall(r"(?:api|fetch)\('(/[a-z_/-]+)", js))):
    if p not in routes:
        errs.append(f"page calls {p}, which app/main.py does not define")

# `hidden` is an attribute the UA styles as display:none, and ANY display rule of our own beats it. This has
# shipped twice: an empty orange act strip on every node with nothing to act on (.actstrip sets display:grid),
# and a broken-image box with its alt text on every node that had not fetched satellite data yet (#earth-img
# sets display:block). Both times the script had set .hidden correctly and the CSS quietly ignored it.
CSS = h[: h.index("</style>")] if "</style>" in h else ""
ids = dict(re.findall(r"const\s+(\w+)\s*=\s*\$\('#([a-zA-Z0-9_-]+)'\)", js))
ids.update(dict(re.findall(r"(\w+)\s*=\s*\$\('#([a-zA-Z0-9_-]+)'\)", js)))
hidden_ids = {ids[v] for v in re.findall(r"(\w+)\.hidden\s*=", js) if v in ids}
hidden_ids |= set(re.findall(r"\$\('#([a-zA-Z0-9_-]+)'\)\.hidden\s*=", js))
for i in sorted(hidden_ids):
    tag = re.search(rf'<(\w+)([^>]*\bid="{re.escape(i)}"[^>]*)>', h)
    if not tag:
        continue
    classes = re.findall(r"[\w-]+", (re.search(r'class="([^"]*)"', tag.group(2)) or re.match("", "")).group(1)) \
        if re.search(r'class="([^"]*)"', tag.group(2)) else []
    # selectors that could give this element a display, and the guards that would cancel it
    setters = [sel for sel in [f"#{i}"] + [f".{c}" for c in classes]
               if re.search(rf"(^|[,}}\s]){re.escape(sel)}\s*(,[^{{]*)?\{{[^}}]*display\s*:", CSS, re.M)]
    guarded = re.search(rf"(^|[,}}\s])#{re.escape(i)}\[hidden\]", CSS, re.M) or any(
        re.search(rf"(^|[,}}\s])\.{re.escape(c)}\[hidden\]", CSS, re.M) for c in classes)
    if setters and not guarded:
        errs.append(f"script hides #{i}, but {' and '.join(setters)} sets display: and nothing "
                    f"cancels it — add #{i}[hidden]{{display:none}}")

sql = open("init.sql").read()
stats = sql[sql.index("CREATE VIEW stats"):]
stats = stats[: stats.index(";")]
cols = set(re.findall(r"\bAS (\w+)", stats)) | {"sensor_id", "metric", "name", "local", "indoor", "kind", "scale", "lat", "lon"}
# `r` is a stats row inside .filter(r=>...) / .map(r=>...) callbacks; elsewhere it is a fetch Response
row_ctx = " ".join(re.findall(r"(?:filter|map|forEach|reduce)\(r=>[^;]{0,200}", js))
for f in sorted(set(re.findall(r"\br\.([a-z_0-9]+)", row_ctx))):
    if f not in cols and f not in ("key", "value", "label", "help", "secret", "set", "source", "group", "id", "cell", "state", "unit", "ts", "level", "text", "rule_id", "acted_at", "pack", "description", "name",
                                    "coverage_7d", "frozen_channels", "age_hours"):  # /trust
        errs.append(f"page reads r.{f}, which is not a column of the stats view")

print("\n".join(f"  x {e}" for e in errs) or "  GUI: script parses; every id, endpoint and field resolves; nothing hidden is un-hidden by CSS")
sys.exit(1 if errs else 0)
