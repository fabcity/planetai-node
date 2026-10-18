# thingdata

**What it adds** — reads one or more [ThingData](https://github.com/reuse-city/thingdata-server) servers
(reuse-city's repair-knowledge protocol) and publishes two `Economic|City` cells — how much of a place's catalogue
has repair knowledge attached, and how much of that knowledge exists at all — plus a rule that fires when nobody
has written anything for a quarter. Code pack: set `THINGDATA_INSTANCES` and `PACKS_ALLOW_CODE=1`.

```
THINGDATA_INSTANCES=reuse-city=https://thingdata.example.org
```

**Why these numbers** — a ThingData server's own `/health` reports CPU and memory, which says nothing about whether
the commons is alive. Counts do, and one ratio does more: the share of catalogued things that any guide, story or
relationship actually names. A catalogue of 400 devices with guides for nine is a wish list. The freshness figure
is the same DIDO signal `open-data-health` reads off a CKAN portal — a repository nobody adds to is an archive.

**Thresholds** — the rule fires below 10 % of guides and stories touched in 90 days. That is the same guess
`open-data-health` makes about portals, carried over unchanged, and it has never been watched against a real
ThingData deployment. Correct it once someone has.

**What it assumes** — ThingData v0.1.3's public read API: `GET /api/v1/{things,guides,stories,relationships}` with
`skip`/`limit`, no auth. The federation endpoints are ignored; a federated server is counted as what it serves. There
is no count endpoint, so the pack pages the whole catalogue (100 rows a request) and refuses above `THINGDATA_MAX`
(5000) rather than report a truncated total as a total.

**What it does not know** — where any of it is. ThingData entities carry no coordinates, so a server three
continents away counts the same as the one down the road; the cell says City because whoever runs the server says
which city. It does not know whether a guide is any good, whether anyone followed it, or whether a thing was
actually repaired — those are the impact-tracking parts of the ThingData roadmap, unbuilt on both sides.

**Where it was learned** — nowhere yet. Written against the reference implementation's source, not against a
deployment.
