# Configuration

Every setting a node has, what it does, and where its value comes from. Read against v0.57.

## How a setting is read

The base is `.env` in the node's folder. `install.sh` writes it, it holds the tokens and the database password, and
it is never committed. Keep it `chmod 600`. Docker hands the whole file to the `app`, `agent` and `reticulum`
containers at start.

On top of `.env` sits the `settings` table in the database. A **runtime** setting can be overridden there from
four places: the dashboard's Set up view, `planetai config set`, `PUT /settings` with the admin token, and the MCP
`settings_set` tool. The override wins over `.env`, the node sees it within about 20 seconds (the settings cache
lives that long), and nothing needs a restart. Writing a blank value deletes the override, and the node falls back
to whatever `.env` says, then to the built-in default. `GET /settings` reports the source of every value as
`gui`, `env` or `default`, and `planetai config list` prints the `.env` value in red when the database is
overriding it, so the file is never silently wrong.

A **bootstrap** setting is read once, by Docker when it composes the containers or by the process when it starts:
the node's name and position, the port, the compose profiles, the backup paths, the poll interval. The dashboard
shows these read-only. To change one, edit `.env` and run `planetai restart`. `planetai config set` does the edit
for you and offers the restart.

A few keys are read from the environment only and are not editable through the API at all. They are not runtime
settings and not in the bootstrap list, so `PUT /settings` refuses them and `planetai config set` says they are
not a setting this node has. They are `ADMIN_TOKEN`, `POSTGRES_PASSWORD`, `DATABASE_URL`, `OLLAMA_URL`,
`AGENT_MODEL`, `MQTT_USER`, `MQTT_PASS`, `RETICULUM_URL`, and the keys packs declare in their `pack.yaml`
(`FORECAST_*`, `EARTH_*`, `PLACE_*`, `OVERPASS_URL`, `EE_SERVICE_ACCOUNT`, `BAD_BACKFILL_DAYS`). Edit them in
`.env` and restart.

A handful of keys are read through `settings.get` by the app but through the plain environment by the code that
acts on them: `NODE_KIND`, `COAST_MAX_KM`, `EE_PROJECT`, `EE_KEY_FILE`. They accept an override, and the override
does nothing. See [Known gaps](#known-gaps-in-v053).

### Validated values

Most settings are free text on purpose: a node has to keep running through a typo. Six keys refuse a value they
cannot honour, because a report interval the scheduler cannot keep would make the node silent instead of wrong.

| Setting | Accepted |
|---|---|
| `REPORT_EVERY` | `3`, `4`, `6`, `8`, `12`, `24` |
| `REPORT_ANCHOR` | `0` to `23` |
| `REPORT_DEPTH` | `auto`, `brief`, `standard`, `deep` |
| `AGENT_PREFER` | `strongest`, `fallback`, `private` |
| `SHARE_LEVEL` | `off`, `open` |
| `MAP_TILES` | `off`, `on` |

`PUT /settings` answers 400 for anything else, and `GET /settings` publishes the list under `choices` so the
dashboard offers the values instead of a text box. `SHARE_LEVEL` names `cell` and `means` in its help; both are
reserved and refused today.

A number that ships blank in `.env` keeps the code default. `update.sh` copies new keys into your `.env` with the
value they carry in `.env.example`, and the `REPORT_*` keys ship blank so an updating node keeps the rhythm it had.

### Public and outward

**Public** is the set of runtime keys whose value an anonymous `GET /settings` may see. Everything else shows as
`•••• set` until the admin token is presented. Chat ids, sensor hosts, account names and remote URLs are not
secrets, but they are the household's, and `GET /settings` answers anyone on the WiFi. At `SHARE_LEVEL=off` a
caller who is neither on this machine nor carrying a token sees the values of `UI_LAYOUT` and `SHARE_LEVEL` only.
A secret is masked for everyone, at every level; `GET /settings/raw` with the admin token is the one unmasked read.

**Outward** marks the keys that change what leaves this machine, as opposed to what the node does with what it
keeps: who it speaks to, where it posts means, whether it announces itself on radio, whether the online model is
used at all. The node declares the set so every surface can draw those settings apart from the one that says how
far the sea is.

### Rules of the `.env` file

- No space after `=`. `VAR= value` is a shell command, not an assignment.
- A comment goes above a key that ships blank, never after it. Compose strips a trailing comment only when the key
  has a value, so `KEY=   # note` hands the container `# note` as the value. Node #1 once held the text of a
  comment in `AGENT_ONLINE_URL` this way.
- `planetai doctor` checks the file for stray spaces.

### Retired keys

`BRIEFINGS`, `BRIEF_MORNING`, `BRIEF_EVENING` and `BRIEF_HOUR` belonged to the two-briefings schedule. Nothing
reads them. Rows for them are left in `settings` and in `.env` so an updating node does not lose a value it chose;
a node that had `BRIEF_MORNING=7` is migrated once to `REPORT_EVERY=12`, `REPORT_ANCHOR=7`, and a fresh install
takes `6` and `6` from the defaults.

## The command line

`planetai config` works on the value in force: it reads `GET /settings`, so it sees the database overlay, and
falls back to `.env` when the node is down. Runtime keys are written through `PUT /settings` with
`X-Agent: planetai-cli`; bootstrap keys are written to `.env`.

| Command | What it does |
|---|---|
| `planetai config` | Guided walk: categories, then the settings in one. Changes are staged; `s` saves them in one call, `q` cancels, `b` goes back. Needs a terminal. |
| `planetai config --section G` | Straight into one category. The categories are the groups below: `issues`, `sources`, `alerts`, `integrations`, `packs`, `keys`, `agent`, `node`, `bootstrap`. |
| `planetai config list [--section G]` | Every setting, its value in force and where it came from. Red means `.env` holds something else and is being ignored; a value set from the dashboard says so. |
| `planetai config get KEY` | One setting: its help, the value in force, its source, and whether `.env` disagrees. Says when a restart is needed. |
| `planetai config set KEY VALUE` | A runtime key goes to the database and the node has it within 20 s. A bootstrap key goes to `.env`, and the command offers `planetai restart`. |
| `planetai config unset KEY` | Removes the database override, back to `.env` or the built-in default. |
| `planetai config edit` | Opens `.env` in `$EDITOR` (nano by default) and offers a restart. This is what `planetai config` used to be. |

Shortcuts for the settings people change most:

| Command | Sets |
|---|---|
| `planetai report every N` | `REPORT_EVERY`, one of 3, 4, 6, 8, 12, 24. |
| `planetai report at H` | `REPORT_ANCHOR`, 0 to 23. |
| `planetai report level act\|warn\|info` | `ALERT_LEVEL`, what interrupts between reports. |
| `planetai telegram` | Validates the bot token with `getMe`, waits up to two minutes for you to message the bot, writes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` to `.env` and to the runtime settings, sends a hello, recreates the app. |
| `planetai ui` | Creates `ADMIN_TOKEN` and `ACT_TOKEN` in `.env` if either is missing (and recreates the app), then prints the dashboard URLs, `SHARE_LEVEL` and the three tokens: admin, backup, act. |
| `planetai storage set backups DIR` · `set remote REMOTE:PATH` · `set keep DAYS` | `BACKUP_DIR` (checked to be a mount point and writable), `BACKUP_REMOTE`, `BACKUP_KEEP`. `set data` refuses and explains why `DATA_DIR` must be an internal disk. |
| `planetai packs install` | Appends the `env:` keys of every pack to `.env` under a dated marker, with their explanation lines, then rebuilds the app image. |

## Reference

Kind is `runtime` (database overlay, live within 20 s), `bootstrap` (read at start, edit `.env` and restart) or
`env only` (read from the environment, not editable through the API). `public` means an anonymous `GET /settings`
may see the value; `outward` means the key changes what leaves the machine; `secret` means the value is always
masked; `restart` means the setting is runtime but the container that reads it picks it up at its next start.

## Identity and place

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `NODE_NAME` | `node`; `.env.example` ships `bayu-2` | lowercase, dashes | The node's name. Appears in `/health`, `/export`, the MQTT client id and Home Assistant ids, the pushes to a parent, and the `out/earth/<name>` folder. | bootstrap |
| `NODE_KIND` | `home` | `home`, `business`, `community`, `district` | Defaults and which packs load; not the Index scale. `planetai setup` sets `NODE_SCALE=city` for a district. In v0.57 the only reader is `/presence`, which reads the environment. | runtime · public |
| `NODE_SCALE` | `community` | `community`, `city`, `region` | The Full Stack Metrics scale. Stamped on sensors, sent with pushes to a parent, in `/export`, and capitalised for the `Governance\|<Scale>` cell. | bootstrap |
| `NODE_CITY` | `unknown`; `.env.example` ships `bali` | pilot key or slug | The city key in Index cells, `/health` and `/export`. `planetai setup` picks a pilot key by bounding box for bali, barcelona, boston and santiago, else a slug of the place. | bootstrap |
| `NODE_LAT`, `NODE_LON` | `0` | decimal degrees | The node's position. Handed to Postgres, used for local stamping, the first-start bootstrap, the presence cell and the ground map. Rounded to three decimals (about 110 m) in `/health`, `/export` and an untrusted `/sensors`; unrounded in `/forecast`, `/earth` and `/place/geojson`. `install.sh` refuses to start without them. | bootstrap |
| `NODE_TZ` | `UTC`; `.env.example` ships `Asia/Makassar` | IANA name | The database session time zone: local midnight and local hours in rules, reports and quiet hours. Also `TZ` of the agent container; echoed in `/health`. | bootstrap |
| `NODE_ISSUES` | blank = every issue | comma list of `air`, `heat`, `land`, `coast` | What this place watches, most important first. The first is where the dashboard starts; the one with something to say takes the top. A name nothing declares is ignored with a line in the log. Your preset guessed for this place; change it. | runtime · public |
| `NODE_VERSION` | written by `install.sh` | string | `git describe`, the `VERSION` file, or `dev`. Shown in `/health`, `/presence`, `/export`. | env only |
| `LOCAL_RADIUS_M` | `500` | metres | How far from the node a sensor can be and still count as this node's own. A kit of yours further than this is yours but not here: it stays out of the ambient average and out of every `live` claim. | runtime · public |

## Sharing and security

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `SHARE_LEVEL` | `off` | `off`, `open` | What a request with no token may read. `off` = the dashboard shell, `/health` with the position rounded, the daily export and the layout, and nothing else. `open` = the whole read API to anything on your network, so a wall screen or a phone works with no token; writes still need one. A request with a token reads everything at either level. See [the API](api.md). | runtime · public · outward |
| `ADMIN_TOKEN` | blank; `install.sh` generates one | hex string | Unlocks `PUT /settings`, `/settings/raw`, `POST /readings`, `/report/now`, `/test-alert` and the whole `/mcp`; also accepted where `BACKUP_TOKEN` or `ACT_TOKEN` would be. `planetai ui` creates and prints it. | env only · secret |
| `BACKUP_TOKEN` | blank; `update.sh` generates one | string | Read-only: lets a NAS fetch `/backups`, `/backups/<name>` and `/report/bundle`. Separate from the admin token and cannot read `/settings/raw`. `planetai storage` reports whether it is set. | runtime · secret |
| `ACT_TOKEN` | blank; `planetai ui` generates one | string | Lets someone in the house record that they acted on an alert (`POST /actions`) from off this machine without holding the admin token. It cannot read a secret or change a setting. The Reticulum bridge uses it to post actions. | runtime · secret |
| `POSTGRES_PASSWORD` | `change-me`; `install.sh` replaces it | string | The database password, composed into `DATABASE_URL` by Docker. | env only · secret |
| `DATABASE_URL` | set by `docker-compose.yml` | URL | The database connection the app and the settings module use. Compose-internal; nothing to set by hand. | env only |
| `MAP_TILES` | `off` | `off`, `on` | Live satellite and street tiles under the cells. Each tile request tells a tile server which square of the planet this house is looking at. `off` = tiles from the node's local copy of OpenStreetMap; `on` = live tiles. A keeper turns this on in Set up. | runtime · public |
| `STATIONS_SHOWN` | `3` | integer, `0` = all | How many of the neighbourhood's stations the dashboard lists, nearest first. This node's own hardware is always listed and never counted. Nothing is discarded: the page says how many it is not listing. To collect fewer stations, turn `BAD_RADIUS_KM` down instead. | runtime · public |
| `UI_LAYOUT` | blank | JSON | Order and visibility of the dashboard's cards. Managed by the dashboard's Arrange mode; blank restores the default. Readable by every screen in the house at every level. | runtime · public |
| `LOG_LEVEL` | `INFO` | Python logging level | Log level of the app and the Reticulum bridge. | env only |

## Sensors and sources

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `SC_DEVICES` | blank | comma-separated kit ids | Smart Citizen kits read directly from the cloud API, the number in `smartcitizen.me/kits/<id>`. Always treated as yours, at this address. Any id enables the adapter. | runtime |
| `SC_USER` | blank | username | Discover every kit on a Smart Citizen account instead of listing ids. Indoor or outdoor comes from each kit's own setting. Also used by `/nearby?audit=1`. | runtime |
| `SC_EXCLUDE` | blank | comma-separated kit ids | Account kits that belong to another site. | runtime |
| `AIRGRADIENT_HOSTS` | blank | comma-separated hostnames or IPs | AirGradient ONE or Open Air units on your WiFi. In v0.57 the key only keeps these units out of the Bali Air Dispatch ring; see [Known gaps](#known-gaps-in-v053). | runtime |
| `PURPLEAIR_HOSTS` | blank | comma-separated IPs | PurpleAir units on your WiFi. Use the IP; the `.local` name is unreliable. Same gap as `AIRGRADIENT_HOSTS`. | runtime |
| `SENSOR_INDOOR` | `0` | `1`, `0` | Whether the LAN sensors above are indoors. Smart Citizen carries this itself. Nothing reads this key in v0.57. | runtime · public |
| `BAD_ENABLED` | `0`; `.env.example` and the bali preset ship `1` | `1`, `0` | Bali only: the island's public stations from Bali Air Dispatch as outdoor reference. Needs `NODE_LAT`. `planetai setup` sets `0` outside Bali. | runtime · public |
| `BAD_RADIUS_KM` | `15`; bali preset `8` | km | How far out the ring of other people's stations reaches. Also `/nearby.radius_km`. | runtime · public |
| `BAD_MIN_SEPARATION_M` | `150` | metres | A station closer than this to the node is assumed to be our own hardware, not a neighbour. | runtime · public |
| `BAD_EXCLUDE` | blank | comma-separated station ids | Stations that are ours and the identity and distance rules missed. | runtime · public |
| `BAD_INCLUDE_INDOOR` | `0` | `1`, `0` | `1` keeps stations the archive suspects are indoors. Off by default: they are not the street. | runtime · public |
| `BAD_BACKFILL_DAYS` | `0` | days | Size of the one-off history fetch by `planetai run nearby backfill`. Off by default: it is a large fetch against someone else's server. The script's argument overrides it. | env only |
| `OPENMETEO_ENABLED` | `1` | `1`, `0` | Open-Meteo weather and CAMS air model point samples at the node's coordinates, two adapters. Free, key-free, anywhere. Context from the planet scale, never rolled into an index cell. Needs `NODE_LAT`. | runtime · public |
| `BOOTSTRAP` | `1` | `1`, `0` | On first start, fill the database from 92 days of CAMS history and NASA POWER climatology at these coordinates. Skipped once `cams-point` history older than two days exists. `0` starts empty. | env only |
| `CKAN_PORTALS` | blank | `slug=url,slug=url` | CKAN open-data portals to watch. One adapter reads any CKAN portal; feeds the `Governance\|City` cell. The presets fill this per city. | runtime · outward |
| `CKAN_SCALE` | `city` | scale string | The scale stamped on CKAN observations. | env only |
| `POLL_SECONDS` | `300` | seconds | How often the source loop polls. | bootstrap |
| `MESH_INDOOR_NODES` | blank | comma-separated `!hex` ids | Meshtastic radios that are indoors, e.g. `!8f491db0,!64e0bfd1`. Mesh sensors default to outdoor. | runtime |
| `MQTT_HOST` | blank | hostname | The broker. When set, the MQTT thread starts and subscribes to `msh/#` and `planetai/sensors/#`. `planetai meshtastic` sets it. | bootstrap |
| `MQTT_USER`, `MQTT_PASS` | blank | strings | Broker credentials. `planetai meshtastic` generates them and writes the broker's password file. | env only · secret |
| `FORECAST_BMKG` | `1` | `1`, `0` | Forecast pack: read BMKG, Indonesia's meteorological agency. | env only |
| `FORECAST_BMKG_ADM4` | blank | Permendagri village code | The village code for this point. `planetai run forecast verify` proves it resolves to somewhere near the node. | env only |
| `FORECAST_OPENMETEO` | `0` | `1`, `0` | Forecast pack: read Open-Meteo. Works anywhere, but its free tier is non-commercial only, so it is the operator's decision. Off until you turn it on. | env only |
| `FORECAST_POLL_HOURS` | `6` | hours | Declared by the forecast pack. No code reads it in v0.57; the forecast sensor's cadence is fixed at `PT3H`. | env only |
| `EARTH_RADIUS_M` | `5000` | metres | Earth pack: half-width of the square around the node. 5000 is a 10 km square, about 64 MB on disk and 103 MB pulled per year. Also `/earth.radius_m`. | env only |
| `EARTH_YEARS` | blank = every year | comma-separated years | Earth pack: which years to fetch. The dataset has 2017 to 2025. | env only |
| `PLACE_RADIUS_M` | `1000` | metres | Place pack: the radius around the node to describe from OpenStreetMap. Also `/place/geojson.radius_m`. | env only |
| `PLACE_REFRESH_DAYS` | `30` | days | Place pack: how often to fetch from Overpass again. A moved node refetches at once. | env only |
| `OVERPASS_URL` | `https://overpass-api.de/api/interpreter` | URL | Place pack: the Overpass endpoint. | env only |
| `EE_PROJECT` | blank = read from the key file | project id | Earth Engine project id, not the service account number. The pack code reads the environment. | runtime |
| `EE_SERVICE_ACCOUNT` | blank = the key file names it | email | The Earth Engine service account. | env only |
| `EE_KEY_FILE` | `/app/config/ee-key.json` | path inside the container | The service-account JSON key; the file goes in `config/`. The pack code reads the environment. | runtime |
| `COAST_MAX_KM` | `30` | km | Coast pack: refuse to report if the nearest ocean grid cell is further away than this. The pack code reads the environment. | runtime · public |

## Channels

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | blank | BotFather token | Alerts and reports to Telegram. Blank = they go to the log only. Never shown again once saved. `planetai telegram` sets it. | runtime · secret · outward |
| `TELEGRAM_CHAT_IDS` | blank | comma-separated ids | Recipients. Add the bot to a group, or let `planetai telegram` find yours. | runtime · outward |
| `ALERT_LEVEL` | `act` | `act`, `warn`, `info` | What interrupts you between reports. `act` = only when something needs doing; `warn` = also when something changed; `info` = everything. Everything is recorded regardless, on the dashboard and in the next report. | runtime · public |
| `QUIET_HOURS` | `1` | `1`, `0` | `1` = between the hours below only act-level alerts are sent; the rest wait for the morning report. A report due in quiet hours is held and folded into the next. | runtime · public |
| `QUIET_FROM` | `22` | local hour | When quiet hours start. | runtime · public |
| `QUIET_TO` | `6` | local hour | When quiet hours end. | runtime · public |
| `HA_DISCOVERY` | `0` | `1`, `0` | `1` publishes local sensors and alerts as Home Assistant entities over MQTT discovery. Needs `MQTT_HOST`. `planetai homeassistant` sets it. | runtime · public · outward |
| `MESH_ALERTS` | `0` | `1`, `0` | `1` sends the first line of act-level alerts back over the LoRa mesh through the gateway radio. Needs downlink enabled on the gateway's channel. | runtime · public · outward |
| `MESH_GATEWAY_NODE_NUM` | `0` | decimal integer | The gateway's node number, used as the sender for downlink. `planetai meshtastic` shows how to find it. | runtime |
| `RETICULUM_URL` | blank; `planetai reticulum` sets `http://reticulum:4243` | URL | The bridge. When set, act alerts are posted to its `/send` and the node polls it for `/health.reticulum`. | env only |
| `RETICULUM_ALERT_DESTINATIONS` | blank | comma-separated LXMF hashes | Where the bridge delivers act alerts. Addresses from Sideband, no spaces. | runtime · outward |
| `RETICULUM_PRESENCE` | `0` | `1`, `0` | `1` announces the node's name and a coarse map cell every half hour, so other PLANETAI nodes can see that it exists and how far away it is. No readings, no address, nothing else, and nothing at all while this is `0`. `SHARE_LEVEL` governs what the node answers; this is the node speaking unprompted. | runtime · public · outward |
| `RETICULUM_PRESENCE_RES` | `3` | H3 resolution `0` to `6` | How exactly the announce places this node, and the whole of the privacy decision. `3` is about 60 km across and says the island; `4` about 22 km; `5` about 8 km. Anything finer than `6` is clamped to `6`: a node announcing its street to an open radio network is not a thing to do by typing a number. | runtime · public · outward |
| `RETICULUM_ANNOUNCE_S` | `1800` | seconds | The bridge's announce interval; echoed in `/health.reticulum.announce_s`. | env only |
| `RETICULUM_DATA`, `RETICULUM_CONFIGDIR`, `NODE_API_URL` | `/data`, `/etc/reticulum`, `http://app:8080` | paths, URL | Bridge container internals, set by `docker-compose.yml`. Nothing to set by hand. | env only |

## Reports

One report every `REPORT_EVERY` hours in the node's own time zone, starting from `REPORT_ANCHOR`. A report is
written in the first 20 minutes of a due hour; the `reports` row for that hour is the lock, so it is written once.

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `REPORT_EVERY` | blank = `6` | `3`, `4`, `6`, `8`, `12`, `24` | Hours between reports. `6` is four a day. Each accepted value divides 24, so the rhythm does not walk round the clock. Also the default window of `/report/bundle`. | runtime · public |
| `REPORT_ANCHOR` | blank = `6` | `0` to `23` | The local hour the rhythm starts from. With a 6-hour interval, `6` gives 06, 12, 18 and 00. | runtime · public |
| `REPORT_DEPTH` | blank = `auto` | `auto`, `brief`, `standard`, `deep` | How much the report says. `auto` lets the strongest model the node can reach decide. Until a model is in the path every report is the node's own, and this changes nothing. Nothing reads it in v0.57. | runtime · public |
| `ALERT_LOCALE` | `en` | `en`, `id`, `es` | Language of alerts and reports. The alert rules carry `en` and `id`; the report carries all three. Anything else falls back to English. Echoed in `/health.locale`; read by the agent loop too. | runtime · public |

## Model and agent

Read by the agent loop in the `agent` container (compose profile `agent`), which builds its ladder of models from
`/settings/raw` with the environment as fallback. The runtime keys here carry the `restart` flag: the dashboard
saves them live, and the agent container uses them at its next start. `planetai agent local` installs Ollama and
sets this group up.

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `AGENT_PREFER` | `strongest` | `strongest`, `fallback`, `private` | `strongest` tries online, remote, local; every question goes to the online model when one is set. `fallback` tries your remote model, then online, then the small local one. `private` never uses online: nothing leaves the network. | runtime · public · outward · restart |
| `AGENT_ONLINE_URL` | blank | `https://api.anthropic.com/v1`, `https://api.openai.com/v1`, … | An OpenAI-compatible online endpoint. The URL and nothing else; a value that does not start with `http` is not a rung, and the agent logs it and skips it. The rung exists only when the key is set too. | runtime · outward · restart |
| `AGENT_ONLINE_MODEL` | `claude-sonnet-4-6` | model id | Ask the key which models it can see (`GET $AGENT_ONLINE_URL/models`) and paste an id from that list. A retired model answers 404, which reads like a bad key. | runtime · public · outward · restart |
| `AGENT_ONLINE_KEY` | blank | secret | The only thing that lets household data leave your network. Your choice. | runtime · secret · outward · restart |
| `AGENT_REMOTE_URL` | blank | `http://<host>:8082/v1` | A bigger local model on your tailnet, OpenAI-compatible. | runtime · restart |
| `AGENT_REMOTE_MODEL` | `gpt-oss-120b` | model id | e.g. `gpt-oss-120b` or `qwen3:8b`. | runtime · public · restart |
| `AGENT_REMOTE_KEY` | blank | secret | If that server asks for one. | runtime · secret · restart |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | URL | Ollama on this machine, the `local` rung. `planetai agent local` sets `http://172.17.0.1:11434` on Linux. | env only |
| `AGENT_MODEL` | `qwen3:4b` | Ollama model | The local rung's model, passed to the container as `MODEL`. `qwen3:4b` for an 8 GB machine, `qwen3:8b` on 16 GB or more. It must do tool calling; `gemma3` does not. | env only |
| `AGENT_NAME` | `local-model` | string | How the agent's actions appear in the audit trail, sent as `X-Agent`. | env only |
| `MCP_URL` | `http://app:8080/mcp` | URL | Where the loop reaches the node's MCP. Compose-internal. | env only |
| `COMPOSE_PROFILES` | blank | comma-separated `mqtt`, `agent`, `ipfs`, `reticulum` | Which optional containers run. Blank = the two base containers only. Set by `planetai meshtastic`, `agent local`, `ipfs` and `reticulum`; leave alone by hand. | bootstrap |

## Federation

A node with a parent posts hourly means to `PARENT_API_URL/aggregates` and alert timestamps to
`PARENT_API_URL/events`, with `PARENT_TOKEN` as Bearer and `NODE_SCALE` as `scale`. A node that is a parent
demands `AGGREGATE_TOKEN` from its children. Leave all three empty on node #1.

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `PARENT_API_URL` | blank = none | `http://<district>:8080` | The parent node. When set, hourly `POST /aggregates` and `POST /events` go there. | runtime · outward |
| `PARENT_TOKEN` | blank | string | What this node presents to its parent. | runtime · secret |
| `AGGREGATE_TOKEN` | blank | string | What this node demands from its children on `POST /aggregates` and `POST /events`. Without it the node accepts no children at all (403). Set it before pointing another node at this one. | runtime · secret |

## Storage, backups and export

All read by `docker-compose.yml` or `backup.sh`, the nightly cron job. `planetai storage` shows the state of each
and `planetai storage set` changes the first three.

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `DATA_DIR` | blank = the Docker volume `db` | path | Where the live database lives. A path is a local disk or partition only; never a NAS. `planetai storage set data` refuses for that reason. | bootstrap |
| `BACKUP_DIR` | `./backups` | path | Where `pg_dump` files go. If it is a mount point it must be mounted, or the backup refuses. | bootstrap |
| `BACKUP_KEEP` | `30` | days | Days of dumps kept in `BACKUP_DIR`. | bootstrap |
| `BACKUP_REMOTE` | blank | rclone `remote:path` | Off-machine copy after each backup: S3, B2, R2, Drive, Dropbox, SFTP, WebDAV, Nextcloud. Run `rclone config` once. | bootstrap |
| `EXPORT_ENABLED` | `1` | `1`, `0` | Each night fetch `GET /export?day=` for yesterday and write `exports/<node>/YYYY-MM-DD.json`: hourly means, cells, alerts, rho, never raw. | bootstrap |
| `IPFS_PUBLISH` | `0` | `1`, `0` | `ipfs add` each export through the `ipfs` container and record the CID in `exports/<node>/CIDS.txt`. `planetai ipfs` turns it on and starts the container. | bootstrap |
| `APP_PORT` | `8080` | port | The host port, published on every interface. Change it if something else on this machine uses 8080. `backup.sh` and the CLI reach the node on `localhost:$APP_PORT`. | bootstrap |

## Packs and paths

| Setting | Default | Values | Meaning | Kind |
|---|---|---|---|---|
| `PACKS_ENABLED` | blank = every pack in `packs/` | comma-separated pack ids | Which packs load. | runtime · public |
| `PACKS_ALLOW_CODE` | `0` | `1`, `0` | Data packs (rules, cells) always load. Code packs (`adapter.py`) run Python with this node's privileges: read them first, then set `1`. | runtime · public |
| `PACKS_DIR` | `/app/packs` | path inside the container | The pack directory. | env only |
| `PACK_OUT` | `/app/out` | path inside the container | The writable folder for pack artifacts, mounted from `./out`. `planetai run` passes it to every script. | env only |
| `RULES_PATH` | `/app/config/rules.yml` | path inside the container | The core rules file. | env only |
| `CHANNELS_PATH` | `/app/config/channels.yml` | path inside the container | The channel-role declarations packs contribute to. | env only |

## Presets

A preset is a file in `presets/` that `install.sh --preset` copies into `.env` before it applies the flags, so
coordinates given on the command line override the preset's centre. Four are Fab City Index pilots; Delhi is the
non-pilot example. Every preset sets exactly these keys and nothing else, and every preset guesses `NODE_ISSUES`:
change it, because what matters here is decided by the people who live here.

| Key | bali | barcelona | boston | delhi | menorca | santiago |
|---|---|---|---|---|---|---|
| `NODE_CITY` | `bali` | `barcelona` | `boston` | `delhi` | `menorca` | `santiago` |
| `NODE_LAT` | `-8.6500` | `41.3874` | `42.3601` | `28.6139` | `39.8885` | `-33.4489` |
| `NODE_LON` | `115.2167` | `2.1686` | `-71.0589` | `77.2090` | `4.2658` | `-70.6693` |
| `NODE_TZ` | `Asia/Makassar` | `Europe/Madrid` | `America/New_York` | `Asia/Kolkata` | `Europe/Madrid` | `America/Santiago` |
| `ALERT_LOCALE` | `id` | `en` | `en` | `en` | `es` | `en` |
| `BAD_ENABLED` | `1` | `0` | `0` | `0` | `0` | `0` |
| `BAD_RADIUS_KM` | `8` | — | — | — | — | — |
| `CKAN_PORTALS` | `bali-satu-data=https://balisatudata.baliprov.go.id` | `open-data-bcn=https://opendata-ajuntament.barcelona.cat/data` | `analyze-boston=https://data.boston.gov` | blank | `menorca=https://intranet.caib.es/opendatacataleg` | `datos-gob-cl=https://datos.gob.cl` |
| `NODE_ISSUES` | `air,heat,land,coast` | `heat,air` | `heat,air` | `air,heat` | `coast,heat,air,land` | `air,heat` |

`planetai setup` picks the preset itself when the geocoded place falls inside the bali, barcelona, boston or
santiago bounding box.

## Known gaps in v0.57

- `AIRGRADIENT_HOSTS` and `PURPLEAIR_HOSTS` are declared and the adapters exist and are tested, but the source
  registry does not register them for polling. The keys are used only to keep those units out of the Bali Air
  Dispatch ring. The changelog documents both adapters as shipped, so this may be a regression.
- `SENSOR_INDOOR` has no reader anywhere in the app or the packs.
- `REPORT_DEPTH` is declared and validated but read by nothing outside the settings module.
- `NODE_KIND` is a runtime setting, but its one reader, `/presence`, reads the environment, so a dashboard
  override does not reach it. `COAST_MAX_KM`, `EE_PROJECT` and `EE_KEY_FILE` follow the same pattern: editable as
  runtime settings, read from the environment by the pack code. Set them in `.env` and restart.
- `FORECAST_POLL_HOURS` is declared by the forecast pack and read by nothing.
- `FCI_PUBLISHER`, `ALLOWED_CITIES` and `PEERS` are named in other documents and are not present in this code.
