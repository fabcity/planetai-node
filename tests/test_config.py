"""`planetai config`, and the line under the logo. Reads the files and asserts on them; no node needed.

The bug this file mostly exists for: the rows that `config` formats were tab-separated, and a tab is an IFS
*whitespace* character, so bash's `read` collapses runs of them. Every setting with no `.env` entry lost a
field and slid its own help text into the column that reports what `.env` says — which is a listing that
lies about the thing the command was written to stop lying about.
"""
import re

cli = open("bin/planetai").read()
stub = open("install").read()
settings = open("app/settings.py").read()

# ---- the separator
assert "SEP=$'\\x1f'" in cli, "bin/planetai: config rows need an explicit non-whitespace separator"
rows = cli[cli.index("config_rows()"):cli.index("config_list()")]
assert '"\\t"' not in rows and "'\\t'" not in rows, (
    "config_rows is tab-separated again: tab is IFS whitespace, so `read` swallows every empty field and "
    "each setting with no .env entry shifts its help text into the .env column")
for f in ("sort -t", "awk -F", "IFS="):
    seg = [l for l in cli.splitlines() if f in l and ("config_" in l or "read -r key" in l)]
    assert seg, f"config no longer uses {f} — check the separator is still threaded through"
    assert all("$SEP" in l for l in seg), f"{f} in config must use $SEP, not a literal: {seg}"

# ---- the subcommands actually reach the function
assert re.search(r'config\)\s*shift;\s*cmd_config "\$@"', cli), (
    'the dispatch must be `config) shift; cmd_config "$@"` or every subcommand is silently dropped')
for sub in ("list", "get", "set", "unset", "edit"):
    assert f"    {sub})" in cli or f"    {sub}|" in cli, f"planetai config {sub} is not in cmd_config"
assert "config_wizard" in cli, "the navigable menu is missing"

# ---- config navigates; it does not march. `planetai setup` is the flow that walks all sixty-six settings
# once, at install. A config command that makes you answer every one to change a single value is a setup
# flow wearing the wrong hat, and that is what the first version of this was.
nav = cli[cli.index("config_wizard()"):cli.index("cmd_config() {")]
assert "config_menu_group" in cli, "there is no category level: config must navigate, not walk every setting"
grp = cli[cli.index("config_menu_group()"):cli.index("config_wizard()")]
for token, why in ((" b|B", "back"), (" q|Q", "quit"), (" s|S", "save and exit")):
    assert token in grp, f"the settings menu has no {why} key — you must be able to leave from anywhere"
for token, why in (("q|Q", "quit"), ("s|S", "save and exit")):
    assert token in nav, f"the category menu has no {why} key"

# ---- changes are staged, so cancel means something
assert "CFG_PENDING" in cli and "cfg_pend_put" in cli, "changes must be staged, or `cancel` cannot exist"
edit = cli[cli.index("config_edit_one()"):cli.index("config_menu_group()")]
assert "runtime_set" not in edit and "envset" not in edit, (
    "editing one setting must stage it, not write it — otherwise quitting cannot throw it away")
save = cli[cli.index("config_save()"):cli.index("cfg_quit()")]
assert "runtime_set" in save and "envset" in save, "save must write both the runtime keys and the .env ones"
assert "confirm" in cli[cli.index("cfg_quit()"):cli.index("config_edit_one()")], (
    "quitting with unsaved changes must ask before discarding them")
# Bash 3.2 is Apple's /bin/bash and has no associative arrays; pending is a string of KEY<US>VALUE lines.
assert "declare -A" not in cli, "declare -A is bash 4; this runs on Apple's bash 3.2"

# ---- a runtime key is written where the node reads it, a bootstrap key where the container reads it
cset = cli[cli.index("config_set()"):cli.index("config_unset()")]
assert "runtime_set" in cset and "envset" in cset, "config set must route runtime -> node, bootstrap -> .env"
assert "cmd_restart" in cset, "a bootstrap change must offer the restart it needs to take effect"

# ---- the node says why it refused, rather than the caller guessing it was unreachable
rset = cli[cli.index("runtime_set()"):cli.index("# ---------------------------------------------------------------- the rest")]
assert "400" in rset and "warn" in rset, "runtime_set must surface the node's own refusal, not swallow it"

# ---- the line under the logo, in both places that draw one
assert cli.count("a Fab City project") >= 1, "bin/planetai: the logo must say whose project this is"
assert "a Fab City project" in stub, "install: the logo must say whose project this is"
assert "version()" in cli and "$(version)" in cli, "bin/planetai: the logo and `planetai version` share one resolver"
assert cli.count("git describe --tags --always") == 1, (
    "there is a second copy of the version resolver; they drift — one version() and everything calls it")
assert "$SITE/get/VERSION" in stub, "install: show the version this install is about to fetch"
assert "--max-time" in stub[stub.index("a Fab City project") - 400:stub.index("a Fab City project")], (
    "install: the version fetch needs a timeout, or an offline machine waits at a banner")

# ---- every group the wizard can be pointed at is a real group
groups = set(re.findall(r'^\s*"[A-Z_]+":\s*\("(\w+)"', settings, re.M))
assert {"sources", "alerts", "node"} <= groups, f"settings.py groups moved: {groups}"
print("config: separator safe, subcommands wired, writes routed, banner says Fab City and a version")
