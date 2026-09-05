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
