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

**Check the setup** once configured, instead of waiting a day for the first fetch:

```bash
docker compose exec -T app python /app/packs/earth-engine/verify.py
```

It walks the five steps in order — library, settings, key file, credentials, a real query — and names the one that
is not done. Step 5 prints the ground elevation at the node, which is a harmless query that proves the whole path.

**What it needs from you**
1. **A registered project.** Go to https://code.earthengine.google.com/register — creating a Cloud project and
   registering it for Earth Engine are separate things, and starting at that page does both. Choose *Unpaid usage →
   Non-commercial*, the closest role (research or educational), and the **Community tier** unless you plan heavy
   compute. Registration enables the Earth Engine API immediately.
2. **A service account and its JSON key.** A node has no browser, so the interactive login is not an option.
   Cloud Console → *IAM & Admin → Service Accounts → Create*. Grant it **Earth Engine Resource Viewer** and
   **Service Usage Consumer** on the project. Then *Keys → Add key → Create new key → JSON*; it downloads once.
   Copy it to `config/ee-key.json` on the node (that directory is mounted read-only into the app; the file is
   gitignored). Over the tailnet:
   `scp key.json <user>@<node>.ts.net:~/planetai/planetai-node/config/ee-key.json`
3. In `.env`: `EE_KEY_FILE=/app/config/ee-key.json` and `PACKS_ALLOW_CODE=1`. `EE_PROJECT` and
   `EE_SERVICE_ACCOUNT` may be left blank — the key file names both, and the pack reads them from it.
   If you do set `EE_PROJECT`, it must be the **project id** (`planetai-node-472103`), not the service account's
   21-digit unique id; Earth Engine reports that mistake as `Project not found or deleted`.
4. `planetai packs` — installs the pack's Python dependency into the image and rebuilds.

Until all of that exists the pack logs one line and stays idle. It cannot take the node down.

**What it is not.** A measurement of your place. Dynamic World is a classifier; the embedding shift says *something*
changed, not what; 1 km around a house in Kuta Selatan is mostly other people's land. `partial` forever, and the
methodology's rule holds: bioregion context flows down to nodes, never up into their cells.

**Status.** Not yet run against a live Earth Engine account. The logic is tested with a fake `ee`
(`tests/test_packs.py`); dataset IDs are as published at time of writing and the fetch logs by name any that fail.
The first real run should be watched in `planetai logs`.
