# Domains

The core measures nothing in particular. It polls sources, stores readings, runs rules, fills Index cells. Which
readings, which rules, which cells: that is a pack. `grep pm25 app/main.py` returns nothing.

## Issues: what a domain is called in the house

A **domain** is what a pack declares. An **issue** is what a household calls it, and there are fewer
of them: air · heat · land · coast, with water, noise and energy designed in `PACK_IDEAS.md`. An
issue is something a place can be better or worse at, that somebody living there recognises by name.

Not every domain is an issue. *Weather* feeds air and heat — wind for working out where a smell came
from, the forecast for the day ahead — but nobody asks how the weather is doing as a quality of their
place. *Place* is the ground everything else sits on. *Governance* is the loop and the Index. *Trust*
is the node's own instruments, not the place at all.

| issue | packs | kind | the line, and where it comes from |
|---|---|---|---|
| **air** | `air-quality`, `nearby` | sensed | 15 µg/m³ — WHO 2021, 24-hour mean |
| **heat** | `heat` | sensed | 35 °C apparent — measured at node #1, this place's line and not a global one |
| **land** | `earth`, `earth-engine` | context | none. A year-over-year change is not a threshold |
| **coast** | `coast` | context | none |
| — | `forecast` (weather) | | feeds air and heat |
| — | `place` | | the ground, its own band on the dashboard |
| — | `open-data-health` (governance) | | the loop and the Index |
| — | `trust` | | the instruments |
| — | `insight`, `cold-start` (cross-domain) | | each rule belongs to the issue it names |

A **sensed** issue has eyes on it and rules that can ask somebody to do something. A **context**
issue informs and never asks: it has no act-level rules, and land's cadence is a year.

The declarations are `app/issues/*.yml` — one file per issue, holding its name in three languages,
its metric and unit, its line and that line's source, which packs feed it, how each of the four
distances (room · yard · ring · region) is computed, and its sentence templates. **Adding a fifth
issue is a fifth file plus a pack that declares its domain.** `tests/test_issues.py` asserts that by
loading a synthetic `water.yml`, and it also asserts that every enabled pack reaches an issue or is
named as deliberately not one — so a new pack cannot arrive unmapped and unnoticed.

`NODE_ISSUES` is the keeper's order, most important first. The presets guess per place (Bali:
`air,heat,land,coast`; Barcelona and Boston: `heat,air`) and every preset says to change it. This is
the political layer and it should be: what matters in Serangan is decided by the people in Serangan,
not by which pack was written first. An issue the keeper has not declared is still shown, greyed, so
a stranger can see what the node could report.

`GET /issues` is where all of it comes out, and the `issues` MCP tool returns the same object, so an
agent and the household describe the same evening in the same words.

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
and ρ in the core). **Trust** (`packs/trust`): not a place, the node's own instruments — whether they are frozen,
missing hours or disagreeing with a neighbour.

## Designed, not written

**Water**: turbidity, TDS, tank level from a DIY probe over MQTT; is the well safe, will the tank last to the rain.
**Energy**: grid up/down from a smart plug; outage hours as an Economic cell. **Noise**: Smart Citizen emits it already;
school-hours rules. **Classroom CO₂**: AirGradient emits it; open the windows above 1,200 ppm. **Fire smoke**: NASA
FIRMS detections crossed with wind direction. Details and effort in `PACK_IDEAS.md`.

## Writing one

Copy `packs/heat`. Change the metrics, the thresholds, the messages. Say in the README where the thresholds come from
and which place you wrote for. Run `make lint`. You have a domain pack.
