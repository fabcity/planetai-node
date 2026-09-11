# Start here: what the person in front of you is asking for

Four situations bring somebody to this repository with an agent. Find theirs in the first column, read
that skill, then do the third column. If none of them fits, read the rest of this file — it is written
for an agent already inside a running node.

| the person says | read this skill | then do this |
|---|---|---|
| "help me install this", "I want a node", "will it run on my old laptop?" | `skills/setup-node/SKILL.md` | Run the preflight first and read its exit code. Never continue past exit 2. |
| "it stopped working", "no alerts since Tuesday", here is a log | `skills/troubleshoot-node/SKILL.md` | Ask for `planetai doctor --json`, `status --json` and twenty lines of logs. Never `.env`. |
| "connect this to Claude / Codex / my agent", "how do I reach it from outside?" | `skills/connect-agent/SKILL.md` | Get the URL and token from `planetai agent`. Tailscale, never a port forward. |
| "put our city on the Fab City Index", "how do we publish cells?" | `skills/publish-to-index/SKILL.md` | Establish the tier first. One node per pilot writes; a home node never does. |

The skills order the documents; they do not replace them. Everything below is what an agent operating a
node needs to know, and it is the authority.

# For the agent operating this node

You are working on a PLANETAI node: a small computer that connects everything measuring one place, from sensors on the
wall to satellites overhead, decides where it stands, and tells the people there what to do about the air, the heat,
the sea and the land. Raw readings never leave it. Its own measurement is ρ, the share of alerts that
led to an action. Your job is to keep it healthy, useful and truthful. This file is for you; the human docs are in `docs/`.

## A local model may already be running here

`planetai agent local` puts Ollama on the node with `qwen3:4b` (or `qwen3:8b` on 16 GB) and a loop (`app/agent_loop.py`)
that answers the household on Telegram using these same tools and sends a brief each morning. It appears in the audit
trail as `local-model`. If you are a remote agent, you are not alone on this node; read `alerts` and the actions before
acting, and do not undo what the person's local model did without asking.

## Two ways in

**MCP**, from anywhere on the tailnet or from this machine: `http://<node>:8080/mcp`, header
`Authorization: Bearer <ADMIN_TOKEN>`, and `X-Agent: <your name>` so the audit trail knows who acted. Twenty tools:
`status`, `health_check`, `issues` (how the place is doing, in the household's own words), `sensors`,
`context` (sea, weather, satellite air, land), `readings`, `report_latest`,
`report_now`, `report_bundle`, `history`, `alerts`, `act`, `settings_get`, `settings_set`, `packs`, `cells`, `series`,
`export_day`, `run_pack_script`, `maintenance`. Start with `health_check`; every failing check names its fix.

**A shell on the node**, for what needs Docker or git:

```bash
planetai status --json      planetai doctor --json      planetai sensors --json      planetai cells --json
planetai report             planetai report last        planetai report every <h>   planetai report at <h>
planetai update             planetai backup             planetai restart             planetai logs
planetai setup --answers node.json      # install without a terminal; see the JSON shape in bin/planetai
```

`maintenance` over MCP returns these commands with an explanation. If you have no shell, tell the person which to run.

## Invariants. Do not break these.

- Raw readings stay on this machine. Exports and aggregates travel; rows never do.
- `.env` holds secrets. Never print it, never paste it, never commit it. Logs containing `api.telegram.org/bot` are a leak.
- The database lives on a local disk. Never a network mount. Backups are how data reaches a NAS.
- A model or a portal is `partial`, whatever its quality. `live` means measured here.
- Alerts say what to do in one sentence and name the threshold's source. Do not add alerts a household would ignore.
- Nothing runs pip on the host. The node's Python is Apple's 3.9 with the standard library only. The CLI must stay that way.
- The dashboard names no metric. Issues are declared in `app/issues/*.yml`, ordered by `NODE_ISSUES`, and
  served at `GET /issues`. The node computes; the page draws. A number the page works out for itself is a bug.
- Do not put the node's database on IPFS. Only the daily export goes to the commons.
- When a document and a skill disagree, the document wins and the skill has a bug. Fix the skill, not the doc.

## Changing code

Development happens on a dev machine, not on the node. The node only runs `planetai update`.

A merge is not a release, and nothing reaches a tester without one. `/install` and `/preflight` are
stubs that read the published `node0/get/VERSION`, take the commit it names, and fetch their script
from exactly that commit — so the bootstrap, the preflight check and the node in the tarball all come
from one commit. They used to fetch from main every run, which meant a tester received two versions at
once: on 2026-09-08 a bootstrap that knew about `planetai remove` handed over a v0.41.2-23 node that
did not have it, and the tester was told to type a command their copy did not contain.

So a fix to the installer is not live when it merges. `make released` says whether the site is behind
main; `make ship` rebuilds the tarball, commits it in the site repo and deploys. To hand somebody an
unreleased fix without shipping, `PLANETAI_REF=main` still overrides the pin.

Before any commit: `make lint && make test`. Lint runs every gate that exists because something once shipped broken:
SQL idempotency, compose mounts, CLI snippets as Python 3.9, rules and cells against the schema, docs against the code,
the dashboard's ids, pyflakes, the app import. If you add a gate, break something on purpose first and watch it fail.
Test the file itself, not a copy typed into the test.

Adding a source, a rule or a cell is a pack: `docs/PACKS.md`. Copy `packs/heat`. Say in the README where the thresholds
came from and which place they were written for.

## Reading the node

- `status.errors` is per loop. A key present means that loop failed on its last run.
- `sensors[].local` means the person's own **and** at this node; a kit of theirs further than `LOCAL_RADIUS_M` is theirs but not this node's measurement. `indoor` is what the rules use to tell the room from the street.
- `alerts[].acted_at` is null until someone acts. It is the person's note on what they did, not the node's own
  measurement: ask them, record it with `act` in their words, and never invent one.
- "Outside" means: the person's own outdoor sensors, else the three nearest public references, else the model. Same order
  everywhere.
- `cells[].state`: green is measured, blue derived or modelled, absent has no source. Do not fill what cannot be measured.

## Tone

Plain sentences. One at a time. Say what you know, say what you do not. The person is not a user; they live here.
