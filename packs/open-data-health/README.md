# open-data-health

**What it adds** — a `Governance|City` cell from any CKAN open-data portal, and a rule that fires when a portal has
gone quiet. Requires the `ckan` adapter (set `CKAN_PORTALS` in `.env`).

**Why this cell** — the Index registry has four CKAN portals under `governance|city` (Open Data BCN, Analyze Boston,
datos.gob.cl, Bali Satu Data) and no way to say anything about them. Dataset *count* is a vanity number; the share
touched in 90 days says whether anyone is home. That is a DIDO signal: a city that publishes and maintains its data
is doing distributed data, a city with a frozen portal is doing a press release.

**What it assumes** — a CKAN portal with a public `package_search` endpoint. Socrata and ArcGIS portals need their own
adapters; the cell SQL would not change, only the source.

**Where it was learned** — nowhere yet. This pack is written from the registry, not from a deployment. It runs, but the
thresholds (10% for "stale") are a guess until someone watches a real portal for a quarter and corrects them.
