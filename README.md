<p align="center">
  <img src=".github/banner.png" alt="planetai-node — Sense. Observe. Act." width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-20388D?style=flat-square"></a>
  <a href="CHANGELOG.md"><img alt="Version 0.31" src="https://img.shields.io/badge/version-0.31-171717?style=flat-square"></a>
  <img alt="Node #1 live" src="https://img.shields.io/badge/node%20%231-live%20in%20Bali-00A057?style=flat-square">
  <img alt="Containers: 2" src="https://img.shields.io/badge/containers-2-171717?style=flat-square">
  <img alt="Clouds required: 0" src="https://img.shields.io/badge/clouds%20required-0-171717?style=flat-square">
  <a href="https://planetai.fab.city/node0/"><img alt="Landing page" src="https://img.shields.io/badge/planetai.fab.city-node0-20388D?style=flat-square"></a>
</p>

# planetai-node

**See your place at higher resolution.** A small program for a computer in your home, lab or community centre. It
connects everything that measures where you stand, from a particle sensor on the wall to a satellite overhead, into
one picture sharp enough to act on: what to do about the air, the heat, the sea, the land, today, here. It tells the
people there in plain sentences, on Telegram, and passes upward what the models of a bioregion and a planet cannot see
from above: what the ground is doing.

> **Alpha.** This is an experiment. Installing a node makes you part of it: things will break, some will surprise you,
> and what you report decides what gets fixed first. Write to **info@fab.city** with what broke, what helped, what did not.

```bash
curl -fsSL planetai.fab.city/install | bash
```

Four questions, two minutes, running. Then `planetai telegram` for the alerts and `planetai ui` for the dashboard.
Walk-through in [`docs/START_HERE.md`](docs/START_HERE.md).

## What it is

Hyperlocal awareness for climate and local challenges, built on distributed design and production. A city is measured
today by satellites, by models with 11 km squares, and by a few reference stations; none of them know your kitchen at
3 am, the shade on your street, or which hour to open the windows. A node fills that resolution gap from below, with the
sensors people already own, and decides where it stands instead of sending readings away. Community scale first, then
city, then region; upward, only summaries, to the [Fab City Index](https://index.fab.city) and to the models that need
ground truth.

## What it does

- **Connects every scale.** Sensors on WiFi (Smart Citizen, AirGradient, PurpleAir), radios over LoRa where there is no
  WiFi (Meshtastic), public stations nearby, the city's open-data portal, Copernicus atmosphere and ocean models, Earth
  Engine's view of the land. One schema from the room to the planet.
- **Turns awareness into action.** Alerts say what is happening, what it means, what to do. Then the node measures
  whether anything changed: ρ, the share of alerts that led to an action, a number the Index never had.
- **Shows the place.** A dashboard with the room's number as a sentence, the day as an annotated chart, every source with
  a note, the sea, the land, the weather. Four views: Now, Network, Set up, Wall.
- **Answers questions.** A bot on your Telegram, running a small model on your own machine, reads the node and explains
  it; point it at a bigger model when you have one.
- **Keeps the data where it was made.** Local database, nightly backups a NAS can collect, an open daily export you decide
  where to send.
- **Grows by folders.** Air, heat, coast, land, place (what is around you, from OpenStreetMap, in PostGIS) and open-data packs ship. Water, energy, noise, classroom CO₂, fire smoke
  are a folder of rules each, written by whoever needs them, for their place.

Node #1 has run in Kuta Selatan, Bali, since 2 September 2026.

## Read next

```
docs/     getting a node running   START_HERE · PLATFORMS · REVIVE_A_LAPTOP · MAC_MINI · UPDATING · STORAGE
          when it goes wrong       TROUBLESHOOTING
          what it can tell you     USE_CASES · sensors · DOMAINS · COVERAGE · PREFILL · GUI
          extending it             PACKS · PACK_IDEAS · DEVELOPING
          radios and reachability  NETWORKING · MESHTASTIC
          the beta review          BETA_TESTER_GUIDE · HANDOFF_beta_review · reviews/
          the earth pack           HANDOFF_earth_pack
          the dashboard's design    HANDOFF_dashboard_violations · design/shots/
          reports and messages     HANDOFF_reports
          the trust pack           HANDOFF_trust
          the ring and the forecast HANDOFF_nearby_forecast
          air, heat, land, coast   HANDOFF_issues · DOMAINS
AGENTS.md         for an AI agent operating the node
ARCHITECTURE.md   how it is built; SPEC.md   what was left out and when it returns; PRODUCT.md   who pays for what
```

## Bring your own agent

A node is a thing you operate, and most people who install one will do it with an agent beside them. This
repository is written for that: `AGENTS.md` opens with a table that routes an agent to one of four skills
in `skills/`, and `make lint` fails if a skill names a command or a path that does not exist. Paste this
to your agent and nothing else:

> You are helping me with a PLANETAI node — an open-source program that turns a spare computer in my home
> or lab into a hyperlocal environmental monitor. Start by reading
> https://raw.githubusercontent.com/fabcity/planetai-node/main/AGENTS.md — its first section is a table
> that routes you to the right skill for what I am asking, and the rest of it is what you must not break.
> Read that skill before you tell me to run anything. Never ask me for the contents of my `.env` file, and
> never suggest exposing the node to the internet; the answer to reaching it from elsewhere is Tailscale.

`llms.txt` indexes every document here for an agent arriving from outside, and `.mcp.json` wires a clone of
this repository to a running node — the URL and the token come from your shell, so nothing secret is in the
file. `planetai agent` on the node prints the three facts you need for any other client.

## Layout

```
app/       main.py · sources.py · index.py · packs.py · settings.py · agent.py · agent_loop.py · static/index.html
bin/       planetai, the command line
packs/     air-quality · heat · insight · trust · cold-start · open-data-health · coast · earth-engine · earth · place · example
config/    rules.yml · mosquitto · reticulum
tools/     the checks, hooks, bundle and release scripts, mesh-provision.sh, nas/, remote-model.sh
tests/     offline suites
presets/   bali · barcelona · boston · santiago · delhi
```

## Licence

Apache 2.0. Fab City Foundation, 2026. Alpha; feedback to info@fab.city.
