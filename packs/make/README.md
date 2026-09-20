# make — where somebody can go to make or fix something

The node reads the air, the sea, the heat, the portal. Then it says the air is bad, and stops.
This pack is the other half of that sentence: the nearest active fab labs, with what each one
can do, so an alert can end with somewhere to go instead of a number to worry about.

## Turning it on

```
MAKE_ENABLED=1
PACKS_ALLOW_CODE=1
```

**Both**, and `MAKE_ENABLED` ships as `0`. That is not caution about code — it is the licence below.
An empty `PACKS_ENABLED` means every pack is enabled, so without its own switch this pack would
start reading a directory nobody licensed the moment a node updated. It did exactly that on node #1
on 2026-09-20, minutes after a release note saying it was off until you turned it on.

## What it stores

One `sensors` row per lab inside `MAKE_RADIUS_KM` (default 50), `kind='facility'`,
`scale='community'`, `local=False`, `source='fablabs-io'`. **No readings.** A facility is a place
with a name and a point; there is nothing to measure about it, and a row that carried a number
would invite somebody to average it.

`meta` holds the slug, capabilities, kind, city, country, distance, the lab's own URL, the
snapshot it came from, and the registry id `economic/community/fablabs-io`. It does **not** hold
email or telephone. Those are in the upstream payload on most records and are never read: a
registry entry is consent to be listed, not consent to be mailed by everybody who imports the list.

## What it never does

**Never a cell.** There is no `cells.yml`, deliberately. `custody` is generated as `kind='child' OR
(local AND kind<>'peer')`, so a `facility` row can never make an Index cell say `live` — which is
right, because a fab lab five kilometres away is not this node's instrument and never becomes one.

**Never an alert.** `rules.yml` is empty and says why. A lab opening is news on the scale of a
year. The line this pack produces belongs in *other* packs' asks — the moment to hear where the fab
lab is, is the moment you have been told you need something made.

**Never `deployed_at`.** Nothing here was deployed by anyone.

## Where it reads

`MAKE_SOURCE=archive` (default) reads the Fab Foundation's own monthly freezes at
`gitlab.fabcloud.org/fl-management/fablab-network-data` — 48 dated files, monthly since January
2025. `MAKE_SNAPSHOT` pins one; blank takes the newest and logs that it did. A pin is the point:
two nodes on the same snapshot answer the same question the same way, which is the discipline
`data/sources/` already applies to the registry this pack's `sources:` point at.

`MAKE_SOURCE=live` reads `api.fablabs.io/0/labs.json`, whose own root page says *"This is the
legacy API endpoint, which has now been removed. A new API will soon be available"* — while serving
5.38 MB anyway. Archive is the default because a dated file is a better dependency than a
contradiction.

Either way one read is ~5.3 MB and there is no way to ask for less: every query parameter is
ignored and the whole directory comes back. So the staleness check runs **before** the fetch, and a
node that already has its labs does nothing at all.

## Licence — read this before relying on the pack

The directory is **not openly licensed**. Each lab retains copyright in its own record (fablabs.io
Terms of Use §8.1) and no data licence is published; §7.4 restricts bulk collection and §7.5
restricts commercial use.

Fab City Foundation decided on 2026-09-20 that PLANETAI may read it and accepted responsibility for
that, pending a Terms of Use clause. **That decision covers the Foundation, not each node's
operator** — every operator is a separate party to those terms. The full reading is in
`data/sources/data/economic/community/fablabs-io.yaml`. If that matters to you, leave this pack off.

## Labs with no coordinates

179 active labs network-wide publish no latitude or longitude. They cannot be placed, so they are
not in the ring — but they are counted, and `planetai doctor` says how many. A real lab in a real
city disappearing into a smaller number is the kind of quiet loss this repo tries not to have.
