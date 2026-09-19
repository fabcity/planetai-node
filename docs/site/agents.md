# Bring your own agent

A node is a thing you operate, and most people who install one will do it with an agent beside them —
Claude, Codex, a local model. The repository is written for that. `AGENTS.md` at its root is the front door:
its first section is a table that routes an agent to one of four skills for what the person is actually
asking, and the rest of it is what an agent must not break. `llms.txt` indexes every document for an agent
arriving from outside. `make lint` fails if a skill names a command or a path that does not exist.

Paste this to your agent and nothing else:

> You are helping me with a PLANETAI node — an open-source program that turns a spare computer in my home or
> lab into a hyperlocal environmental monitor. Start by reading
> https://raw.githubusercontent.com/fabcity/planetai-node/main/AGENTS.md — its first section is a table
> that routes you to the right skill for what I am asking, and the rest of it is what you must not break.
> Read that skill before you tell me to run anything. Never ask me for the contents of my `.env` file, and
> never suggest exposing the node to the internet; the answer to reaching it from elsewhere is Tailscale.

## The four skills

| the person says | skill | what it makes the agent do |
|---|---|---|
| "help me install this", "will it run on my old laptop?" | `skills/setup-node` | Run the preflight first and read its exit code; never continue past exit 2. Install with the one line or `planetai setup --answers`. Then Telegram, the test alert — the only end-to-end proof — the dashboard, the doctor. Never a machine that sleeps, never print `.env`, never tune a threshold during setup, never pip on the host. |
| "it stopped working", "no alerts since Tuesday", here is a log | `skills/troubleshoot-node` | Ask for exactly `planetai doctor --json`, `status --json` and twenty lines of logs; `sensors --json` if it is a sensor. Never `.env` — if one arrives, tell them to revoke the bot token. It may read, restart, update, back up; it may not change a threshold, record an action, move the database or edit `.env` without consent. "A node that is quiet because you raised its threshold is lying." |
| "connect this to Claude / Codex", "reach it from outside" | `skills/connect-agent` | Get the URL, token and snippet from `planetai agent`. Tailscale, never a port forward, ngrok or a public reverse proxy. Name yourself in every write's `agent` argument. Call `health_check` first, then `status`. See [MCP](mcp.md). |
| "put our city on the Fab City Index" | `skills/publish-to-index` | Establish the tier first: one node per pilot writes, a home node never does. `planetai cells --json`; the state must be honest. The writer lives with the Index and needs a per-pilot token issued by hand. See [Federation](federation.md). |

All four end the same way: when a document and the skill disagree, the document wins and the skill has a bug.

## Two ways in

**MCP**, from this machine or anywhere on the tailnet: `http://<node>:8080/mcp`, header `Authorization: Bearer <ADMIN_TOKEN>`; pass your name in the write tools' `agent` argument so the audit trail knows who acted. Twenty tools, listed on
[MCP](mcp.md). Start with `health_check`; every failing check names its fix.

**A shell on the node**, for what needs Docker or git:

```bash
planetai status --json      planetai doctor --json      planetai sensors --json      planetai cells --json
planetai report             planetai report last        planetai report every <h>   planetai report at <h>
planetai update             planetai backup             planetai restart             planetai logs
planetai setup --answers node.json
```

The `maintenance` MCP tool hands these back as commands with an explanation, because the container has no
Docker and no git. An agent with no shell tells the person which to run.

## A local model may already be running

`planetai agent local` puts Ollama on the node with a small model and a loop that answers the household on
Telegram using the same tools; it appears in the audit trail as `local-model/<rung>`. A remote agent is not
alone on the node: read the alerts and the actions before acting, and do not undo what the household's own
model did without asking. See [The bot](bot.md).

## Invariants an agent must not break

- Raw readings stay on this machine. Exports and aggregates travel; rows never do.
- `.env` holds secrets. Never print it, never paste it, never commit it. A log containing
  `api.telegram.org/bot` is a leak.
- The database lives on a local disk. Never a network mount. Backups are how data reaches a NAS.
- A model or a portal is `partial`, whatever its quality. `live` means measured here.
- Alerts say what to do in one sentence and name the threshold's source. Do not add alerts a household would
  ignore.
- Nothing runs pip on the host. The CLI runs on Apple's Python 3.9 with the standard library only.
- The dashboard names no metric. Issues are declared in `app/issues/*.yml`, ordered by `NODE_ISSUES`, served
  at `GET /issues`. The node computes; the page draws.
- Do not put the node's database on IPFS. Only the daily export goes to the commons.
- Peers never roll up, and never drive an alert or a report line. Custody — `local OR kind='child'` — is the
  only thing a cell may count.
- State is never upgraded by aggregation. A parent's cell is `partial` if any input was.
- Exact place never leaves; a coarse cell may, and says how coarse. The Reticulum announce is an H3 cell
  rounded up with a floor of resolution 6.
- Exactly one node per pilot writes to the Index's spine.
- `alerts[].acted_at` is the person's note on what they did, not the node's measurement: ask them, record
  it in their words with `act`, never invent one.

## Reading the node well

`status.errors` is per loop: a key present means that loop failed on its last run. `sensors[].local` means
the person's own **and** at this node. "Outside" means their own outdoor sensors, else the three nearest
public references, else the model — the same order everywhere. `cells[].state`: green is measured, blue
derived or modelled, absent has no source; do not fill what cannot be measured.

Tone: plain sentences, one at a time. Say what you know, say what you do not. The person is not a user;
they live here.
