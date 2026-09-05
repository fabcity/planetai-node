# earth-engine

What the land within a kilometre of the node did last year, from Google Earth Engine. A code pack with a dependency
and a credential; the worked example of both.

**Adds**, once a day, computed server-side over a 1 km buffer: tree, built, crop and water fractions (Dynamic World);
annual median NDVI (Sentinel-2, clouds masked); the latest night-lights radiance (VIIRS); a land-change score, 1 minus
the cosine similarity between this year's and last year's mean AlphaEarth embedding. Stamped mid-year; a daily fetch
inserts nothing new after the first. Two `Environmental|Bioregion` cells and a monthly rule that says the land changed
without pretending to know how.

## Setup

1. Register a project at code.earthengine.google.com/register. Creating a Cloud project and registering it for Earth
   Engine are separate; that page does both. Non-commercial, Community tier.
2. Cloud Console → IAM → Service Accounts → create one. Roles: **Earth Engine Resource Viewer**, **Service Usage
   Consumer**, and **Earth Engine Resource Writer** if you want the timelapse images. Keys → add key → JSON.
3. Copy the JSON to `config/ee-key.json` on the node. In `.env`: `EE_KEY_FILE=/app/config/ee-key.json`,
   `PACKS_ALLOW_CODE=1`. `EE_PROJECT` and `EE_SERVICE_ACCOUNT` can stay blank; the key names both. If you set
   `EE_PROJECT`, use the project id (`planetai-node`), not the service account's 21-digit number; Earth Engine reports that
   mistake as "project not found".
4. `planetai packs` (installs `earthengine-api`), `planetai restart`.
5. `planetai run earth-engine verify`: library, settings, key, credentials, a real query, the four datasets. Names the step
   that failed.

Until configured the pack logs one line and idles.

## Images

```bash
planetai run earth-engine timelapse                              # 4 frames, 5 years apart, ending last year
planetai run earth-engine timelapse --n 5 --gap 2 --source sentinel --km 1
```

Each frame is the annual median of clear pixels: what you see is the year. Landsat by default, the only archive reaching
2010 with one instrument family; Sentinel-2 for 2016 onward at 10 m. If a year has no clear imagery (Landsat 5 over
Indonesia is thin), the nearest year within three is used and said so. PNGs and a side-by-side page land in `out/`.

## Node #1, 2025

91% built, 9% trees, no crops, NDVI 0.51, night lights 14.5. Land-change score 0.037: little changed, because on the
Bukit the change already happened.

## Not

A measurement of your place. Dynamic World is a classifier; the embedding shift says something changed, not what;
a kilometre around a house is mostly other people's land. `partial`, always.
