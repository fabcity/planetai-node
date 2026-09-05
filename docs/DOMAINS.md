# Domains

The core measures nothing in particular. It polls sources, stores readings, runs rules, fills Index cells. Which
readings, which rules, which cells: that is a pack. `grep pm25 app/main.py` returns nothing.

## The shape of any domain

Every domain fits the same four parts:

1. **Sources**: sensors you own, public references nearby, a model as fallback. The adapter contract in `sensors.md`.
2. **A local number**: what your sensors say. Indoor and outdoor kept apart.
3. **A comparison**: yours against the street, the street against the model. The gap is the local signal.
4. **A decision**: one sentence someone can act on, with the threshold's source named.

Air was first because Bali has the sensors and the burn season. Everything below is the same shape.

## Running

**Air** (`packs/air-quality`): PM2.5 inside and outside, spikes, WHO thresholds. **Heat** (`packs/heat`): apparent
temperature from temp and humidity, heat stress, nights over 28 °C. **Coast** (`packs/coast`): waves and sea
temperature. **Land** (`packs/earth-engine`): built-up, tree cover, change. **Governance** (`open-data-health`,
and ρ in the core).

## Designed, not written

**Water**: turbidity, TDS, tank level from a DIY probe over MQTT; is the well safe, will the tank last to the rain.
**Energy**: grid up/down from a smart plug; outage hours as an Economic cell. **Noise**: Smart Citizen emits it already;
school-hours rules. **Classroom CO₂**: AirGradient emits it; open the windows above 1,200 ppm. **Fire smoke**: NASA
FIRMS detections crossed with wind direction. Details and effort in `PACK_IDEAS.md`.

## Writing one

Copy `packs/heat`. Change the metrics, the thresholds, the messages. Say in the README where the thresholds come from
and which place you wrote for. Run `make lint`. You have a domain pack.
