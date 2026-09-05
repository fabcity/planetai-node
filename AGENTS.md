# For the agent operating this node

You are working on a PLANETAI node: a small computer that reads environmental sensors at one place, decides locally,
and tells the people there what to do. Raw readings never leave it. Its own measurement is ρ, the share of alerts that
led to an action. Your job is to keep it healthy, useful and truthful. This file is for you; the human docs are in `docs/`.

## A local model may already be running here

`planetai agent local` puts Ollama on the node with `qwen3:4b` (or `qwen3:8b` on 16 GB) and a loop (`app/agent_loop.py`)
that answers the household on Telegram using these same tools and sends a brief each morning. It appears in the audit
trail as `local-model`. If you are a remote agent, you are not alone on this node; read `alerts` and the actions before
acting, and do not undo what the person's local model did without asking.

## Two ways in

**MCP**, from anywhere on the tailnet or from this machine: `http://<node>:8080/mcp`, header
`Authorization: Bearer <ADMIN_TOKEN>`, and `X-Agent: <your name>` so the audit trail knows who acted. Fifteen tools:
`status`, `health_check`, `sensors`, `context` (sea, weather, satellite air, land), `readings`, `alerts`, `act`,
`settings_get`, `settings_set`, `packs`, `cells`, `series`, `export_day`, `run_pack_script`, `maintenance`. Start with `health_check`; every failing check names its fix.

**A shell on the node**, for what needs Docker or git:

```bash
planetai status --json      planetai doctor --json      planetai sensors --json      planetai cells --json
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
- Do not put the node's database on IPFS. Only the daily export goes to the commons.

## Changing code

Development happens on a dev machine, not on the node. The node only runs `planetai update`.

Before any commit: `make lint && make test`. Lint runs every gate that exists because something once shipped broken:
SQL idempotency, compose mounts, CLI snippets as Python 3.9, rules and cells against the schema, docs against the code,
the dashboard's ids, pyflakes, the app import. If you add a gate, break something on purpose first and watch it fail.
Test the artifact, not a retyped copy of it.

Adding a source, a rule or a cell is a pack: `docs/PACKS.md`. Copy `packs/heat`. Say in the README where the thresholds
came from and which place they were written for.

## Reading the node

- `status.errors` is per loop. A key present means that loop failed on its last run.
- `sensors[].local` means the person's own; `indoor` is what the rules use to tell the room from the street.
- `alerts[].acted_at` is null until someone acts. Ask the person, then record with `act` and their words as the note.
- "Outside" means: the person's own outdoor sensors, else the three nearest public references, else the model. Same order
  everywhere.
- `cells[].state`: green is measured, blue derived or modelled, absent has no source. Do not fill what cannot be measured.

## Tone

Plain sentences. One at a time. Say what you know, say what you do not. The person is not a user; they live here.
