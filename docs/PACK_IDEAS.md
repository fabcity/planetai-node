# Ten packs someone could write this month

A pack is a folder: `pack.yaml`, and any of `rules.yml`, `cells.yml`, `adapter.py`. Most useful packs contain no
code. Each idea below says what it adds, which Index cell it feeds, what it needs, roughly how big it is, and who is
the natural author. Three of them are built and shipped as prototypes: **heat**, **coast**, **earth-engine**.

| # | pack | kind | cell(s) | needs | size | natural author |
|---|---|---|---|---|---|---|
| 1 | **heat** — apparent temperature, heat-stress hours, nights that never cool | data | `Social\|Community` | any temp + humidity sensor (Smart Citizen, BME680 on a Tracker, AirGradient) | 60 lines SQL | a clinic, a school, anyone in Bali or Delhi in April · **shipped** |
| 2 | **coast** — waves, swell, sea temperature at the nearest ocean cell | code | `Environmental\|Bioregion` (context) | nothing: Open-Meteo Marine is free, key-free, global | 50 lines | a surf school, fishers, a coastal community · **shipped** |
| 3 | **earth-engine** — what the land around the node did this year: tree cover, built-up, NDVI, night lights, and the AlphaEarth change score | code | `Environmental\|Bioregion` | a Google Earth Engine project and a service-account key | 150 lines | a university GIS lab, a bioregion node · **shipped** |
| 4 | **fire-smoke** — active fires upwind within 25 km (NASA FIRMS) crossed with wind direction from Open-Meteo: "smoke likely from the SE within two hours" | code | `Environmental\|City` | a free FIRMS MAP_KEY | 60 lines | anyone in Bali's burning season, Chiang Mai, California |
| 5 | **classroom** — CO₂ over 1,200 ppm for 20 minutes → open the windows; a `Social` cell of teachable hours | data | `Social\|Community` | an AirGradient (already emits `co2`) | 40 lines SQL | a school; the Making Sense Bali schools |
| 6 | **outage** — grid up/down from a Shelly or Tasmota plug over MQTT, or a Home Assistant entity: how long, how often, at what hour | data (+ 10-line adapter if not MQTT) | `Economic\|Community` | any smart plug on the broker | 50 lines | a fab lab, a clinic with a fridge, anywhere with brownouts |
| 7 | **water** — turbidity, TDS, tank level from a DIY pod on `planetai/sensors/#`; is the well safe this week, will the tank run dry before the rain | data | `Environmental\|Community` | a $30 probe on an ESP32 | 60 lines SQL | a subak, a village water committee, a permaculture farm |
| 8 | **lab-machines** — hours run, jobs completed, material in, waste out, from a Fabman/Airtable/CSV job log; the closest thing to PITO→DIDO anyone has | code | `Economic\|Community` (the empty column) | the lab's own log or Fabman API token | 100 lines | a fab lab; this is the Fab City question |
| 9 | **portal-socrata** / **portal-arcgis** — the two adapters that fill `governance\|region` for Barcelona (Generalitat) and Boston (MassGIS), same shape as the CKAN one | code | `Governance\|Region` | nothing: public APIs | 40 lines each | a civic-tech group, a public-data journalist |
| 10 | **participation** — a `survey` kind: how many people are in the alert group, how many answered the last question, how many acted; a Telegram poll or a form is the sensor | code | the four empty `Social` cells | a Telegram bot the node already has | 80 lines | Making Sense, a community organiser |

Also worth someone's afternoon: **procurement latency** (TED, ChileCompra, LKPP: institutional ρ at Bioregion, already in
the registry); **noise** (Smart Citizen already emits `noise`; school-street hours); **local language** (a pack that is
only translated messages — Balinese, Catalan, Hindi); **tides** (WorldTides, key) for harbours; **pollen** (Open-Meteo
carries it in Europe).

## How to pick one

Take the one whose sensor you already own and whose decision you already face. The heat pack exists because three
sensors in one house already report temperature and humidity and nobody was reading them for heat. The best pack is
the one that turns a number the node is already storing into a sentence someone acts on.

## What every pack needs from you

A `README.md` that says where the thresholds came from, what the pack assumes about the place, and what it does
not know. `tools/check_rules.py` will tell you if your SQL references a column that does not exist or a placeholder
the SQL never returns; run `make lint` before you open the PR. Code packs should log once and return nothing when
their key or service is missing — a pack must never take the node down. See [`PACKS.md`](PACKS.md).
