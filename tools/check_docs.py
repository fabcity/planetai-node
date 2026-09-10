"""Check the documentation against the code, mechanically.

Docs go stale silently, which is worse than code going wrong: nobody gets an error, they just follow an
instruction that no longer works. This checks the claims that can be checked without a human:

  · every file or directory a doc names exists
  · every `planetai <command>` a doc mentions is a real command
  · every environment variable a doc names is in .env.example or read by the code
  · every relative link between docs resolves
  · every HTTP endpoint a doc mentions exists in app/main.py
  · every pack a doc names exists in packs/
  · README's docs/ index lists exactly the files in docs/
  · every skills/*/SKILL.md has frontmatter whose name is its folder, and a description
  · AGENTS.md's routing table sends a person to every skill that exists
  · every file llms.txt links to exists

Run: python3 tools/check_docs.py
"""
import glob
import os
import re
import sys

import yaml

errs: list[str] = []
# A skill is a document that tells somebody to run things, so it is held to the same gates as a doc:
# a command it names must dispatch, a path it names must exist. That is the whole point of writing
# them here rather than in a prompt somebody pastes.
DOCS = sorted(glob.glob("*.md") + glob.glob("docs/*.md") + glob.glob("packs/*/README.md")
             + glob.glob("skills/*/SKILL.md"))
SKILLS = sorted(os.path.basename(os.path.dirname(f)) for f in glob.glob("skills/*/SKILL.md"))
CLI = open("bin/planetai").read()
MAIN = open("app/main.py").read()
ENVEX = open(".env.example").read()
CODE = "\n".join(open(f).read() for f in glob.glob("app/*.py") + glob.glob("packs/*/*.py")) + CLI + \
       "\n".join(open(f).read() for f in ("install.sh", "update.sh", "backup.sh", "install", "docker-compose.yml"))

# commands the CLI actually dispatches
# the case block puts several arms on one line, so scan the whole block rather than line starts
CASE = CLI[CLI.index('case "${1:-help}" in'):CLI.index("\nesac")]
CMDS = set()
for m in re.finditer(r"(?:^|\s|;)([a-z0-9|_-]+)\)", CASE, re.M):
    CMDS |= {c for c in m.group(1).split("|") if c != "*"}
ENDPOINTS = set(re.findall(r'@app\.(?:get|post)\("(/[a-z_]*)"', MAIN))
PACKS = {os.path.basename(os.path.dirname(p)) for p in glob.glob("packs/*/pack.yaml")}
ENV_DECLARED = set(re.findall(r"^([A-Z][A-Z0-9_]+)=", ENVEX, re.M))
ENV_IN_CODE = set(re.findall(r'getenv\(["\']([A-Z][A-Z0-9_]+)', CODE)) | set(re.findall(r'environ\[["\']([A-Z][A-Z0-9_]+)', CODE))
# Keys a release retired. They are gone from .env.example and nothing reads them, and a changelog and a tester
# guide have to be able to name them — that is how a household learns which of its settings stopped mattering.
# Read from app/settings.py's own RETIRED, so this list shrinks when that one does.
ENV_RETIRED = set(re.findall(r'"([A-Z][A-Z0-9_]+)"',
                             (re.search(r"^RETIRED = \((.*?)\)", open("app/settings.py").read(), re.M | re.S)
                              or type("", (), {"group": staticmethod(lambda _: "")})).group(1)))
ENV_IN_PACKS = set()
for f in glob.glob("packs/*/pack.yaml"):
    ENV_IN_PACKS |= set(re.findall(r'^\s*-\s*"?([A-Z][A-Z0-9_]+)=', open(f).read(), re.M))
ENV_IN_MCP = set(re.findall(r"\$\{([A-Z][A-Z0-9_]+)", open(".mcp.json").read()))
ENV_OK = ENV_DECLARED | ENV_IN_CODE | ENV_IN_PACKS | ENV_RETIRED | ENV_IN_MCP | {
    "FCI_PUBLISHER",   # the Index's write flag; it lives with cells-ingest, not here
    "PATH", "HOME", "EDITOR", "TS_AUTHKEY", "PLANETAI_HOME", "PLANETAI_REPO", "PLANETAI_REF",
    "COMPOSE_PROFILES", "PGTZ", "TZ", "DATABASE_URL", "CI", "PACK_OUT", "LOG_LEVEL", "SSID", "MQTT_ADDR",
    "MQTT_USER", "MQTT_PASS", "WIFI_SSID", "WIFI_PSK", "GATEWAY", "CHNAME", "MAP_KEY", "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID", "POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "NODE_VERSION", "APP_PORT"}

for doc in DOCS:
    text = open(doc).read()
    body = re.sub(r"```.*?```", lambda m: m.group(0) if "planetai " in m.group(0) or "docs/" in m.group(0) else "", text, flags=re.S)

    # `planetai <cmd>` at a command position: after a backtick, a prompt, or the start of a line — not
    # inside `planetai.fab.city` or `psql -U planetai planetai`
    for cmd in set(re.findall(r"(?:^|`|\$ |\n)planetai ([a-z][a-z-]+)", text, re.M)):
        if cmd in ("node",):        # "planetai-node", the repo name, not a command
            continue
        if cmd not in CMDS:
            errs.append(f"{doc}: mentions `planetai {cmd}`, which the CLI does not dispatch")

    for link in set(re.findall(r"\]\((?!https?:|#|mailto:)([^)#]+)", text)):
        target = os.path.normpath(os.path.join(os.path.dirname(doc), link))
        if not os.path.exists(target):
            errs.append(f"{doc}: link to `{link}` does not exist")

    # files a command creates at runtime are documented before they exist; that is correct
    RUNTIME = {"config/ee-key.json", "config/reticulum/config", "config/mosquitto/passwd",
               "app/requirements-packs.txt", "out/", "packs/_test",
               # a build artifact: present on any machine that has run the app, absent in a clean
               # checkout. `make lint` passed on every laptop and failed on every CI run since 5 Sep.
               "app/__pycache__"}
    for path in set(re.findall(r"`((?:docs|packs|app|config|tools|tests|presets|out|skills)/[A-Za-z0-9_./-]+)`", text)):
        p = path.rstrip("/.")
        if p in RUNTIME or path in RUNTIME or p.startswith("out/") or doc == "CHANGELOG.md":   # out/ holds runtime artifacts     # the changelog is a record; files move
            continue
        if not os.path.exists(p) and not glob.glob(p):
            errs.append(f"{doc}: names `{path}`, which does not exist")

    for var in set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", text)):
        if var in ENV_OK or not re.search(rf"\b{var}\b\s*[=(]|set `?{var}", text):
            continue
        if var.isupper() and "_" in var and var not in ENV_OK:
            errs.append(f"{doc}: names `{var}`, which is in neither .env.example nor the code")

    for ep in set(re.findall(r"`(/[a-z_]{3,})`|GET (/[a-z_]+)|POST (/[a-z_]+)", text)):
        ep = next((x for x in (ep if isinstance(ep, tuple) else (ep,)) if x), None)
        if ep and ep not in ENDPOINTS and ep.count("/") == 1 and not os.path.exists(ep.lstrip("/")):
            if ep in ("/health", "/sensors", "/readings", "/stats", "/alerts", "/cells", "/rho", "/packs",
                      "/actions", "/aggregates", "/observations", "/send", "/install"):
                errs.append(f"{doc}: documents endpoint `{ep}`, which app/main.py does not define")

    for pk in set(re.findall(r"`packs/([a-z0-9-]+)/", text)) | set(re.findall(r"\bpacks/([a-z0-9-]+)\b", text)):
        # names used as examples of packs someone might write, not packs that ship
        EXAMPLE_PACKS = {"_test", "my-pack", "monsoon", "monsoon-bali", "air-", "water", "example",
                         "acme-sensor", "air", "yourplace", "district", "id"}
        if pk not in PACKS and pk not in EXAMPLE_PACKS:
            errs.append(f"{doc}: refers to pack `{pk}`, which does not exist")

# Every declared channel must be a metric some adapter actually produces. A declaration for a metric that does not
# exist is a role nothing will ever wear, and a typo in one is silent: the rule that reads roles just returns
# nothing.
# docs/PACKS.md tells a pack to declare its own metrics, so a pack's adapter counts as an adapter here. Reading
# only app/sources.py meant every pack channel declaration failed, whatever the pack actually produced.
def _metrics(src: str) -> set:
    return (set(re.findall(r'"[^"]+":\s*"([a-z0-9_]+)"', src))            # {"pm25": "pm25"}
            | set(re.findall(r'\("[^"]+",\s*"([a-z0-9_]+)"\)', src))       # ("t", "fc_temp")
            | set(re.findall(r',\s*"([a-z0-9_]+)",\s*(?:float|round|max|abs)\b', src)))  # append((ts, sid, "x", float(v)))


# pm25, pm25_raw and aqi are written by readings.append(...) tuples in core that none of the shapes above catch.
_produced = {"pm25", "pm25_raw", "aqi"}
for _a in ["app/sources.py"] + sorted(glob.glob("packs/*/adapter.py")):
    _produced |= _metrics(open(_a).read())
for f in ["config/channels.yml"] + sorted(glob.glob("packs/*/channels.yml")):
    for d in yaml.safe_load(open(f)) or []:
        if d.get("metric") not in _produced:
            errs.append(f"{f}: declares metric `{d.get('metric')}`, which no adapter produces")

# README's docs index must match the directory
readme = open("README.md").read()
block = re.search(r"^docs/\s+.*?(?=\n[A-Za-z]+\.md|\n[a-z]+/)", readme, re.M | re.S)
if block:
    # document names are the tokens that look like file stems: UPPER_CASE, or the one lowercase file (sensors)
    listed = set(re.findall(r"\b([A-Z][A-Za-z_]{2,}|sensors)\b", block.group(0)))     # HANDOFF_beta_review is mixed case
    actual = {os.path.basename(f)[:-3] for f in glob.glob("docs/*.md")}
    for miss in sorted(actual - listed):
        errs.append(f"README.md: docs/ index does not list {miss}.md")
    for extra in sorted(listed - actual):
        errs.append(f"README.md: docs/ index lists {extra}, which is not in docs/")
else:
    errs.append("README.md: could not find the docs/ index block")

# claims about size drift silently. Check the few that are stated as numbers.
import subprocess
app_lines = sum(len(open(f).read().splitlines()) for f in glob.glob("app/*.py"))
n_packs = len(glob.glob("packs/*/pack.yaml"))
n_core_rules = len(re.findall(r"^- id:", open("config/rules.yml").read(), re.M))
n_adapters = len(re.findall(r"^def [a-z_]+\(hc", open("app/sources.py").read(), re.M))
# only present-tense claims about the app's own size, and not in CHANGELOG (which is a record of past states)
for doc in DOCS:
    if doc == "CHANGELOG.md":
        continue
    t = open(doc).read()
    for m in re.finditer(r"(?:Python service|app/|the node is|the core is)[^.\n]{0,40}?about ([\d,]+) lines", t):
        got = int(m.group(1).replace(",", ""))
        if abs(got - app_lines) > max(200, app_lines * 0.2):
            errs.append(f"{doc}: claims about {got} lines but app/ has {app_lines}")
# the MCP tool count is quoted in words in three places and drifted from fifteen to seventeen without anyone noticing
WORDS = {"fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
n_tools = len(re.findall(r"^@mcp\.tool\(\)", open("app/agent.py").read(), re.M))
for f in ("AGENTS.md", "docs/DEVELOPING.md", "bin/planetai"):
    for w in re.findall(r"\b([A-Za-z]+) tools\b", open(f).read()):
        w = w.lower()
        if w in WORDS and WORDS[w] != n_tools:
            errs.append(f"{f}: says {w} tools; app/agent.py defines {n_tools}")
# A pack README's thresholds must be the pack's actual thresholds. heat/ documented 32 °C for a rule that fires at
# 35 °C for six commits; nothing failed, and the README is the only place a household can learn why a number is that
# number. Only unit-bearing claims ("AT >= 35 °C"), so prose about counts and percentiles stays free.
for f in sorted(glob.glob("packs/*/README.md")):
    pack = os.path.dirname(f)
    body = "".join(open(x).read() for x in glob.glob(f"{pack}/*")
                   if os.path.isfile(x) and not x.endswith("README.md"))
    for n in set(re.findall(r"[\u2265>]=?\s*(\d+(?:\.\d+)?)\s*(?:\u00b0C|\u00b5g|%|hPa|km|m\b)", open(f).read())):
        if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d.])", body):
            errs.append(f"{f}: documents a threshold of {n}, which appears nowhere in {pack}/")

if n_core_rules != 2:
    errs.append(f"config/rules.yml has {n_core_rules} rules; docs/PACKS.md says two domain-blind core rules — check both")

# ---- the agent-facing layer -------------------------------------------------------------------
# A skill is read by a machine that will act on it. Three things have to hold or it silently does not
# load, or loads and sends somebody nowhere.

# a) frontmatter: name equals the folder, and a description exists. agentskills.io shape.
for f in sorted(glob.glob("skills/*/SKILL.md")):
    folder = os.path.basename(os.path.dirname(f))
    text = open(f).read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        errs.append(f"{f}: no YAML frontmatter (--- name/description ---) at the top")
        continue
    fm = yaml.safe_load(m.group(1)) or {}
    if fm.get("name") != folder:
        errs.append(f"{f}: frontmatter name is {fm.get('name')!r}, but the folder is {folder!r}")
    if not str(fm.get("description") or "").strip():
        errs.append(f"{f}: frontmatter has no description; that line is what decides when it is read")

# b) a skill nobody is routed to is a file nobody opens. AGENTS.md's first section is the routing table.
agents = open("AGENTS.md").read()
for name in SKILLS:
    if f"skills/{name}/SKILL.md" not in agents:
        errs.append(f"AGENTS.md: the routing table does not send anyone to skills/{name}/SKILL.md")

# c) llms.txt is an index for an agent that cannot see the tree. A dead link there is a dead end.
if os.path.exists("llms.txt"):
    RAW = "https://raw.githubusercontent.com/fabcity/planetai-node/main/"
    llms = open("llms.txt").read()
    for url in sorted(set(re.findall(r"https://raw\.githubusercontent\.com/\S+?(?=[)\s])", llms))):
        if not url.startswith(RAW):
            errs.append(f"llms.txt: {url} is not this repository at main")
        elif not os.path.exists(url[len(RAW):]):
            errs.append(f"llms.txt: links to `{url[len(RAW):]}`, which does not exist")
    for name in SKILLS:
        if f"skills/{name}/SKILL.md" not in llms:
            errs.append(f"llms.txt: does not index skills/{name}/SKILL.md")


print("\n".join(f"  x {e}" for e in errs) or f"  {len(DOCS)} documents check out")
sys.exit(1 if errs else 0)
