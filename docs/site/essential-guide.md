# The essential guide to a node
<!-- checked: v0.91.0 -->

This page takes a fab lab, a community centre or a city office from an empty machine to a community node that
reads its place, speaks to the people in it, runs a pack written for that place, answers questions on a model of
its own, hands its tools to an agent you already use, and draws the ground around it. One sitting, about two
hours, most of it waiting for downloads. Every command below exists on a v0.91.0 node; where a feature is on
`main` and not yet in a release, the page says so.

The six parts build on each other. Do them in order the first time.

| part | what you have at the end | the proof |
|---|---|---|
| 1. Install | two containers, a database on this disk, readings every five minutes | `planetai status` says `errors none` |
| 2. Readings | a sensor of yours counted, a phone that gets alerts, a first ρ | `planetai cells` shows a value with its state |
| 3. Packs | the packs that fit this place switched on, and one written for it | your message in `planetai status` under `alerts` |
| 4. Local AI | a model on this machine answering the household | the bot answers "is the node healthy?" |
| 5. Your agent | Claude Desktop, Claude Code or any MCP client holding the node's tools over the tailnet | `health_check` returns `ok` with your agent's name in the ledger |
| 6. The ground | the Place door drawing streets, buildings and the cell, from maps kept on the node | the Place door draws the house's kilometre with no internet |

## Before you start

**The machine.** A community node wants a computer that stays on and boots on its own after a power cut. In
order: an x86 Linux box (a mini PC, or an old laptop with Ubuntu Server on it, `REVIVE_A_LAPTOP.md`), a Mac on
macOS 13 or newer (`MAC_MINI.md` has the settings that stop it sleeping), Windows through WSL2. The node itself is
230 MiB across both containers and needs 4 GB of memory and 3 GB of disk. The model in part 4 is what sets the real
floor: 16 GB of memory for the 9B model, 8 GB for the 4B one. Node #1 in Bali runs on a Mac mini with 16 GB.
Nobody has run a node on a Raspberry Pi, a Jetson or a reComputer yet; `docs/ARM64.md` is the test plan for whoever
goes first.

**The place.** The installer asks for a town and finds the coordinates, but a lab should know its own: the point
fixes the H3 resolution-8 cell the node stands in, the 500 m radius inside which a sensor counts as the node's own,
and the kilometre the Place door draws. A community node keeps its own cell and the two rings around it, 19 cells;
a home node keeps 7.

**What leaves the machine.** Raw readings never do. What travels is a daily summary (hourly means, Index cells, ρ),
and only where you point it. At the default `SHARE_LEVEL=off` a screen on your network sees the node's name and
status and no readings until someone unlocks it with a token. Nothing in this guide opens a port on a router.

**An agent beside you.** Most people install a node with an agent in another window. If that is you, paste this
to it and nothing else:

> You are helping me with a PLANETAI node, an open-source program that turns a spare computer in my home or lab
> into a hyperlocal environmental monitor. Start by reading
> https://raw.githubusercontent.com/fabcity/planetai-node/main/AGENTS.md. Its first section is a table that routes
> you to the right skill for what I am asking, and the rest of it is what you must not break. Read that skill before
> you tell me to run anything. Never ask me for the contents of my `.env` file, and never suggest exposing the node
> to the internet; to reach it from elsewhere, use Tailscale.

## 1. Install

```bash
curl -fsSL https://planetai.fab.city/preflight | bash
```

It reads the machine in a few seconds and installs nothing: OS, architecture, memory, disk, container runtime,
`python3`, egress and ports, one row each, with the fix next to any failing row. Exit `0` means install. Exit `1`
means fix the named rows and run it again. Exit `2` means no container runtime can be installed on this OS, and the
answer is Linux on the metal or in a virtual machine, never continuing.

```bash
curl -fsSL https://planetai.fab.city/install | bash
```

The stub fetches the released version's installer, downloads the node's tarball, checks its checksum and its
signature, unpacks it into `~/planetai`, links `~/.local/bin/planetai`, and hands over to `planetai setup`, which
asks four things:

1. A short name for the node, lowercase with dashes (`NODE_NAME`). Name it after the place, not the machine:
   `bayu-ungasan`, not `mac-mini-2`.
2. Where it is. Type the neighbourhood or town; it lists the hits with their time zone and asks you to confirm
   even when there is one. If nothing matches, paste `lat,lon` (`NODE_LAT`, `NODE_LON`, `NODE_TZ`, `NODE_CITY`).
3. What the node is for. Answer **a community or lab node** (`NODE_KIND=community`). A district or region node
   is a different tier with different duties, see [Federation](federation.md).
4. Whether you have a sensor. The installer offers one kit, a Smart Citizen, and asks for its number from the
   smartcitizen.me URL (`SC_DEVICES`). Every other sensor is added in part 2.

After the place, one line names the node's outdoor reference: inside Bali the island's public stations through the
`bali-air-dispatch` pack, everywhere else the Copernicus CAMS model at your coordinates. A place inside Bali,
Barcelona, Boston or Santiago also takes that pilot's preset. **Here's the plan** lists everything and asks
`Install with these?`.

Then seven steps run, each with its elapsed time: the container runtime (installed on Linux if missing), `.env`
with a generated `POSTGRES_PASSWORD` and `ADMIN_TOKEN`, port 8080 and the folders, the database image
(`imresamu/postgis:16-3.4-alpine`, 162 MB), the build, the schema, the checks. The first start pulls 92 days of
hourly PM2.5 and PM10 from the Copernicus air model and NASA POWER's forty years of monthly normals, so the node
has something to say within minutes. The installer adds the nightly backup to your crontab (`17 3 * * *`) and a
second line that lets Set up › Packs install a pack from the page.

Near the end it offers **The map of this place**. Say `y`. It fetches OpenStreetMap as vector tiles in three rings
around the node and any open drone imagery, up to tens of MB, into `out/ground/`, and after that the map is read
from disk. build.protomaps.com and OpenAerialMap learn which square the node is in, once. Without it the Place
door and the Wall draw no streets. If you skipped it, `planetai run place basemap` does the same later.

The last screen is **● Your node is running.**, the dashboard's address on this machine and on your network, and
the settings token. If the terminal says `planetai: command not found`, open a new one.

```bash
planetai doctor
```

One line per check, `✓`, `✗` or an amber `!`, the fix after a `→` under every one that is not `✓`. Below the
checks, **Data sources** lists what the node reads and **To finish setting up** lists what is left, most
important first. Everything in parts 2 to 6 of this page clears a line from that list.

**Without a terminal.** An agent, CI or a provisioning script installs from a file:

```bash
cat > node.json <<'JSON'
{"name": "lab-poblenou", "place": "Poblenou, Barcelona", "kind": "community", "sensor": {"sc": "19880"}}
JSON
planetai setup --answers node.json
```

`sensor` is `{}` or one of `{"sc": "19880"}`, `{"sc_user": "name"}`, `{"airgradient": "host"}`, `{"purpleair": "ip"}`.

## 2. Readings

### 2.1 See that it reads

```bash
planetai status
```

`polls` goes up by one every `POLL_SECONDS` (300). `errors none` means every source answered. `sensors` says
`none of yours yet (models only)` until part 2.2, and `reference` names the first public stations and models it
reads against. Already on, with nothing to configure: Open-Meteo weather at your coordinates, the CAMS air model
at 11 km (PM2.5, PM10, O₃, NO₂, dust, UV), NASA POWER's normals, and the Bali Air Dispatch stations inside Bali.
These are `model` and `reference` rows: they never enter an ambient average and never make a cell say `live`.

### 2.2 Add a sensor of yours

The node polls one sensor with nothing to install, a Smart Citizen kit on the public API:

```bash
planetai config set SC_DEVICES 19880        # your kit's id; or SC_USER=<account> for every kit on it
```

The terminal answers `SC_DEVICES is now 19880, on this node, within 20 s`. Set up › Sources on the dashboard sets
the same key. Wait one poll, then:

```bash
planetai sensors            # id, kind, yours or reference, indoor or outdoor, name
planetai sensors --json     # the same with "custody": true on the rows a cell may count
```

`yours` means the adapter claimed the kit and it stands within `LOCAL_RADIUS_M` (500 m) of the node. A kit on your
account 1.2 km away prints `reference`, because it is not this node's measurement of this place. `indoor` comes
from the kit's own `exposure` on the platform; fix it there if it is wrong, because every air rule depends on it.

Other sensors, each a pack that is on as soon as its key is set:

| sensor | key | notes |
|---|---|---|
| AirGradient on the LAN | `AIRGRADIENT_HOSTS=<host>,…` | read at `/measures/current`, never through the cloud; EPA 2021 correction applied, raw kept |
| PurpleAir on the LAN | `PURPLEAIR_HOSTS=<ip>,…` | read at `/json?live=true`; the two lasers averaged, disagreement stored |
| A Bayu or any DIY board (Making Sense Bali v5) | `planetai broker` | prints the broker address and credentials to type into the board's setup portal; flash the board from Data › Workbench on the dashboard |
| Meshtastic radios in a field with no WiFi | `planetai meshtastic`, then `planetai radio` | one gateway radio on the node's USB, field radios on batteries, `docs/MESHTASTIC.md` |
| Xiaomi purifiers | `planetai packs add xiaomi-air` | a wild pack; the token line is masked once saved |

`SENSOR_INDOOR=1` marks AirGradient and PurpleAir units as indoors. Mount an outdoor kit three to six metres up,
away from a kitchen exhaust, a chimney or a parking spot, and name it after the place: the name becomes the sensor's
name on the page and in every message.

### 2.3 Watch it become a cell

```bash
planetai cells
```

`Environmental|Community` carries a value, a state and the unit `µg/m³ PM2.5 (24h mean, sensors in this node's
custody)`. The state reads `partial` until the node holds 12 hourly buckets from sensors in its custody in the last
24 hours, and `live` after that. `custody` is a generated column, `kind = 'child' OR (local AND kind <> 'peer')`;
no adapter writes it. That row is the only form in which a place's measurements reach the Fab City Index. A
community node that is not a pilot's writer never publishes it anywhere; `skills/publish-to-index` and
[Federation](federation.md) explain who does.

### 2.4 Close the loop once

```bash
planetai telegram      # make a bot with @BotFather, paste its token, then message the bot once
planetai test-alert    # a rule that always fires is added, waits up to 90 s, and removed; your phone gets one message
planetai act 12 "read the test alert on my phone"   # the id the test printed; every word after it is the note
```

`planetai status` now shows `rho 1.0 (1/1 act-level alerts answered, 30d)`. ρ is the share of act-level alerts
somebody answered within 24 hours over the last 30 days, and it is the one number on the page that comes from a
person. For more people on the channel, comma-separate their chat ids in `TELEGRAM_CHAT_IDS`.

### 2.5 Open the dashboard

```bash
planetai ui
```

It prints the address on this machine and on your network, and three tokens: admin (Set up, treat it like a
password), backup (read-only, for a NAS), act (closes a loop from a phone, can read no secret and change no
setting). Open the page, go to Set up › This screen, paste the admin token and press **Unlock this screen**. The
readings appear. Under "A phone", **Show the code** draws a QR that opens the phone page holding the act token.

The page opens on five doors, Now, Place, Data, Node and Wall, with Set up behind the gear. A phone lands on the
phone page (`?layout=mobile`); the earlier six-view dashboard is at `?layout=classic`. Set up › Rooms is where you
name the room each sensor is in; a screen without the token reads "Room A" and "Sensor 1" instead.

The node now reads, counts, asks and measures. The nightly backup runs at 03:17; `planetai backup` makes one now,
and `docs/STORAGE.md` says how a NAS collects them.

### 2.6 What the node does by itself from here

None of this needs setting up; each has one switch where you might want to change it.

| it | where | the switch |
|---|---|---|
| A report in sentences every six hours, and a morning message with what the house learned | Telegram; `planetai report` prints the last one | `planetai report every 6` and `report at 7` for the rhythm; Set up › Alerts for quiet hours and how many alerts a day (`ALERT_MAX_PER_DAY`); `LEARN_PUSH` for the morning diary |
| Next days: the rest of today, tomorrow and the day after, air and heat judged against the same lines the alerts use, wind and rain, the sea | Now, under What to do | BMKG answers inside Indonesia with nothing set. The air, the sea and the gusts need `FORECAST_OPENMETEO=1`; it ships off because Open-Meteo's free tier is non-commercial, and turning it on is the operator's call |
| After a week, the hour the street is cleanest and how much of it the building keeps out; after a month, what worked | the morning message, the `learned` tool for an agent | on by default; none of it leaves the machine |
| A screen on the lab's wall that walks out from the house through four scales by itself | the Wall door, `/#wall` | `SHARE_LEVEL` under Set up › Sharing: `off` shows name and status only; a lab that wants the readings on a wall sets it and reads [Sharing](sharing.md) first |
| Three languages for every alert, report and page | everywhere | `ALERT_LOCALE`: `en`, `id`, `es` |
| A daily open-data export, CC BY 4.0, one JSON a day | `exports/<node>/` | where it goes is yours to decide; `planetai` lists the IPFS command |
| The node's sensors and its latest alert as entities in Home Assistant, which does the switching | Home Assistant, over MQTT discovery | `HA_DISCOVERY` (the `home-assistant` pack); the node never addresses a device |
| Pictures of the place, kept on the machine and described by an image model; a plant or animal named by GBIF | **+ Add an image** on Place, or a photo sent to the bot | `EYES_MODEL`; species only with the household's yes (`SPECIES_MATCH`) |
| The things the lab keeps, counted privately, and the ones it would lend or give, published | `GET /things`, `GET /offers` | the `things` pack, on by default |

## 3. Choose your packs, then write one

A pack is how a place teaches its node what to watch and what to say about it. The core names no metric: what
`pm25` means, which line matters here, and the sentence a person should read at 9 pm are all written in a pack.
Twenty-five core packs ship in `packs/` and most are already on. Before writing anything, open Set up › Packs,
or run `planetai packs`, and read [Packs that ship](packs-reference.md): for every pack it says what it reads,
what it says, where each threshold came from and what it does not know. Then switch on the ones your place has a
use for, and off the ones it does not. The ones a lab or community node usually decides about:

| if your place | pack | what to set |
|---|---|---|
| is near the sea | `coast` | `COAST_MAX_KM`; waves, swell and sea temperature from Open-Meteo Marine, no key; `posidonia` (wild, Lucas Marangoni, Menorca) reads thermal stress on seagrass from it |
| burns, or sits downwind of fields that do | `fire` | `FIRE_ENABLED=1`, a free NASA FIRMS key in `FIRMS_MAP_KEY`, and `PACKS_ALLOW_CODE=1`; says when a fire is near, and when one is upwind |
| has a public open-data portal | `open-data-health` | `CKAN_PORTALS=slug=url`; a `Governance\|City` cell from how much of the portal was touched in 90 days |
| has a repair café or a ThingData server | `thingdata` | `THINGDATA_INSTANCES`; how many things are described and whether anyone is still writing |
| wants the nearest fab lab named in the report | `make` | `MAKE_ENABLED=1` and `PACKS_ALLOW_CODE=1`; read its README first, the Fab Lab Network directory is not openly licensed |
| wants the ground's heat and the land's change from orbit | `surface-heat`, `earth`, `earth-engine` | `surface-heat` and `earth` are key-free; `earth-engine` needs a Google Earth Engine credential (`EE_*`) and brings Dynamic World, NDVI and the yearly buildings |
| wants to know where the rain goes | `terrain` | `planetai run terrain fetch` once; Copernicus DEM GLO-30, routed on the node |
| is in Bali | `bali-air-dispatch`, `nearby`, `season` | the Bali preset sets `BAD_ENABLED=1`; `nearby` tells a fire in the lane from a haze over the island, `season` says whether this week is worse than the weeks before |
| wants the one-day scaffold gone | `cold-start` | delete it once your own sensors report; its README says so |

Every pack a node loads shows in Set up › Packs with its switch and its settings, a switched-off one included.
Under them is the wild list, the packs other nodes wrote: `xiaomi-air` (purifiers on the LAN), `tuya-indoor`
(room sensors through the Tuya cloud), `wyze-camera`, `singapore-nea` and `singapore-beach` (Saad Chinoy's
Singapore node, from data.gov.sg), `fire-smoke` (FIRMS within 500 km by compass sector), `bmkg-synop` (the
airport's hourly report over WMO WIS2), `paddy` (rice land kept and lost, from Sentinel-2) and `surf` (two days
of swell for up to three spots, with buttons to say how it was). Ten listed on 6 November 2026, each with who wrote
it, what it reads and the node version it was tested with. Press **Install** on one and the node shows the
commit and whether it runs code before fetching anything.

A pack for your place that none of these covers is a wild pack of your own, in its own repository, never a fork
of the node. A data pack is SQL and words. Make one in ten minutes, then move it to your place.

**Make the folder.** In `~/planetai`, create `packs/<id>/pack.yaml`. The id is the folder's name.

```yaml
id: my-room
name: Workshop floor
description: How warm the workshop floor has been, as one alert a day and one Index cell.
version: 0.1.0
requires: { node: ">=0.76.0" }
domain: heat
```

`packs/` is mounted into the container and read on every pass, so `planetai packs` lists it within a minute, under
`loaded now:`. `domain: heat` puts its alerts under the heat issue on the dashboard; `air`, `land`, `coast`,
`place` are the others, and a pack that fits none declares its own in an `issue.yml`.

**Teach it one thing to say.** `packs/my-room/rules.yml`, with the line set low on purpose so it fires now and
you see the whole path:

```yaml
- id: floor_warm
  level: info
  cooldown_minutes: 1440
  sql: |
    SELECT sensor_id, name, mean_1h FROM stats
    WHERE local AND metric = 'temp' AND mean_1h > 20
  message:
    en: "🌡️ {name} has averaged {mean_1h:.1f} °C over the last hour.\n\n👉 Open the roller door on the shaded side before the afternoon."
    id: "🌡️ Suhu rata-rata {name} {mean_1h:.1f} °C selama satu jam terakhir.\n\n👉 Buka pintu gulung di sisi yang teduh sebelum sore."
    es: "🌡️ {name} ha promediado {mean_1h:.1f} °C durante la última hora.\n\n👉 Abre la persiana del lado de la sombra antes de la tarde."
```

Rules run every 60 seconds as the read-only role `planetai_ro`. Every `{placeholder}` must be a column the SELECT
returns. `stats` holds the last 24 hours per sensor (`mean_15m`, `mean_1h`, `mean_24h`, `silent_minutes`, `local`,
`indoor`); `readings_1h` holds hourly means over all history; `usual_by_hour` holds each room's own median for each
local hour. `planetai status` prints your message under `alerts` with the sensor's name filled in. If nothing
appears, `planetai logs | grep my-room` shows Postgres's reason.

**Say which Index cell it becomes.** `packs/my-room/cells.yml`:

```yaml
- cell: "Environmental|Community"
  unit: "°C (24h mean, sensors in this node's custody)"
  state: live
  min_buckets: 12
  notes: "my-room: every temperature channel in custody, hourly means, last 24 h"
  sql: |
    SELECT avg(mean) AS value FROM readings_1h r JOIN sensors s USING (sensor_id)
    WHERE s.custody AND r.metric = 'temp' AND r.bucket > now() - interval '24 hours'
```

`state` is provenance. `live` means measured here. Never claim `live` for a model; the core demotes it to
`partial` when the buckets are too few, and a `NULL` value leaves the cell out, so absent is never zero.

**Move the line to your place.** Change `20` to the temperature the workshop should not pass and say in a
`README.md` where the number came from. Thresholds written for Kuta Selatan are not thresholds for Poblenou. To
make it an alert that asks for something, set `level: act`, keep `cooldown_minutes` at or under 2880, add
`watch: {metric: temp, over: <the same number>}` so the node can time how long the action took to work, and put
`{line}` in the message so it names the line. A rule can also ask with buttons: return a `buttons` column and with
`TELEGRAM_BUTTONS=1` they reach the phone as a keyboard, and Now lists them under What to do. `{act}` in a message
prints the alert's own `/act 812`.

On a checkout of the repository, `python3 tools/check_rules.py` parses every pack against `init.sql` and names any
placeholder the SQL does not return.

**A pack that fetches.** A folder with an `adapter.py` is a code pack: `fetch(hc) -> (sensors, readings)` adds a
source the core does not read. It runs with the node's privileges and network, so it runs only with
`PACKS_ALLOW_CODE=1`; its `pip:` list is built into the image by `planetai packs install`; a key it needs goes
under `secrets:` so Set up masks it. `packs/earth-engine` is the worked example. A pack can also declare, as data
and with no code, a band on the dashboard (`sections:`), numbers added to an issue (`readouts:`) and a line in Next
days (`ahead:`); `docs/PACKS.md` has every field.

**Share it.** Make a repository that is the pack folder, run `python3 tools/check_rules.py` from the node's folder,
file any source it reads in `fabcity/awesome-fabcity-data` so `sources:` can name it, and add one entry to
`packs.json` in `fabcity/planetai-wild-packs` by pull request. Any node then installs it from Set up › Packs
(**Install** shows who wrote it, the commit, what it reads and whether it runs code, before anything is fetched)
or from the terminal:

```bash
planetai packs add <owner>/<repo>        # or an id from the wild list: posidonia, surf, paddy, xiaomi-air
planetai restart
planetai packs                           # under wild:, with its commit and the day it was added
```

A wild pack is pinned to a commit and fetched with curl and tar, because a default install has no git. To remove
one, delete `packs/<id>` and restart.

## 4. Connect your local AI

A node needs no model: every number is the node's own arithmetic and every alert comes from a template. What a
model adds is conversation, asking "is the air bad right now?" in your own words, and saying "I closed the
windows" and having it recorded.

```bash
planetai agent local                    # installs Ollama, starts the agent container and the Telegram bot; downloads no model
planetai agent local pull qwen3.5:9b    # 6.6 GB, the recommendation at 16 GB and up; qwen3.5:4b (3.4 GB) at 8 GB
```

`planetai agent local` prints the recommendation for this machine's memory and stops; `pull` fetches the tag and
points `AGENT_MODEL` at it. The model must do tool calling: the loop hands it the node's tools and expects it to
call them, and a model that cannot will answer plausibly about a node it never read. On Linux the command sets
`OLLAMA_URL=http://172.17.0.1:11434` and Ollama must listen on `0.0.0.0` so the container can reach it; it says so.

Then message your bot: "is the node healthy?", "how is the air?", `/act 23 closed the windows`, `/model`. The
local model gets the 17 `read` and `act` tools and never the admin ones; it cannot change a setting, run a pack's
code or message the household unprompted. It shows in the ledger as `local-model/<rung>`.

**The ladder.** Set up › Model (or `planetai config set`) names two more rungs, for the bot and the dashboard's
ask pane alike:

| rung | keys | where it runs |
|---|---|---|
| local | `AGENT_MODEL` | this machine, through Ollama |
| remote | `AGENT_REMOTE_URL`, `AGENT_REMOTE_MODEL` | a bigger model on your own network: a laptop's Ollama at `http://<laptop>.local:11434/v1` with `OLLAMA_HOST=0.0.0.0` set on it, or an mlx-lm server on a workstation |
| online | `AGENT_ONLINE_URL`, `AGENT_ONLINE_MODEL`, `AGENT_ONLINE_KEY` | Anthropic, OpenAI or anything that speaks the OpenAI chat API |

`AGENT_PREFER` decides the order. `private`, the default, tries your network, then this machine, and never goes
online; a remote model at a public address counts as online. `fallback` tries your network, then online, then this
machine. `strongest` goes online first. A lab that keeps one workstation with a large model can leave every node
at `private` with `AGENT_REMOTE_URL` pointing at it over the LAN or the tailnet, and nothing leaves the building.

**The ask pane.** On the dashboard, the speech bubble in the bar opens a pane that asks the same model through the
same tools, with the door you are on as its context. Its header says which model answered and where it runs. It
runs reads only; a change goes on a card for a person to press. Nothing asked or answered is stored, and every
tool result the model reads has had the coordinates, the sensor names and the ids removed first. With no model set
up, the box searches these docs instead. `UI_ASK=off` removes it everywhere.

## 5. Use it with your own agent over MCP

The node is an MCP server, streamable HTTP at `/mcp`, with twenty-one tools over its own endpoints. Claude Desktop,
Claude Code, Codex, Cursor, mcphost or oterm with a local Ollama, any client that speaks MCP over HTTP, holds the
same tools the household's bot holds, plus the admin ones, because a person reads what it proposes.

**Put the node on your tailnet.**

```bash
planetai mesh
```

It installs Tailscale, joins the tailnet under the node's name after you approve it once in a browser, and records
the MagicDNS name as `MESH_NAME`. The node answers as `<name>.<tailnet>.ts.net` from any of your devices, with no
port opened on any router. On Linux it also turns on Tailscale SSH. Never a port forward, ngrok or a public reverse
proxy: DNS-rebinding protection on `/mcp` is off because the node is reached by LAN IP, `.local` name and tailnet
name, so the token is the only gate.

**Get the snippet.**

```bash
planetai agent
```

It prints the tools by class, the endpoint on this machine (`http://localhost:8080/mcp`) and on the tailnet
(`http://<MESH_NAME>:8080/mcp`), the header every call carries, and a block to paste into `mcp.json` or
`claude_desktop_config.json`:

```json
{"mcpServers": {"planetai-lab-poblenou": {"type": "http",
  "url": "http://lab-poblenou:8080/mcp",
  "headers": {"Authorization": "Bearer <ADMIN_TOKEN>", "X-Agent": "lab-claude"}}}}
```

The token in it is the admin token, so the file is a password. For Claude Code from anywhere:

```bash
export PLANETAI_MCP_URL=http://lab-poblenou:8080/mcp PLANETAI_ADMIN_TOKEN=<token> PLANETAI_AGENT_NAME=lab-claude
claude mcp add --transport http planetai "$PLANETAI_MCP_URL" \
  --header "Authorization: Bearer $PLANETAI_ADMIN_TOKEN" --header "X-Agent: $PLANETAI_AGENT_NAME"
```

In a clone of the repository `.mcp.json` is already there and reads those three variables from the shell, so
nothing secret is in the file. Cursor does not expand `${VAR:-default}`; paste the printed block instead.

**Tell the agent its name, then read before you write.** The ledger records the name passed in each write tool's
`agent` argument, not the header. Say it once: "your name for this node is lab-claude; pass it as `agent` on every
write." Then: "Call `health_check`, then `status`." `health_check` answers `ok` and a list of checks, each failing
one with its fix; `status` gives the node, version, last poll, per-loop errors and ρ.

The tools by class, from `app/tool_classes.py`:

| class | tools |
|---|---|
| `read` | `status`, `health_check`, `sensors`, `context`, `readings`, `report_latest`, `report_bundle`, `history`, `alerts`, `settings_get`, `packs`, `cells`, `issues`, `series`, `export_day`, `learned` |
| `act` | `act` (needs the person's own words; refuses a blank note and placeholders such as `done` or `ok`) |
| `admin` | `settings_set` (live within 20 s, recorded as a settings row), `run_pack_script` (a core pack's scripts, or a wild pack's listed under `agent_scripts:`), `report_now`, `maintenance` (hands back the `planetai` command to run; runs nothing, because the container has no Docker and no git) |

Gap in v0.91.0: `readings` answers with an error for every sensor; use `series` (aligned hourly arrays, indoor,
outdoor, model, up to 168 h) or `history` instead.

**Record an act through it.** "I closed the north door about alert 361." The agent calls `act` with `alert_id`
361, your words as `note` and its name as `agent`, and gets `{"recorded": true, "alert_id": 361, "by":
"lab-claude"}`. On the dashboard, Data › Ledger shows `lab-claude` with `acted` at the top, and it counts in ρ.
A remote agent is not alone on the node: the household's model is there too, so it reads the alerts and the
actions before acting and does not undo what the bot did without asking.

For a shell agent on the node, `planetai status --json`, `doctor --json`, `sensors --json`, `cells --json`, and
`planetai snapshot`, one JSON of everything the node answers with no raw readings and no token in it.

## 6. The hyperlocal GIS: the Place door

The Place door is the ground around the node, drawn from maps the node keeps on its own disk and geometry it
computes itself. Two packs feed it. The `place` pack fetches everything within `PLACE_RADIUS_M` (1,000 m) from
OpenStreetMap into PostGIS and summarises it monthly: buildings and how much ground they cover, shops, schools,
clinics, places of worship, kilometres of road, the share of green, the walk to the nearest of each. The basemap
from part 1 is the drawing under it. The `earth-engine` pack, with credentials, adds Google Open Buildings
footprints and the yearly building count and height since 2016; the `earth` pack adds the AlphaEarth year compare;
`terrain` adds the Copernicus DEM; `surface-heat` adds the ground's heat from Landsat and MODIS.

**Turn the place pack on.** It is a code pack, so:

```bash
planetai config set PACKS_ALLOW_CODE 1   # or Set up › Packs, which asks once before saving a key that runs code here
planetai packs install                    # builds every loaded pack's libraries into the image, once
planetai restart
planetai run place verify                 # PostGIS, OpenStreetMap, Earth Engine, Open Buildings: each step named
```

The first poll fetches the kilometre from the Overpass API; later polls recompute from what is stored, and every
`PLACE_REFRESH_DAYS` (30) it fetches again. `planetai run place refresh` forces one. Node #1 in September 2026 held
2,904 buildings, 540 road segments and 37 mapped places within its kilometre, and no school, which is
OpenStreetMap's coverage of the Bukit, not the Bukit. Zeroes mean unmapped. `planetai run place gaps` writes
`out/place-gaps.md`, a briefing for a mapping afternoon at the lab: the untyped buildings, the categories with
nothing, the named places without hours, the unnamed streets. StreetComplete, Every Door and iD over Bing or Esri
fix the map; never from Google imagery.

**What the door draws on v0.91.0.** The head gives the cell's id, resolution, edge and area. The map has fourteen
layers behind tabs, the H3 grid at the zoom's resolution, inspect and measure, a back-to-the-house button, PNG
export, the 2, 5 and 15 km rings, and three views: the map, From orbit (the Sentinel-2 years side by side with the
hectares that changed), and What changed. Under it, where the readings come from, the species confirmed here from
the household's images (GBIF, marked introduced or invasive from GRIIS), and what is changing. **+ Add an image**
takes a photo from a phone, a fixed camera, a microscope, a drone, a balloon or a kite; the node strips EXIF and GPS
and keeps the picture; the image model on the node describes it once `EYES_MODEL` names one.

**What is on `main`, unreleased after v0.91.0 (merged 4 November 2026, PR #376).** Place is redrawn as a small GIS
on Ian McHarg's layer cake, three columns around a black screen. On the left, the cake: results, then
microclimate, flows, built, animals, plants, soil, water, ground and frame, the sky at the top and the ground at the
bottom, one row a layer with a dot that is filled for on, hollow for off and dotted for a layer this node does not
hold yet, with its source named beside it (canopy, SoilGrids, terrain, geology, the flows log, samples). In the
middle, the screen: the map, the hour pill, the scale rungs (street, block, cell, village, district), inspect,
measure, from the house, PNG. On the right, the tools: **Rings and distance** runs today; sun and shade, trees
(3-30-300), built form, sealed ground, streets, walking, what changed, where the rain goes and four fitness tools
(`fit.tree`, `fit.roof`, `fit.grow`, `fit.rain`) are listed as not yet. Under the screen, what you selected and the
place in figures. Nothing from inside the house is listed or drawn, and the rooms are gone from Place.

The steps that follow, each its own pull request run on node #1 first (`docs/SPEC_place_microgis.md` §12): a tool
registry (`GET /place/tools`, `POST /place/run/<id>`) that the panel and the ask agent both call, so every tool a
person can press an agent can run from a sentence; the hours bar; soil and water samples as observations with their
method and date; the analyses one by one; light fitness, each a fixed rule that points at an action and never
gives a score, ending in the flows line the household would log (`produce.electricity.cell` is the roof). Heavy work
goes to the fab lab node: OpenDroneMap, microscopy identification, anything with a large model. The drone path
already works: the lab publishes to OpenAerialMap and `planetai run place basemap --only drone` fetches it.

**Privacy.** The grid, the rings, every distance and `/place/geojson` need a token at every sharing level, because
together they place the house. A screen without the token sees the layers with their sources and counts, the
published cell and the yearly figures, and says what it is not drawing and why. Nothing finer than the node's
resolution-8 cell is published to a reader without a token or in an open export.

A git checkout of the repository gets the new Place now with `planetai update`; a node installed from the
release line gets it with the next tag.

## Keep it running

```
planetai status      is it alive, what has it read, what fired, ρ
planetai doctor      every check, with the fix written next to any failure
planetai logs        what it is doing right now
planetai update      backup, fetch the latest version, check its signature, migrate, rebuild, verify
planetai storage     where the data is, where the copies go
```

Every update is signed and a node refuses one that does not verify. A good week is a short report a few times a
day, a handful of alerts, one or two that changed what somebody did, and a fresh file in `backups/` every morning.
Dozens of alerts a day means the thresholds are wrong for your place; write to us with which ones rather than raising
them, because a node that is quiet only because you raised its threshold is lying to you.

`main` is the beta channel. When something breaks, send `planetai status`, `planetai doctor` and the last twenty
lines of `planetai logs` to **info@fab.city**, with what you expected as well as what happened. Never `.env`: it
holds your tokens.

## Where this leads

[Sensors and sources](sensors.md) for every adapter and the rules the node inherits from Bali Air Dispatch's
methodology; [Packs](packs.md) for the whole contract; [MCP](mcp.md) for every tool with its arguments;
[Federation](federation.md) for what a community node sends upward and who writes to the Index.
