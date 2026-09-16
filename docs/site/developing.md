# Developing and contributing

Short version: run a node, tell us what broke, send the fix. The repository is
[`fabcity/planetai-node`](https://github.com/fabcity/planetai-node), Apache-2.0 for the code and CC BY 4.0
for the documentation. By opening a pull request you agree to those terms.

## Two machines

The dev machine has git and pushes. A node runs `planetai update` and never commits. Node #1 is a Mac mini;
its Python is Apple's 3.9 with no third-party libraries, and that is the Python the CLI must run on. Nothing
runs pip on a node's host; what the app needs is in its image.

## Three ways to help

**Run a node and report.** The most useful contribution is [Install](install.md) failing on your machine.
Open an issue with the "Node problem" template — it asks for the exact three commands we need: `planetai
status`, `planetai doctor`, twenty lines of `planetai logs`. Never `.env`.

**Add a sensor or a source.** An adapter is one function returning `(sensors, readings)` —
[the contract](sensors.md). Test it against a saved payload from the real device before opening a PR. Set
`local` and `indoor` honestly; every rule depends on them.

**Write a rule, a cell, a pack.** [Packs](packs.md). Copy `packs/heat`; say in the README where the
thresholds came from and which place you wrote for. A rule should end in something a person does.

## What will not be merged

Anything that makes a node depend on a cloud service to *function* — reference data from public APIs is
fine, control planes are not. A third container without a trigger written in [`SPEC.md`](spec.md) §6. Raw
readings leaving the node — hourly means, cells, model updates, yes; raw, never. Rules that fire on indoor
sensors as if they were ambient: `NOT s.indoor` is not decoration.

## Before every commit

```bash
cp tools/hooks/pre-commit .git/hooks/   # once: the hook blocks .env, credentials, .DS_Store and .git contents, and runs lint
make lint
make test
```

`make lint` is cheap on purpose and runs every gate that exists because something once shipped broken:

| gate | the bug it exists for |
|---|---|
| `bash -n` on every script | shell syntax |
| `check_floors.py`, `gen_floors.py --check`, `render_platforms.py --check` | a platform floor older than 180 days; the Platforms page drifting from `data/platform_floors.yml` |
| `check_sql.py` | a comment ate a closing bracket; a missing config Docker replaced with an empty directory; `.DS_Store` committed; `\| grep -q` under pipefail failing a good dump |
| `check_cli_python.py` | f-strings that crashed on Python 3.9; PyYAML the node does not have; a `for` after a semicolon |
| `check_rules.py` (needs sqlglot) | a 69-day cooldown that made `test-alert` report a dead node; message placeholders the SQL never returned; a cell without a `value` |
| `check_docs.py` | "two containers, five rules" when there were nine adapters and eight packs; links to files that had moved |
| `check_ui.py` | an element id the script referenced that was not in the markup; a network `url()` in a stylesheet; Fab Blue in the dark register |
| `check_theme.py` | the copy of the design repo's theme drifting on this side, where nothing would say what moved |
| `check_requirements.sh` | `uvicorn` pinned against `mcp`; the image failed to build on the node |
| `extract_strings.py --check` | the installer's and the preflight's human-readable sentences out of step with `data/strings/en.yml` |
| `py_compile`, pyflakes, the import check | `PARENT.startswith()` on a function, at import, so uvicorn never listened |
| `.env.example` comment placement; every pack HTTP client has a timeout | a comment after a blank key becoming its value; a client that hangs forever |

`make test` runs the offline suites in `tests/`, one line each with a count at the end and a non-zero exit
when a check skipped that nobody declared: adapters against saved payloads, Meshtastic parsing, cell
provenance and custody, code packs, settings, the issues engine and its geometry, the report templates and
schedule, the forecast and nearby packs, the dashboard, the shell scripts (`preflight`, `remove`, `diagnose`,
`sudo` prompting, release consistency).

Two habits. **Test the file, not a copy typed into the test** — three times a test retyped the code it was
checking, and the retyping hid the bug. **Break something on purpose before trusting a new gate** — a check
that has never failed has not been tested.

## Looking at the page

`python3 tools/shots.py` renders every fixture in Now and on the wall at four widths into
`docs/design/shots/`, with every request fulfilled from disk, and fails on a page error, a component that
drew its guard box, a page that scrolls sideways or a request the fixture path should not have made. It needs
Chromium from the sibling `planetai-design` checkout (`PLANETAI_DESIGN_REPO`) and is not a gate. The
dashboard's frozen visual language and the eight checks against it are in `docs/design/LANGUAGE_GAP.md`.

## Releasing

A merge is not a release, and nothing reaches a tester without one. `/install`, `/preflight` and `/remove`
read the published `node0/get/VERSION`, take the commit it names, and fetch from exactly that commit, so a
tester always gets one self-consistent version.

```bash
tools/release.sh 0.54     # lint, tag v0.54, push; needs a `## v0.54` section in CHANGELOG.md
make released             # is the site behind main?
make ship                 # rebuild the tarball, commit it in the site repo, deploy
```

`make ship` refuses a commit CI has not vouched for and fast-forwards a checkout that is merely behind. To
hand somebody an unreleased fix without shipping, `PLANETAI_REF=main` overrides the pin. `VERSION` is served
with `max-age=300`, so a check right after a deploy may read the old entry for a few minutes.

Schema changes go in `init.sql` additively. One dated line in `CHANGELOG.md` per change, saying why.

## This documentation

The pages under `docs/site/` and the pages of `docs/` and the root that the sidebar lists are rendered by
`tools/build_docs.py` into `planetai.fab.city/docs`:

```bash
pip install markdown                                   # on the dev machine only
python3 tools/build_docs.py --out ../planetai/docs     # one folder per page, on the dashboard's own tokens
python3 tools/build_docs.py --single /tmp/docs.html    # everything on one page, for review
cd ../planetai && make deploy
```

`docs/site/STYLE.md` is how the pages are written: plain words, say what to do, only what the code says,
and the conventions the renderer understands. The version and commit in every page's footer are read from
git at build time.

## Voice

Docs are written for the person installing at 9 pm with a sensor that just went quiet. Plain words. Say
what to do. No emoji, no hype, no "simply".

## Layout of the repository

```
app/          main.py (api, loops, notify) · sources.py (adapters) · index.py (cells, ρ) · packs.py · settings.py
              report.py · agent.py (MCP) · agent_loop.py (the bot) · issues/ · static/ (the dashboard)
bin/planetai  the operator CLI
packs/        fourteen packs; see Packs
config/       rules.yml (two domain-blind rules) · channels.yml · mosquitto · reticulum
skills/       setup-node · troubleshoot-node · connect-agent · publish-to-index
tools/        the gates, hooks, bundle and release scripts, mesh-provision.sh, nas/, remote-model.sh, build_docs.py
tests/        offline suites
docs/         the pages; docs/site/ the ones written for this site; design/ the visual language and its reviews
presets/      bali · barcelona · boston · santiago · delhi · menorca
```
