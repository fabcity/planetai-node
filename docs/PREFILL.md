# Pre-filled data — what a node knows before it has a sensor

A node needs coordinates. That's it. On first start it pulls three months of history and forty years of normals for
its location from free, key-free, global sources, and starts sending useful messages the same day. Hardware makes it
better; hardware is not the entry fee.

```bash
./install.sh --preset barcelona --name lab-roof     # no sensor flags at all
```

Within about a minute: ~2,200 rows in the database, a place name, a modelled air-quality line, and a seasonal
baseline going back to 1981.

## What arrives, and from where

| source | what you get | key? | coverage | when |
|---|---|---|---|---|
| **Copernicus CAMS** via Open-Meteo | 92 days of hourly PM2.5 and PM10 history, then current PM2.5/PM10/dust/AOD/CO/NO₂/O₃/UV every poll | no | global, ~11 km grid | first start + every 5 min |
| **NASA POWER** | monthly long-term normals for solar irradiance, temperature, rainfall, humidity, wind — satellite-derived, 1981–present | no | global, 0.5° grid | first start |
| **Open-Meteo forecast** | current temperature, humidity, precipitation, wind speed and direction | no | global | every poll |
| **OpenStreetMap Nominatim** | a place name, so alerts say somewhere real instead of two decimals | no | global | first start, once |
| **CKAN portals** | how much of your city's open data was updated in 90 days | no | any CKAN portal | daily |

All of it lands as `kind='model'` or `kind='portal'`. **None of it is a measurement of your place**, and the core will
never let a pack claim a `live` Index cell from it. That distinction is the point, not a caveat.

## The one number this makes possible on day one

The `cold-start` pack ships enabled and turns the above into three messages that need no hardware:

- today's modelled air quality, stated plainly as a model;
- today against forty years of normals for this month at this point ("it is 4 °C above normal here");
- and, once you *do* put a sensor up, the weekly gap between your reading and the model.

That third one is the argument for the whole project compressed into one line. When a node's outdoor sensor reads
48 µg/m³ against a modelled 22, the model isn't broken — it's a 11 km grid cell that cannot see a fire two streets
away. **The gap is the local signal.** A global model tells you what the atmosphere is doing over your district; only
something at the address tells you what you are breathing. Being able to show that difference, from day one, is a
better argument for buying a sensor than any brochure.

## What needs a key, and is therefore opt-in

Not shipped enabled, because "sign up for an account" is exactly the friction this page exists to remove.

| source | why you'd add it | what it costs |
|---|---|---|
| **OpenAQ** | harmonised regulatory + low-cost station data worldwide; the reference layer outside Bali | free registration, `X-API-Key` header |
| **Google Flood Hub** | riverine flood forecasts, listed in the Index registry for Bali, Barcelona and Santiago | Google Cloud project |
| **Google Air Quality API** | gridded AQ at higher resolution | paid tier |
| **Copernicus Data Space (Sentinel)** | actual satellite imagery — NDVI, land surface temperature, built-up area | free registration, and raster handling the node doesn't have |
| **Bali Air Dispatch** | island-wide aggregated ambient picture for Bali | none — key-free, but only meaningful in Bali |

## Site presets

Four pilot sites ship as one-line presets: coordinates, timezone, language, and the city's open-data portal.

```bash
./install.sh --preset bali        # Kuta Selatan region · id · Bali Satu Data · BAD reference on
./install.sh --preset barcelona   # · Open Data BCN
./install.sh --preset boston      # · Analyze Boston
./install.sh --preset santiago    # · datos.gob.cl
```

Anywhere else works identically with `--lat --lon`; the bootstrap sources are global. Adding your city is a pull
request with one file in `presets/`.

## What I deliberately did *not* embed

**Static datasets in the repo.** World Bank waste figures, economic complexity rankings, admin boundaries — all
tempting, all a licensing and staleness liability in a git repo, and all fetchable at install if a pack ever needs
them. A repo should ship code and thresholds, not a copy of someone else's database going quietly out of date.

**A pre-seeded demo database.** Fake readings that look real are how a project starts lying to itself. Every row in a
fresh node is either genuinely from your coordinates or absent.

**Anything requiring an account.** The install must complete with no sign-ups. Everything above respects that; the
opt-in table is opt-in for exactly this reason.

## Attribution you inherit

Using this data puts obligations on you, and they're carried in each source's `sensors.meta`:

- **CAMS** — credit the CAMS ENSEMBLE data provider *and* Open-Meteo, per Open-Meteo's terms.
- **NASA POWER** — credit the NASA Langley Research Center POWER Project.
- **Nominatim** — OpenStreetMap contributors, ODbL. The node queries it once per install, never in a loop, with a real user agent, per their usage policy.
- **CKAN portals** — each city's own licence.

If you publish a chart from a node, those credits travel with it.
