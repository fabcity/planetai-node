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
