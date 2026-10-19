# Sharing and security
<!-- checked: v0.82.3 -->

This page is the node's boundary: what a reader on the network may see without a token, which token
opens what, what leaves the machine and how coarse it is when it does, and whose code the node will
run. Reach is how a node joins a household's screens, a district and the Index without giving its
readings away. The repo's first refusal says it in one line: "No raw readings leave the instance that
recorded them."

The node's API is published on every interface of the machine, because the things that read it are on
the network: the NAS that pulls dumps, the phones and the wall screen in the house, Home Assistant, and an
agent's MCP client on the tailnet. Postgres is not: `db` binds `127.0.0.1:5432` only, and so do the IPFS
API and the Reticulum bridge's API. A token guards every write and every secret read. `SHARE_LEVEL` decides
what a reader with no token may see.

## `SHARE_LEVEL`

Two rungs in this version; `cell` and `means` are named in the help and refused until they exist.

| level | a request with no token, from another machine, may read |
|---|---|
| `off` (default) | 10 paths and the static files: `/` and `/ui` (the dashboard shell), `/tester` (the sensor bench, a shell like `/ui`), `/health` with the centre of the node's resolution-8 cell, `/llms.txt`, `/settings` reduced to the layout and the sharing level, the daily CC BY 4.0 `/export`, `/presence`, `/nodes` (the programme's public list of nodes), `/offers` (what the household chose to lend or give), and anything under `/static/`. Everything else is refused with a sentence naming the setting. |
| `open` | 39 paths and 5 prefixes: the `off` list, and `/sensors` and `/stats` (the household's own sensors at the point `/health` publishes, the rest to three decimals, metadata cut to the provenance keys), `/observations`, `/alerts`, `/series`, `/sparks`, `/rho`, `/cells`, `/packs`, `/trust`, `/nearby`, `/forecast`, `/earth`, `/earth/change.png`, `/earth/year.png`, `/earth/frame.png`, `/report/latest`, `/readings`, `/reach`, `/shape`, `/effect`, `/history`, `/exports`, `/sources`, the ask pane's `/ask`, `/ask/status` and `/docs/search`, `/geo/cell` without the fields that place a cell relative to the node (`is_node`, `cells_from_node`, `ring_polar`, `children_polar`), `/learned/place` (what the node learned is usual for the outdoor sensors, never the house), and anything under `/exports/`, `/issues`, `/sources/` and `/ground/`. What a wall screen or a phone with no token needs. |

A refused request gets 403 and one of two sentences. For a path that `open` would answer:

```
{"error": "this node is set to SHARE_LEVEL=off, so /stats answers only this machine or a request carrying a token. Set SHARE_LEVEL to open in the dashboard's Set up view to let anything on your network read it."}
```

For a path no level opens, the last sentence is "No share level opens this one, so it always needs a
token from anywhere but the node itself." The dashboard draws the sentence on its refused page rather
than a blank.

`SHARE_LEVEL` is reach, not publishing: it says who on your network may read; it never sends anything
anywhere. Change it in Set up, with `planetai config set SHARE_LEVEL open`, or over MCP; it is live within 20
seconds.

To see the boundary move:

1. **Ask from another machine at `off`.** `curl http://<node>:8080/rho` answers 403 with
   `{"error": "this node is set to SHARE_LEVEL=off, so /rho answers only this machine or a request carrying a
   token. Set SHARE_LEVEL to open in the dashboard's Set up view to let anything on your network read it."}`.
   The node is answering and keeping ρ to itself.
2. **Open it.** On the node, `planetai config set SHARE_LEVEL open` prints `SHARE_LEVEL is now open, on this
   node, within 20 s`. After those 20 seconds the same `curl` returns the ρ document instead of the refusal.
   Every screen on your network can now read the node without a token; nothing has been sent anywhere.
3. **Ask for a path no level opens.** `curl http://<node>:8080/actions` still answers 403, and the sentence
   now ends "No share level opens this one, so it always needs a token from anywhere but the node itself."
   The ledger of what people did stays behind a token. `planetai config set SHARE_LEVEL off` closes the rest
   again.

`/sources` is on the `open` list on purpose: it is a copy of a public registry of public datasets, the
same entries on every node in a release, and it says nothing about this house.

> **Note.** `/issues` at `open` carries the alert events: their rooms (under the neutral names below), and the stage and time of the last answer. It never carries the text of the message the node sent, who answered or what they wrote; those are behind a token.

> **Note.** `/shape` at `open` is the house's usual day: one mean per local hour, indoor against outdoor,
> over the whole record. It is what the page draws, and it is also a pattern of when the kitchen is in
> use. Weigh that before opening a node on a network you share.

> **Note.** Since v0.79 the same weighing covers the drawings. `/issues` at `open` carries each issue's usual day
> and an open event's rooms hour by hour, and `/issues/days` (under the `/issues` prefix) gives up to 90 days of
> the hourly series, indoor rooms included, with the hours over the line counted per day. That is the
> household's rhythm over three months, to anyone on the network.

### Rooms and sensor names stay in the house

At every level, a screen without a token never reads what the house calls its rooms or its sensors. Every answer it
gets has the house's own labels swapped for neutral ones, "Room A" for a room and "Sensor 1" for a sensor's own name,
the same on every route, so the page still tells one room from another. The sentences of past alerts, written under
the names of their day, are left out of `/alerts` and `/issues` instead. A token reads the real names.

## What needs a token at every level

`/place/geojson` (the shape of your building and what is around it), the `/geo/` routes other than `/geo/cell` (each locates the node), `/machine` and `/storage` (the machine and what it holds), `/settings/raw`, `/settings/phone`, `/backups` and
`/backups/<name>`, `/report/bundle`, `GET /aggregates`, `/briefing`, `GET /actions` and the whole of `/captures` are on neither
list. So is every write, and the whole of `/mcp` checks the admin token itself. Two writes pass the
sharing check because their path is on a list for reading, and their handler refuses them instead:
`POST /readings` at `open`, and `PUT /settings` at every level. Without the admin token, both are refused.
`POST /aggregates` and `POST /events`, what a child sends its parent, pass at every level by path and check
`AGGREGATE_TOKEN` themselves.

A request from the machine itself (loopback: `127.0.0.1` inside the container, which is the node's own MCP
tools and a shell in the container) is trusted without a token. A browser on the host is not loopback: it
arrives from Docker's bridge and is treated as a machine on the network.

`GET /actions` is the ledger of what people did about the alerts: which alert, which stage, who, and the
note they wrote. It is on no list because the note is the household's own words about its own house.
`planetai snapshot` blanks every note before it writes its file, for the same reason.

`/captures` is the household's own pictures (SPEC_eyes step 1). It is on no list at any level, and the
routes then refuse every token but `ACT_TOKEN` and `ADMIN_TOKEN`, so the read-only `BACKUP_TOKEN` that
passes the middleware cannot read a picture. The row keeps the exact point — a tree or a dump is worth
it — and only the file is cleaned of EXIF and GPS. No capture is in `/export`, `/exports`, `/aggregates`,
`/readings` or any parent push; `tests/test_captures.py` greps those roads for the table's name.

> **Careful.** `GET /actions` has no token check of its own. Any of the node's three household tokens opens it,
> and so does `/place/geojson`: the admin token, the backup token on the NAS and the act token on a phone. Give
> each knowing it reads the household's notes and the plan of its building. `AGGREGATE_TOKEN`, which every child
> node holds as its `PARENT_TOKEN`, opens neither.

## The tokens

All travel as `Authorization: Bearer <token>`, compared in constant time. There is no query-string form.

| token | opens | where it comes from | give it to |
|---|---|---|---|
| `ADMIN_TOKEN` | every write and secret read: `PUT /settings`, `/settings/raw`, `/settings/phone`, `POST /readings`, `/report/now`, `/test-alert`, the whole of `/mcp`; also what `BACKUP_TOKEN` and `ACT_TOKEN` open. It does not open `POST /aggregates` or `POST /events`, which take `AGGREGATE_TOKEN` only | generated by the installer; `planetai ui` prints it | yourself, your agent. Treat it like a password |
| `BACKUP_TOKEN` | read-only pulls: `/backups`, `/backups/<name>`, `/report/bundle`; cannot read `/settings/raw` | generated by `update.sh` when blank; `planetai ui` prints it (`planetai storage` says only whether it is set) | a NAS |
| `ACT_TOKEN` | `POST /actions` from off the machine: an act, an acknowledgement, a decision or an answer to an alert event (`event_id`). It cannot read a secret or change a setting | `planetai ui` creates it; Set up › This screen shows it to the admin as a QR code a phone scans | a phone, the dashboard's forms in a browser you trust, the Reticulum bridge |
| `AGGREGATE_TOKEN` | what this node demands on `POST /aggregates` and `POST /events`; unset, the node accepts no children | you set it | your children, as their `PARENT_TOKEN` |
| `PARENT_TOKEN` | sent with this node's hourly pushes to `PARENT_API_URL` | your parent's operator | the node itself |

Any of the three household tokens (admin, backup, act) makes a request trusted by the sharing check,
at every level, so each of them reads the whole read API. The aggregate token does not: every child node
holds it, and a child is another household, so it pushes to `POST /aggregates` and `POST /events` and
reads only what a stranger reads. Routes with a check of their own then apply it:
a backup token cannot change a setting, and an act token cannot fetch a dump. The routes without one are
in the Careful note above. The optional `X-Agent` header names the caller in the audit trail. The dashboard
keeps the token it was given in the browser's local storage and sends the admin token first, then the act
token.

`.env` is mode 600 and never committed. Dumps exclude the `settings` table, so a Telegram token saved from
Set up never travels to a NAS or a remote. The node never logs the Telegram URL, because the token is in it.

## What leaves the machine, and how coarse

| what | to whom | how exact |
|---|---|---|
| the node's position | `/health`, `/export`, and `/sensors` and `/stats` for the household's own sensors, for a reader without a token | the centre of the resolution-8 cell (about 500 m to an edge), since v0.73; this machine or a token gets three decimals |
| hourly means and alert timestamps | a parent node, hourly, if `PARENT_API_URL` is set | values and timestamps; never where, never text, never who |
| the daily export | anyone (CC BY 4.0) | your own sensors by role (`indoor-1`, `outdoor-2`), no raw rows, no chat ids |
| a presence announce | the Reticulum network, every half hour, only with `RETICULUM_PRESENCE=1` | the H3 cell rounded up to `RETICULUM_PRESENCE_RES` (3), with a floor of resolution 6 no setting can go under |
| the node's coordinates | Open-Meteo, for weather and the CAMS air model, with `OPENMETEO_ENABLED=1` | rounded to three decimals by the two core adapters |
| a request for the fab lab directory | gitlab.fabcloud.org (`MAKE_SOURCE=archive`) or api.fablabs.io (`live`), only with `MAKE_ENABLED=1` and `PACKS_ALLOW_CODE=1` | no coordinates: the whole directory comes down and the distances are worked out on the node |
| fires nearby | firms.modaps.eosdis.nasa.gov, at most every three hours, only with `FIRE_ENABLED=1` and `PACKS_ALLOW_CODE=1` | the name of a regional file, nothing about the house; with `FIRMS_MAP_KEY`, a box `FIRE_REGION_KM` (150) round the node, to three decimals |
| the ground's heat | planetarycomputer.microsoft.com, anonymously, once a day, with the `surface-heat` pack on and `PACKS_ALLOW_CODE=1` | the node's own point, unrounded, in each scene search |
| a request for the current version | planetai.fab.city, every hour, with `UPDATE_CHECK=on` (the default) | nothing about the house: a plain request for one file. Fab City's host sees this house's internet address and that a PLANETAI node lives there. `off` = the node never asks |
| a species name | api.gbif.org, when a plant or animal in an image is given a scientific name, with `SPECIES_MATCH=on` (off by default) | the scientific name and nothing else: never the picture, never where it was taken. GBIF's server sees this house's internet address and the names asked. `off` = the node never asks, and the name stays as typed |
| the country's list of introduced and invasive species | api.gbif.org and the checklist's archive host, weekly, with `SPECIES_MATCH=on` | which country's GRIIS checklist to read (the country comes from `NODE_TZ`), and nothing else. `off` = the node never asks |
| the open records others made nearby | api.gbif.org, weekly, with `SPECIES_MATCH=on` | the shape of each of the node's seven res-8 cells, which says where this node is to within about 2 km. Only counts come back, from CC0 and CC BY records; no record or observer is kept. `off` = the node never asks |
| who lives here, in an alert | the household's own Telegram chats, only for an act-level heat or air alert that weighs on someone ticked in Node › What it remembers | one line naming who ("a child under five"), never a name or an age; never sent over the mesh, Reticulum or Home Assistant, and never in the stored alert text |
| a request for the programme's list of nodes | raw.githubusercontent.com (`registry.json` on the repository's main), every hour, with `UPDATE_CHECK=on` | nothing about the house: a plain request for one file, as above. `off` = the node never asks |
| the square the node's own map covers | build.protomaps.com and OpenAerialMap (`planetai run place basemap`) or Earth Engine, under the node's own project (`planetai run earth-engine basemap`), once, only when somebody runs the command | the tiles fetched, the finest of them `GROUND_RADIUS_KM` (12) round the node; afterwards the map is served from the node at `/ground/*` and sends nothing |
| the square being looked at | a tile server, per tile, only with `MAP_TILES=on` | the tile's own square; `off` (the default) draws from the node's local copy of OpenStreetMap |
| the question you asked the bot | an online model, only if you gave it a key and changed `AGENT_PREFER` from its default, `private` | the question and the tool results the model asked for |
| a question asked in the dashboard's pane | the model Set up names: this machine, one on your network, or an online provider only with `AGENT_PREFER` set to `fallback` or `strongest` | the question and the page's own sentences and numbers; the context carries no position, name or id; the node keeps no transcript |
| an offer | anyone: `GET /offers` at every `SHARE_LEVEL`, and the daily export (CC BY 4.0) | only for a thing the household marked lend or give: its class, name, condition and count, at the node's own res-8 cell, with a link to the node's Telegram bot. Never a note, a photo, how often it is used or a point |
| raw readings | nobody | nothing |
| a `private` reading | nobody: not the export, a parent, the report bundle or any agent, and on this machine's raw routes only the admin token | it is used on the page, by rules and by cells; Home Assistant discovery, the household's own automation, still receives it |

The dashboard's ask pane talks to the model Set up names and reads what the page reads, less positions, names and
ids. At `AGENT_PREFER=private`, the default, that model is on this machine or your network and the conversation
never leaves; an online model is a choice somebody here makes under Set up, and the pane says so on every answer
it gives. The node never stores the conversation. A remote agent gets the MCP
surface instead, which rounds, refuses and audits. See [Ask the node](ask.md).

`/forecast`, `/earth` and `/place/geojson` carry the node's exact coordinates and are
respectively open-only, open-only and token-only; read [the API](api.md) before putting `SHARE_LEVEL=open`
on a network you do not trust.

> **Gap in v0.82.3.** The `coast` and `forecast` packs, and the first start's 92 days of CAMS history, send the
> node's full-precision coordinates to Open-Meteo; only the two core adapters in `app/sources.py` round them. The
> first start also sends them to NASA POWER and OSM Nominatim.

## Signed updates

A node runs the code it is sent, so what it trusts is part of its boundary. Since v0.60 `install`, and
`planetai update` on a node installed from the tarball, download it, check its published SHA256, and then
check an `ssh-keygen -Y` signature against one key: principal `fabcity`, namespace `planetai-node`.
The public line is embedded in `install`, `update.sh` and `bin/planetai`, so a node can check an update
before it has one, and published in [tools/allowed_signers](../../tools/allowed_signers); `tests/test_release_consistency.sh` fails if the
four copies drift. The checksum proves the bytes arrived whole. The signature names who built them, with a
key that is not on the web server.

A download that does not verify is not installed, and the node says:

```
this download is not signed by the PLANETAI release key. Nothing was installed and nothing on this machine changed.
   Try again on a network you trust. If it says this twice, do not run it — tell us instead.
```

`planetai version` prints what this node trusts, and `planetai doctor` says whether the last update checked:

```
planetai-node v0.80  ·  a Fab City project  ·  <name> @ <city>
  updates signed by  fabcity  SHA256:OrUQK/jsjNjpei1U8B5tyuEWY36/gwYWXrgVF+5ycIY
```

Compare that fingerprint from a machine that is not the node. If they disagree, something replaced the
node's copy of the CLI, and the CLI is not the thing to ask. Every release is published twice from the same
bytes with the same signature, at `planetai.fab.city/node0/get` and as a GitHub Release, and
`PLANETAI_GET` points an install at the second. `PLANETAI_UNSIGNED=1` installs a tarball nobody signed,
with a red warning, and the doctor's signature row stays red until a signed update. How to report a problem
is in [SECURITY.md](../../SECURITY.md).

## Reaching it from elsewhere

Tailscale. `planetai mesh` joins the tailnet under the node's name; the node is reachable by its MagicDNS
name, `<name>.<your-tailnet>.ts.net`, recorded as `MESH_NAME`, from your devices with no open port, and the
traffic that leaves the machine is encrypted by the tailnet. There is no TLS on the node itself: a node
reachable from outside the tailnet is what turns TLS from a checkbox into a requirement, and the answer to
reaching it from outside is not to. Headscale, self-hosted, is the recorded exit if a partner's governance
forbids a third-party coordinator. Never a port forward, ngrok or a public reverse proxy.

## A network the household does not trust

A loopback-only node (`SHARE_LEVEL=none`) is a retired piece with its trigger written: a node on a network
its household does not trust, *and* one that can afford to lose the NAS pull, the phones, Home Assistant
and MCP, all four of which read over the LAN. It would be a third level, opted into, never a default.

## Known debts

Containers run as root. The first-start bootstrap and the `coast` and `forecast` packs send full-precision
coordinates to Open-Meteo. Each is in the tracker
as work, not as a decision.

## Where this leads

With the boundary set, the node can take its place in a district: [Federation](federation.md) is what a
child sends its parent and what the parent refuses. To hand the node to an agent without handing it the
house, read [Agents](agents.md).
