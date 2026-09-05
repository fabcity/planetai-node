# Packs — how other people extend a node

The core is small on purpose: two containers, four adapters, five rules. Everything specific to a place —
what "bad" means in Kerobokan versus Poblenou, which sensor a lab happens to own, what a banjar wants to be told —
belongs to whoever lives there. **Packs** are how that arrives without going through us.

The split, in one line: **core ships what every node needs; packs ship what one place needs.** Core moves slowly
under tagged releases we review; packs move at the speed of whoever wrote them.

---

## 1. What a pack can extend

A node has exactly four extension points. A pack is a folder that fills in one or more of them.

| point | file | what it is | code? |
|---|---|---|---|
| **Rules** | `rules.yml` | SQL over the `stats` view + a message template. "When this is true, tell these people this." | no |
| **Cells** | `cells.yml` | SQL returning one `value` → an `fci-cells-v0` row for the Fab City Index | no |
| **Sources** | `adapter.py` | a `fetch(hc)` returning `(sensors, readings)` — a new sensor or public data feed | **yes** |
| **Metadata** | `pack.yaml` | id, name, description, author, version, `requires`, scales | — |

The first two are **data**. That's the important part: most of what a community actually knows how to contribute is
a threshold and a sentence, and neither needs to be Python. A pack that teaches nodes in a monsoon climate to ignore
the humidity spike after rain is fifteen lines of YAML.

## 2. Data packs and code packs

**Data packs** (`rules.yml` / `cells.yml`, no `.py`) load automatically. The SQL runs against the node's own database
through the same path the core rules use. Low risk, low ceremony — this is the default and the one we want most of.

**Code packs** (`adapter.py`) do not load unless the operator sets `PACKS_ALLOW_CODE=1`. A pack's Python runs with the
node's privileges and network access. The node warns and skips rather than guessing:

```
pack acme-sensor ships code; set PACKS_ALLOW_CODE=1 to run it (read /app/packs/acme-sensor/adapter.py first)
```

That warning is the whole security model at this scale, and it is deliberately blunt: **read the file**. An adapter is
usually forty lines. If you can't read forty lines of Python, don't enable the pack — ask in the issue tracker and
someone who can will.

## 3. Installing one

```bash
cd ~/planetai/planetai-node
git clone https://github.com/someone/planetai-pack-monsoon packs/monsoon
docker compose restart app          # rules reload by themselves within a minute; adapters need the restart
curl -s localhost:8080/packs | python3 -m json.tool
```

To load only some: `PACKS_ENABLED=monsoon,cooking-hours` in `.env`. To disable one: delete the folder, or drop it
from that list. There is no package manager, no lockfile, no dependency graph. A pack is a folder.

## 4. Writing one

Copy `packs/air-quality/` — the official air pack, and proof the core is domain-blind: three rules, three Index cells,
no code, and a README saying where every threshold was learned. Or `packs/example-cooking-hours/` for something smaller.

```
packs/my-pack/
  pack.yaml     id, name, description, author, version, requires: { node: ">=0.1.1" }, kind: data|code
  rules.yml     optional — ids are namespaced automatically to my-pack/<id>
  cells.yml     optional — [{ cell: "Environmental|Community", unit: "...", sql: "SELECT ... AS value", state: partial }]
  adapter.py    optional — def fetch(hc) -> (sensors, readings); same contract as app/sources.py
  README.md     what it does, where it was learned, what it assumes
```

Two rules of authorship worth stating:

**Your rule must end in something a person does.** "PM2.5 is elevated" is not a pack. "Close the shutters on the
south side, that's where the smoke comes from at this hour" is.

**Declare what you assume.** A pack tuned to a tropical monsoon shouldn't fire in Barcelona. Say so in the README and,
where you can, put it in the SQL — check `indoor`, check `local`, check the sensor exists before you threshold it.

## 4b. Code packs that need a library

Declare it in `pack.yaml`:

```yaml
pip: [earthengine-api]
```

`planetai packs` collects every pack's `pip:` list into `app/requirements-packs.txt` (gitignored) and rebuilds the
image once. Nothing is installed at runtime, nothing is pulled on every start, and a node with no code packs never
runs pip at all. A code pack whose library is missing must log one line and return nothing, not raise: the
`earth-engine` pack is the worked example.

## 4b-ii. Packs that need a setting

Declare it in `pack.yaml`, with the comment that explains it:

```yaml
env:
  - "EE_PROJECT=                          # your Earth Engine project id"
  - "COAST_MAX_KM=30                      # refuse if the nearest ocean cell is further than this"
```

`planetai packs` appends any that `.env` does not already have, under a dated marker, and never overwrites a value
you set. Without this a pack's settings exist only in its README, which is how the earth-engine pack shipped with
three settings nobody could find (5 Sep 2026).

## 4c. Code packs that need a credential

Read it from `.env` (the app container gets the whole file), and put any key *file* in `config/`, which is already
mounted read-only into the container and where the gitignore expects it (`config/ee-key.json`). Never bake a key into
the image or the repo. When the credential is absent, log once and idle: the node must keep running with a pack that
is not yet configured.

Ten pack ideas, three of them shipped as prototypes: [`PACK_IDEAS.md`](PACK_IDEAS.md).

## 5. Where packs live — and why not here

**Packs are not in this repository.** The core repo carries the runtime, the official adapters, and one example pack.
Community packs live in their own repos and are listed in a separate **marketplace repo**, which renders to
`planetai.fab.city/packs`. Adding yours is a pull request there with a manifest entry and a link to your repo.

This is the Omarchy split, and it's the right one. Their core is `omacom/omarchy` with tagged ISO releases; community
plugins live in `omacom/omarchy-plugin-marketplace` and surface at plugins.omarchy.org with verified and unverified
badges; themes are a PR to the site repo with a screenshot. Three tiers, three review bars, one brand. We copy the
shape:

| tier | lives in | who decides | review bar |
|---|---|---|---|
| **Core** | `fabcity/planetai-node` | maintainers | full review; must not add a container or a cloud dependency; a trigger in `SPEC.md §6` for anything deferred |
| **Official pack** | `fabcity/planetai-packs` | maintainers | reviewed like core, but optional at install; where an adapter for a widely-owned sensor lands after it proves out |
| **Community pack** | your repo, listed in `fabcity/planetai-pack-marketplace` | you | listing checks the manifest is valid, the licence is open, and the README says where it was learned. **Not** an audit of your code. |

**Verified** on the listing means a maintainer has read the code and run it on a real node. **Unverified** means
listed but unread. Unverified is a normal state, not a warning — most packs will stay there, and the badge is honest
about what we did rather than pretending to a review we didn't do.

## 6. Releases and versions

**Core** is semver with git tags. `planetai update` moves you to the latest tag; `git checkout v0.1.1` moves you back.
Schema changes are additive only (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`) so a node updates in place without a
migration step. Breaking a contract in `SPEC.md §1` means a major version and a note in `CHANGELOG.md` explaining why.

**Packs** version themselves and declare `requires: { node: ">=0.1.1" }`. A node loads a pack whose requirement it
doesn't meet only after logging a warning — packs are not tested against every core version and we won't pretend
otherwise.

What the core promises pack authors: the four extension points, the `stats` view's columns, the `readings`/`sensors`
schema, the `fci-cells-v0` row shape, and the adapter return contract. Those are the API. Everything else inside
`app/` can change between releases.

## 7. What won't be accepted, at any tier

- A pack that phones home. Adapters read *your* sensors and *public* feeds. Nothing reports usage anywhere.
- A pack that moves raw readings off the node. Hourly means and cells go up; raw stays.
- A rule that treats an indoor sensor as ambient. `NOT s.indoor` is not decoration.
- A pack that needs an API key to a service the operator can't see the terms of.
- Anything requiring a third container. If you genuinely need one, that's a core conversation with a trigger, not a pack.

See [`DOMAINS.md`](DOMAINS.md) for what a node measures today and what a pack could measure next — water, energy,
fabrication, noise, comfort, soil — with the metric names and the decision each would drive.

## 8. The honest state of this

Zero *community* packs exist today. Two ship in-repo: the official `air-quality` pack (which is how node #1 works at all)
and a small worked example. The marketplace repo doesn't exist yet and shouldn't
until there are three real packs to put in it — a marketplace with nothing in it is worse than no marketplace.

What exists now and is worth using: the loader, the four extension points, and the data/code split. If you write a
pack this month, open an issue and it goes in the README until the marketplace earns its own repo.
