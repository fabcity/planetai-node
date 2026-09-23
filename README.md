<p align="center">
  <img src=".github/banner.png" alt="planetai-node — Sense. Observe. Act." width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-20388D?style=flat-square"></a>
  <a href="CHANGELOG.md"><img alt="Version 0.73" src="https://img.shields.io/badge/version-0.73-171717?style=flat-square"></a>
  <img alt="Node #1 live" src="https://img.shields.io/badge/node%20%231-live%20in%20Bali-00A057?style=flat-square">
  <img alt="Containers: 2" src="https://img.shields.io/badge/containers-2-171717?style=flat-square">
  <img alt="Clouds required: 0" src="https://img.shields.io/badge/clouds%20required-0-171717?style=flat-square">
  <a href="https://planetai.fab.city/node0/"><img alt="Landing page" src="https://img.shields.io/badge/planetai.fab.city-node0-20388D?style=flat-square"></a>
</p>

# planetai-node

**Hyperlocal compute and intelligence for distributed production.** A node is one computer per place, on
hardware the place already owns. It reads what measures that place, from a particle sensor on the wall to a satellite
overhead, tells the people there in plain sentences what to do about it, records what they did, and measures whether
it worked. Its purpose is fixed: clean air, water and soil for the people and the other living things around each
node. Raw readings stay on the machine; only summaries travel.

> **Alpha.** This is an experiment. Installing a node makes you part of it: things will break, some will surprise you,
> and what you report decides what gets fixed first. Write to **info@fab.city** with what broke, what helped, what did not.

```bash
curl -fsSL planetai.fab.city/install | bash
```

Four questions, two minutes, running. Then `planetai telegram` for the alerts and `planetai ui` for the dashboard.
Walk-through in [`docs/START_HERE.md`](docs/START_HERE.md).

## What it is

Twenty years of fab labs and makerspaces built a distributed infrastructure for making things, and since 2014 the
cities of the Fab City pledge have committed to producing half of what they consume by 2054. What that
infrastructure never had is computing of its own: a machine at each place that reads the place, works out what it
needs, and says why it should be made there rather than shipped in. A node is that machine.

The rule it runs on is Fab City's rule for production, applied to data: DIDO, data in, data out. Raw readings stay on
the machine; only summaries travel, to a parent node if you name one, to the [Fab City Index](https://index.fab.city),
and to the models that need ground truth. Today a node reads air and heat from sensors, land and coast from public and
satellite sources; water and soil have no pack yet, and no node has handed a job to a workshop yet. Programme:
[planetai.fab.city](https://planetai.fab.city/) · documentation: [planetai.fab.city/docs](https://planetai.fab.city/docs/).

## What it does

- **Connects every scale.** Sensors on WiFi (Smart Citizen, and Xiaomi purifiers through a pack; the AirGradient and
  PurpleAir adapters are written and not polled in this version), radios over LoRa where there is no WiFi (Meshtastic),
  public stations nearby, the city's open-data portal, Copernicus atmosphere and ocean models, Earth Engine's view of the
  land. One schema from the house to the planet.
- **Turns awareness into action.** Alerts say what is happening, what it means, what to do. Then the node measures
  whether anything changed: ρ, the share of act-level alerts somebody answered, a number the Index never had.
- **Shows the place.** A dashboard with the house's number as a sentence, the day as an annotated chart, every source with
  a note, the sea, the land, the weather. Six views: Now, Historical, Network, Wall, Arrange, Set up.
- **Answers questions.** A bot on your Telegram, running a small model on your own machine, reads the node and explains
  it; point it at a bigger model when you have one.
- **Keeps the data where it was made.** Local database, nightly backups a NAS can collect, an open daily export you decide
  where to send.
- **Grows by folders.** Air, heat, coast, land, place (what is around you, from OpenStreetMap, in PostGIS) and open-data packs ship. Water, energy, noise, classroom CO₂, fire smoke
  are a folder of rules each, written by whoever needs them, for their place.

Node #1 has run in Kuta Selatan, Bali, since 2 September 2026.

## Read next

The documentation site is **[planetai.fab.city/docs](https://planetai.fab.city/docs/)** — the same pages, with a
sidebar, search and the API reference, built from this repository by `tools/build_docs.py`. The files themselves:

```
docs/     getting a node running   START_HERE · PLATFORMS · REVIVE_A_LAPTOP · MAC_MINI · UPDATING · STORAGE
          when it goes wrong       TROUBLESHOOTING
          what it can tell you     USE_CASES · sensors · DOMAINS · COVERAGE · PREFILL · GUI
          extending it             PACKS · PACK_IDEAS · DEVELOPING · SOURCES
          what is still owed       NEXT_RELEASE
          radios and reachability  NETWORKING · MESHTASTIC
          the beta review          BETA_TESTER_GUIDE · HANDOFF_beta_review · reviews/
          the earth pack           HANDOFF_earth_pack
          nodes finding nodes     SPEC_discovery
          deciding, and measuring it SPEC_decide
          the dashboard's design    HANDOFF_dashboard_violations · design/shots/
          the page redesign        HANDOFF_dashboard_redesign · design/shots/redesign/
          reports and messages     HANDOFF_reports
          the trust pack           HANDOFF_trust
          the ring and the forecast HANDOFF_nearby_forecast
          air, heat, land, coast   HANDOFF_issues · DOMAINS
          the dashboard renderer  HANDOFF_dashboard_renderer · GUI
          a model on the node      MODELS
          three directions, picked HANDOFF_dashboard_directions · design/DIRECTIONS_2026-09 · design/REDESIGN_2026-09_ground
          signing the releases     HANDOFF_signing
          arm64, and the Pi        HANDOFF_arm64
          proposed, not decided   SPEC_custody · SPEC_identity · SPEC_rho · decisions/
SECURITY.md       reporting a vulnerability, and the key a node checks an update against
AGENTS.md         for an AI agent operating the node
ARCHITECTURE.md   how it is built; SPEC.md   what was left out and when it returns; PRODUCT.md   who pays for what
```

## Who runs this

One person maintains it today, with a second holding access and a proposed scope — `MAINTAINERS.md`.
`GOVERNANCE.md` says who has to agree to what, and why the installer and `init.sql` need two people.

## Bring your own agent

A node is a thing you operate, and most people who install one will do it with an agent beside them. This
repository is written for that: `AGENTS.md` opens with a table that routes an agent to one of six skills
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
packs/     air-quality · heat · insight · trust · cold-start · open-data-health · coast · earth-engine · earth · place ·
           nearby · season · forecast · make · posidonia · thingdata · xiaomi-air · example-cooking-hours
config/    rules.yml · channels.yml · mosquitto · reticulum
tools/     the checks, hooks, bundle and release scripts, mesh-provision.sh, nas/, remote-model.sh
tests/     offline suites
presets/   bali · barcelona · boston · santiago · delhi · menorca
```

## Licence

Apache 2.0. Fab City Foundation, 2026. Alpha; feedback to info@fab.city.
