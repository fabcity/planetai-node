# planetai-node

Turn a computer you already own into a PLANETAI node: it reads the sensors at your place, compares them
with the public sensors around you, and tells the people there what to do — in one message, on their phone.

    git clone <repo> planetai-node && cd planetai-node
    ./install.sh --name bayu-2 --sc 19880 --lat -8.8271 --lon 115.15709

Two containers (Postgres, one Python service). Runs on a Mac mini, an old laptop, a NUC, a Raspberry Pi 4/5.
First reading lands within five minutes. First alert lands when the air earns one.

This is Stage 0 of a larger building — three layers (Sense → Observe → Act) closing on the Fab City Index, the same
shape at every scale from a house to a bioregion, with compute attachable downstream (phones) and upstream (clusters,
frontier models). The whole drawing is in `ARCHITECTURE.md`. This repo is the first brick, and it already speaks the
Index contract: `GET /cells` emits `fci-cells-v0` rows, `POST /actions` measures ρ.

## Node #1

Smart Citizen Kit 19880, "Bayu 2 – Indoor", Kuta Selatan, Bali. Indoor sensor. Around it, the ambient
picture from Bali Air Dispatch's public API — eight networks, humidity-corrected where it matters, stale and
indoor sensors flagged.

So the first service is the one nobody else in Bali offers: **is the air in this room better or worse than the
street, and should the windows be open or shut.** Five rules ship in `config/rules.yml`:

| rule | fires when | message says |
|---|---|---|
| `indoor_pm25_high` | indoor 15-min mean > 35.5 µg/m³ | run the purifier, check outside before opening |
| `outside_worse_keep_shut` | ambient > 35.5 and > 1.5× indoor | keep windows shut |
| `inside_worse_ventilate` | indoor > 15 and > 1.5× ambient | something's burning or cooking inside, ventilate |
| `sensor_silent` | our sensor quiet > 90 min | power? WiFi? |
| `daily_pulse` | once a day | node up, N sensors, 24h indoor vs ambient |

Thresholds are US EPA / WHO 2021, the same scale Bali Air Dispatch publishes. Messages ship in English and
Bahasa Indonesia; `ALERT_LOCALE` picks.

## What's here

```
install.sh          the product. platform detect → docker → .env → up → doctor → nightly backup cron
docker-compose.yml  db (postgres:16) + app
app/main.py         poll sources → postgres · rules (SQL) → telegram · hourly push to parent · http
app/sources.py      adapters: smartcitizen, baliairdispatch (+ EPA correction helper for Plantower sensors)
app/index.py        Index brick: fci-cells-v0 cells this node can honestly compute, and ρ from the actions ledger
config/rules.yml           the alerts. SQL in, message out. edit without touching code.
init.sql            sensors, readings, alerts; two views (readings_1h, stats)
registry.json       the node directory. adding a node = a PR
contrib/            proposed entry for awesome-fabcity-data (the Index's source registry)
backup.sh           nightly pg_dump, 14-day retention, point BACKUP_DIR at the NAS
ARCHITECTURE.md     the building: layers, scales, contracts, compute elasticity, stages
SPEC.md             this brick's contracts, and what comes back when it's earned
PRODUCT.md          who this is for and what they pay for
docs/sensors.md     adding sensors and sources: SC, AirGradient, PurpleAir, MQTT; the data-honesty rules we inherit
```

~700 lines, all in. The version before this one was 1,479 lines and twelve containers. See SPEC §Staged upgrades
for what was cut and the condition under which each piece comes back.

## Never run a server? Read `docs/START_HERE.md` first.

It walks node #1 end to end — requirements, four pre-flight checks, install, Telegram, a forced test alert,
closing the loop, and what to do when something breaks — for someone who has never opened Terminal.

## Day one

```bash
make health      # polls, last error, ingested count
make stats       # rolling 15m/1h/24h per sensor — this is what the rules read
make alerts      # what fired
make logs
```

Close the loop on an alert (this is how ρ gets measured — an app or a Telegram reply handler does the same call):

```bash
curl -X POST localhost:8080/actions -H 'content-type: application/json' \
  -d '{"alert_id": 1, "stage": "acted", "actor": "tomas", "note": "closed windows"}'
curl -s localhost:8080/cells | python3 -m json.tool     # what this node reports to the Index
```

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` in `.env`, then `docker compose up -d`. Until then alerts
go to the log, which is the right place for them on day one.

If `daily_pulse` reports `refs: 0`, widen `BAD_RADIUS_KM` — the nearest public ambient sensors to Kuta Selatan
are in Jimbaran and south Denpasar.

## Principles

1. **One alert someone acts on beats any dashboard.** If nothing here changes a decision at the address, the node is decoration.
2. **Nothing we can't run ourselves.** Postgres, Python, Docker. The public APIs we read are read-only and key-free. Telegram is the one outside dependency and it's a function, not a service.
3. **Raw stays local.** Readings live on this machine. Hourly means go up to a district node when one exists. Nothing else leaves.
4. **Inherit the honesty rules.** Indoor flagged. Stale dropped. Corrected values stored next to raw. Credit the network that measured. Bali Air Dispatch wrote these down; we follow them.
5. **Boring wins.** Novelty is spent on the alerts, nowhere else.

## Licence

Apache 2.0 (code) · CC-BY 4.0 (docs). Data from Bali Air Dispatch and its upstream networks stays under their terms; attribution required.
