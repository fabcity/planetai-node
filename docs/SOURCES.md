# Sources: the registry the node carries

`GET /cells` says what this node measures. `planetai sources` says what the network has established
*could* be measured where this node stands, and which of it anything reads yet. The gap between the
two is the useful part: on 5 September somebody worked it out by hand for the Bali pilot — nine cells
with a registered source and no adapter, seven with no source at all — and that sentence went stale
the week it was written. It is a query now.

## Where it lives

The source of truth is [`awesome-fabcity-data`](https://github.com/fabcity/awesome-fabcity-data): one
YAML file per source at `data/<pillar>/<scale>/<slug>.yaml`, validated against its own schema in its
own CI. It is the network's decision about what can be measured at each pillar and scale, and **a
source a pack reads has to be a row there first** — the same rule `docs/site/federation.md` states
for the Index.

This repository carries a **pinned copy** at `data/sources/`, vendored by `tools/sync_registry.sh`.
`data/sources/REGISTRY_VERSION` says which commit, when it was taken, and how many entries it holds.

Pinned rather than fetched, for three reasons. A node on a boat with the uplink down answers the same
question as a node in Barcelona. Every node in a release answers it the *same way*, instead of each
one getting whatever upstream main said the morning it rebooted. And a change to what a node believes
about the network is then a diff somebody reviewed, in a release, like every other change. It is why
the sync script refuses a branch name.

Nothing in this repository edits a source entry. `make lint` fails if anything did:
`tools/check_registry.py` re-derives `index.json` from the YAML and compares it byte for byte.

## Reading it

    planetai sources                      # this node's pilot, plus the global rows
    planetai sources --all                # all 209
    planetai sources --cell 'Social|City' # what is filed for one Index cell
    planetai sources --pillar economic --scale community
    planetai sources --json

One line per source: the slug a pack names, its status, its licence, which pilots it covers, and
`wired` when something here already reads it. **A cell with sources and no `wired` is a cell nobody
has written an adapter for yet** — which is the list of things worth building next, for this place,
sorted by somebody other than whoever is in the room.

It reads the node over HTTP when the node is answering and `data/sources/index.json` off the disk
when it is not, and gives the same answer either way. Over HTTP it is `GET /sources`, with the same
filters as query parameters, plus `GET /sources/<pillar>/<scale>/<slug>` for one entry.

`/cells` rows carry two fields from the same snapshot: `registered`, how many sources are filed for
that cell, and `adapter`, whether anything reads one. A cell with a registered source and **no**
adapter has no `/cells` row at all — a node only emits rows it can compute — so that half of the
question is `planetai sources --cell` and not `/cells`.

`planetai doctor` prints which pin the node carries, and goes amber when it is over 180 days old.

## Adding a source

1. PR the entry to [`awesome-fabcity-data`](https://github.com/fabcity/awesome-fabcity-data),
   following its `CONTRIBUTING.md`. One pillar and one scale, the one where the signal is strongest;
   the schema is `additionalProperties: false`, so a key it does not name is a failed PR.
2. Wait for the merge. What a pack may name is what the registry has *published*.
3. On a dev machine, re-pin: `tools/sync_registry.sh <the merge sha>`. It refuses a branch name.
4. Commit the diff — `data/sources/` and nothing else — and put one line in `CHANGELOG.md`.
5. Only now may a `packs/*/pack.yaml` name it in `sources:`. `make lint` enforces that order.

The entry travels to the node in the next release, with everything else.
