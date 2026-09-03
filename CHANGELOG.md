# Changelog

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
