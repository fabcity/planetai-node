# MCP server and tools

The node is an MCP server. `app/agent.py` mounts it on the API at exactly `/mcp`, streamable HTTP, twenty
tools over the existing endpoints. The tools call the node's own API back on `127.0.0.1`, so they arrive as loopback; `report_now`, `settings_set` and `report_bundle` carry the admin token, and every write records who did it from the tool's own `agent` argument. The same tools
serve Claude Code on a laptop across the tailnet, the household's own local model on Telegram, and any
client that speaks MCP over HTTP.

## Connecting

```bash
planetai agent
```

prints the endpoint on this machine (`http://localhost:8080/mcp`) and on the tailnet
(`http://<name>.<your-tailnet>.ts.net:8080/mcp`, the MagicDNS name recorded as `MESH_NAME` once `planetai mesh` has run), the header every call must carry —
`Authorization: Bearer <ADMIN_TOKEN>` — and a ready-made snippet:

```json
{"mcpServers": {"planetai-bayu-2": {"type": "http",
  "url": "http://bayu-2:8080/mcp",
  "headers": {"Authorization": "Bearer <ADMIN_TOKEN>", "X-Agent": "tomas-claude"}}}}
```

For Claude Code, from a clone of the repository, `.mcp.json` is already there and reads the values from
the shell — `PLANETAI_MCP_URL` (default `http://localhost:8080/mcp`), `PLANETAI_ADMIN_TOKEN`,
`PLANETAI_AGENT_NAME` — so nothing secret is in the file. Or from anywhere:

```bash
claude mcp add --transport http planetai "$PLANETAI_MCP_URL" \
  --header "Authorization: Bearer $PLANETAI_ADMIN_TOKEN" --header "X-Agent: $PLANETAI_AGENT_NAME"
```

Cursor does not expand `${VAR:-default}`; paste the snippet from `planetai agent` instead. A local Ollama
with an MCP client (mcphost, oterm) uses the same URL on localhost.

Access: the whole of `/mcp` needs the admin token and nothing else; it bypasses `SHARE_LEVEL`. A missing or
wrong token is `401 {"error": "the agent surface needs Authorization: Bearer <ADMIN_TOKEN>"}`. DNS-rebinding
protection is off on purpose, because the node is reached by LAN IP, `.local` name and tailnet name — the
token is the access control, not the Host header. Reaching it from off the tailnet is a port forward, and the
answer to that is no.

## The tools

Start with `health_check`, then `status`. Four tools write; the rest read.

| tool | arguments | returns |
|---|---|---|
| `status` | — | node, version, schema, uptime, last poll, readings ingested, polls, per-loop errors, mesh, ρ (the `/rho` body), whether the last backup succeeded |
| `health_check` | — | `{ok, checks: [{check, ok, fix}]}` — polled in the last 15 minutes; no source errors; a backup in the last two days; no local sensor's ambient channel frozen; with a broker, LoRa radios heard in the last hour. Every failing check names its fix |
| `issues` | `issue?` | the whole `/issues` object, or one issue — how the place is doing in the household's own words: state, the four distances with provenance, the sentence, the open asks |
| `sensors` | — | one row per sensor from `/stats`: local, indoor, kind, the 15-minute mean per metric, minutes silent; local first |
| `context` | — | sea, weather, satellite air, place and land from `/observations`, labelled; or a note that the first poll fills this |
| `readings` | `sensor_id`, `metric`, `hours=24` (≤168) | hourly means oldest first; or an error naming the sensors that have that metric |
| `history` | `sensor_id`, `metric` | every `{ts, value}` oldest first, for slow series such as `place-point / sat_buildings_yearly` |
| `series` | `metric="pm25"`, `hours=24` (≤168) | aligned hourly arrays: indoor, outdoor, model |
| `alerts` | `limit=10` (≤100) | the most recent alerts with id, level and `acted_at` |
| `report_latest` | — | the last report row |
| `report_bundle` | `hours=6` (1–168) | every number the report was written from |
| `cells` | — | the Fab City Index cells with value, unit and state |
| `packs` | — | the loaded packs: id, kind, description |
| `export_day` | `day?` (default yesterday) | the open-data export for that day |
| `settings_get` | — | every runtime setting with its group, help and value, secrets masked; bootstrap keys read-only |
| `maintenance` | `task` — update, backup, restore, restart, logs, doctor, storage, ui, telegram | the `planetai` command to run on the node, what it does and where. It runs nothing |
| **`act`** | `alert_id`, `note="acted"`, `agent="agent"` | records `stage: acted` for that alert with the agent as actor — **writes** |
| **`report_now`** | `agent="agent"` | writes and sends a report now — **writes** |
| **`settings_set`** | `changes: {KEY: value}`, `agent` | changes runtime settings; live within 20 seconds; a blank returns the key to `.env` — **writes** |
| **`run_pack_script`** | `pack`, `script`, `args?`, `agent` | runs `packs/<pack>/<script>.py` inside the container (15-minute limit) and returns exit code, stdout and stderr — **runs code** |

> **Gap in v0.57.** `llms.txt` and `skills/connect-agent/SKILL.md` still say nineteen tools; `issues` made it
> twenty, and `AGENTS.md` and `planetai agent` say so.

## The audit trail

Every write records who did it, from the tool's `agent` argument: `act` writes it as the action's actor,
`settings_set` as the actor of the `actions` row with `stage='settings'`, and the tools pass it on to the API
as the `X-Agent` header. The default is `agent`, so ask your client to pass its name — `tomas-claude` — in
that argument; the household's bot appears as `local-model/<rung>` because its loop fills it in on every
call. The `X-Agent` header a client sends on `/mcp` itself is not read by the tools. Two agents on one node
read each other's rows before acting.

## What the tools will not do

They will not print `.env` or any token; `settings_get` masks every secret as `•••• set`. They will not run
Docker or git — the container has neither; `maintenance` hands the command back. They will not invent an
action: `act` records what a person said they did. They will not expose the node: the server's own
instructions to a model say to prefer one clear sentence to a list and never to reveal a token.

## For a shell agent

`planetai status --json`, `doctor --json`, `sensors --json`, `cells --json`, and `planetai setup --answers
node.json` to install without a terminal. `planetai snapshot` writes one JSON of everything a stranger may
see, with no raw readings and no token.
