# place

What is around the node, from OpenStreetMap, kept in PostGIS on the node, summarised once a month.

**Adds** the sensor `place-point` (kind `map`, scale `community`) with: buildings and the share of ground they cover;
the share of buildings that are commercial; mapped businesses per km²; places to eat, shops and markets, schools,
clinics and pharmacies, places of worship, lodging, services; kilometres of road; share of green; and the walk to the
nearest school, clinic, market and place of worship. One `Economic|Community` cell (businesses per km², `partial`). One
message a month.

**Setup.** Nothing to configure. `PACKS_ALLOW_CODE=1` (it is a code pack), `planetai packs`, `planetai restart`. The
first poll fetches everything within `PLACE_RADIUS_M` (1000) from the Overpass API and stores the geometries in
PostGIS, which the node's database image now includes. Later polls recompute from what is stored; every
`PLACE_REFRESH_DAYS` (30) it fetches again. `planetai run place refresh` forces a fetch.

## Node #1, September 2026

Within a kilometre of bayu-2: 2,904 buildings, 540 road segments, 37 mapped places. Nineteen to eat at (Warung Made,
Bali Buda Bukit, Semboja), six markets (Alfamart, Indomaret, the Morning Market), sixteen villas and guesthouses, two
health, no school. That last number is OpenStreetMap coverage on the Bukit, not the Bukit.

## What it is, and is not

Structure, and change between refreshes. Not behaviour: three warungs on the map say nothing about how busy the street
is; the sensors do. Not production: the Fab City question for the Economic pillar is what a place makes, repairs and
sells, and the honest numbers for that are a fab lab's machine log and a market's stall count. Business density is the
proxy until those exist, and the cell says `partial`.

**Zeroes mean unmapped.** Every message and label says so. If the map is wrong about your place, fix the map: that
is what OpenStreetMap is for, and the node picks it up on the next refresh.

## Why PostGIS

The questions above are a fixed set and could be answered in Python. PostGIS is there because the next questions are
not fixed: distance from the kitchen sensor to the nearest busy road, how much roof is within 200 m of the outdoor kit,
which sensors sit downwind of the burning. The geometries are in the node's database, queryable by any pack.

## Sources to add

Overture Maps (monthly releases: diff two and see what opened, closed, was built); Google Open Buildings (footprints
and heights where OSM is thin). Both open. Both a second fetch into the same table.

© OpenStreetMap contributors, ODbL.
