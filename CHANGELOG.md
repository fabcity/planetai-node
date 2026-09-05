# Changelog

## v0.12 — 2026-09-05

**Packs can make things you look at, not only numbers.**

- `out/` is mounted read-write into the app container as `/app/out` — the one writable path a pack has, for images, charts and briefs. Gitignored.
- **`planetai run <pack> <script> [args]`** runs a script a pack ships, inside the container where its dependencies are. With no arguments it lists what is available.
- **`packs/earth-engine/timelapse.py`**: four satellite images of the same place, five years apart, plus a side-by-side HTML page. Each frame is the annual median of clear pixels, so clouds are gone and what you see is the year. Landsat by default (the only archive reaching back far enough with one instrument family — 2010, 2015, 2020, 2025 out of the box); Sentinel-2 for 2016 onward at three times the resolution. `--years`, `--n`, `--gap`, `--km`, `--px`, `--lat/--lon`, `--dry-run`.
- Fixed while building it: `COPERNICUS/DEM/GLO30` in the verifier was an ImageCollection used as an Image, and deprecated. Replaced with SRTM, and a step 6 now probes the four datasets the pack actually reads.

## v0.11.5 — 2026-09-05

- **Fixed:** `planetai packs` treated a pack's `env:` comment lines as settings, so it appended four bare comments to `.env` and reported them as four added settings (the real settings were already present and correctly skipped). A comment now travels only with the setting it explains, and only when that setting is actually added.
- Verified by running the real function from `bin/planetai` against a temporary `.env`, not a retyped copy — retyping it the first time introduced an escaping bug that made the test lie.

## v0.11.4 — 2026-09-05

- **Fixed:** pack `env:` declarations padded the value column for alignment, so a value pasted after the padding produced `VAR=   value`. The shell reads that as "run `value` with VAR empty", and `update.sh` sources `.env` — so filling in the Earth Engine service account made `planetai update` try to execute an email address. Declarations now put the explanation on its own comment line and leave nothing after `=`.
- **Added:** `update.sh` checks `.env` for a space after `=` before sourcing it and names the offending line; `planetai doctor` checks the same thing. A file this central should not fail with "command not found".

## v0.11.3 — 2026-09-05

- **Fixed:** a pack's settings had no route into `.env`. The earth-engine pack documented `EE_PROJECT`, `EE_SERVICE_ACCOUNT` and `EE_KEY_FILE` in its README only, so they appeared in no config file and could not be found. Packs now declare `env:` in `pack.yaml` alongside `pip:`, and `planetai packs` appends the missing ones under a dated marker without overwriting anything. Also added to `.env.example` so a plain `planetai update` picks them up.
- `packs/earth-engine/verify.py`: checks library, settings, key file, credentials and a real query, and names the step that failed.

## v0.11.2 — 2026-09-05

- **Fixed:** `planetai packs` printed a `SyntaxError` instead of the pack list. The `json` helper wrapped snippets after a semicolon, where a `for` loop is a syntax error. The snippet now goes on its own line, so any statement works.
- **Fixed the gate that missed it:** `check_cli_python.py` compiled each snippet standalone, where `for p in d: print(...)` is perfectly valid. It now compiles them as the helper actually wraps them. Verified by injecting a broken snippet and watching the gate fail.

## v0.11.1 — 2026-09-05

- **Fixed:** `planetai packs` read `pack.yaml` with PyYAML, which a node's Apple Python does not have, so the command crashed on node #1. It now parses the one line it needs with awk. Nothing else in the CLI needed a third-party library and nothing should: `tools/check_cli_python.py` now fails the build if a CLI snippet imports one.
- **Fixed:** when the API did not answer, the command printed "(node not answering)" and carried on. It now says so as a warning, points at `planetai doctor`, and lists what is on disk while making clear that is not what is running.

## v0.11 — 2026-09-05

**Ten pack ideas, three built.** `docs/PACK_IDEAS.md` lists ten packs someone could write this month, each with its
Index cell, what it needs, its size and a natural author. Three ship as prototypes:

- **`heat`** (data): Steadman apparent temperature in SQL from any local temp + humidity; heat-stress and danger
  alerts; nights that never cool below 28 °C; a `Social|Community` cell of heat-exposure hours — one honest number for
  the Index's emptiest column.
- **`coast`** (code, key-free): waves, swell and sea temperature from Open-Meteo Marine at the nearest ocean cell,
  refusing to run if that cell is more than 30 km away. Tested live: 1.7 m at 11.8 s off the Bukit, sea 27.4 °C.
- **`earth-engine`** (code, needs a Google Earth Engine project): tree, built, crop and water fractions from Dynamic
  World, Sentinel-2 NDVI, VIIRS night lights, and a land-change score from consecutive AlphaEarth annual embeddings,
  all computed server-side over a 1 km buffer. The worked example of a pack with a dependency and a credential: it
  logs once and idles until configured, and cannot take the node down. Logic tested with a fake `ee`; not yet run
  against a live account.

**Mechanics that came with them**
- `pip:` in `pack.yaml` + `planetai packs`: code-pack Python dependencies are installed into the image once, on
  demand, never at runtime.
- `long_cooldown_ok: true` lets a rule declare a deliberately long cooldown to the rule checker, which otherwise
  flags anything over a fortnight (the test-alert bug).
- `tests/test_packs.py` covers both code packs offline.

## v0.10.1 — 2026-09-05

- **Fixed:** a Smart Citizen kit the node polls directly also arrived through Bali Air Dispatch as `bad-sc-<kit>`, so it was counted twice in the ambient average — and BAD's indoor/outdoor metadata disagreed with Smart Citizen's own on two of your kits. Kits read directly are now skipped from BAD. Seen on node #1 once account discovery was on.
- **Fixed:** `update.sh` pulled a named branch, which skips tags, so the version stamp stuck at `v0.7-N`. Tags are fetched first now.

## v0.10 — 2026-09-05

**The node reads your whole account, tells you more, and hands automations to Home Assistant.**

- **Smart Citizen account discovery** (`SC_USER`): every kit that has published recently, indoor from the API's `exposure` field, local if within `SC_LOCAL_KM` of the node, otherwise a reference station you own. Node #1's account turned out to hold six live kits; it was reading one.
- **`insight` pack**: `digest` every three hours (inside / outside / model / 24h mean / peak / trend); `agreement` daily (Pearson r between indoor, outdoor and CAMS, how much the house filters, the model's bias); `rhythm` daily (the street's worst and cleanest hours, when to open the windows). Pure SQL; Postgres has `corr()`.
- **Home Assistant** via MQTT discovery: local sensors and the latest alert appear as HA entities with no configuration on the HA side. `planetai homeassistant` sets it up. HA does automations; the node never addresses a device.
- **`NODE_KIND`** (`home | business | community | district`): a fourth setup question that sets defaults. Not an Index scale — a house is a Community-scale observation.
- **`docs/USE_CASES.md`**: three things node #1 can say today, with the real numbers from seven days of data: indoor tracks the street at r = 0.55 and the house filters ~30%; the CAMS model tracks the street at r = 0.51 and reads high; it tracks indoor air at r = −0.18. Also: one kit in the account has a dead PM sensor.

## v0.9 — 2026-09-05 — audit

Six defects found by auditing rather than by hitting them in the field. Each has a gate now.

**Wrong, silently**
- `POST /aggregates` stored a child's hourly means as `kind='sensor'`, so they entered the `stats` view and could be averaged into "nearby public sensors" as ambient reference. Children are `kind='child'` and belong in `observations`. Found before the district node made it matter.
- `NODE_TZ` was written by setup and **read by nothing**, while `.env` claimed daily buckets used it. Postgres defaulted to UTC, so `current_setting('TimeZone')` put local midnight and local hours eight hours out in Bali: the WHO exceedance-day cell split days at 08:00 WITA, and the cooking-hours rule fired at dawn. The database session timezone now comes from `NODE_TZ`.
- `packs/air-quality` declared its 24h-mean cell `partial` with a comment saying the core would promote it. The core only ever demotes. The cell could never be `live` while `COVERAGE.md` and `START_HERE.md` both promised it would be. It now declares `live` and is demoted until 12 hourly buckets exist.
- Any loop's exception overwrote `state["last_error"]`, which `poll_once` clears when its sources succeed — a permanently broken rules thread looked healthy. Each loop keeps its own key.
- The poll loop was an anonymous lambda, so its thread and every error it logged were named `<lambda>`.
- MQTT ingest counted every reading as new, including duplicates dropped by `ON CONFLICT`.

**Closed while it is free**
- `POST /aggregates` accepted anything that could reach the port. It now requires `Authorization: Bearer <AGGREGATE_TOKEN>` and refuses outright when no token is set. No child exists yet, so nothing breaks.

**Removed**
- `UPSTREAM_MODEL_URL` and `UPSTREAM_COMPUTE_URL` from `.env.example`: no code reads them. The contract stays described in `ARCHITECTURE.md`; the setting comes back with the code that uses it.

**New gates**
- `tools/check_rules.py`: parses `init.sql` for every table and view, then checks each rule and cell — unknown columns, message placeholders the SQL never returns, cells with no `value` column, and cooldowns over a fortnight. The last of those is exactly the bug that made `test-alert` report a dead node for 69 days. Verified against four deliberately broken rules.
- `tests/test_logic.py`: cell provenance (demote a `live` claim below `min_buckets`, never promote `partial`, show the shortfall in the note) and per-loop error isolation.
- Both run in `make lint` / `make test` and in CI.

## v0.8.2 — 2026-09-05

**First real packet from the gateway reached node #1**, and the day-long silence had one cause: the fleet channel was
a secondary, and radios send telemetry on the primary. `mesh-provision.sh` now makes the fleet channel the primary.
Also documented: enabling the XIAO's serial console and debug log to read the radio's own output over USB; the
Mosquitto config that was missing for a day; connection logging on the broker.

## v0.8.1 — 2026-09-04

**First radios provisioned; the failures documented.**

- `tools/mesh-provision.sh`: one command per radio over USB (region, preset, names, role, telemetry and position intervals, fleet channel; first radio creates the channel and saves its URL, the rest import it). No pairing, no PIN.
- `docs/MESHTASTIC_FLEET.md`: the laptop procedure, naming and roles, the channel file as a key, the CLI's enum values, and field notes: region `0` explained last week's silence; UF2 drag fails on macOS 26 (FSKit) regardless of bootloader version and serial DFU is the working path; the flasher offered a non-release 2.8.1, the fleet is on stable 2.7.26; Seeed's verified Grove list excludes the BME680.
- `docs/MESHTASTIC_APP.md`: Part 0 fast path; the -36 paragraph corrected (the earlier "update the bootloader" explanation was wrong for this case); a sensor on the gateway; two symptom rows.
- First Tracker L1 flashed to 2.7.26 over serial DFU and provisioned as `SENSOR` on channel `planetai`, `SG_923`.

## v0.8 — 2026-09-04

**Meshtastic and Reticulum ready.** Both behind compose profiles, off by default; node #1 stays two containers until
you turn one on.

- **`planetai meshtastic`**: creates broker credentials, starts Mosquitto (`mqtt` profile, password required, LAN-reachable on 1883), restarts the node with its MQTT thread on, prints the exact gateway settings (region for your city, address, credentials, JSON output on, uplink/downlink on), waits for the first packet, lists the sensors it saw.
- **Meshtastic adapter** (`sources.meshtastic_message`): pure function, tested offline against 2.x payload shapes. `telemetry` → readings (environment + air quality + battery/LoRa health), `position` → sensor coordinates from GPS, `nodeinfo` → name. Protobuf topics ignored; unknown fields logged once. Pressure converted hPa → kPa to match the rest of the node.
- **Alerts over the mesh**: `MESH_ALERTS=1` + the gateway's node number; act-level alerts go out on the downlink topic, first line only, capped at ~200 bytes.
- **DIY pods**: the same broker takes `planetai/sensors/<id>/<metric>` from anything on the WiFi.
- **`planetai reticulum`**: a bridge container with an LXMF address. Inbox: `act <id> [note]` from Sideband records the action (closing the loop with no internet). Outbox: act-level alerts to `RETICULUM_ALERT_DESTINATIONS`. TCP server on 4242 now; RNode LoRa is a commented block in `config/reticulum/config` plus a device mapping (Linux).
- `/health` gains `mesh` (root topic, gateway, packet count) when MQTT is on; doctor checks the broker, packets and bridge when their profiles are on.
- Found by the new tests: the root topic parse included the protocol version segment, which would have doubled `/2/` in every downlink. Fixed before it shipped.
- `docs/NETWORKING.md` and `docs/sensors.md` updated; SPEC §6 marks the MQTT trigger fired and splits Reticulum into shipped (bridge) and parked (node-to-node transport).

## v0.7 — 2026-09-03

- **`planetai mesh`**: joins the node to a Tailscale tailnet with its own name and Tailscale SSH on, so `ssh bayu-2` and `planetai update` work from anywhere with no ports opened and no keys managed. Uses the Homebrew daemon on macOS so a headless mini stays reachable with nobody logged in. `TS_AUTHKEY` for unattended joins. `MESH_NAME` recorded in `.env`.
- **`docs/NETWORKING.md`**: the three-layer evaluation. Tailscale for reachability (shipped, Headscale as the recorded exit). Meshtastic for sensors and alert delivery off-grid (next; it is the missing pipe in the FAB26 six-month program, and the gateway must point at the node's own broker, not the public default). Reticulum parked with a precise trigger.
- SPEC §6: the Tailscale and MQTT triggers are marked fired; Reticulum added with its trigger.

## v0.6 — 2026-09-03

**One command to a running node.** Applied the Omarchy install pattern: a URL that does everything, a form that
asks only what it cannot detect, phased steps logged to a file, a plain error screen, and one CLI so operators never
touch a Makefile, a flag list or a YAML file.

- `install`: `curl -fsSL planetai.fab.city/install | bash`. Gets git if missing, clones or updates `~/planetai`, hands off to `planetai setup`. Re-runnable.
- `bin/planetai setup`: three questions. Name. **A place name** (Open-Meteo geocoding, with OpenStreetMap as fallback for neighbourhoods and sub-districts) → coordinates, time zone, country, and whether the location falls inside one of the four pilot bounding boxes, which sets the city key and turns the Bali archive on or off. Sensor, or none. Then a summary, a confirm, and the install with a log.
- `planetai telegram`: validates the token with `getMe`, waits for your message, reads the chat id from `getUpdates` itself, writes `.env`, sends a hello, restarts. No JSON to read.
- `planetai test-alert`: a temporary pack with a rule that always fires; waits, removes itself, hands you the alert id. Your rules are untouched.
- `planetai act <id> [note]`: records the action and prints ρ.
- `planetai status | doctor | sensors | cells | logs | update | backup | config | start | stop | restart`. Doctor names the fix next to each failing check.
- `planetai geocode <place>` to try the lookup without installing.
- README and START_HERE now lead with the one-liner; the flag and by-hand routes remain below it.

## v0.5 — 2026-09-03

**Location independence.** Read the docs as someone setting up in Delhi or Santiago and most of it did not work.

- **Functional, not editorial:** the indoor/outdoor comparison, the flagship service, only fired in Bali. It looked for nearby public reference *sensors*, which exist in the node's data only where a network adapter supplies them. CAMS ships globally but lives in `observations`, so the rule could never fire elsewhere. The two comparison rules now resolve "outside" in order of preference (nearby public sensors, then the CAMS model point sample) and the message names which one it used. Added `outdoor_pm25_high` for nodes whose own sensor is outside.
- `docs/START_HERE.md` rebuilt around **your five inputs**: coordinates, time zone, city key, sensors or none, and what "outside" means where you are. Includes how to find each, how to test whether your city runs a CKAN portal, and what to expect when there are no `bad-` rows (everywhere except Bali). Bali is now a labelled worked example rather than the spine.
- `presets/delhi.env` — a non-pilot site, so the docs' own counter-example is real.
- Bali-specific claims corrected across README, `sensors.md`, `PREFILL.md`, `PLATFORMS.md`, `MAC_MINI.md` (the UPS advice now says where it applies), `ARCHITECTURE.md` (the cell table is labelled an example) and `PRODUCT.md` (states that its numbers are one market's and not portable).

## v0.4.3 — 2026-09-03

- **Security fix:** httpx logs every request URL at INFO, and Telegram carries the bot token in the URL path — so a live credential was written into the container logs, and therefore into any log someone pasted for support. Found when exactly that happened during node #1's update. httpx/httpcore loggers are now set to WARNING, the notifier logs `telegram -> <chat> ok` instead, and exception text is never interpolated (it contains the URL too).
- The installer and updater now scan the container logs for an exposed token and tell you to revoke it.
- `docs/START_HERE.md` gained a short section on treating the token as a password, and the "send this when you ask for help" block now says to scan the log first.

## v0.4.2 — 2026-09-03

- **Fixed:** `app/Dockerfile` listed modules explicitly (`COPY main.py sources.py index.py ./`), so `packs.py` (v0.2) and `bootstrap.py` (v0.4) were never in the image and the app crashed on import after updating. Now `COPY *.py ./`.
- **Added:** `make lint` fails if the Dockerfile enumerates modules; the installer and updater doctors compare the number of modules on disk with the number inside the running container, so a missing file is caught before "done" is printed rather than after.

## v0.4.1 — 2026-09-03

Both found by running `./update.sh` on node #1 — the update path's first real use.

- **Fixed:** a stray comment injected into the `stats` view's `FILTER (WHERE …)` clause swallowed a closing bracket, so the schema failed to apply on any node. Comments no longer sit inside SQL expressions.
- **Fixed:** `backup.sh` read `BACKUP_DIR` and `NODE_NAME` from `.env` without stripping inline comments, so the backup path became `./backups                   # or a NAS mount, e.g. …`. It now strips comments and quotes.
- **Added:** CI spins up a real Postgres and applies `init.sql` **twice**, then selects from every view. A schema that doesn't parse, or isn't idempotent, can no longer be released. The paren-balance check in `make lint` catches it earlier and offline.

## v0.4 — 2026-09-02

**Updating a running node actually works now.** Found while planning node #1's upgrade: Postgres runs `init.sql` only
when the data volume is created, so every schema change since v0.1 would have silently missed an existing node, and
`stats` could not be swapped with `CREATE OR REPLACE` because columns moved.

- `init.sql` is now the complete schema, fully idempotent, applied on both fresh install and update.
- **`update.sh`** — backup (refuses to continue if it fails) → preserve local `rules.yml`/`.env` → pull → apply schema → add new `.env` keys without overwriting yours → rebuild → verify readings/alerts/actions survived, with counts.
- `schema_version` table; `/health` reports code version and schema version, and says `pre-0.4 (run ./update.sh)` when they've diverged.
- `make bootstrap` backfills CAMS history and NASA POWER normals onto a node that predates v0.4.
- `docs/UPDATING.md` — the workflow, rollback, tarball updates, and why editing `config/rules.yml` is the wrong place to tune a threshold.

**A node is useful before it has a sensor.** Coordinates are the only requirement.

- **First-run bootstrap** (`app/bootstrap.py`): 92 days of hourly Copernicus CAMS PM2.5/PM10, NASA POWER monthly climatology (satellite-derived, 1981–present), and one OpenStreetMap reverse geocode so messages name a place. ~2,200 rows, about a minute, no key, anywhere on earth. Runs once when `readings` is empty; `BOOTSTRAP=0` opts out.
- **`openmeteo_air` adapter** — Copernicus CAMS current PM2.5, PM10, dust, aerosol optical depth, CO, NO₂, O₃, UV. Free, key-free, global, every poll.
- **`cold-start` pack** — three rules that need no hardware: today's modelled air, today vs 40 years of normals, and (once a sensor exists) the weekly sensor-vs-model gap. That gap is the local signal a global grid cell cannot see.
- **Site presets** — `--preset bali|barcelona|boston|santiago` sets coordinates, timezone, language and the city's CKAN portal in one flag. Anywhere else works with `--lat --lon`.
- **`docs/PREFILL.md`** — what arrives free, what needs a key (OpenAQ now requires one; Flood Hub and Sentinel need accounts), and what I refused to embed: static datasets that go stale in git, and any pre-seeded demo data.
- Installer now *requires* coordinates and no longer warns about a missing sensor as if it were a problem.

## v0.3 — 2026-09-02

**The node reaches past its own address.** Evaluated against the Fab City Index's 4 pillars × 5 scales using the
registry's own 32 sources; the node was filling one corner of it.

- **Schema:** `sensors.kind` (`sensor | portal | model | survey | child`), `sensors.scale`, `sensors.cadence`. Additive — a v0.2 node updates in place. New `observations` view (latest value per slow source); `stats` is now sensors-only, because a city statistic has no business in a 24-hour rolling mean.
- **`ckan` adapter** — reads any CKAN portal, which covers four of the registry's `governance|city` sources (Barcelona, Boston, Santiago, Bali) with one function. Publishes datasets total, updated-in-90-days, and the share.
- **`openmeteo` adapter** — global model point sample at the node's coordinates. Free, key-free, works anywhere on earth: a node with no sensors at all still has something true to say. Planet scale, boundary condition, never aggregated upward.
- **`open-data-health` pack** — turns portal maintenance into a `Governance|City` cell and warns when a portal goes quiet.
- **`docs/COVERAGE.md`** — the full matrix, what fills today, and the seven empty cells. Finding worth stating: `governance|community` has no source in the registry, and ρ is that source.

## v0.2 — 2026-09-02

**The core is now domain-blind.** Air moved out of `app/` and `config/` into `packs/air-quality/`.

- `config/rules.yml` keeps two rules that work whatever a node measures (dead sensor, daily pulse). The three PM2.5 rules are now `air-quality/indoor_pm25_high` etc.
- `app/index.py` no longer mentions PM2.5. It computes ρ (Governance, every node, every domain) and evaluates cell SQL that packs declare — policing provenance, including refusing a `live` claim before the data supports it (`min_buckets`).
- The test: no threshold, message or pillar mapping in `app/`. Adapters still name metrics, because devices do — that's a driver translating fields into the schema.
- New: `docs/DOMAINS.md` — what a node measures today, and what water, energy, fabrication, noise, comfort and soil packs would look like, with the decision each drives.
- **Updating a v0.1.1 node:** your three air rules move into the shipped `air-quality` pack and keep working; ids gain the `air-quality/` prefix, so existing alert cooldowns reset once. Nothing else changes.

## v0.1.1 — 2026-09-02 (same night as v0.1)

Fixes from the first live install at Fab Lab Bali, and the first two asks from the field.

**Fixed**
- `last_error` in `/health` now clears when every source succeeds on a poll. It used to show the last failure forever. Several failing sources are joined with ` | `.
- Installer: scripts shipped without exec bits; `COPY` syntax failed on Docker's legacy builder; `index.py` wasn't copied into the image; a port clash with another container failed ten seconds in instead of before building. All fixed; `APP_PORT` in `.env` moves the host port.
- `.env`: inline comments after empty values confused the parser (phantom `PARENT_API_URL`). Comments now sit on their own lines; values are stripped in code; a parent URL without `http(s)://` is ignored with a warning.
- Rules are mounted as a directory (`config/`) so editors that save-by-replace (TextEdit) don't break the mount.
- `make restart` applies `.env` changes; `daily_pulse` prints integers and says "no public sensors in range" instead of a dash.

**Added**
- **AirGradient** and **PurpleAir** adapters — both read directly over the LAN, no cloud. EPA 2021 correction applied; raw stored beside corrected. PurpleAir path reproduces Bali Air Dispatch's published Klungkung example.
- Installer flags `--airgradient`, `--purpleair`, `--indoor`, `--no-bad`; env `AIRGRADIENT_HOSTS`, `PURPLEAIR_HOSTS`, `SENSOR_INDOOR`.
- Linux: installer installs `make`/`curl` if missing. Windows: WSL2 detected; uses Docker Desktop's engine instead of trying to install one.
- `docs/PLATFORMS.md` — Linux, Raspberry Pi, Windows (WSL2), Intel Mac: only what differs.
- `docs/START_HERE.md` — choose-your-sensor, pre-flight checks for each, multi-sensor install examples.

**Added — packs (community extension point)**
- `app/packs.py`: scan `packs/`, merge `rules.yml` (ids namespaced), `cells.yml` (extra Index cells), and optionally load `adapter.py`. `GET /packs` lists what's loaded.
- **Data packs** (rules/cells, no code) load automatically. **Code packs** (`adapter.py`) stay off until `PACKS_ALLOW_CODE=1` — the node logs the file to read first.
- Worked example: `packs/example-cooking-hours/`. Model and tiers: `docs/PACKS.md`.

**Repository**
- `LICENSE` (Apache 2.0 full text), `NOTICE`, `CONTRIBUTING.md`, issue templates (node problem / new source), CI lint + offline adapter tests (`tests/test_sources.py`, `make test`), README rebuilt for the public repo, banner on the Fab City design system.
- Landing page for `planetai.fab.city/node0/` (in the planetai site repo, not here) — rebuilt v0.2 with the packs section.

**Not changed**
- Rules, schema, Index contract, ρ ledger. A v0.1 node updates in place: `git pull && docker compose up -d --build`.

## v0.1 — 2026-09-02

First running node. Smart Citizen 19880 + Bali Air Dispatch → Postgres → five SQL rules → Telegram. `GET /cells` (fci-cells-v0), `POST /actions` (ρ). Node #1: "Bayu 2 – Indoor", Kuta Selatan.
