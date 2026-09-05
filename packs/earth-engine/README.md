# earth-engine

What the land within a kilometre of the node did this year, from Google Earth Engine's public catalog. A **code pack**
with a **dependency** (`earthengine-api`) and a **credential** (a service-account key), which makes it the worked
example of everything a heavier pack has to get right.

**What it adds** — once a day the pack asks Earth Engine for scalars over a 1 km buffer, all computed server-side:
tree, built, crop and water fractions from Dynamic World; the annual median NDVI from Sentinel-2 with clouds masked;
the latest VIIRS night-lights radiance; and a **land-change score**, 1 minus the cosine similarity between this
year's and last year's mean 64-dimension AlphaEarth embedding. Readings are stamped mid-year and dedupe, so a daily
fetch inserts nothing new after the first. Two `Environmental|Bioregion` cells (tree cover, land change) and a
monthly rule that says the land changed without pretending to know how.

**What it needs from you**
1. An Earth Engine project (free for research and non-commercial use) at https://code.earthengine.google.com.
2. A service account with Earth Engine access and its JSON key, saved as `config/ee-key.json` (that directory is
   already mounted read-only into the app; the file is gitignored).
3. In `.env`: `EE_PROJECT=<project id>`, `EE_SERVICE_ACCOUNT=<email>`, `EE_KEY_FILE=/app/config/ee-key.json`,
   and `PACKS_ALLOW_CODE=1`.
4. `planetai packs` — installs the pack's Python dependency into the image and rebuilds.

Until all of that exists the pack logs one line and stays idle. It cannot take the node down.

**What it is not.** A measurement of your place. Dynamic World is a classifier; the embedding shift says *something*
changed, not what; 1 km around a house in Kuta Selatan is mostly other people's land. `partial` forever, and the
methodology's rule holds: bioregion context flows down to nodes, never up into their cells.

**Status.** Not yet run against a live Earth Engine account. The logic is tested with a fake `ee`
(`tests/test_packs.py`); dataset IDs are as published at time of writing and the fetch logs by name any that fail.
The first real run should be watched in `planetai logs`.
