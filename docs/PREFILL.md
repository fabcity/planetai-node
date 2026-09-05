# What a node knows before it has a sensor

On first start, with an empty database, the node pulls for its coordinates:

| source | what | span | cost |
|---|---|---|---|
| Copernicus CAMS (via Open-Meteo) | hourly PM2.5, PM10, O₃, NO₂, dust, UV, 11 km grid | last 92 days, then live | free, no key |
| NASA POWER | monthly temperature, humidity, rain normals | 40 years | free, no key |
| Open-Meteo | weather now: temp, humidity, wind, rain | live | free, no key |
| OpenStreetMap Nominatim | the place name | once | free |

So `planetai status` has something to say within minutes, anywhere on Earth: today's modelled air against three months
of history, today's weather against forty years of normals. `BOOTSTRAP=0` skips it.

## The number this makes possible

The gap between the model and your first sensor. At node #1 the CAMS cell tracks the street at r = 0.51 and the room at
r = −0.18. The model knows the district; a sensor knows the address. That difference is the reason the sensor exists,
and the node can state it the day a sensor arrives.

## Opt-in, because they need a key

OpenAQ (global public sensors), Google Flood Hub, Sentinel-5P via Earth Engine, NASA FIRMS. Each is a code pack or an
adapter behind a flag, off by default. Nothing that needs an account runs unless you turn it on.

## Presets

`presets/<city>.env`: bali, barcelona, boston, santiago, delhi. Coordinates, time zone, city key, the open-data portal,
and for Bali the public station feed. `planetai setup` picks one when your place falls inside a pilot city.

## Not embedded

No copies of datasets, no model weights, no map tiles. The node fetches what it needs when it needs it and keeps only
what it computed. A node is a few hundred kilobytes of code.

## Attribution

Copernicus Atmosphere Monitoring Service (CC BY 4.0); NASA POWER; Open-Meteo (CC BY 4.0); OpenStreetMap (ODbL). The
daily export names them.
