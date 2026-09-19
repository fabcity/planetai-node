# Next release — collecting

Changes asked for after v0.60 and not yet built. Tomas is collecting. Each item says what was asked,
what it touches, and what somebody picking it up needs to know that is not obvious from the code.

Add to the bottom. When a release goes out, move what shipped into its tag message and delete it from
here, so this file is only ever what is still owed.

---

## How two large changes are staged

Two things are coming that are larger than an item on this list: **the interface redrawn end to end**,
and **new data sources**. They are staged differently on purpose, because they fail differently. A data
source that is wrong is one pack saying something false and can be switched off with a blank `.env` key;
a page that is wrong is every household reading it, on a wall, with no way back but an update.

Three rules for the queue while both are in flight:

1. **Only one branch at a time may change the suite count in `tests/all`.** That number is written by
   hand, git merges two bumps of it without a conflict and keeps one, and the result is a tree where
   every suite passes and the gate fails. Every new pack adds a suite. Merge them singly, in order.
2. **`app/static/*` and `packs/*` are merged in separate releases, never the same one.** When a node
   comes back wrong, the question "was it the page or the data" has to have one answer.
3. **A release ships one of the two, not both.** The tarball reaches Menorca and Bali before anyone here
   sees a screen; two large changes in one hop cannot be bisected by the person who has to report it.

---

## 1. The interface, redrawn — the September design work landed on the node

**Asked, September 2026, and half-built already.** Direction H — the loop `observe · decide · act ·
measure`, one dial, every section a module — was chosen out of nine drawings and its shell shipped in
v0.54. What has not landed is the drawing itself: the graphic language the prototypes are in.

**Where the work already is.** `planetai-design`, branch `dashboard-directions-2026-09`, is **39 commits
ahead of its own `origin/main` and unpushed**. That is the whole of the redesign — H as a shell,
`h/mods/` registered against `kit-page.js`, the wall as the grid, the ground rule at resolution 9, the
hardware section, and every state re-rendered. It exists on one laptop. **Push it before anything else
on this item**: nothing below matters if that disk fails.

**What holds the two repos together, and what it does not hold.** `tools/check_theme.py` is in
`make lint` and it *fails* rather than reports: `app/static/planetai-theme.css`, `signs.svg` and
`kilometre-cells.json` are byte-identical to `planetai-design`'s copies, so a token cannot drift onto
a wall screen. What it does not hold is what the page *reaches for*.
`docs/design/LANGUAGE_GAP.md` is that reading: **13 of the layer's 34 tokens are referenced, 12 more are
this surface's business and hard-coded instead** — `--rho-closed` reached past to `--rings`, the ground's
opacities baked into `node-ground.svg`, the wall's credit lines using the page-local `--mute`. They
resolve to the same pixel today. That is what makes it quiet: when a token moves, the page will not.

**The staging, in the order it has to happen:**

- **1a · Push `dashboard-directions-2026-09`.** One command, and it is the only irreplaceable step here.
- **1b · Close the 12 hard-coded tokens first, before any redrawing.** Each is a one-line change from a
  literal to `var(--token)`, no visual change today, and `python3 tools/shots.py` proves it: the fixtures
  render identically at four widths or the change was not what it claimed. This is what turns the
  redesign from a rewrite into a re-tokening — after it, moving the language moves the page.
- **1c · Port the modules, one section per PR, against the existing gates.** `tools/check_ui.py` and
  `check_theme.py` stay in `make lint`; `docs/design/UX_REVIEW_2026-09.md` (64 findings) and
  `_skeleton.md` (26 more) are the acceptance list, and the four P0s v0.53 fixed are the regressions to
  watch for — a unit the page shouts into a different unit, a gap in a series drawn as a line through it,
  a locale the page claims the node did not send.
- **1d · Two containers, not one.** The review rig on `pai-clean` runs the old and the new side by side
  on `:8081` and `:8082`. A screenshot of the new page alone proves nothing; the pair is the argument.
- **1e · Node #1 last, and for a day before a tarball.** `planetai-design` is not a node and a fixture is
  not node #1: `docs/design/fixtures/` is what the page does with data somebody chose.

**Cost if wrong:** every household's page at once, including the wall at 1920 where nobody is standing
next to it to notice. This is the one on this list that ships alone.


### The open question inside this item: Grafana, and which surface it is for

**Asked, 18 September 2026.** Look at whether Grafana would show the data better than the drawings
this page makes by hand.

**Worth knowing before anyone starts — the node is closer to this than it looks:**

- `docker-compose.yml` already ships optional services behind profiles: `mqtt`, `agent`, `ipfs`,
  `reticulum`. A `grafana` profile is the established pattern, not a new idea, and it stays off on
  a household node that does not want it.
- `init.sql` already creates `planetai_ro`, a read-only Postgres role with SELECT on every table
  except `settings`. That is exactly the grant a Grafana datasource needs, and it exists.

**The real question, which is not technical.** Every number on this page carries provenance: it is
in `_provenance()`, it has a word — `live`, `partial`, `stale` — and the Figures band is generated
from that list, so a number with no row there cannot be drawn at all. Grafana queries Postgres
directly and would bypass all of it. A panel showing a 24-hour line has no way to say "this sensor
was silent for seven hours and the line is drawn across the hole", which is the exact fault the
September review found and v0.53 fixed.

So the question to answer is not "can we run Grafana" — we can, cheaply — but **which surface it
is for**:

- *For the household, on the dashboard*: it has to inherit the provenance rules, and today it
  cannot. This is the hard version.
- *For the keeper, beside the dashboard*: a separate Grafana at its own port, for somebody
  debugging a sensor or reading a month of data, with no claim to be the household's page. This is
  cheap, honest, and does not touch the dashboard's rules at all.

**Suggested first step:** stand it up behind a profile against `planetai_ro`, point it at node #1's
readings, and look at what it shows that the page cannot — then decide which of the two surfaces it
is. An evening's work to answer properly, and nothing shipped to households until it is answered.

---

## 2. New data sources

**Asked, September 2026.** More of what a node can read. Three are already in flight and they are the
pattern, not the exception: `xiaomi-air` (LAN purifiers, merged), `thingdata` (a repair commons, PR #70),
`earth` (AlphaEarth, nine years a square).

**A source is a pack, and the pack contract is the whole of the discipline.** `pack.yaml` declares
`metrics`, `scales`, `requires: {node: ">=x"}`, its `env:` keys and, for a code pack, its `pip:` line;
`channels.yml` declares each channel's *role* — `ambient`, `enclosure`, `device_health`, `derived`,
`index` — which is what stops a radio's own warm box being pooled into the street's temperature;
`cells.yml` is what it may publish; `rules.yml` is what it may say. Nothing new is needed to add one.

**What a new source has to clear before it is merged, in this order:**

1. **A test file and the suite count.** `tests/test_<pack>.py`, a line in `tests/all`, and the count at
   the bottom of that file moved. One pack per release, per rule 1 above.
2. **Three languages.** Once #67 lands, `tests/test_packs.py` fails any message that does not carry `en`,
   `id` and `es` with the same placeholders. Write all three when the rule is written; retrofitting a
   language across nine packs is what #67 is.
3. **`contributes: report` or an alert, never both and never neither.** `tests/test_packs.py` checks it.
   A number that belongs in the daily report is not an interruption.
4. **Provenance, or it cannot be drawn.** A number with no row in `_provenance()` cannot appear on the
   page at all, and `live` is not the pack's to claim: `s.local OR s.kind = 'child'`, ≥2 sensors across
   ≥2 children for a community node. A pack that wants a cell to say `live` is asking for custody, which
   is a decision, not a field.
5. **A timeout on every HTTP client.** `make lint` fails on `httpx.Client()` with no timeout, because
   httpx has no read timeout by default.
6. **Off by default.** A blank `env:` key idles the pack. A source that costs money, needs a token, or
   leaves the household's network says so in `needs:` and does nothing until somebody sets it.

**What is NOT decided and should be, before the queue gets long:** whether a source that has never run
against its real server ships to households at all. `thingdata`'s threshold is a guess carried over from
`open-data-health`'s guess about CKAN portals; `xiaomi-air` was verified live on node #1 and is the
better precedent. Proposal: a pack reaches a tarball only after one live run somewhere, and `pack.yaml`
carries the date and the node it ran on.

**Cost if wrong:** one pack says something false on one node, and a blank `.env` key switches it off.
That is why these can go out two or three to a release while item 1 cannot.

---
