# Ten packs someone could write this month

Three are built (heat, coast, earth-engine). Each row: what it adds, the Index cell, what it needs, rough size, who
would naturally write it.

| # | pack | kind | cell | needs | size | author |
|---|---|---|---|---|---|---|
| 1 | **heat**: apparent temperature, heat-stress hours, nights that never cool | data | Social\|Community | any temp + humidity sensor | 60 lines SQL | a clinic, a school · shipped |
| 2 | **coast**: waves, swell, sea temperature | code | Environmental\|Bioregion | nothing; Open-Meteo Marine is free | 50 lines | a surf school, fishers · shipped |
| 3 | **earth-engine**: tree cover, built-up, NDVI, night lights, land change | code | Environmental\|Bioregion | a Google Earth Engine project | 150 lines | a GIS lab · shipped |
| 4 | **fire-smoke**: active fires upwind within 25 km (NASA FIRMS) crossed with wind | code | Environmental\|City | a free FIRMS key | 60 lines | Bali's burning season, Chiang Mai |
| 5 | **classroom**: CO₂ over 1,200 ppm for 20 min: open the windows | data | Social\|Community | an AirGradient | 40 lines SQL | a school |
| 6 | **outage**: grid up/down from a smart plug over MQTT | data | Economic\|Community | any plug on the broker | 50 lines | a lab, a clinic with a fridge |
| 7 | **water**: turbidity, TDS, tank level from a DIY probe | data | Environmental\|Community | a $30 probe on an ESP32 | 60 lines SQL | a subak, a water committee |
| 8 | **lab-machines**: hours run, jobs, material in and out, from a job log | code | Economic\|Community | a Fabman token or a CSV | 100 lines | a fab lab; the Fab City question |
| 9 | **portal-socrata / portal-arcgis**: the adapters for Barcelona and Boston | code | Governance\|Region | nothing | 40 lines each | a civic-tech group |
| 10 | **participation**: a `survey` kind: who is in the alert group, who answered, who acted | code | the empty Social cells | the Telegram bot the node has | 80 lines | Making Sense |

Also an afternoon each: procurement latency (TED, ChileCompra, LKPP), noise (Smart Citizen emits it), a pack that is
only translated messages, tides, pollen.

## Picking one

Take the one whose sensor you own and whose decision you face. The heat pack exists because three sensors in one house
already reported temperature and humidity and nobody was reading them for heat.

## What every pack needs

A README that says where the thresholds came from, which place they were written for, and what the pack does not know.
`make lint` before the PR. A code pack must log once and do nothing when its key or service is missing.
