# Developing

## Two machines

The dev machine has git and pushes. A node runs `planetai update` and never commits. Node #1 is a Mac mini at Fab Lab
Bali; its Python is Apple's 3.9 with no third-party libraries, and that is the Python the CLI must run on.

## Before every commit

```bash
make lint      # shell syntax, SQL idempotency, compose mounts, CLI snippets as Python 3.9 with stdlib only,
               # rules and cells against init.sql, docs against the code, the GUI, pyflakes, the app imports
make test      # six offline suites: adapters, Meshtastic parsing, cell provenance, code packs, settings, outside resolution
```

The pre-commit hook runs lint and refuses `.env`, credentials, `.DS_Store`, and anything under `.git`. Install it once:
`cp tools/hooks/pre-commit .git/hooks/`.

## What each gate exists for

Every gate is a bug that shipped.

| gate | the bug |
|---|---|
| `check_sql.py` | a comment ate a closing bracket; a missing config Docker replaced with an empty directory; `.DS_Store` committed; `\| grep -q` under pipefail failing a good dump |
| `check_cli_python.py` | f-strings that crashed on Python 3.9; PyYAML the node does not have; a `for` after a semicolon |
| `check_rules.py` | a 69-day cooldown that made `test-alert` report a dead node; message placeholders the SQL never returned |
| `check_docs.py` | "two containers, five rules" when there were nine adapters and eight packs; links to files that had moved |
| `check_ui.py` | an element id the script referenced that was not in the markup |
| import check | `PARENT.startswith()` on a function, at import, so uvicorn never listened |

## Two habits

**Test the artifact, not a transcription of it.** Three times a test retyped the code it was testing and the escaping
bug made it pass.

**Break something on purpose before trusting a new gate.** A check that has never failed has not been tested.

## Releasing

```bash
tools/release.sh v0.19     # lint, tag, push. Needs a CHANGELOG section.
tools/bundle.sh            # the tarball the website serves to testers without repo access
cd ../planetai && make deploy
```

## Agents

`AGENTS.md` at the root is the operating manual for an AI agent (Claude, Codex, a local model): the MCP surface at
`/mcp`, the `--json` commands, the invariants, the gates. `planetai agent` prints the endpoint, the token and a config
snippet. The MCP server is `app/agent.py`, thirteen tools over the existing API; host operations are handed back as
commands because the container has no Docker or git.

## Layout

```
app/          main.py (api, loops, notify) · sources.py (adapters) · index.py (cells, ρ) · packs.py · settings.py ·
              bootstrap.py · static/index.html (the dashboard)
bin/planetai  the operator CLI
packs/        eight packs; see PACKS.md
config/       rules.yml (two domain-blind rules), mosquitto, reticulum
tools/        gates, hooks, bundle, release, mesh-provision.sh, nas/ (the NAS puller)
tests/        offline suites
docs/         you are here
```
