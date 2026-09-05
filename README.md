<p align="center">
  <img src=".github/banner.png" alt="planetai-node — Sense. Observe. Act." width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-20388D?style=flat-square"></a>
  <a href="CHANGELOG.md"><img alt="Version 0.18" src="https://img.shields.io/badge/version-0.18-171717?style=flat-square"></a>
  <img alt="Node #1 live" src="https://img.shields.io/badge/node%20%231-live%20in%20Bali-00A057?style=flat-square">
  <img alt="Containers: 2" src="https://img.shields.io/badge/containers-2-171717?style=flat-square">
  <img alt="Clouds required: 0" src="https://img.shields.io/badge/clouds%20required-0-171717?style=flat-square">
  <a href="https://planetai.fab.city/node0/"><img alt="Landing page" src="https://img.shields.io/badge/planetai.fab.city-node0-20388D?style=flat-square"></a>
</p>

# planetai-node

A node is the smallest unit of a distributed computer for places. It observes where it stands, decides locally, tells
the people there what to do, and sends upward only what it chooses. Readings stay on your machine. What travels is
hourly means, [Fab City Index](https://index.fab.city) cells, and the number nobody else measures: whether an
observation became an action.

```bash
curl -fsSL planetai.fab.city/node0/install | bash
```

It asks four things: a name, the place (typed as words), what the node is for, and your sensor if you have one. Two
minutes later it is running. Then:

```bash
planetai telegram      # alerts to your phone
planetai test-alert    # see the whole path fire
planetai ui            # the dashboard
```

No sensor yet? The node still knows something: on first start it pulls three months of Copernicus air-quality history
and forty years of NASA climate normals for its coordinates. Free, no key, anywhere. Add a sensor when you have one;
the interesting number is then the gap between your reading and the model.

## What it is

Two containers, Postgres and one Python service, about 1,900 lines. Domain-blind: the core knows readings, rules and
cells, not air. Eight packs know air, heat, the coast, the land. Scale-blind: sensors at an address, open-data portals
at a city, Earth models at the planet, one schema. Node #1 has run in Kuta Selatan, Bali, since 2 September 2026.

It reads Smart Citizen (your whole account), AirGradient and PurpleAir (over your WiFi, no cloud), Meshtastic radios
over LoRa, Bali's public stations, and free global models. It speaks Telegram, the LoRa mesh, Reticulum, Home
Assistant, and MCP, so your own AI agent can run it. `planetai agent local` puts a small model on the node itself. It runs on a Mac, Linux, a Raspberry Pi, or Windows with WSL2.

## Read next

```
docs/     getting a node running   START_HERE · PLATFORMS · MAC_MINI · UPDATING · STORAGE
          what it can tell you     USE_CASES · sensors · DOMAINS · COVERAGE · PREFILL
          extending it             PACKS · PACK_IDEAS · DEVELOPING · GUI
          radios and reachability  NETWORKING · MESHTASTIC
ARCHITECTURE.md   the building; SPEC.md   what was cut and when it returns; PRODUCT.md   who pays for what
AGENTS.md         for an AI agent operating the node: MCP at /mcp, --json commands, invariants
```

## Layout

```
app/       main.py · sources.py · index.py · packs.py · settings.py · bootstrap.py · static/index.html
bin/       planetai, the operator CLI
packs/     air-quality · heat · insight · cold-start · open-data-health · coast · earth-engine · example
config/    rules.yml (two domain-blind rules) · mosquitto · reticulum
tools/     the gates · hooks · bundle.sh · release.sh · mesh-provision.sh · nas/
tests/     six offline suites
presets/   bali · barcelona · boston · santiago · delhi
```

## Licence

Apache 2.0. Fab City Foundation, 2026.
