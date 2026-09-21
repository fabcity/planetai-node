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
for f in ("awk -F", "IFS="):
    seg = [l for l in cli.splitlines() if f in l and ("config_" in l or "read -r key" in l)]
    assert seg, f"config no longer uses {f} — check the separator is still threaded through"
    assert all("$SEP" in l for l in seg), f"{f} in config must use $SEP, not a literal: {seg}"

# ---- one order, and the node declares it
# `cfg_groups` sorted alphabetically and `config_list` sorted by group, while the dashboard's Set up tabs
# were a hand-written object literal. Three orders for the same nine groups, and `agent` led two of them
# because it starts with an a. app/settings.py's RUNTIME is the declaration now, and all three read it.
assert "!seen[$2]++" in cli, (
    "cfg_groups must keep the node's own order, first-seen. `sort -u` is alphabetical, which is not an order "
    "anybody chose — see the comment at the top of app/settings.py's RUNTIME")
for fn in ("config_list()", "config_wizard()"):
    body = cli[cli.index(fn):][:1400]
    assert not re.search(r"config_rows\s*\|\s*sort|cfg_groups\s*\|\s*sort", body), (
        f"{fn} sorts the rows again; the order is settings.RUNTIME's and nothing else re-decides it")

_groups = re.findall(r'^\s*"[A-Z0-9_]+":\s*\(\s*"([a-z]+)"', settings, re.M)
assert _groups, "could not read the group of a single RUNTIME key — has the tuple shape changed?"
_runs = [g for i, g in enumerate(_groups) if i == 0 or _groups[i - 1] != g]
assert len(_runs) == len(set(_runs)), (
    f"a settings group is split across RUNTIME rather than declared in one block: {_runs}. All three "
    "surfaces print a heading when the group changes, so a strayed key prints a second heading for it.")
assert _runs[0] == "issues", (
    "issues leads the settings, on every surface: it is the one setting that says what this place is for")

# The dashboard must take the list and the order from the node, not keep its own copy. A group the node
# gains was unreachable in the UI and visible in the CLI, and nothing said so.
_js = open("app/static/dashboard.js").read()
assert "function groupsOf(" in _js, "the dashboard must derive its Set up tabs from /settings"
assert re.search(r"groupsOf\(DESC\)", _js), "...and actually call it when it draws them"
assert not re.search(r"Object\.entries\(GROUPS\)|Object\.keys\(GROUPS\)", _js), (
    "the dashboard is enumerating its own GROUPS object again. That object is a lookup for titles and "
    "blurbs; the list of groups belongs to the node, which is what `planetai config` reads too.")

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
assert "$GET/VERSION" in stub, "install: show the version this install is about to fetch"
assert 'GET="${PLANETAI_GET:-$SITE/get}"' in stub, (
    "install: the three files must come from one place, so PLANETAI_GET can point at a GitHub Release")
assert "--max-time" in stub[stub.index("a Fab City project") - 400:stub.index("a Fab City project")], (
    "install: the version fetch needs a timeout, or an offline machine waits at a banner")

# ---- every group the wizard can be pointed at is a real group
groups = set(re.findall(r'^\s*"[A-Z_]+":\s*\("(\w+)"', settings, re.M))
assert {"sources", "alerts", "node"} <= groups, f"settings.py groups moved: {groups}"
# ---- a pack's own keys reach /settings, or nobody can turn the pack on -------------------------
#
# Until 21 September 2026 they did not reach it at all. settings.py listed only its own RUNTIME
# dict, so a pack could declare five keys in its pack.yaml and none of them appeared in the body
# GET /settings returns — including the switch whose entire job is to turn that pack on. Node #1
# had MAKE_ENABLED=1 in its .env and the string MAKE appeared nowhere in its settings body.
#
# EVERY INSTALLED PACK, enabled or not. packs.manifests() filters by PACKS_ENABLED and
# PACKS_ALLOW_CODE, which is right for loading code and exactly wrong here: a keeper cannot enable
# what the page will not show them, and the pack that is off is the one they most need to see.
# This file reads its inputs relative to the repo root, the way the asserts above do.
import os as _os, sys as _sys                                        # noqa: E402
_sys.path.insert(0, "app")
_os.environ.setdefault("PACKS_DIR", "packs")
import settings as _st                                               # noqa: E402

_declared = _st.pack_settings()
assert _declared, "no pack declares an env key, which means this is reading the wrong directory"
_rows = {r["key"]: r for r in _st.describe(unlocked=True, public=_st.PUBLIC)["runtime"]}
for _d in _declared:
    _r = _rows.get(_d["key"])
    assert _r, f"{_d['pack']} declares {_d['key']} and /settings does not carry it"
    assert _r["group"] == "packs", f"{_d['key']} is not in the packs group"
    assert _r["default"] == _d["default"], \
        f"{_d['key']} publishes default {_r['default']!r}, pack.yaml says {_d['default']!r}"
    assert _r["help"], f"{_d['key']} reaches the page with no help text"

# The one that is the point: `make` ships OFF, and its switch has to be visible anyway.
_mk = _rows.get("MAKE_ENABLED")
assert _mk and _mk["default"] == "0", \
    "MAKE_ENABLED is the switch that turns on a pack that ships off; a keeper who cannot see it " \
    "cannot turn it on, which is the whole of the bug this checks for"
assert "not openly licensed" in (_mk["help"] or "").lower(), \
    "MAKE_ENABLED reaches Set up without the licence sentence pack.yaml puts above it"

# ---- and every key says what a fresh node would have given it ---------------------------------
#
# `.env.example` is the record of that and `make lint` already holds it to a rule, but it is at the
# repo root and the app image is built from app/, so the container could never read it: a row could
# say "this value is a default" and never "the default is X". tools/gen_defaults.py generates the
# same facts into data/, which IS mounted, with a --check in lint so the two cannot drift.
_os.environ.setdefault("ENV_DEFAULTS", "data/env_defaults.yml")
_st._defaults_cache.clear()
_src = {k: v for k, v in
        ((l.split("=", 1)[0].strip(), l.split("=", 1)[1].split("#")[0].strip())
         for l in open(".env.example") if "=" in l and not l.strip().startswith("#"))
        if k.isupper()}
_rt = {r["key"]: r for r in _st.describe(unlocked=True, public=_st.PUBLIC)["runtime"]}
for _k, _r in _rt.items():
    if _r["group"] == "packs":
        continue                                     # those come from pack.yaml, checked above
    if _k == "UI_LAYOUT":
        assert _r.get("default") in (None, ""), \
            "UI_LAYOUT has no default VALUE — blank is how a keeper restores the default layout"
        continue
    assert _r.get("default") is not None, \
        f"{_k} reaches Set up with no default, so a keeper who overrode it cannot see what it was"
    if _k in _src:
        assert _r["default"] == _src[_k], \
            f"{_k}: /settings says {_r['default']!r}, .env.example says {_src[_k]!r}"

print("config: separator safe, subcommands wired, writes routed, banner says Fab City and a version")
print(f"config: {len(_declared)} pack-declared keys reach /settings with their defaults and help")
