# Start here

You need a computer that stays on, Docker, and the name of a place. A sensor helps but is not required.

## Install

```bash
curl -fsSL planetai.fab.city/node0/install | bash
```

Works on macOS, Linux, a Raspberry Pi 4/5, and Windows with WSL2. The installer asks four things:

1. **A name** for the node. It appears in every alert. `bayu-2`, `lab-roof`.
2. **The place**, typed as words. It finds coordinates and time zone, shows them, and asks before going on.
3. **What the node is for**: a home, a business, a community or lab node, or a district. Sets defaults, nothing more.
4. **Your sensor**, if you have one. Smart Citizen (kit id, or your username to read every kit on the account),
   AirGradient or PurpleAir (address on your WiFi), or none.

Then it installs. First build takes one to three minutes. It ends with a `doctor:` block and `Done!`. A cross next to
*telegram connected* is expected; that is the next step. A cross next to *database* or *node answers* means stop and
read [When it breaks](#when-it-breaks).

Within five minutes the node has its first readings. On the first start it also pulls three months of Copernicus
air-quality history and forty years of NASA climate normals for your coordinates, so it has something to say from day one.

## Get the alerts

```bash
planetai telegram      # message @BotFather, /newbot, paste the token; then message your bot once
planetai test-alert    # fires a real alert within a minute
planetai act 3         # tell the node you did something about alert 3. This is what it measures.
```

The last one matters. The node's own number, ρ, is the share of alerts that led to an action. Nobody else measures it.

## Everyday

```
planetai status      alive? what has it read, what fired, your ρ
planetai doctor      every check, with the fix named next to each failure
planetai ui          the dashboard in a browser, and the token for its settings pages
planetai logs        what it is doing now
planetai update      backup, fetch, migrate, rebuild, verify
planetai storage     where the data is, where copies go
```

`planetai` alone lists everything else: mesh radios, Home Assistant, packs, IPFS.

## A good week

The daily pulse arrives each morning. `planetai status` shows no errors and a growing count. A few alerts, not dozens.
You changed something because of one and told the node with `planetai act`. There is a fresh file in `backups/`.

Dozens of alerts means the thresholds are wrong for your place. Say so; that is the most useful thing a tester can report.

## What it needs from you

Nothing automatic. The database stays on your machine. Raw readings never leave it. If you point the node at a community
node later, hourly averages travel, not rows, and you decide whether to do that at all.

What helps: which alerts were wrong, which were useful, what broke, and whether anyone did anything differently.

## When it breaks

Start with `planetai doctor`. Every line below happened to a real node.

| symptom | first thing to check |
|---|---|
| Nothing installs | Docker is not running. Open OrbStack or Docker Desktop, wait, run the line again. |
| `command not found: planetai` | Open a new terminal window. The PATH change does not reach the old one. |
| `port is already in use` | `planetai config`, set `APP_PORT=8081`, `planetai restart`. |
| No alerts at all | Normal when the air is fine. `planetai test-alert` proves the path. |
| Alerts every few minutes | Thresholds wrong for your place. Tell us. |
| The sensor shows nothing | `planetai sensors`. A Smart Citizen kit must be publishing; an AirGradient must be on the same network. |
| Telegram says nothing | Message the bot first. A bot cannot start a conversation. Then `planetai telegram` again. |
| Stopped after a power cut | Containers restart themselves; the computer must boot and log in on its own. macOS: Login Items, and Energy → start after power failure. |
| A setting changed nothing | `planetai restart`. And no space after `=` in `.env`: `NAME= value` runs `value` as a command. |
| `planetai update` fails on `.DS_Store` | `find . -name .DS_Store -delete`, then update again. |

When you ask for help, send `planetai status`, `planetai doctor` and the last twenty lines of `planetai logs`. Not `.env`:
it holds your bot token and database password. If you paste a log anywhere, check it for `api.telegram.org/bot` first.

## Remove it

`planetai stop` keeps the data. To remove everything: `docker compose down -v` in the node folder, then delete the folder.
