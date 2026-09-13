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
# The page is three files: a skeleton, a renderer and a stylesheet. It used to be one, and every
# rule below was written against that one — so this is where they are told where to look now.
js = open("app/static/dashboard.js").read() if "src=\"static/dashboard.js\"" in h \
    else h[h.rindex("<script>") + 8: h.rindex("</script>")]
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
routes = set(re.findall(r'@app\.(?:get|post|put)\("(/[a-z_./{}-]*)"', main))   # paths may nest: /place/geojson
# app/issues/api.py is an APIRouter mounted with include_router, and this FastAPI version defers
# that — app.routes holds an _IncludedRouter with no .path, so nothing here can see /issues by
# importing. Read its decorators and put the router's own prefix back on the front.
_api = open("app/issues/api.py").read()
_prefix = (re.search(r'APIRouter\(prefix="([^"]+)"', _api) or [None, ""])[1]
routes |= {(_prefix + p) or "/" for p in re.findall(r'@router\.(?:get|post|put)\("([^"]*)"', _api)}
# `fetch('/x')`, and `get('/x')` — snapshot()'s own helper, which is how most of them are called
_called = set(re.findall(r"(?:api|fetch|get)\('(/[a-z_/.-]+)", js))
_called |= set(re.findall(r"[\"'`](/(?:earth|issues|actions|settings|packs|health|alerts|rho|report)[a-z_/.-]*)", js))
for p in sorted({x.rstrip("/") or "/" for x in _called}):
    if p not in routes:
        errs.append(f"page calls {p}, which app/main.py does not define")

# `hidden` is an attribute the UA styles as display:none, and ANY display rule of our own beats it. This has
# shipped twice: an empty orange act strip on every node with nothing to act on (.actstrip sets display:grid),
# and a broken-image box with its alt text on every node that had not fetched satellite data yet (#earth-img
# sets display:block). Both times the script had set .hidden correctly and the CSS quietly ignored it.
CSS = h[: h.index("</style>")] if "</style>" in h else open("app/static/dashboard.css").read()
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
# strip line comments first: `-- rolling stats are for sensors only;` sits inside the view and ends in a
# semicolon, which cut the view off at its SELECT list and would silently reject any column added below it.
sql = "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())
stats = sql[sql.index("CREATE VIEW stats"):]
stats = stats[: stats.index(";")]
cols = set(re.findall(r"\bAS (\w+)", stats)) | {"sensor_id", "metric", "name", "local", "indoor", "kind", "scale", "lat", "lon"}
# `r` is a stats row inside .filter(r=>...) / .map(r=>...) callbacks; elsewhere it is a fetch Response
row_ctx = " ".join(re.findall(r"(?:filter|map|forEach|reduce)\(r=>[^;]{0,200}", js))
for f in sorted(set(re.findall(r"\br\.([a-z_0-9]+)", row_ctx))):
    if f not in cols and f not in ("key", "value", "label", "help", "secret", "set", "source", "group", "id", "cell", "state", "unit", "ts", "level", "text", "rule_id", "acted_at", "pack", "description", "name",
                                    "coverage_7d", "frozen_channels", "age_hours",   # /trust
                                    "km", "network", "pm25", "reporting", "silent_minutes", "last_ts"):  # /nearby  (indoor is a stats column)
        errs.append(f"page reads r.{f}, which is not a column of the stats view")


# ---------------------------------------------------------------------------------------------------------------
# The visual language. Six of these shipped to real households and were found by looking, not by a check
# (planetai-design/decisions/design-log.md, 7 Sep 2026). Each rule below is one of them, so each one now costs a
# lint failure instead of a design round. Break one on purpose before you trust it.
#
#   colour is a role, never decoration:  green = a response, a loop closed, an act taken · red = a signal that got
#   worse or crossed a line · blue = data, identity, a selected cell · orange = what only the satellite knows.
#   Anything else on this page is ink.

def strip_comments(text):
    """Colours and radii inside /* */ and // comments are documentation, not paint."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", text)

CSS_SRC = strip_comments(CSS)
JS_SRC = strip_comments(js)
# the markup. It used to be "whatever follows the inline <style>"; the skeleton has no inline
# style at all, and an empty BODY silently switched off every rule that reads the markup.
BODY = strip_comments(h[h.index("</style>"):] if "</style>" in h else h)
RULES = [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS_SRC)]

def rule_width(body):
    m = re.search(r"(?<!max-)(?<!min-)\bwidth\s*:\s*(\d+(?:\.\d+)?)px", body)
    return float(m.group(1)) if m else None

# --- 1. regular hexagons as decoration --------------------------------------------------------------------------
# The one shape this language does not permit. A hexagon glyph small enough to be a bullet still carries meaning
# (an alert's level, a sensor's state) and is kept; the design kit's own hexagon check skips small cells for the
# same reason. Above this it is wallpaper — .bighex, .bighex2 and .wall .halo all were.
HEX_GLYPH_MAX_PX = 24
for sel, body in RULES:
    for pts in re.findall(r"clip-path\s*:\s*polygon\(([^)]*)\)", body):
        if len(pts.split(",")) != 6:
            continue
        widths = [rule_width(b) for s2, b in RULES if s2 == sel or s2.endswith(" " + sel.lstrip(".").join(["."] * 0) + sel) or re.search(rf"(^|[\s,]){re.escape(sel)}(\s|,|$)", s2)]
        widths = [w for w in widths if w is not None]
        relative = any(re.search(r"(?<!max-)(?<!min-)\bwidth\s*:[^;}]*(%|vw|vmin|vh|min\(|max\(|clamp\()", b)
                       for s2, b in RULES if re.search(rf"(^|[\s,]){re.escape(sel)}(\s|,|$)", s2))
        biggest = max(widths) if widths else None
        if relative or (biggest is not None and biggest > HEX_GLYPH_MAX_PX):
            errs.append(f"{sel} is a six-sided clip-path wider than {HEX_GLYPH_MAX_PX}px — a regular hexagon as "
                        f"decoration. The ground is static/node-ground.svg, which is computed geometry.")
        elif biggest is None:
            errs.append(f"{sel} is a six-sided clip-path and no rule gives it a width, so nothing here can tell a "
                        f"bullet from wallpaper — give it a width under {HEX_GLYPH_MAX_PX}px or delete it")

# --- 2. the website palette --------------------------------------------------------------------------------------
# fab.city's palette, not the master brand's. --hue:#7AC943 as a general accent was violation 3.
WEBSITE_PALETTE = {
    "#7AC943": "web-green",
    "#3FA9F5": "web-blue",
    "#E8873A": "the old web-orange (the satellite layer uses #FF931E)",
}
PALETTE_EXCEPTIONS = {}       # {"#XXXXXX": "why, and who decided"} — empty on purpose. Add a reason, not a colour.
for hexv, name in WEBSITE_PALETTE.items():
    if hexv in PALETTE_EXCEPTIONS:
        continue
    for src, where in ((CSS_SRC, "the stylesheet"), (JS_SRC, "the script"), (BODY, "the markup")):
        if re.search(hexv, src, re.I):
            errs.append(f"{hexv} ({name}) is in {where}. This page uses roles, not the website palette: "
                        f"green a response, red a line crossed, blue data, orange satellite-only, else ink.")

# --- 3. gradients and glows ---------------------------------------------------------------------------------------
for fn in ("linear-gradient", "radial-gradient", "conic-gradient"):
    for src, where in ((CSS_SRC, "the stylesheet"), (JS_SRC, "the script"), (BODY, "the markup")):
        if fn + "(" in src:
            errs.append(f"{fn}() is in {where}. No gradients and no glows: .glow.a and .glow.b were two "
                        f"drifting radial-gradients behind the whole page.")

# --- 4. radius -----------------------------------------------------------------------------------------------------
# A control is at most 8px and a card at most 18px. The dashboard predates the rule and its pills and 30px cards
# are recorded below with the date they were counted. The list may shrink. It may not grow: a selector that is not
# on it and breaks the limit fails, which is what stops the next .prov being born.
CONTROL = re.compile(r"button|input|select|btn|chip|tag|prov|switch|nav|toast|arr|exit|tip|pill|\ba:")
RADIUS_LEGACY = {           # counted 2026-09-07, at v0.35. 16 controls, 5 cards.
    "nav.views", "nav.views button", ".chip", ".earthctl button", ".btn", ".plan-legend button", ".tabs button",
    ".field input,.field select", ".switch .tr", ".gate input", ".tag", ".wall .exit", ".arr button", ".arrbar",
    ".arrbar select", ".toast", ".card", ".r1", ".r2", ".r3", ".r4",
}
for sel, body in RULES:
    m = re.search(r"border-radius\s*:\s*([^;}]+)", body)
    if not m:
        continue
    vals, w = m.group(1), rule_width(body)
    if "%" in vals:
        if w is None or w <= 24:      # a dot or a ring, not a pill
            continue
        biggest = 999.0
    else:
        px = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)px", vals)]
        if not px:
            continue
        biggest = max(px)
    kind, limit = ("a control", 8) if CONTROL.search(sel) else ("a card", 18)
    key = re.sub(r"\s*,\s*", ",", " ".join(sel.split()))
    if biggest > limit and key not in RADIUS_LEGACY:
        errs.append(f"{sel} rounds {kind} to {biggest:g}px; the limit is {limit}px. If this is deliberate and old, "
                    f"it belongs in RADIUS_LEGACY with today's date — but that list is meant to shrink.")

# --- 5. provenance is ink -------------------------------------------------------------------------------------------
# A pill in a role colour reads as a verdict on the number beside it. Provenance says where a number came from and
# nothing about whether it is good. Ink family and currentColor only.
# The layer's names (planetai-design/references/planetai-layer.md). The page used to call these
# --red/--green/--blue/--orange; those four no longer exist, so a rule written against them could
# never fire again. Both sets are listed: a fork still on the old names is still checked.
ROLE_TOKENS = ("--signal-worse", "--rings", "--loop-closed", "--cells", "--satellite-only",
               "--red", "--green", "--blue", "--orange")
PAINT = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|" + "|".join(re.escape(t) for t in ROLE_TOKENS))
for sel, body in RULES:
    if "prov" in sel and PAINT.search(body):
        errs.append(f"{sel} carries a colour ({PAINT.search(body).group(0)}). Provenance is ink only — glyph, "
                    f"then one of live / partial / model / cached / example. A pill must never look like a verdict.")
for tag in re.finditer(r"<[^>]*\b(?:class|id)=\"[^\"]*prov[^\"]*\"[^>]*>", BODY):
    style = re.search(r"style=\"([^\"]*)\"", tag.group(0))
    if style and PAINT.search(style.group(1)):
        errs.append(f"an element with prov in its class or id carries an inline colour: {style.group(1)[:60]}")

# --- 6. orange is the satellite and nothing else -----------------------------------------------------------------
# "What only the satellite knows." It was the act button (violation 6), every link hover and the arrange bar.
# #DB7200 is the paper register's satellite orange (3.02:1 on paper); #FF931E is the dark
# register's. Neither may appear away from the satellite layer, and neither may cross registers —
# that last part is planetai-theme.css's own guard, checked by tools/check_theme.py.
ORANGE_DEF = re.compile(r"--(?:orange|satellite-only)\s*:\s*#(?:FF931E|DB7200)|ORANGE\s*=\s*'#FF931E'")
SATELLITE = re.compile(r"satellite|\bsat\b|only the satellite", re.I)
for i, line in enumerate(strip_comments(h + "\n" + CSS_SRC + "\n" + JS_SRC).splitlines(), 1):
    if not re.search(r"--orange|--satellite-only|#FF931E|#DB7200|rgba\(255,\s*147,\s*30|\bORANGE\b", line):
        continue
    # The exemption is "this line is about the satellite layer". The TOKEN is called
    # --satellite-only, so it contains that word itself and would exempt every use of it — the rule
    # would pass anything as long as it used the token, which is exactly what it is guarding.
    # Test the line with the token's own name taken out of it.
    context = line.replace("--satellite-only", "").replace("satellite-only", "")
    if ORANGE_DEF.search(line) or SATELLITE.search(context):
        continue
    errs.append(f"line {i} paints with orange away from the satellite layer: {line.strip()[:80]}")

# --- 7. the dark register --------------------------------------------------------------------------------------
# Fab Blue #20388D on ink #171717 measures 1.72:1 and is invisible; the dark register uses #7FA5E8 at 7.21:1,
# which on paper #F9F5F2 is 2.29:1 and may never appear there. Measured, not assumed — design-log A5.
DARK_DOC = re.search(r"<html[^>]*data-theme=\"dark\"", h) is not None
dark_sel = re.compile(r"\[data-theme=[\"']dark[\"']\]|\.variant-dark")
for sel, body in RULES:
    in_dark = DARK_DOC or bool(dark_sel.search(sel))
    if in_dark and re.search(r"#20388D", body, re.I):
        errs.append(f"{sel} uses Fab Blue #20388D in the dark register, where it measures 1.72:1 on ink and "
                    f"cannot be seen. The dark register's blue is #7FA5E8.")
    if not in_dark and re.search(r"#7FA5E8", body, re.I):
        errs.append(f"{sel} uses the lifted blue #7FA5E8 outside the dark register. On paper it is 2.29:1.")
if not DARK_DOC:
    for src, where in ((CSS_SRC, "the stylesheet"), (JS_SRC, "the script"), (BODY, "the markup")):
        if re.search(r"#7FA5E8", src, re.I):
            errs.append(f"#7FA5E8 is in {where}, but <html> does not declare data-variant=\"dark\", so nothing "
                        f"says this page is the dark register.")
elif re.search(r"#20388D", CSS_SRC + JS_SRC + BODY, re.I):
    errs.append("#20388D is in this page, which declares itself the dark register. Use #7FA5E8.")

# --- 8. what index.html asks the node for --------------------------------------------------------------------------
# The page is one HTML file, and the two companions it does reference (the H3 ground, the mono) are served by an
# allowlist in app/main.py. A src the node does not serve is a silent 404 and a missing ground on every node.
served = set(re.findall(r'"([a-zA-Z0-9._-]+)":\s*\(', main[main.find("COMPANIONS = {"):] if "COMPANIONS = {" in main else ""))
# Everything the DOCUMENT asks for, and everything the RENDERER writes into the document. Both are
# relative to "/", so both must say static/<name>. A url() inside app/static/*.css is relative to
# /static/ already, where a bare name is the correct form — those are rule 9's.
#
# The renderer half matters: the hero's ground, the sign sprite and every satellite frame are
# written by dashboard.js, so scanning only index.html checked almost nothing.
_refs = set(re.findall(r'src="(?!https?:|data:|#)([^"]+)"', h))
_refs |= set(re.findall(r'<link[^>]+href="(?!https?:|data:|#)([^"]+)"', h))
# Any literal src/href the renderer writes — NOT only the ones already under static/, or a
# reference that drops the prefix drops out of the check with it, which is the mistake this line
# was written with. Template expressions (src="${...}") are the satellite frames and are routes,
# not assets; they are excluded by the character class.
_refs |= set(re.findall(r'src="([^"${}]+)"', js))
_refs |= {m.split("#")[0] for m in re.findall(r'href="([^"${}]+)"', js) if "/" in m}
# A src whose PATH is literal and whose query is a template: the ground asks for its register with
# `?variant=${ctx.register}`. Without this the whole reference drops out of the check, because the
# character class above excludes `${}` — which is the same way a reference dropping its prefix
# dropped out, two comments up. The asset is the path; the query is not part of the allowlist.
_refs |= set(re.findall(r'src="([^"${}?]+)\?[^"]*"', js))
for ref in sorted(_refs):
    ref = ref.strip("'\"").split("?")[0]
    if not ref.startswith("static/"):
        errs.append(f"the page loads {ref}, which is not under static/ — app/main.py serves nothing else")
    elif ref[len("static/"):] not in served:
        errs.append(f"the page loads {ref}, which app/main.py's COMPANIONS allowlist does not serve")

# --- 9. the stylesheets the page loads ------------------------------------------------------------
# Everything under app/static/*.css is served to a household LAN by the COMPANIONS allowlist in
# app/main.py, and a node may have no route out at all. Two ways that goes wrong silently: a url()
# naming a file nothing serves (no typography, no error), and an @import to a CDN (works on the
# laptop it was written on, dead in the house). tokens.css arrived with both.
import glob as _glob
# The one dead reference this project has decided to live with, named exactly, in exactly one file.
# planetai-theme.css is generated from planetai-design/references/planetai-layer.md and is copied
# here byte-for-byte — tools/check_theme.py holds it to the design repo. Its @font-face names
# `fonts/jetbrains-mono-latin.woff2`, a NESTED path, and /static/<name> takes a name and not a path
# on purpose, on a port that answers a household LAN. So that one request 404s. It costs nothing
# but the request: dashboard.css declares the same family at the flat name the node does serve.
# Making it resolve means a path parameter reaching the filesystem, which is the trade that was
# weighed and refused. Do not widen this to a pattern.
DEAD_BY_DECISION = {("planetai-theme.css", "fonts/jetbrains-mono-latin.woff2")}
for css_path in sorted(_glob.glob("app/static/*.css")):
    body = strip_comments(open(css_path).read())
    name = css_path.split("/")[-1]
    for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)", body):
        ref = ref.strip()
        if ref.startswith("data:"):
            continue
        if ref.startswith(("http://", "https://", "//")):
            errs.append(f"{name} loads {ref[:60]} from the network. A node serves this page on a LAN "
                        f"that may have no route out; bundle it and put it in COMPANIONS.")
        elif ref not in served and (name, ref) not in DEAD_BY_DECISION:
            errs.append(f"{name} loads {ref}, which app/main.py's COMPANIONS allowlist does not serve")
    for imp in re.findall(r"@import\s+(?:url\()?\s*['\"]([^'\"]+)", body):
        if imp.startswith(("http://", "https://", "//")):
            errs.append(f"{name} @imports {imp[:60]} from the network — same reason.")
        elif imp not in served:
            errs.append(f"{name} @imports {imp}, which COMPANIONS does not serve")

print("\n".join(f"  x {e}" for e in errs) or
      "  GUI: script parses; every id, endpoint, field and asset resolves; nothing hidden is un-hidden by CSS;\n"
      "       no decorative hexagon, no website palette, no gradient, no rounded verdict, orange only on the\n"
      "       satellite, and the dark register's blue is the one that can be seen")
sys.exit(1 if errs else 0)
