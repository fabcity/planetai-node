# Handoff: nine directions, and the question

**14 September 2026, extended 15 September (twice).** Phase 1 of the dashboard redesign is done and
this session stops here. Phase 2 builds the one that is picked; it starts from this file, in this
session if Tomas answers, else in a fresh one.

**Nine directions now, in three rounds.**

- **A, B, C** were the first. Tomas leaned to C's logic — the page organised by *where*.
- **D, E, F** answered "put [H3](https://h3geo.org/) in the navigation, not in a picture". All
  three keep C's claim that a household navigates by place and differ in which H3 relation does the
  navigating: the resolution ladder (D), the disk outward (E), or none, with the grid supplying each
  of C's four zones a picture, an address and a scale (F).
- **G, H, I** answer "go more radical, and base *all* the navigation on it". These have no document
  spine at all. G is one cell at a time and the URL is the place. H has one control and it is
  resolution. I is one grid that never moves, with the issue as a layer over it. **In all three the
  four distances leave the navigation** and come back as a word on a reading saying whose it is —
  which is what round two measured them to be.

Branch: `dashboard-redesign-2026-09`, cut from `main` at **v0.53** (`a06655a`). Nothing on the node's
own surface has changed: the commits on it are a measuring script, a Phase 0 reading, the argument
and this. `make lint` and 33/33 after each.

---

## What to open

The drawings are **served, not opened** — from a `file://` page Chromium refuses the sign sprite and
two of the three faces fall back silently, which makes a drawing judged on type and signs unreadable.

```bash
cd ~/Documents/Claude/Projects/FAB\ CITY/planetai-design/prototypes/dashboard-directions
python3 -m http.server 8090
```

| | | the wall |
|---|---|---|
| **A** the index is the page | http://127.0.0.1:8090/a/ | http://127.0.0.1:8090/a/?view=wall |
| **B** the matrix | http://127.0.0.1:8090/b/ | http://127.0.0.1:8090/b/?view=wall |
| **C** the ground | http://127.0.0.1:8090/c/ | http://127.0.0.1:8090/c/?view=wall |
| **D** the ladder — H3 | http://127.0.0.1:8090/d/ | http://127.0.0.1:8090/d/?view=wall |
| **E** the disk — H3 | http://127.0.0.1:8090/e/ | http://127.0.0.1:8090/e/?view=wall |
| **F** the ground, gridded — H3 | http://127.0.0.1:8090/f/ | http://127.0.0.1:8090/f/?view=wall |
| **G** the address — H3 navigates | http://127.0.0.1:8090/g/ | http://127.0.0.1:8090/g/?view=wall |
| **H** the dial — H3 navigates | http://127.0.0.1:8090/h/ | http://127.0.0.1:8090/h/?view=wall |
| **I** the surface — H3 navigates | http://127.0.0.1:8090/i/ | http://127.0.0.1:8090/i/?view=wall |

Narrow the window for 390. **Open I first, then E's wall.** I is the page the third round is really
arguing for; E's wall is still the one thing a stranger walking past would understand with nothing
explained.

**G, H and I move, so press them.** They are the only three where a screenshot is not the drawing:

| | try this | what it is meant to show |
|---|---|---|
| G | press **in** three times, then a neighbour with no number on it | most cells are empty, and the page has to say so |
| G | `?cell=8495a4dffffffff` | standing above every source this node has |
| H | the dial's **4**, then **11** | the map zooms with the dial; at 4 the 3 km this node has mapped is a smudge inside a 237 km cell |
| H | scroll to **What leaves this house by radio** | a peer is a cell and a rough distance, never a pin |
| H | scroll to **What the satellite says** | four real Sentinel passes, and the 1,874 buildings only the satellite knows |
| H | the base strip on the map: **satellite → street map → plan, offline** | live tiles rescale with the dial; the third sends nothing. From resolution 9 inward the plan is the default (Tomas's rule) — the dial opens at 8 on the tiles; turn it in one stop and the ground is the node's own drawing |
| H | **What the stations read** → press **temperature** | fourteen stations regroup by cell as the dial turns; every source is a link |
| H | `?view=wall` and wait eight seconds | the dial turns by itself; the map and every number re-derive per stop |
| H | the **Notes** at the foot | every explanation on the page, folded per section |
| H | `?view=setup` | the sections this node runs, by pack, from the real registry — on · move · **propose back** — drawn, not built |
| H | **The hardware in this house** | the four devices on this ground, and the open-hardware-manager row honestly "not connected" |
| I | the layer switch: **Air → Land → Coast** | four issues, four completely different geometries |
| I | press any cell with a heavy outline | one station's own reading, which `/issues` does not publish today |

Add `?state=empty` for a fresh node and `?state=refused` for a phone with no token. The
wireframes are `?view=network`, `?view=setup`, `?view=arrange`.

Every render is also a JPEG, at one device pixel, in
`planetai-design/prototypes/dashboard-directions/shots/<a…i>/` — `_fold.jpg` is the first screen
and `_full.jpg` the whole page. The shipped page, measured the same way on the same afternoon, is the
baseline in [`docs/design/REDESIGN_2026-09_ground.md`](design/REDESIGN_2026-09_ground.md).

The argument, reader by reader, and every number:
[`docs/design/DIRECTIONS_2026-09.md`](design/DIRECTIONS_2026-09.md).

---

## The third round, short

| | target | C | E disk | G address | H dial | I surface |
|---|---|---|---|---|---|---|
| first screen says everything @ 390 | five of five | ✓ | ✓ | ✓ *in this node's cell* | ✓ | ✓ |
| empty share @ 1440 | ≤ 30 % | 70.5 | 63.7 | 63.7 | 59.6 | **42.2** |
| empty share @ 390 / 768 | ≤ 20 % | 43.2 / 55.3 | 34.9 / 31.9 | 33.9 / 33.9 | 33.7 / 36.3 | **33.2** / 34.5 |
| page @ 1440 / 390, screens | ≤ 4 / ≤ 8 | 3.1 / 5.5 | 3.4 / 4.9 | 4.1 / 5.5 | 5.5 / **8.4** | **2.4 / 3.1** |
| orphan numerals · components | 0 · 0 | 0 · 2 | 0 · 4 | 0 · **0** | 0 · **0** | 0 · **0** |

H's column is the revised page — the map, the radio and the satellite. It has since been rebuilt
again as a **modular shell**: ten sections from six packs, registered against a contract
(`kit-page.js`), ordered by the loop *observe · decide · act · measure*, with a live tile map,
the station list with a variable selector and source links, every explanation folded at the foot,
and a wall whose dial turns by itself. Measured: empty share fell to **48.9 %** at 1440 (from 59.6)
and the page grew to **8.1 screens** at 1440 and **12.6** at 390. The argument for that version is
in the directions document under *H, revised again*; the lever for its length is the contract's own
— a section is a file, and a file can move to the Network view.
| wall on a 1,080 px screen | 1,080 | **1,080** | 1,133 | **1,080** | **1,080** | **1,080** |

**I is the first page in three rounds to move T2 at 1440** — 42.2 % against C's 70.5 — and it does it
with a drawing that is the instrument rather than a decoration behind the text. It is also the
shortest page measured, at 2.4 screens. It still misses the 30 % target, and after nine compositions
that is now a statement about the target.

Five things the third round measured that the first two could not, because nothing in them varied
the grain or put the issues on one ground:

- **Between resolution 7 and resolution 10 nothing changes.** Four stops of the dial, 343 times
  smaller by area, and the same nine cells hold the same fourteen stations. Past res 7, grain is
  precision with no information in it.
- **The satellite square is 374,551 cells at its own 10 m grain and 4,063 after `compactCells`** —
  the same ground exactly, 92 times smaller. The only place in three rounds where H3 does something
  the node could not already do by hand.
- **Six of the seven footprints were already declared** in packs and presets. The one that is not
  belongs to the model point, which covers 4,396 cells where a probe in this room covers 1.
- **Four issues, four geometries** on one 217-cell grid: air 7, heat 7 — and heat's own declared
  footprint is smaller than one cell of it, so 0 — land 15 with no station in any of them, coast all
  217, water none. The shipped page draws all four as bands of equal height.
- **Navigating away from your own cell costs the numeral.** G in an empty cell fails T1's second leg,
  measured. That is the idea's cost, not the drawing's.

## The second round, short

| | target | C | D ladder | E disk | F gridded |
|---|---|---|---|---|---|
| first screen says everything @ 390 | five of five | ✓ | ✓ | ✓ | ✓ |
| empty share @ 390 / 768 | ≤ 20 % | 43.2 / 55.3 | 42.8 / 60.2 | **34.9 / 31.9** | 43.7 / 55.8 |
| page @ 1440 / 390, screens | ≤ 4 / ≤ 8 | **3.1** / 5.5 | 4.3 / 5.7 | 3.4 / **4.9** | 5.4 / **8.6** |
| orphan numerals · components | 0 · 0 | 0 · 2 | 0 · **2** | 0 · 4 | 0 · 5 |
| wall on a 1,080 px screen | 1,080 | **1,080** | **1,080** | 1,133 | 1,130 |

**E is the only page in either round to pass T2's 30 % at any width** (31.9 % at 768), and the thing
filling its fold is a drawing that carries readings rather than a decorative map. C and D are the
only two whose wall fits; E's and F's are 53 and 50 px too tall and lose `stale`, which is a line to
trim rather than a composition to rebuild.

Five things the grid measured that nothing else had, all printed on the three pages rather than
reconciled away: **the ring's cell is bigger than the region's** (res 4, 26 km against res 5,
9.9 km — two of the four distances are the wrong way round as scales); at the grain the street is
drawn at, **this house's own cell also holds two of somebody else's sensors**; the grid **cannot tell
the room from the wall outside at all**, because this node's three sensors carry one coordinate; the
ring reaches **14.7 km** where `presets/bali.env` declares 8; and two of seven child cells reach
**6 m** outside their own parent while indexing to it exactly.

## The first round, short

| | target | shipped | A | B | C |
|---|---|---|---|---|---|
| the first screen says everything, at 390 | five of five | four | **five** | **five** | **five** |
| issues named with a number, first screen at 1440 / 390 | all five | none marked | 2 / 1 | **4** / 2 | 3 / **3** |
| empty share at 1440 · as written / discounting decoration | ≤ 30 % | 35.3 / 64.4 | 69.3 | 71.8 | 70.5 / 70.8 |
| empty share at 390 | ≤ 20 % | 21.4 / 46.8 | 46.5 | 52.5 | **43.2** |
| page height at 1440, in screens | ≤ 4 | 5.7 | 5.2 | 4.2 | **3.1** |
| page height at 390 | ≤ 8 | 8.9 | 8.4 | **6.9** | **5.5** |
| card kinds | 4 | 0 declared, 24 grammars | **4** | 3 | 2 |
| numerals with nothing to compare them to | 0 | 26 drawn, none marked | **0 of 70** | **0 of 47** | **0 of 26** |
| components with no link in or out | 0 | **47 of 47** | 2 | **1** | 2 |
| the wall at 1920, on a 1,080 px screen | 1,080 | 1,080 (**1,052 on 900 at 1440**) | **1,142** | **1,550** | **1,080** |
| every issue line on the wall ≥ 9 mm | yes | **7.5 mm** | **10.1** | 8.4 | 8.4 |

---

## The three real choices

**1 · Is the page read by issue, by place, or by grid?** A and B organise by issue; C, D, E and F by
place; G, H and I by the grid itself, with the four distances demoted to a word on a reading. It
decides what a household is taught to ask — *which issue is loud*, *which part of my place is the
problem*, or *what is known about this ground, and how finely*. C's cost is the mirror of its claim:
air appears in three zones, so reading one issue end to end means walking the page. The third
round's cost is bigger and is stated with each of the three.

**2 · T2's 30 % and 20 % do not survive contact with any composition.** The best first screen
measured is 43.2 % empty against a target of 20 %. The shipped page reads 21.4 % only because a
decorative full-bleed drawing counts as a mark; discount it and it is 46.8 %, the same neighbourhood
as all three. So: restate the targets against the measure that discounts decoration and set them
near 45 % at 390 and 65 % at 1440 — which every direction already beats — or make the page
materially denser than any of these, or put a picture back behind the first screen, which is what
the page does today and what the complaint calls too much empty space. **This one needs answering
before Phase 2 starts**, because it is the difference between building a page and building a table.

**3 · The wall was C's, and now five pages fit it.** C, D, G, H and I are all 1,080 px on a 1,080 px
screen; E and F overrun by 53 and 50; A by 62 and B by 470. The paragraph below is the first round's
and still describes what a wall that does not fit actually loses.

**3a · The wall is C's, of the first three.** Measured at 1920 dark, on a 1,080 px screen: C is 1,080 px with nothing
below the fold; A is 1,142 and loses the node name, **`stale`** and "Answer on Telegram"; B is 1,550
and loses a whole issue row as well. A wall does not scroll, so a household reads a number and is
never shown the word saying it is old — the September skeleton review's **S-01**, which v0.53 closed
at 1920 and left open at 1440. If A or B is the pick, its wall is a separate composition and not the
same page at a larger size; that is work Phase 2 has to plan for. All three do put a provenance word
on every wall number, which closes **L2** whichever way it goes.

Two smaller ones, recorded so they are not decided by accident: **the stack may not be a card** (B
and C dissolve it, which takes T3's four kinds down to three or two), and **the plan only explains
something in C**, where it is the ring's own drawing rather than a card in a band.

---

## The question, in one paragraph

Nine drawings of the same evening now, on the same frozen layer, from the same file. The first fork
is no longer which one: it is **whether the four distances stay in the navigation**. A to F keep them
— C organises the page by place and is the shortest of the first three; D makes the resolution ladder
the spine and is the only composition anywhere that puts the privacy argument where a household can
see it; E makes the neighbourhood the spine and answers *is it me or is it everywhere* as something
countable; F changes C as little as possible. G, H and I drop them: G is one cell at a time and makes
a place sendable as a URL, H turns one dial and makes resolution into provenance, and I is one
surface with the issue as a layer, which is the shortest, densest and best-measured page of the nine
on every target except card kinds. **Which one should be built** — and three things that decide with
it: **do the four distances navigate, or only label custody**; **does `/issues` publish a value per
station**, which G and I need and which the fenced median exists to prevent; and **do the emptiness
targets move to the measure that discounts decoration**, after nine compositions have missed them.
Name anything from the other eight you want carried over; Phase 2 builds one page, not a merge.

## If the answer is A

Then: the stack stays a card; the index is deleted as an object; the hero is the first row with a
`lead` class and not a component of its own; the loop band keeps the funnel; and two problems come
first — only two issues are named on the first screen at 1440 and one at 390, because the lead takes
the whole fold, and the wall is 62 px too tall.

## If the answer is B

Then: `ANATOMY` gains a `matrix` band and loses `stack`; the wall needs its own composition, because
the matrix overruns it by 470 px; the per-row sentence at 14 px is the first thing to check at 390;
and `check_ui`'s card-kind count becomes three.

## If the answer is C

Then: `layout()` orders by distance and not by issue, which is the one change that touches the
renderer's own shape rather than its lists; the plan gets drawn from `/place/geojson` with the res-9
mesh and the res-8 outline rather than being an artboard; every reading keeps its link to the same
issue at the next distance, which is C's answer to the scatter; and `check_ui`'s card-kind count
becomes two unless the row and the stack come back somewhere.

## If the answer is D, E or F

All three need one thing from the node and it is small: **`/issues` carries the cell id and the
resolution per distance**, so the page can show the scale without inventing it. That is a field on a
stack cell, not an endpoint, and `app/ground.py` already calls `latlng_to_cell`, `grid_disk` and
`cell_to_children`, so nothing has to be built — only published. `make-h3.mjs` is the working
reference for what to publish.

**D** also wants `PRESENCE_RES_FLOOR` and `RETICULUM_PRESENCE_RES` on the same read, because the line
across the ladder is drawn from them. **E** wants per-station coordinates, which `/sensors` already
answers, and it wants somebody to decide whether a cell may show a value — today it can only show
that a station is there, because the node publishes the ring as one fenced median and a number per
cell would be the page computing. **F** wants nothing beyond the cell ids.

And all three inherit the same three sentences, which are not optional: the grid cannot tell indoors
from outdoors, it cannot tell mine from the street's at the grain the street is drawn at, and its
containment is exact in the index and approximate on the ground.

## If the answer is H, the modular one

Then Phase 2 is the contract, not a page: `kit-page.js` becomes the node's renderer, a pack's
`dashboard` contribution in its pack.yaml is one static file that calls `register`, and the shell
is the only thing the node ships as its own. The ten sections in the prototype are the first ten
contributions — the renderer's own four (claims, grain, asks, measure) and six from packs (place,
air-quality, earth, reticulum, meshtastic, hardware). Two decisions ride with it: **live tiles or not** —
the page sends a tile server the square being looked at; under the rule now in place the plan is
the default from resolution 9 inward and the tiles show at 8 and coarser, so the dial as it opens
sends twelve tile requests and one stop in sends nothing — and **which sections stay in Now**, because nine of them are twelve
screens on a phone and the Network view already has a home for the radio.

## If the answer is G, H or I

These need two things from the node. The first is small and the second is not:

1. **A plate per cell, on `/issues`** — the cell, the cells around it, each one's parent, area and
   what is read in it. `app/ground.py` already calls `latlng_to_cell`, `grid_disk` and
   `cell_to_children`; nothing has to be built, only published, and it measures **3.0 kB** for the
   plate a reader is standing on. `make-h3.mjs` is the working reference for the shape. H also wants
   each source's declared footprint as a compacted cell set — the numbers it is computed from are
   already in the packs.
2. **A value per station.** G and I show one station's own 15-minute mean. `/issues` publishes the
   street as a single **fenced median** and never a value per station, and the fence is deliberate.
   **This is a STOP.** Nothing gets built on G or I without an answer, and "no" is a real answer:
   both still work showing that a station is there and how far away it is, which is what E does — it
   costs G its numeral on most screens and costs I the reason to press a cell.

**H needs neither.** Everything on its page is a count, an area or a footprint, and all of them come
from what the node already declares. If the per-station question is a "no", H is the only one of the
three that survives it intact.

And all three inherit the same sentences, which are not optional: the grid cannot tell indoors from
outdoors; it cannot tell mine from the street's at the grain the street is drawn at; its containment
is exact in the index and approximate on the ground; and **the plate ends** — two steps out is what
this node published, and a page that drew a door past it would be drawing the planet.

---

## What Phase 2 inherits whichever it is

The four shared findings in `DIRECTIONS_2026-09.md` — the as-of under the ask, "nothing has been
asked" as a sentence of its own, a pack's own unit and comparison travelling with its contribution,
and the line's source named once — are not part of the choice. Nor are the four card kinds, the
`data-num`/`data-cmp` pair, the `data-ref` link, or the refused page saying three things.

`tests/visual/measure.mjs` is the one measuring script and it already computes T1–T7 and T9. Phase
2's gates read the same numbers.

**Three things to fix in Phase 2 that the drawings get wrong.** The ρ caption is 8.8 mm on
every wall, just under the floor. `data-num` on a readout was a label before it
was a key, and a gate that walks `[data-num]` has to be able to tell which issue a numeral belongs
to. And the wireframe views carry one component and one link, so they pass T5 by being almost empty
— a real Network view will not.

---

## Not done, and not claimed

The first set of renders fell back to system-ui for Funnel Sans and Figtree, because the node serves
its faces by flat name from an allowlist and the rig served the directory they live in. Every number
here is from a re-render with all three faces loading; the shipped baseline was unaffected and
re-measuring it returned the same numbers to the decimal.

No live data: node #1 and node #2 were not contacted, and nothing on pai-clean was written — no
setting, no restart. `en` only. No real wall in a real room. The committed fixture carries no open
ask, so no drawing shows the green button in use. The funnel's 2×2 axes are inferred, because
`PLANETAI_Response_Funnel_Briefing_2026-09-10.md` and
`PLANETAI_Models_by_Node_Class_2026-09-14.md` are in the PLANETAI project and on neither disk nor any
branch here.
