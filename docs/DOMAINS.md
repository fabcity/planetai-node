# Domains — what a node can measure

> Domains are the *what*. Scales are the *how far* — a node fills Index cells at Community through Planet using three
> different ingestion classes. See [`COVERAGE.md`](COVERAGE.md) for the 4×5 matrix and what's missing.


The core knows nothing about air, water, or electricity. It knows about **readings**: a time, a sensor, a metric name,
a number. Everything domain-specific — what counts as bad, what someone should do about it, which Index cell it feeds —
lives in a pack. Air is the first one and the template for the rest; nothing in `app/` mentions PM2.5.

That's the modularity claim, and here's the precise version so it can be checked rather than believed:

- **No threshold, no message, no pillar mapping in `app/`.** Those live in packs. `grep -rn pm25 app/main.py app/index.py app/packs.py` returns nothing.
- **Adapters do name metrics**, because devices do — an AirGradient adapter has to know its `pm02` field is `pm25`. That's a driver, not a domain: it translates a device into the schema and stops there.
- The line is: *the core moves numbers and evaluates SQL; a pack decides what a number means.*

## The shape of any domain

```
sensor  ─▶  readings(ts, sensor_id, metric, value)     the core: domain-blind
             │
             ├─▶ rules.yml   "when this SQL is true, tell these people this"      a pack
             └─▶ cells.yml   "this SQL is our number for Pillar|Scale"            a pack
```

To add a domain you need three things: a sensor that can emit a number, a rule that ends in something a person does,
and — optionally — a cell that maps it to one of the Index's four pillars. Not a fork, not a new service.

## Running today

| domain | metrics | rules | cells | status |
|---|---|---|---|---|
| **Air** | `pm25 pm25_raw pm10 pm1 temp humidity pressure aqi` | indoor/outdoor decision, WHO exceedance, ventilate | `Environmental\|Community`, `Environmental\|City` | **live** — `packs/air-quality`, running at node #1 |

## Designed, not written

These are honest sketches, not promises. Each is a pack someone can write without touching the core — the metric names
below are proposals, and the first person to build one gets to fix them.

| domain | metrics | the decision it would drive | pillar | what's needed |
|---|---|---|---|---|
| **Water** | `turbidity tds ph water_level flow_rate rainfall` | Is the well or spring safe this week? Is the tank going to run out before the rain? Should the subak divert? | Environmental | a $30 TDS/turbidity probe on an ESP32 → the MQTT adapter (SPEC §6 trigger) |
| **Energy** | `power_w energy_kwh voltage grid_up solar_w battery_soc` | Run the kiln now or in two hours? Is the lab about to trip its supply? Did the outage last night hit the fridge? | Economic | a clamp meter or a shelly/tasmota device on the LAN — an adapter and a rule |
| **Fabrication** | `machine_hours jobs_completed material_kg filament_g uptime_pct` | Which machine is the bottleneck this week? Is the lab producing more than it imports? | Economic | reads the lab's own job log or machine controller; feeds the PITO→DIDO ratio directly |
| **Mobility & noise** | `noise_db vehicle_count occupancy` | Is the school street too loud to teach in at 8am? Did the traffic change after the intervention? | Social | the Smart Citizen kit already emits `noise`; the rule doesn't exist yet |
| **Buildings & comfort** | `temp humidity co2 tvoc_index lux` | Ventilate the classroom before the CO₂ makes them sleepy. Is this room habitable in a heatwave? | Social | AirGradient already emits `co2` and `tvoc_index`; a pack away |
| **Food & soil** | `soil_moisture soil_temp ec canopy_temp` | Irrigate or wait. Is this plot drying faster than last season? | Environmental | cheap probes, an MQTT adapter, and someone who farms |

The Fab City Index has four pillars — Environmental, Economic, Social, Governance — across five scales. Air fills two
cells. **Governance is already filled by the core**, at every node, in every domain, because ρ is computed from the
actions ledger regardless of what the node measures. The other pillars are open, and Economic in particular is where a
fab lab's own machine data would say something no environmental sensor can: whether the place is producing what it consumes.

## Why start with air

Not because it's the mission. Because it was on the wall. Node #1 had a Smart Citizen kit already installed, a public
reference network already published, and a decision people genuinely face every morning. That made it the cheapest
possible test of the actual thesis: *can an observation become an action at an address, and can we measure whether it did.*

The second domain is more interesting than the first, because it's the one that proves the answer generalises. If it
needs a fork, the architecture is wrong. If it needs a folder, it's right.

## Writing a domain pack

Copy `packs/air-quality/` — it's a data pack, no code, and it carries the three things a domain needs: rules, cells, and
a README saying where the numbers were learned. Full model in [`PACKS.md`](PACKS.md); metric naming and units in
[`sensors.md`](sensors.md).

One rule of authorship worth repeating: **the numbers are local.** 35.5 µg/m³ means something in the US EPA's scale and
something else in a kitchen in Kuta Selatan at dinner time. A pack that hardcodes a threshold without saying where it
came from is a pack nobody outside that place can trust.
