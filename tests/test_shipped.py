"""Every feature the CHANGELOG and docs claim must exist in the files. On 5 September two versions shipped with edit
blocks that failed silently: the loop landed, the compose service, settings, GUI tab, CLI command and .env keys did not,
and lint passed because nothing inconsistent was present. This test names each artifact a version promised."""
import re
import yaml

compose = yaml.safe_load(open("docker-compose.yml"))
settings = open("app/settings.py").read()
cli = open("bin/planetai").read()
env = open(".env.example").read()
gui = open("app/static/index.html").read()
main = open("app/main.py").read()

# v0.17 storage
assert "${DATA_DIR:-db}" in open("docker-compose.yml").read(), "compose: DATA_DIR volume var"
assert "ipfs" in compose["services"] and "ipfs" in compose["services"]["ipfs"].get("profiles", []), "compose: ipfs profile"
for k in ("BACKUP_KEEP", "BACKUP_REMOTE", "EXPORT_ENABLED", "IPFS_PUBLISH", "DATA_DIR"):
    assert re.search(rf"^{k}=", env, re.M), f".env.example: {k}"
assert "def export(" in main and "cmd_storage()" in cli and "cmd_ipfs()" in cli
# v0.18 NAS pull
assert "def list_backups" in main and "./backups:/app/backups:ro" in open("docker-compose.yml").read()
assert '"BACKUP_TOKEN"' in settings and "BACKUP_TOKEN" in open("update.sh").read()
# v0.20 agents
assert "_mcp_auth" in main and "def settings_raw" in main and "x_agent" in main
assert "JSON -eq 1" in cli and "--answers" in cli and "cmd_agent()" in cli
assert "sc-user" in open("install.sh").read()
# v0.21/22 local model and the ladder
assert "agent" in compose["services"] and compose["services"]["agent"]["command"][-1] == "agent_loop.py", "compose: agent service"
for k in ("AGENT_PREFER", "AGENT_REMOTE_URL", "AGENT_REMOTE_MODEL", "AGENT_REMOTE_KEY", "AGENT_ONLINE_URL", "AGENT_ONLINE_MODEL", "AGENT_ONLINE_KEY"):
    assert f'"{k}"' in settings, f"settings.py: {k}"
    assert re.search(rf"^{k}=", env, re.M), f".env.example: {k}"
assert "agent:['Model'" in gui, "gui: Model tab"
assert "cmd_agent_local()" in cli and "local) cmd_agent_local" in cli
assert "def refresh_ladder" in open("app/agent_loop.py").read()
print("all shipped claims present")

# v0.32 — the LAN write that could wake the household. Every POST that writes raw data must check a token before touching
# the database. Found on the clean node: a curl from the WiFi created an indoor sensor at 999 µg/m³ and two act-level alerts.
def _handler(name):
    m = re.search(rf"^@app\.post\(\"/{name}\"\)\n(.*?)(?=^@app\.|\Z)", main, re.M | re.S)
    assert m, f"main.py: no POST /{name}"
    return m.group(1)
_body = _handler("readings")
assert "_admin(authorization)" in _body.split("with db()")[0], "POST /readings must check the admin token before it opens the database"
print("write endpoints gated")
# v0.32 — tokens are compared in constant time, by one helper. A `!=` on a token is the pattern to refuse.
assert "secrets.compare_digest" in main and "def _bearer_ok" in main, "main.py: token compares go through _bearer_ok"
assert not re.search(r'!= f"Bearer|not in tokens', main), "main.py: a token is still compared with != or `in`"
print("token compares constant-time")
# v0.32 — dumps leave the settings rows behind (the Telegram token lived there on node #1 and travelled to the NAS)
assert "--exclude-table-data=settings" in open("backup.sh").read(), "backup.sh: settings rows must stay out of dumps"
print("dumps carry no settings rows")
# v0.32 — pack SQL runs as a read-only role that cannot see settings
_sql = open("init.sql").read()
assert "CREATE ROLE planetai_ro" in _sql and "REVOKE ALL ON settings FROM planetai_ro" in _sql, "init.sql: read-only role for pack SQL"
assert "index.run_ro(cur, rule[\"sql\"])" in main, "main.py: rules run through run_ro"
assert "run_ro(cur, c[\"sql\"])" in open("app/index.py").read(), "index.py: cells run through run_ro"
print("pack SQL runs read-only")
# v0.32 — every container's log is capped; db, agent and ipfs were not, and the agent logs every tool call
for _svc, _def in compose["services"].items():
    assert _def.get("logging", {}).get("options", {}).get("max-size"), f"docker-compose.yml: service {_svc} has no log cap"
print("every container log is capped")
# v0.32 — `planetai packs` lists; only `planetai packs install` touches .env and the image
assert 'packs) shift; cmd_packs "$@"' in cli and "packs_install()" in cli and 'install" ]]; then packs_install' in cli, "CLI: packs vs packs install"
_list = cli[cli.index("cmd_packs() {"):cli.index("packs_install() {")]
assert "docker compose build" not in _list and ">> .env" not in _list, "planetai packs (the listing) must not build or write .env"
print("packs listing is read-only")
# v0.32 — envset escapes what sed would swallow (a CKAN list carries `|` and `&`), and the setup log is capped
assert "sed -e 's/[\\\\&|]/\\\\&/g'" in cli, "CLI: envset must escape \\ & | before the sed replacement"
assert "tail -c 200000" in cli, "CLI: .planetai-setup.log is trimmed"
print("envset escapes, setup log capped")
# v0.32 — a report or a test alert says `/act N` only when the bot that reads it is running; otherwise `planetai act N`
assert "def act_hint" in main and main.count("act_hint(") >= 3, "main.py: the /act hint goes through act_hint()"
assert "→  /act {" not in main and "Reply /act with the number" not in main, "main.py: an unconditional /act instruction remains"
print("act hints honest without a bot")
# v0.32.1 — a reinstall over an earlier node's volume left an app that could not log in while every check said fine
assert "docker volume inspect planetai_db" in open("install.sh").read() and "NEWPW" in open("install.sh").read(), "install.sh: refuse a new password over an old volume"
assert "app logs in to the database" in cli, "doctor: the locked-out app must be a named failure"
print("reinstall over a leftover volume is refused and diagnosed")
# v0.33 — the earth pack. A pack whose files, endpoint, card and cell must ship together: the pack alone
# leaves the dashboard blank, the endpoint alone has nothing to serve, the card alone renders an empty box.
import os as _os
for _f in ("pack.yaml", "README.md", "adapter.py", "cells.yml", "fetch.py", "change.py", "status.py", "verify.py", "similar.py"):
    assert _os.path.exists(f"packs/earth/{_f}"), f"packs/earth/{_f}"
_earth = yaml.safe_load(open("packs/earth/pack.yaml"))
assert _earth["pip"] == ["rasterio", "numpy"] and _earth["kind"] == "code"
assert "EARTH_RADIUS_M=5000" in "".join(_earth["env"]) and "EARTH_YEARS=" in "".join(_earth["env"])
assert "Google and Google DeepMind" in _earth["attribution"], "the licence's own wording, not a paraphrase"
_cells = yaml.safe_load(open("packs/earth/cells.yml"))
assert len(_cells) == 1 and _cells[0]["cell"] == "Environmental|City" and _cells[0]["state"] == "partial"
print("the earth pack, its endpoint, its card and its cell all ship")
# v0.33.1 — one number for the land. earth-engine published a second land-change score with different
# provenance; it was retired and the alert moved to the pack that owns the metric.
for _f in ("adapter.py", "pack.yaml", "cells.yml"):
    assert "land_change" not in open(f"packs/earth-engine/{_f}").read(), f"earth-engine/{_f} still has land change"
assert not _os.path.exists("packs/earth-engine/rules.yml"), "earth-engine's land_changed was retired"
# and no pack alerts on land change until the number can be calibrated across climates: any threshold that
# fires in Kuta Selatan (0.041) also fires in Boston (0.040), most likely on snow and leaf-off.
assert not _os.path.exists("packs/earth/rules.yml"), "the earth pack must ship no alert; see its README"
assert "a household would ignore" in open("packs/earth/README.md").read(), \
    "packs/earth/README.md must say WHY there is no alert, not just that there is none"
for _n in ("0.0414", "0.0404", "0.0164", "0.0151"):
    assert _n in open("packs/earth/README.md").read(), f"the README must carry the {_n} measurement"
# v0.33.1 — every comparison is reachable, so a NAS can archive the ones that cannot be recomputed cheaply
assert 'def _earth_changes' in main and '"changes": changes' in main
assert 'pattern=r"^(\\d{4}_\\d{4})?$"' in main, "main.py: the pair must be a pattern, not a path"
assert 'def earth(ddir)' in open("tools/nas/pull.py").read(), "tools/nas/pull.py: archive the earth results"
print("one land-change number, its alert, and the results a NAS can archive")
# v0.33.3 — `planetai update` ships a pack's code, not its libraries. Node #1 got ModuleNotFoundError nine
# times with no remedy named. Every entry point that needs a pack library must say which command installs it.
assert "def require(" in open("packs/earth/adapter.py").read(), "packs/earth/adapter.py: the preflight"
for _s in ("fetch", "change", "similar"):
    assert "A.require(" in open(f"packs/earth/{_s}.py").read(), f"packs/earth/{_s}.py must preflight its libraries"
assert "planetai packs install" in open("update.sh").read(), "update.sh must say when a pack needs installing"
assert 'grep -q "planetai packs install" <<<' in open("update.sh").read(), "under pipefail, not a pipe into grep -q"
print("a pack that lacks its libraries says which command installs them")
# v0.33.8 — `planetai run earth change --all` is documented. Its behaviour, and the refusal of an argument
# the script does not know, are tested by running the script in tests/test_earth.py: a string check here
# would have passed while --all quietly did the default pair, which is the bug being fixed.
assert "planetai run earth change --all" in open("packs/earth/README.md").read(), "the README must document --all"
print("change --all is documented; tests/test_earth.py runs it")
# v0.34 — the years as pictures: a frame per cached year, animated in the card, one shared projection.
assert _os.path.exists("packs/earth/frames.py"), "packs/earth/frames.py"
assert "def fit_view" in open("packs/earth/adapter.py").read(), "the projection must be fittable once"
assert '"view"' in open("packs/earth/frames.py").read(), "the projection must be kept, not refitted per year"
assert '@app.get("/earth/year.png")' in main and 'f"year_{year}.png"' in main, \
    "main.py: a frame is addressed by an integer year, never by a name from the request"
assert '"frames": frames' in main and '"dir": str(d)' in main
for _id in ("earth-ctl", "earth-play", "earth-slider", "earth-year", "earth-mode", "earth-hist", "earth-path"):
    assert f'id="{_id}"' in gui, f"gui: #{_id}"
assert "not a photograph" in gui.lower() or "Not a photograph" in gui, \
    "gui: a rendering of a model must not be presented as a photograph"
print("the years render, animate, and are not called photographs")
assert 'libexpat1' in open("app/Dockerfile").read(), "app/Dockerfile: rasterio cannot import without libexpat1"
assert '@app.get("/earth")' in main and '@app.get("/earth/change.png")' in main
assert 'Path(str((want or {}).get("png", ""))).name' in main, "main.py: the png name must be stripped of path components"
assert 'data-card="earth"' in gui and 'id="earthcard"' in gui and 'drawEarth()' in gui
assert "class=\"prov\"" in gui, "gui: the earth card needs its provenance pill"
assert "planetai run earth fetch" in gui, "gui: the empty state must name the command that fills it"
# v0.33.6 — the dashboard must not be cacheable: a node that updates has to reach the screens looking at it
_ui = re.search(r"^def ui\(\):(.*?)(?=^def |\Z)", main, re.M | re.S).group(1)
assert "no-cache" in _ui, "the dashboard route must send a cache-control header, or an update never reaches an open browser"
print("the dashboard is not cacheable")
# v0.33.7 — one unusual OpenStreetMap object must not blank the plan. A poi mapped as an open way made
# drawPlan destructure a number and the kilometre stayed empty, silently, because drawPlan() is not awaited.
_gui = gui
assert "const firstPt=g=>" in _gui, "the plan needs a geometry-agnostic first point for its poi markers"
assert "px(firstPt(g))" in _gui, "the poi marker must not index coordinates[0][0]"
assert "}catch(e){skipped++;}" in _gui, "the plan's feature loop must survive one undrawable feature"
print("the plan survives real OpenStreetMap geometry")
# v0.35 — `local` was written once and never corrected. Node #1 carried three smartcitizen kits at local=false
# that no current code path can produce: they were born from Bali Air Dispatch before the bad- prefix existed.
# Both upserts must now update it, or a wrong partition of house and street survives every poll forever.
_main = open("app/main.py").read()
assert _main.count("local=EXCLUDED.local") + _main.count("local = EXCLUDED.local") == 2, \
    "both sensor upserts (poll and MQTT) must update local, or a stale flag never heals"

# The no-wind Steadman form is the indoor form, as packs/heat/README.md says. Both heat rules compute it, so both
# read indoor sensors only. After LOCAL_RADIUS_M a node's local sensors may all be outdoors, where the same
# arithmetic overstates the load; going quiet is the right answer, a wrong number is not.
_heat = {r["id"]: r for r in yaml.safe_load(open("packs/heat/rules.yml"))}
for _rule in ("heat_stress_now", "heat_danger"):
    assert "t.local AND t.indoor AND t.metric = 'temp'" in _heat[_rule]["sql"], \
        f"{_rule}: apparent temperature indoors only, and its threshold was measured indoors"
