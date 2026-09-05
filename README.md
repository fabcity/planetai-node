<p align="center">
  <img src=".github/banner.png" alt="planetai-node — Sense. Observe. Act." width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-20388D?style=flat-square"></a>
  <a href="CHANGELOG.md"><img alt="Version 0.24" src="https://img.shields.io/badge/version-0.24-171717?style=flat-square"></a>
  <img alt="Node #1 live" src="https://img.shields.io/badge/node%20%231-live%20in%20Bali-00A057?style=flat-square">
  <img alt="Containers: 2" src="https://img.shields.io/badge/containers-2-171717?style=flat-square">
  <img alt="Clouds required: 0" src="https://img.shields.io/badge/clouds%20required-0-171717?style=flat-square">
  <a href="https://planetai.fab.city/node0/"><img alt="Landing page" src="https://img.shields.io/badge/planetai.fab.city-node0-20388D?style=flat-square"></a>
</p>

# planetai-node

**Know your air. Keep your data.** A small program for a computer in your home, lab or office. It reads the sensors you
have, compares them with the street and the sky, and tells you what to do, in plain sentences, on Telegram. Readings never
leave your machine.

```bash
curl -fsSL planetai.fab.city/node0/install | bash
```

Four questions, two minutes, running. Then `planetai telegram` for the alerts and `planetai ui` for the dashboard.
Full walk-through in [`docs/START_HERE.md`](docs/START_HERE.md).

## What it does

- **Tells you when it matters.** Inside worse than outside; the street over the WHO line; heat the body cannot shed; a
  sensor that went quiet; a swell worth knowing about. Each message says what is happening, what it means, and what to do.
- **Shows you the place, not a table.** A dashboard with the room's number as a sentence, the day as an annotated chart,
  every sensor with a note, the sea, the land and the weather. Four views: Now, Network, Set up, Wall.
- **Answers questions.** A bot on your Telegram, running a small model on your own machine, reads the node's data and
  explains it. Point it at a bigger model on your network, or online with a key, and it gets sharper.
- **Learns the house.** After a week it knows the street's daily rhythm and how much of it your building keeps out.
- **Keeps the data yours.** Local database, nightly backups a NAS can collect, exports in an open format you decide where
  to send. Twenty years of readings would fit on a phone.
- **Works with what you have.** Smart Citizen (your whole account), AirGradient and PurpleAir over your WiFi, Meshtastic
  radios over LoRa, public stations nearby, free global models. Mac, Linux, Raspberry Pi, Windows with WSL2.
- **Extends with a folder.** Air, heat, coast, land and open-data packs ship; a new domain is a folder of rules, not a fork.

## Why

Air-quality maps know your district. They do not know your kitchen, your bedroom at 3 am, or which hour to open the
windows. A sensor at your address does, and most people who own one look at it twice and stop. This turns that sensor
into something that speaks up when it should and stays quiet when it should not, and it measures whether anyone listened.

The node is the smallest unit of the [Fab City Index](https://index.fab.city): places measuring themselves and sharing
summaries upward, never raw data. Node #1 has run in Kuta Selatan, Bali, since 2 September 2026.

## Read next

```
docs/     getting a node running   START_HERE · PLATFORMS · MAC_MINI · UPDATING · STORAGE
          what it can tell you     USE_CASES · sensors · DOMAINS · COVERAGE · PREFILL · GUI
          extending it             PACKS · PACK_IDEAS · DEVELOPING
          radios and reachability  NETWORKING · MESHTASTIC
AGENTS.md         for an AI agent operating the node
ARCHITECTURE.md   how it is built; SPEC.md   what was left out and when it returns; PRODUCT.md   who pays for what
```

## Layout

```
app/       main.py · sources.py · index.py · packs.py · settings.py · agent.py · agent_loop.py · static/index.html
bin/       planetai, the command line
packs/     air-quality · heat · insight · cold-start · open-data-health · coast · earth-engine · example
config/    rules.yml · mosquitto · reticulum
tools/     the checks, hooks, bundle and release scripts, mesh-provision.sh, nas/, remote-model.sh
tests/     offline suites
presets/   bali · barcelona · boston · santiago · delhi
```

## Licence

Apache 2.0. Fab City Foundation, 2026.
