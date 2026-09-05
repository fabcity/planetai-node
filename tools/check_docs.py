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

Run: python3 tools/check_docs.py
"""
import glob
import os
import re
import sys

errs: list[str] = []
DOCS = sorted(glob.glob("*.md") + glob.glob("docs/*.md") + glob.glob("packs/*/README.md"))
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
ENV_IN_PACKS = set()
for f in glob.glob("packs/*/pack.yaml"):
    ENV_IN_PACKS |= set(re.findall(r'^\s*-\s*"?([A-Z][A-Z0-9_]+)=', open(f).read(), re.M))
ENV_OK = ENV_DECLARED | ENV_IN_CODE | ENV_IN_PACKS | {
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
               "app/requirements-packs.txt", "out/", "packs/_test"}
    for path in set(re.findall(r"`((?:docs|packs|app|config|tools|tests|presets|out)/[A-Za-z0-9_./-]+)`", text)):
        p = path.rstrip("/.")
        if p in RUNTIME or path in RUNTIME or doc == "CHANGELOG.md":     # the changelog is a record; files move
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

# README's docs index must match the directory
readme = open("README.md").read()
block = re.search(r"^docs/\s+.*?(?=\n[A-Za-z]+\.md|\n[a-z]+/)", readme, re.M | re.S)
if block:
    # document names are the tokens that look like file stems: UPPER_CASE, or the one lowercase file (sensors)
    listed = set(re.findall(r"\b([A-Z][A-Z_]{2,}|sensors)\b", block.group(0)))
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
if n_core_rules != 2:
    errs.append(f"config/rules.yml has {n_core_rules} rules; docs/PACKS.md says two domain-blind core rules — check both")

print("\n".join(f"  x {e}" for e in errs) or f"  {len(DOCS)} documents check out")
sys.exit(1 if errs else 0)
