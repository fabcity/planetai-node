# Command line

`planetai` is one bash script, `bin/planetai`, installed as a symlink in `~/.local/bin`. It runs on the
Python the machine already has — Apple's 3.9 with the standard library on a Mac, nothing installed by pip —
and talks to the node over its own [API](api.md) on `localhost:$APP_PORT` with the admin token from `.env`.
`planetai` on its own prints the list; `planetai <word>` on a node that predates the word says so, names the
node's version and suggests `planetai update`. Commands arrive in releases.

Nothing here needs `sudo` except `mesh` (Tailscale), `agent local` on Linux (enabling Ollama as a service)
and, through the installer, `setup` when Docker has to be installed.

## Install and lifecycle

| command | what it does |
|---|---|
| `planetai preflight [--json]` | Can this machine run a node. Checks only, installs nothing. Exit `0` go, `1` fixable, `2` below the floor. |
| `planetai setup` | The four questions, then the installer. On an existing node offers update · reconfigure · nothing · remove. Detects a version gap against the published `VERSION` and an unfinished install. |
| `planetai setup --answers file.json` | Headless install from a JSON file — see [Install](install.md). |
| `planetai status [--json]` | `/health`, sensors, recent alerts and ρ on one screen. |
| `planetai doctor [quiet\|--json]` | Every check with its fix: Docker running, both containers, Postgres ready, `/health`, the app logged in to the database, coordinates set, no stray spaces in `.env`, backup folder mounted, a backup in the last two days, Telegram set, a nightly cron, more than 1 GB free; with profiles, the broker, mesh packets and the Reticulum bridge. |
| `planetai update` | Backup, fetch, migrate, rebuild, verify — [Updating](updating.md). |
| `planetai start` · `stop` · `restart` | `docker compose up -d` · `down` (data kept) · recreate the app container, which is how `.env` changes take effect. |
| `planetai logs [service]` | Follow the container's log; `app` by default, `agent`, `db`, `reticulum` by name. |
| `planetai remove [--keep-data]` | Asks twice — yes, then the node's name typed — and removes containers, volumes, the folder, the crontab line and the command; then checks what is actually left. |
| `planetai version` | Version, node name, city. |
| `planetai geocode <place>` | Run the setup wizard's geocoder on its own. |

## Configuration

| command | what it does |
|---|---|
| `planetai config` | A guided walk through the setting groups; changes are staged, `s` saves, `q` cancels. |
| `planetai config list [--section G]` | Every setting, the value in force and where it came from; red when `.env` and the running value disagree. |
| `planetai config get KEY` | One setting and its source. |
| `planetai config set KEY VALUE` | A runtime key goes to the database and is live within 20 seconds; a bootstrap key goes to `.env` and the command offers the restart. |
| `planetai config unset KEY` | Back to `.env`, or to the built-in default. |
| `planetai config edit` | `$EDITOR` on `.env`, then the offer to restart. |
| `planetai ui` (`dashboard`) | The dashboard's addresses; creates `ADMIN_TOKEN` and `ACT_TOKEN` if missing; prints the three tokens and the sharing level. |
| `planetai test-alert` | Fires one act-level alert through every channel and waits up to 90 seconds for it. |

The settings themselves are on [Configuration](configuration.md).

## Sources and channels

| command | what it does | needs sudo |
|---|---|---|
| `planetai telegram` | Validates the bot token, waits for your first message to learn the chat id, writes both, sends a hello, recreates the app. | no |
| `planetai mesh [up\|status\|down]` | Installs Tailscale and joins the tailnet under the node's name (`TS_AUTHKEY` optional); records `MESH_NAME`. | yes |
| `planetai meshtastic` | Starts the MQTT broker (compose profile `mqtt`), writes its password, prints the gateway radio's settings for your region, waits up to three minutes for the first packet. | no |
| `planetai reticulum` | Starts the LXMF bridge (profile `reticulum`), prints the node's address and the Sideband instructions. | no |
| `planetai homeassistant` (`ha`) | Ensures the broker, sets `HA_DISCOVERY=1`, prints the integration details. | no |

## Reading the node

| command | what it does |
|---|---|
| `planetai report` (`report now`) | Writes a report now and sends it; prints the text. |
| `planetai report last` | The last report. |
| `planetai report every N` | Hours between reports: 3, 4, 6, 8, 12 or 24. |
| `planetai report at H` | The local hour the rhythm counts from. |
| `planetai report level act\|warn\|info` | What interrupts you between reports. |
| `planetai act <id> [note]` | Records that you acted on alert `<id>`; prints ρ. |
| `planetai sensors [--json]` | Every sensor the node reads. |
| `planetai cells [--json]` | The Index cells the node can fill, with their state. |
| `planetai snapshot [--out FILE]` | One JSON of health, issues, stats, alerts, ρ, cells, observations, sensors, trust, the last report, the ring and the forecast, read with the admin token. The file carries no raw readings and no token. |

## The agent

| command | what it does |
|---|---|
| `planetai agent` (`mcp`) | The MCP endpoint, the twenty tools, the header to send, and a ready-made `mcp.json` snippet — see [MCP](mcp.md). |
| `planetai agent local` | Installs Ollama, picks and pulls a model, starts the `agent` container that answers on Telegram — see [The bot](bot.md). Linux: `sudo systemctl enable --now ollama`. |
| `planetai agent stop` | Stops the agent container. |

## Packs

| command | what it does |
|---|---|
| `planetai packs` | What is loaded (from the node) or on disk (when it is down), and whether `packs install` has anything to do. |
| `planetai packs install` | Adds every pack's missing `env:` keys to `.env` under a dated marker, writes the union of their `pip:` lists, rebuilds the image once. |
| `planetai run` | Lists every pack script with its first line. |
| `planetai run <pack> <script> [args]` | Runs it inside the app container with `PACK_OUT=/app/out`. |

See [Packs](packs.md) and [Packs that ship](packs-reference.md).

## Storage and the commons

| command | what it does |
|---|---|
| `planetai storage` | Where the database is and how big; the backup folder, the last dump, the retention; the rclone remote; exports; IPFS; whether a backup token exists. |
| `planetai storage set backups <dir>` | Move the dumps; the folder must be a mounted, writable path. |
| `planetai storage set remote <rclone remote:path>` | Copy the last three days of dumps and every export off the machine after each backup. |
| `planetai storage set keep <days>` | Retention. |
| `planetai storage set data` | Refuses, and explains why the database must stay on an internal disk. |
| `planetai backup` | Dump now, export yesterday, copy to the remote, publish to IPFS if on. |
| `planetai restore <dump.sql.gz>` | Type the node's name; a safety backup; stop the app; drop and recreate; restore; re-apply `init.sql`; start. Dumps carry no `settings` rows. |
| `planetai ipfs` | Start Kubo (profile `ipfs`), turn publishing on; CIDs land in `exports/<node>/CIDS.txt`. |

Where the data lives, and why never on a network mount: [Storage](storage.md).

## Not commands

There is no `planetai publish`, `share`, `rho` or `model`. ρ is printed by `status` and `act`; `/model` is a
Telegram command for the bot; publishing to the Index is done by the Index's own writer, not by a node
([Federation](federation.md)); and sharing is a setting, `SHARE_LEVEL`.

## For scripts and agents

`planetai status --json`, `doctor --json`, `sensors --json` and `cells --json` take the flag and are the four an agent with a shell uses; `planetai setup --answers node.json` installs without
a terminal. The MCP tool `maintenance` hands these back as commands to run, because the container has no
Docker and no git.
