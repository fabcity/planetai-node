# Three directions for the node dashboard

**14 September 2026.** Phase 1 of the redesign. Three drawings of the same data, differing in their
organising idea and not in their skin, so that one of them can be picked and built. They are HTML
because HTML is how a drawing of this page can be measured; they fetch nothing, arrange nothing, and
no button on them does anything.

| | |
|---|---|
| Where they are | `planetai-design/prototypes/dashboard-directions/{a,b,c}/index.html` |
| What they read | `snapshot.js` — node #1 at 2026-09-06 14:08 UTC replayed through the **real engine** (`GET /issues/fixtures/node1-2026-09-06`), extended by hand with the three synthetic contributions of 1.4. All three read the same file. |
| What they draw with | the frozen layer from the node's own `app/static` — `tokens.css`, `planetai-theme.css`, `signs.svg` — served at the node's own origin, byte for byte the files `tools/check_theme.py` holds to this repo's sibling |
| What else they are allowed | two artefacts the design repo already holds of node #1's own place on the same day: the R3 kilometre drawing (`assets/h3/kilometre.svg`) and the four brightness-matched Sentinel frames. Both are labelled on the page with the word `cached` or `partial`. Nothing else. |
| Where the numbers come from | `tests/visual/measure.mjs`, the one measuring script, run against every render. `planetai-design/prototypes/dashboard-directions/shots/<a\|b\|c>/` holds the renders and the JSON each number came out of. |
| Where they ran | pai-clean, the September review's `:8081` container answering the API. Node #1 and node #2 were not contacted. |

**Everything below was seen in a render.** Where a direction does not show something, this document
says so rather than describing what it would look like.

**One correction, made before this was written.** The first set of renders fell back to system-ui for
both Funnel Sans and Figtree: the node serves its three faces by flat name from an allowlist, and the
rig was serving the directory they live in, so `/static/FunnelSans-VariableFont_wght.ttf` 404'd and
the page said nothing. Measured: `document.fonts.check` false for both, and every cap height in the
first pass belonged to a face the layer does not name. Every number below is from a re-render with
all three faces loading and nothing 404ing. The shipped baseline was unaffected — its faces came from
the container — and re-measuring it returned the same numbers to the decimal.

---

## What the three share, and why

All three build from one file, `kit.js`, which holds the four card kinds and nothing about where
they go. That is deliberate: if the directions differed in their cards as well as in their
composition, nothing could be learned by comparing them. So the four kinds — **readout**, **stack**,
**series**, **row** — are the same code in all three, and what differs is which of them each
direction uses and how it arranges them.

Four things fell out of drawing all three, and they are the same in all three. They are not part of
the choice; they are what the choice sits on.

**1 · The as-of belongs under the ask, not in the header.** T6 asks for reading order to be
headline condition → ask → as-of → the rest. With the time in the header it arrives first, before
the thing it is the age of. Moving it under the ask also puts it where a phone can reach it, which
is Part 1's **H7** closed as a side effect rather than as a fix.

**2 · "Nothing to do" and "nothing has been asked" are two different sentences.** The shipped page
renders a hidden div when there is no open ask, so a household infers the absence. Saying "Nothing to
do" for every absence is worse: the kicker's own reason for `notable` is *"over the line, and nobody
has been asked to do anything"*, and a strip under it reading "Nothing to do" contradicts the line
above it. An issue over its line with no rule asking for anything is **unattended**, not quiet, and
the page says which. This showed up the first time direction A rendered.

**3 · A column a pack filled carries the pack's own unit and its own declared comparison.** Water's
room is turbidity in NTU and its region is metres below a water table. Reading the issue's unit and
line for both painted `4.2 m` red for crossing a 1.0 NTU line — two quantities on one scale, which is
the thing a stack exists not to do. The comparison has to arrive with the contribution.

**4 · The line's source is named once.** Repeating *"WHO 2021 global air quality guidelines, 24-hour
mean"* under all four columns of a stack put twenty-eight words of citation under four numbers. The
comparison is the number; whose number it is, is the why line above.

---

## A · The index is the page

**The idea.** One column, one grammar: the row. Every issue is a row, and a row opens in place into
the stack, the day and the sources behind it. The hero is not a different object — it is the row that
won, grown large.

**The five readers.**

| reader | what they meet first |
|---|---|
| the household member, phone, five seconds | the kicker, the sentence with its numeral, the line, then "Nothing has been asked", then the time. All five are on the first screen at 390 — measured. |
| the keeper at 1440 | the same, and then a column they can scroll rather than a layout they have to parse. Two issues are named with a number on the first screen; the other three are one scroll down. |
| the wall at three metres | the same rows, larger. Four issue lines at 10.1 mm cap height, the only direction over the 9 mm floor. But the wall is **1,142 px on a 1,080 px screen**, so the node name, **`stale`** and "Answer on Telegram, not here" are below a fold that does not scroll — the shipped page's own S-01, reproduced. |
| the tester on an empty node | the rows survive: every issue is still a row, and each says what it has no source for. The page is 2.0 screens instead of 8.4. |
| the stranger at `SHARE_LEVEL=off` | the shell, the household sentence, the node's own sentence, and what to do. One screen. |

**The four open decisions.** *(8) one band per issue* — kept, but a band is a row that has opened,
so there is no second object. *(9) R5's hero plus mini stack* — the hero is the first row grown, and
it carries the **full** stack rather than a mini one; there is no mini variant in A. *(10) the index
under the hero* — dissolved: the index **is** the page, so there is nothing under the hero but the
next row. *(11) quiet issues collapse* — a quiet issue is not collapsed, it is short: it keeps its
row and its one sentence and opens into less.

**Where the new things land.** The funnel and ρ are in the loop band, under the rows
(`shots/a/now_populated_1440_full.jpg`, foot). The peer is a row beside them. The water pack is a
row like any other, and its `band.gauge` contribution is an `unplaced` readout with the pack's name
on it in the same band. A hazard row or a child would be another row. The stranger's water pack
needed no new shape at all — that is A's strongest claim.

**What it costs.** The column is long: **8.4 screens at 390**, the worst of the three; only two
issues are named with a number on the first screen at 1440 and **one** at 390, because the lead takes
the whole fold; and the wall overflows by 62 px, which is a composition to shorten rather than a size
to tune. A is the direction that answers "what is happening" fastest and "is it me or is it
everywhere" slowest — the comparison is inside a row you have to open.

---

## B · The matrix

**The idea.** Issues down, distances across. The stack is not a component inside a band; it is the
page's grid. Every number on the first screen already sits beside the number it is compared with,
because the column it is in *is* the comparison. The hero is the row that won, printed above its own
matrix and marked `leads` inside it.

**The five readers.**

| reader | what they meet first |
|---|---|
| the household member, phone, five seconds | the sentence and the ask, then the matrix transposed — one block per issue with its four distances as a 2×2. Two issues are named with a number on the first screen. |
| the keeper at 1440 | **four of the five issues, at all four distances, on the first screen.** The best answer of the three to "show me everything at once". |
| the wall at three metres | the matrix, dark. It does **not fit, by 470 px**: 1,550 px on a 1,080 px screen, so the last issue row, the ρ row and the footer carrying `stale` are all below a fold that does not scroll. A composition that wants one more row than a wall has. |
| the tester on an empty node | a matrix of dashes, each saying why. Honest, and bleak: 74.5 % of the first screen is empty at 1440. |
| the stranger at `SHARE_LEVEL=off` | as A. |

**The four open decisions.** *(8)* dissolved — there are no bands; a row is the issue. *(9)* the hero
keeps R5's anatomy and there is no mini stack, because the matrix is the stack. *(10)* the index is
the matrix's first column. *(11)* a quiet issue keeps its row at every width; collapsing it would
punch a hole in a table.

**Where the new things land.** The water row is a row of the matrix with its own units per cell — the
clearest demonstration in the three that a pack can fill one cell and not another. The funnel and the
peer are below the matrix. A hazard pack would be a row whose room, yard and ring cells are all
"nothing at this distance", which reads correctly as *this is a region-only issue* without anything
being said.

**What it costs.** The wall does not fit, and that is not a tuning problem — it is one row too many
for a surface that cannot scroll. And a matrix is a table: it answers comparison brilliantly and says
nothing about *why* until you read the row's own sentence, which is set below the row at 14 px and is
the first thing to go at any smaller size.

---

## C · The ground

**The idea.** The page is organised by **where**. Room, yard, ring and region are the four sections,
and every issue hangs off the distance its evidence actually lives at. A household does not have an
air problem and a heat problem; it has a room, a wall outside, a street and a model.

**The five readers.**

| reader | what they meet first |
|---|---|
| the household member, phone, five seconds | the sentence, the ask, the time, then **The room** with air, heat and water in it. Three issues named with a number on the first screen at 390 — the most of the three on a phone. |
| the keeper at 1440 | the same, and the plan of the kilometre beside the ring, the satellite beside the region. The shortest page of the three: **3.1 screens** at 1440 and 5.5 at 390. |
| the wall at three metres | **the only wall of the three that fits — 1,080 px on a 1,080 px screen, nothing below the fold.** Four columns, every issue at every distance, `stale` on it, the ρ row and its caption on it. |
| the tester on an empty node | four zones, each saying what it has no instrument for — *No kit is on the wall outside.* It is the only direction whose empty state reads as a **map of what to buy next**. |
| the stranger at `SHARE_LEVEL=off` | as A. |

**The four open decisions.** *(8)* replaced: one band per **distance**, issues inside. *(9)* the hero
keeps the sentence and the ask and drops the stack entirely — the page below it is the stack. *(10)*
there is no index; the four zones are the index. *(11)* nothing collapses, because an issue with
nothing at a distance is simply not on that list.

**Where the new things land.** The plan is the ring's own drawing and the satellite is the region's —
which is the first composition in this project where the plan is not an ornament. The peer sits under
**Beyond the ring**, which is exactly where a node 61 km away belongs and is the only direction that
gives it a true home. The funnel and ρ sit there too. The water pack's room value appears in **The
room** beside air and heat, and its region value in **This square of the map** — one pack, two zones,
no band of its own.

**What it costs.** Two things. An issue is **scattered**: air appears in three zones, and reading one
issue end to end means walking the page, which is the exact complaint (2) the redesign is answering,
moved rather than removed. C answers it with a link — every reading points at the same issue at the
next distance — but a link is not a glance. And C carries the fewest card kinds: **two** of the four
appear at all, because it has no stack and no row. That is a smaller vocabulary than T3 asks for, and
either T3's four are wrong or C is short of two.

---

## The measurements

Every row from `tests/visual/measure.mjs`, on the same fixture, on the same afternoon. **T2 is
reported twice**: as the target is written, where any image counts as a mark, and again discounting
what the page itself marked `aria-hidden`. The shipped page is the only one of the four where the two
readings differ, and the thing between them is its hero's ground drawing.

### Now, populated

| | target | shipped | A | B | C |
|---|---|---|---|---|---|
| **T1** @ 390 · sentence · numeral · state · ask · as-of | all five | ✓ ✓ ✓ **✗** ✓ | ✓✓✓✓✓ | ✓✓✓✓✓ | ✓✓✓✓✓ |
| **T1** @ 1440 · the same + index + mini stack | all seven | ✓✓✓**✗**✓ · idx 4 ✓ | ✓✓✓✓✓ · idx 1 **✗** | ✓✓✓✓✓ · idx 0 **✗** | ✓✓✓✓✓ · idx 0 **✗** |
| **T1b** issues named with a number on the first screen @ 1440 | all five | — (marks none) | air water | **air coast heat water** | air heat water |
| **T1b** the same @ 390 | | — | water | air water | **air heat water** |
| **T2** empty @ 1440, as written / discounted | ≤ 30 % | 35.3 / 64.4 % | 69.3 / 69.3 % | 71.8 / 71.8 % | 70.5 / 70.8 % |
| **T2** empty @ 390, as written / discounted | ≤ 20 % | 21.4 / 46.8 % | 46.5 % | 52.5 % | **43.2 %** |
| **T2** page height @ 1440, in viewports | ≤ 4 | 5.7 | 5.2 | 4.2 | **3.1** |
| **T2** page height @ 390 | ≤ 8 | 8.9 | 8.4 | **6.9** | **5.5** |
| **T3** card kinds declared | 4 | 0 (24 grammars, undeclared) | **4** | 3 | 2 |
| **T4** numerals with no comparison | 0 | 0 of 0 declared (26 drawn) | **0 of 70** | **0 of 47** | **0 of 26** |
| **T5** components with no link in or out | 0 | 47 of 47 | 2 of 52 | **1 of 31** | 2 of 25 |
| **T6** reading-order swaps in the first viewport @ 1440 / 390 | 0 | 3 / 3 | 10 / 5 | 7 / 7 | 8 / **2** |

### The wall, 1920 dark

| | target | shipped | A | B | C |
|---|---|---|---|---|---|
| document height on a 1,080 px screen | 1,080 | 1,080 (**1,052 on the 900 px screen at 1440**) | **1,142 — over by 62** | **1,550 — over by 470** | **1,080 — exactly** |
| what falls below the fold | nothing | nothing at 1920; at 1440 the ρ caption, the node name, `As of`, **`stale`** and "Answer on Telegram" | the node name, **`stale`**, "Answer on Telegram" | the last issue row, the ρ row, the whole footer | **nothing** |
| the sentence, cap height | ≥ 9 mm | 34.0 | 29.9 | 27.2 | 27.9 |
| the numeral | ≥ 9 mm | 80.9 | 73.6 | 66.2 | 69.2 |
| every issue line | ≥ 9 mm | **7.5** | **10.1** | **8.4** | **8.4** |
| the ρ row's caption | ≥ 9 mm | **5.7** | **8.8** | **8.8** | **8.8** |
| issues named with a number | all | — | all four | all four | all four |

### Empty and refused

| | shipped | A | B | C |
|---|---|---|---|---|
| empty @ 390, page height in viewports | — | 2.0 | 3.8 | **1.7** |
| empty @ 1440, empty share | — | 68.3 % | 74.9 % | 77.2 % |
| issues named with a number on an empty node @ 1440 | — | air | air coast heat land | none |
| refused @ 390 | the shell + two sentences | the shell + three: what, why, and what to do | same | same |

---

## What the three agree on, and what the pick actually decides

### Fixed regardless of the pick

1. **The four card kinds are enough**, and three of them do all the work: readout, series and row
   appear in every direction. Only A uses `stack` as a card, because only A has a place that is not
   already a stack.
2. **Every numeral carries its comparison, and an absent one carries the pack's own reason.** All
   three score 0 orphan numerals across 26 to 70 declared. It costs nothing and it is the whole of
   complaint (2).
3. **Every component links in or out.** All three are at 1 or 2 orphans out of 25 to 52, against the
   shipped page's 47 of 47 — and in every case the two are the header and the lead, which the target
   exempts by name.
4. **The as-of goes under the ask**, the four shared findings above, and "nothing has been asked" as
   a sentence distinct from "nothing to do".
5. **A refused page says three things, not two**: what is happening, why, and what the reader can do
   about it — which closes Part 1's **R3**, routed to Tomas and never answered.
6. **The wall carries the provenance word.** All three put a pill beside every wall number, which is
   **L2**, the one P0 still open from the September walk.

### The three things the pick decides

**1 · Whether the page is read by issue or by place.** A and B are organised by issue; C is
organised by distance. This is not a layout preference — it decides what a household is being taught
to ask. A and B teach *which issue is loud*; C teaches *which part of my place is the problem*. C's
own cost is the mirror of its claim: one issue is scattered across three zones.

**2 · Whether T2's 30 % and 20 % survive, or the measure does.** **No direction comes close**: the
best first screen measured is 43.2 % empty, against a target of 20 %. The shipped page appears to
pass at 21.4 % only because a decorative full-bleed drawing counts as a mark — discount it and it is
46.8 %, which is the same neighbourhood as all three drawings. So one of three things is true, and
only Tomas can say which: the targets should be restated against the measure that discounts
decoration (and set near 45 % at 390, 65 % at 1440, which every direction already beats); or the page
should be materially denser than any of these three; or the hero's ground drawing comes back, and the
first screen is filled by a picture rather than by readings. The third is what the shipped page does
today, and it is what the complaint calls too much empty space.

**3 · The wall is C's, and the other two have to give something up to get it.** Measured at 1920
dark: C is 1,080 px on a 1,080 px screen with nothing below the fold; A is over by 62 px and loses
the node name, `stale` and "Answer on Telegram"; B is over by 470 px and loses a whole issue row as
well. A wall does not scroll, so a household reads a number and is never shown the word saying it is
old — which is exactly the P0 the September skeleton review filed as **S-01** and which v0.53 closed
at 1920 and left open at 1440. If A or B is the pick, its wall is a separate composition rather than
the same page at a larger size, and that is work Phase 2 has to plan for.

All three do put a provenance word on every wall number, which closes **L2**, the one P0 still open
from the September walk — so the wall's other failing is answered by the pick whichever way it goes.

### Two smaller things that are decisions, not findings

- **The stack as a card may not survive.** B and C both dissolve it, and a "stack" card exists in
  only one of the three. If B or C is picked, T3's four kinds become three or two, and `check_ui`'s
  count changes with it.
- **The plan's place.** C is the only direction where the plan of the kilometre explains something —
  it is the ring's own drawing. In A and B it is a card in a band, which is what it is today.

---

## What is not drawn, and was not claimed

- **Live data.** Every number is the 6 September fixture or a synthetic extension. Node #1 and node
  #2 were not contacted.
- **Bahasa and Spanish.** The drawings render `en` only. The water pack's three locales are in
  `snapshot.js` and have been read by nobody who speaks two of them.
- **A real wall in a real room.** The millimetre figures convert angular size on a 55-inch 1920
  panel. O2 and O10 in the layer record the same gap.
- **Network, Set up and Arrange** are wireframes — grey bars and outlined controls — at 390 and 1440
  in every direction. They show where those views live and how they read, and nothing else. The Set
  up wireframe carries the Issues pane, which does not exist on any surface today.
- **The ask strip with a real ask.** The committed fixture has no open ask on any issue, so all three
  drawings show the "nothing has been asked" state and none shows the green button in use.
- **The plan is the R3 artboard**, not a drawing the page made from `/place/geojson`. Phase 2 draws
  it, with the res-9 mesh and the res-8 outline, from the fifteen lines
  `NODE_DASHBOARD_PLAN_SPEC.md` names.
- **The funnel's 2×2 axes are inferred.** `PLANETAI_Response_Funnel_Briefing_2026-09-10.md` was not
  reachable from this machine. The axes drawn — was it answered, did the reading come back — are the
  pair a node can compute from `alerts` and `actions`. If the briefing names a different pair, this
  is the thing to re-read against it.

---
---

# Part two · three iterations on C, navigated by H3

**15 September 2026.** Tomas read A, B and C and leaned to C's logic — the page organised by *where*
— and asked for three more with the H3 grid built into the navigation rather than used as a
picture. These are those three. They are D, E and F; A, B and C stand unchanged above.

All three keep C's claim that a household navigates by place. What differs is **which H3 relation
does the navigating**:

| | the relation | H3's own word for it |
|---|---|---|
| **D · the ladder** | up and down: the page is the resolution ladder, and the four distances are rungs on it | `cellToParent` / `cellToChildren` |
| **E · the disk** | outward: the page is the cells around this one, and every sensor is drawn in the cell it is actually in | `gridDisk(cell, k)` |
| **F · the ground, gridded** | none — C's four zones are kept exactly, and the grid supplies each zone's picture, address and scale | `latLngToCell` per zone |

## Where the geometry comes from

`make-h3.mjs` computes everything with **h3-js 4.2.1** from the committed fixture's own `/health`
coordinates, and writes `h3.js` — 61 kB of cell ids, edges, areas and projected path strings.
Nothing in any browser knows what a hexagon is, which is the division the node's own dashboard
already keeps with `kilometre-cells.json` and the rule R0 settled: *geometry is computed, signs are
lifted or built on a grid.*

Two checks, because a drawing of a grid is worthless if the grid is wrong:

| | | |
|---|---|---|
| against the design repo's own committed geometry | res 7 `8795a4c86ffffff` · res 8 `8895a4c86bfffff` · res 9 `8995a4c86a7ffff` | **all three match `assets/h3/kilometre-cells.json`** |
| against [h3geo.org's resolution table](https://h3geo.org/docs/core-library/restable/) | res 2 edge 182.5130 km against 182.5129565 · 5,882 cells against 5,882 · res 8 area 0.737328 km² against 0.737327598 | **match** |

**The node can already do all of this.** `app/ground.py` calls `latlng_to_cell`, `grid_disk` and
`cell_to_children` today. Nothing in these three is a capability the node would have to gain — only
a shape it would have to publish.

**One method note, because it cost a render.** The first grid drew as a solid disc: `d3.geoPath`
applies spherical polygon semantics, and a ring wound the other way is read as *the whole planet
minus the cell*, so thirty-seven cells were each filled as everything-but-themselves. The fix is the
rule `NODE_DASHBOARD_PLAN_SPEC.md` already settles for the plan — **project every vertex, never
resample** — and it cut `h3.js` from 274 kB to 61 kB on the way.

## What drawing the grid found, before any of the three was composed

These are measurements, not opinions, and every one of them is printed on all three pages rather
than reconciled away.

**1 · Two of the four distances are the wrong way round.** The cell that contains the ring is
resolution 4, 26 km to an edge. The cell that contains *the region* is resolution 5, 9.9 km. **The
ring is the bigger of the two.** The four words are custody and provenance, not scale, and nothing
had made that visible before the grid was drawn beside them.

**2 · At the grain the street is drawn at, the grid cannot tell mine from theirs.** The cell this
house stands in at resolution 6 holds three of this node's own sensors *and two that are not* —
`Ungasan Kit - TEST` and `BAYU NEW ENCLOSURE`, 1.3 km away. A cell is a place; "ours" is not a
place, it is custody, and only the node knows it.

**3 · The grid cannot tell the room from the wall outside at all.** All three of node #1's own
sensors carry one coordinate, so they are in one cell at every resolution down to 15. H3 answers
*where*; it does not answer *indoors*.

**4 · The ring is wider than the setting that declares it.** `presets/bali.env` sets
`BAD_RADIUS_KM=8`. The furthest station in this capture is **14.7 km** away. All three grids are
drawn from the data, and say so.

**5 · Containment is exact in the index and approximate on the ground.** Two of the seven resolution-9
children of this node's cell reach **6 m** past their own parent's furthest vertex, and all seven
index to that parent exactly — h3geo.org's own "approximate containment only applies when truncating
the precision of an H3 index", measured on this node.

---

## D · The ladder

**The idea.** The page is the resolution ladder, finest first. Moving down it is `cellToParent`,
moving up is `cellToChildren`, and each rung carries the cell this node actually stands in there,
what a cell is worth on the ground at that grain, and what is read at it. The four distances sit on
the rungs they belong to, named.

**What only D does.** It has a **line across it**. Everything finer than resolution 6 is what this
machine keeps; resolution 6 is `PRESENCE_RES_FLOOR`, the finest any node may announce; everything
coarser is what may leave. `SHARE_LEVEL`, the radio announce and `/health`'s published cell stop
being three paragraphs in Set up and become three positions on one page. No other direction in
either round puts the privacy argument where a household can see it.

**The five readers.** The household member gets the same first screen as C — all five T1 legs at 390.
The keeper gets the ladder and the line. The wall gets four columns, not the ladder, because nine
rungs of fifteen-character cell ids at three metres is the opposite of a wall; **it fits 1,080 px on
a 1,080 px screen exactly.** The tester on an empty node still gets every rung, each saying what it
has no instrument for. The stranger gets the refused page.

**What it costs.** The ladder is a teaching object, and a household does not need to be taught the
aperture-7 hierarchy to shut a window. Two of its rungs — resolutions 4 and 5 — exist only because
the geometry demanded them, not because anybody reads anything there. And it is 5.7 screens at 390,
longer than C.

## E · The disk

**The idea.** `gridDisk(cell, k)`. k = 0 is the cell this house stands in, k = 1 the six around it,
k = 3 as far as any station reporting here. Every sensor is placed in the cell it is actually in,
computed from coordinates the node already stores. The grain is not a taste: the page prints the
table it was chosen from — resolution 6, k = 3, 37 cells, 7 of them with a sensor — and the row
above and below say why one is a single hexagon and the other is 217 cells with eight things in them.

**What only E does.** It answers *is it me or is it everywhere* as a **count** rather than a
sentence. Seven of thirty-seven cells have anything reading in them, and they are not evenly spread —
two at 1.3 km, three at about 4 km, two at 6.3, and three singletons at 14 km and beyond. A ring
reported as one fenced median has already thrown that shape away. E is also **the densest page
measured in either round: 34.9 % empty at 390 and 31.9 % at 768**, against a target of 20 % and
against the shipped page's honest 46.8 %.

**The five readers.** The household member gets the sentence, the ask and the grid on the first
screen. The keeper gets the neighbourhood. **The wall is the best of the six**: at three metres the
grid reads as a constellation of where the readings are, which no list does. The tester on an empty
node gets thirty-seven dashed outlines and a sentence per step — the clearest "you have no
neighbours yet" in either round. The stranger gets the refused page.

**What it costs.** Two things, and the first is serious. **A cell is not a house**: at resolution 6
this house's own cell also holds two of somebody else's sensors, so the drawing's centre cell is not
"mine" — it is "here", and the page has to say so in a sentence rather than in the drawing. And E
shows *where* a station is but not *what it read*: the node publishes the ring as one fenced median,
not a value per station, so a number per cell would be the page computing something the node has not
said. E draws the shape of the ring and still cannot colour it.

## F · The ground, gridded

**The idea.** C, kept. The four zones stay in order, the issues stay hung off the distance their
evidence lives at, the reading order is untouched. H3 supplies the three things C had to assert: each
zone's **picture** (its cell among its six neighbours, at that zone's grain), its **address** (the
cell id in full), and its **scale** (what a cell is worth there).

**What only F does.** It is the smallest change of the three and the only one that does not re-spine
the page. If the answer to "does the grid help a household?" turns out to be "a little", F is the
version that costs a fortnight instead of a quarter.

**The five readers.** Identical to C everywhere except that each zone now carries a drawing, an
address and a scale.

**What it costs.** Height. **8.6 screens at 390 and 9.6 at 768**, against C's 5.5 and 5.2 — four
grids, four addresses and four scale lines added to a page that was already the shortest of the
first three. At 768 the two-column zone collapses and every aside goes full width, which is why 768
is worse than 390. F buys the grid and pays for it in scrolling.

---

## The measurements, D E F beside C

Same script, same fixture, same afternoon. C is repeated from Part One so the comparison is direct.

| | target | C | D ladder | E disk | F gridded |
|---|---|---|---|---|---|
| **T1** @ 390, five legs | all five | ✓✓✓✓✓ | ✓✓✓✓✓ | ✓✓✓✓✓ | ✓✓✓✓✓ |
| **T1b** issues named, first screen @ 1440 | all five | air heat water | air heat water | **water only** | air heat water |
| **T2** empty @ 1440 | ≤ 30 % | 70.5 % | 72.1 % | **63.7 %** | 66.2 % |
| **T2** empty @ 390 | ≤ 20 % | 43.2 % | 42.8 % | **34.9 %** | 43.7 % |
| **T2** empty @ 768 | — | 55.3 % | 60.2 % | **31.9 %** | 55.8 % |
| **T2** page @ 1440, screens | ≤ 4 | **3.1** | 4.3 | 3.4 | 5.4 |
| **T2** page @ 390 | ≤ 8 | 5.5 | 5.7 | **4.9** | **8.6** |
| **T3** card kinds | 4 | 2 | 2 | 2 | 3 |
| **T4** orphan numerals | 0 | **0 of 26** | **0 of 39** | **0 of 27** | **0 of 33** |
| **T5** orphan components | 0 | 2 of 25 | **2 of 30** | 4 of 25 | 5 of 32 |
| **T6** swaps @ 1440 / 390 | 0 | 8 / 2 | 6 / **2** | **4 / 2** | 7 / **2** |
| **wall** on a 1,080 px screen | 1,080 | **1,080** | **1,080** | 1,133 | 1,130 |
| **wall**, what falls off | nothing | **nothing** | **nothing** | node name, `stale`, "Answer on Telegram" | the same, plus the announce address |
| **wall** issue line, cap height | ≥ 9 mm | 8.4 | 8.4 | **7.5** | 8.4 |

**E and F lose `stale` off the wall by 53 and 50 px.** That is a line to trim, not a composition to
rebuild — unlike B's 470 px in Part One — but it is the same S-01 failure and it is not fixed here.

**None of the six reaches T2's 20 % at 390.** E gets closest at 34.9 %, and it is the only one of
the six to pass 30 % at any width. The question from Part One stands and E is the first evidence
that a denser page is achievable at all: the thing that fills E's fold is a drawing that carries
readings, which is exactly what the complaint asked for and what the hero's decorative ground is not.

---

## What the six agree on now

Part One's four shared findings hold unchanged. Three more come out of the H3 round, and they are
not part of the choice either:

**5 · The four distances are custody, and the grid is scale, and the page needs both.** Every one of
D, E and F ended up printing the disagreement rather than resolving it. Whatever is picked, `/issues`
should carry the cell id and resolution per distance, so the page can show the scale without
inventing it — that is a field on a stack cell, not a new endpoint.

**6 · A cell id belongs on the page, once per object, in full.** It is the only thing that makes a
reading citable by anybody else, and truncating it makes a different id.

**7 · The grid's limits have to be said out loud.** It cannot tell indoors from outdoors, it cannot
tell mine from the street's at the grain the street is drawn at, and its containment is exact in the
index and approximate on the ground. All three directions carry those as sentences, because a reader
who believes a hexagon means "my house" has been misled by the page.

## What the pick now decides, restated

**1 · Does the grid navigate, or illustrate?** D and E navigate by it; F illustrates with it. F is a
fortnight, D and E are a re-spine.

**2 · T2 still.** E is the only page in either round to pass 30 % anywhere. If the targets stand as
written, E is the only direction with a path to them; if they move to the honest measure, all six
already clear it.

**3 · The wall.** C and D fit it exactly. E's wall is the best of the six to look at and is 53 px
too tall. F's is the same. B's, from Part One, is 470 px too tall.

**4 · New, and only H3 raises it: whether the page should teach the grid at all.** D teaches it, E
uses it without teaching it, F mentions it. A household that never learns what resolution 6 means
still reads E's drawing correctly — the centre cell is where I am, the filled ones are where
somebody else is reading, the dashed ones are empty — and that is an argument for E over D that has
nothing to do with the measurements.

---

# Part three · three that navigate by nothing but the grid

**15 September 2026.** Tomas read D, E and F and asked to *go more radical on the use of the H3 grid,
and base all the navigation on it*. These are those three. They are G, H and I; A to F stand
unchanged above.

D, E and F put H3 into a page that was still a document: a spine of sections, read top to bottom.
These three do not have one. Each takes a different H3 operation and makes it the **only** thing a
reader can do:

| | what the reader moves through | H3's own words for it |
|---|---|---|
| **G · the address** | one cell at a time. The page *is* a cell; out, in, across and home are the whole interface, and the URL is `?cell=8895a4c86bfffff` | `cellToParent` · `cellToChildren` · `gridDisk` · `latLngToCell` |
| **H · the dial** | one control, and it is resolution. Everything on the page re-derives from where the dial stands, 2 to 12 | `getResolution` · `cellToParent` · `cellArea` |
| **I · the surface** | one grid that never moves, and the issue is a layer over it. Every cell is a control | `polygonToCells` · `compactCells` · `gridDisk` |

## What "all the navigation" actually costs, and what it buys

**The four distances leave the navigation.** In all three, room · yard · ring · region are no longer
where anything lives. They come back as what Part Two measured them to be — a word on a reading
saying whose custody it is. This is the one decision in this document that reverses something from
10 September, and it is deliberate: finding 1 above says the four words are custody and not scale,
and a page cannot navigate by custody and by geometry at the same time without lying about one of
them.

**The URL becomes a place.** `?cell=8895a4c86bfffff` is fifteen characters that resolve to the same
0.64 km² on every node on the planet. "What did your street read" becomes a link somebody in Menorca
can open against their own node. *My room* is not portable; a cell is. That is the whole argument for
navigating this way, and it is worth more than any of the drawings.

**Two things the node would have to publish.** Neither is a new endpoint; both are shapes on
`/issues`, and the second is a product decision rather than a drawing one — it is in the handoff as
a question and is **not** assumed here:

1. **A plate per cell** — the cell, the cells around it, each one's parent, area and contents.
   `app/ground.py` already calls `latlng_to_cell`, `grid_disk` and `cell_to_children`; it does not
   publish them per cell. Measured: **3.0 kB** for the plate a reader is standing on.
2. **A value per station.** G and I show one station's own 15-minute mean. `/issues` publishes the
   street as a single **fenced median** and never a value per station. The fence exists for a reason.
   Asking for it to come down is a decision about what a node says about its neighbours, and it is
   Tomas's, not this document's.

## Where the third round's geometry comes from

The same generator, `make-h3.mjs`, extended. Three new objects, all computed with h3-js 4.2.1 from
the committed fixture:

| | what it is | size |
|---|---|---|
| `nav` | eleven plates, resolutions 2 to 12, two steps published around this node at each — 209 cells, with every cell's parent, neighbours, area, contents and which claims cover it | **3.0 kB** per plate |
| `claims` | what each source's word covers, as the cell set that covers it, compacted | six claims |
| `surface` | 217 cells at resolution 7, wide enough to hold every station, with each issue's evidence placed on it | one plate |

**Not one radius on these pages was chosen by them.** Every footprint is a number the product
already declares: `COAST_MAX_KM=30` (packs/coast), `BAD_RADIUS_KM=8` (presets/bali.env),
`EARTH_RADIUS_M=5000` at 10 m a pixel (packs/earth), `PLACE_RADIUS_M=1000` (packs/place),
`LOCAL_RADIUS_M=500` (.env.example), and the three decimals `GET /health` rounds a coordinate to —
about **110 m**, which is the finest grain anything from this node may honestly be drawn at.

`h3.js` is now **245 kB**, up from 61. That is the prototype's convenience, not a shipping shape: it
carries eleven plates at once so the drawings can be walked with no server behind them, and a node
would publish one. Two things were measured on the way there and are worth keeping: spreading the
whole sensor object into every drawing cost 180 kB for the same object thirty times over, and one
space of JSON indentation cost 150 kB.

## What building the navigation found

Findings 1 to 5 are in Part Two and all five still hold. These are new, and each is printed on the
pages rather than reconciled away.

**6 · Between resolution 7 and resolution 10, nothing changes.** Four stops of the dial, each seven
times finer than the last — 343 times smaller by area — and the answer to *who is near me* is
identical at every one: nine cells hold something, three sensors sit in this node's own cell. Past
resolution 7, on this node on this day, grain is precision with no information in it. Nothing in
rounds one or two could have shown this, because nothing in them varied the grain.

**7 · The satellite square is 374,551 cells at the grain its own data has, and 4,063 after
compaction.** `EARTH_RADIUS_M=5000` at 10 m a pixel is resolution 12; `polygonToCells` on that square
returns 374,551 cells and `compactCells` returns 4,063 covering exactly the same ground — **92 times
smaller**. This is the only place in three rounds where an H3 operation does something the node could
not already do by hand, and it is the answer to "how would you ever publish a covering that fine".

**8 · Six of the seven footprints were already declared; the one that is not belongs to the source
that speaks for the most ground.** Every pack that keeps a distance states it in its own `env` block.
The exception is the model point — CAMS — whose sample covers, at the grain a sensor is drawn at,
**4,396 cells**, against the **one** cell a probe in this room covers. Nothing in the product says how
big a model point's word is.

**9 · Four issues, four completely different geometries, and the shipped page draws them as four
bands of the same height.** On one grid of 217 cells at resolution 7: air is 11 stations in **7**
cells; heat is 10 stations in the same 7, and *its* declared footprint — `LOCAL_RADIUS_M`, the wall
outside — is **smaller than one cell of this grid**, so it draws **0**; land is **15** solid cells
with no station anywhere in them; coast is **all 217**, one model's word over the whole screen; water
is **0**, a reading with no ground under it at all. Four equal bands is the flattest possible lie
about what is known.

**10 · Navigating away from your own cell costs the numeral.** G standing in a published but empty
cell fails T1's second leg, measured: there is no number, because nothing is read there. That is a
property of place-first navigation and not of the drawing — and it is the strongest argument against
G as the household's default screen.

---

## G · The address

**The idea.** One cell at a time. The address bar carries the H3 index, and out, in, across and home
are the only moves. Under it: what is read in this cell, whose word reaches it, and the seven
children as seven doors. Seven and six are not numbers this page chose — they are H3's arity, and
the page can therefore show every option it has at once.

**What only G does.** It makes a place *sendable*. It is also the only direction where the privacy
argument is a position you can stand on rather than a paragraph: the plate ends two steps out
because that is what this node published, and everything finer than resolution 6 is what the machine
keeps.

**The five readers.** The household gets all five T1 legs at 390 — *when standing in this node's own
cell*, and not otherwise. The keeper gets the one thing no other direction offers: a walk through
what a stranger can and cannot resolve. The wall gets one cell and its readings and **fits 1,080 px
exactly**. The tester on an empty node gets a plate with nothing in it and a page that says so. The
stranger gets the refused page.

**What it costs.** Most cells are empty, and a page that navigates by cell spends most of its life
saying "nothing reads here". T1's numeral leg fails at every such position (finding 10). And it is
the direction most dependent on the node publishing a value per station.

## H · The dial

**The idea.** One control: resolution, 2 to 12. Which sources count as speaking about here, how much
ground each one's word covers, how many cells fourteen stations fall into, and whether what you are
looking at may leave this machine — all of it re-derives from where the dial stands.

**What only H does.** It makes **resolution into provenance**. A model that samples one point and a
probe on a shelf both produce one number, and every page in rounds one and two draws them the same
size. Here they are 4,396 cells and 1. It also puts the product's two existing lines — the announce
floor at resolution 6 and the 110 m the node is willing to say it is at — on the same control, where
a household can see which side of both it is standing on.

**The five readers.** The household gets the node's own headline unchanged, with one line under it
saying what the dial is currently letting the page say. The keeper gets the grain table, which is
where finding 6 came from. The wall drops the dial — nobody presses a wall — and keeps the
comparison; it **fits 1,080 px exactly**. The tester gets a dial over an empty node, which still
answers "how coarse must I be to say anything". The stranger gets the refused page.

**What it costs.** It is the most abstract of the nine. A dial marked 2 to 12 is a control a
household has no reason to understand, and the page has to work when nobody ever touches it — which
it does, but that makes the dial furniture for most readers. It is also 4.4 screens at 1440, the
longest of the third round.

### H, revised · the ground under the dial

**15 September, same day.** Tomas read H and said the hexagons feel abstract: keep a map under the
scales, with the cells over the place the node actually stands in — and add a section for the node's
radio and one for the satellite. All three are in, and none of them needed anything the node does
not already have on disk.

**The map is the node's own plan, not a tile server.** `planetai-design/data/place.geojson` is the
kilometre around node #1 as the `place` pack keeps it: **OpenStreetMap** (ODbL), 2,904 buildings,
540 roads, 21 green, 37 uses, plus 1,874 buildings one satellite pass found that OSM does not have —
26,311 vertices, the same data `drawPlan()` draws on the shipped page. `make-plan.mjs` projects it
with the node dashboard's own formula, which `NODE_DASHBOARD_PLAN_SPEC.md` measured within
**0.015 px on an 800 px frame** of `geoAzimuthalEqualArea` over these exact vertices, and `plan.js`
is 346 kB with every vertex kept. The seven rules of that file are followed, including the two that
matter most here: never resample, and the grid is drawn **over** the town, because the index is a
thing laid on a place.

No tiles, and that is not a shortcut. A slippy map means a node fetching tiles, and a household node
that fetches tiles tells somebody else's machine where it is every time anybody opens the page —
which is the single thing this product is built not to do. If photographic ground is wanted, it is
already here: four Sentinel passes on the node's own disk.

**The frame is the cells.** The dial picks the resolution, the resolution picks the cells, the cells
pick how much ground is in view. Turning the dial zooms the map and nobody has to line up two
pictures. Past 20 km across, the plan stops being drawn as buildings and becomes the rectangle it
actually is — at resolution 4 the view is 237 km across and everything this node has ever mapped is
a 3 km smudge in the middle, which is a true and useful thing for a page about grain to show.

**The radio section draws what a radio actually says, which is a cell.** Two radios and neither
sends a coordinate: Reticulum announces the cell this node is in at resolution 3 — 69 km to an edge,
10,857 km² — and the LoRa mesh device in this house has no position at all. The fixture's peer,
`ungasan-2`, kept its resolution and its distance and not the cell it announced, so the drawing shows
**all three cells 61 km could be in**. A page that put a pin at 61 km on a bearing it was never sent
would be inventing the one thing the scheme refuses to send.

**The satellite section is four real passes and one orange fact.** Sentinel-2 at 10 m over about
3 km, 2016 · 2019 · 2022 · 2025, brightness matched across years per Decision 2 of 8 September —
stamped with the year, carrying `satellite` provenance, never interpolated, and with nothing coloured
sitting on the photograph. Beside them, the 1,874 buildings only the satellite knows, drawn in
`--satellite-only` over the hairline outlines of the ones OSM already has, and the earth pack's own
numbers: `EARTH_RADIUS_M=5000` at 10 m a pixel, 100.42 km², 374,551 cells at that grain and 4,063
compacted. The `land` issue itself has no reading in this capture and the section says so rather than
implying one.

**What it cost, measured.** 1440 went from 58.4 % empty and 4.4 screens to 59.6 % and 5.5; 390 went
from 6.9 screens to **8.4, which is over T3's eight**. Three things bought most of it back and are
worth recording: the eleven-row grain table folded into a `<details>` (−0.5 screens, and the finding
it produced is printed in prose above it), the claim cards in two columns past 1040 px (−0.6 screens
at 1440, T6 unchanged at 5), and the satellite strip at two columns on a phone rather than four
(−0.8 screens). The honest summary is that a page carrying a map, a radio and a satellite section is
not a four-screen page, and if eight screens on a phone is the real limit then one of the three
belongs in the Network view, which already has a box called "What leaves this house".

## I · The surface

**The idea.** One grid of 217 cells, wide enough to hold every station this node reads, and it never
moves. The issue is a layer over it. Every cell is a control; pressing one asks what is read there.
There are no sections, no scroll position that means anything, and no order to argue about.

**What only I does.** It puts every issue's evidence on one ground, at one grain, and lets a reader
see that the four are not comparable (finding 9). It is also the only direction in three rounds that
makes the drawing the instrument rather than an illustration beside one — which is the honest version
of what the shipped page does with a decorative full-bleed map.

**The five readers.** The household gets all five T1 legs at 390 with the surface capped at 36vh —
measured; 44vh pushed the as-of below the fold. The keeper gets the layer counts. The wall is the
same surface, and **fits 1,080 px exactly**. The tester gets an empty grid, which is the most honest
empty state of the nine: the ground is still there, nothing is on it. The stranger gets the refused
page.

**What it costs.** It is the least like a document of the nine, and everything below the surface is
secondary by construction — the loop, ρ and the funnel end up as a footer. A reader who wants to
compare two issues must press twice and remember. And it asks the node for a value per station just
as hard as G does.

## The measurements, G H I beside C and E

Same fixture, same script, real faces, one device pixel. C is the first round's strongest and E the
second's.

| | target | C | E disk | G address | H dial | I surface |
|---|---|---|---|---|---|---|
| T1 @ 390 | five legs | ✓ | ✓ | ✓ *(in this node's cell)* | ✓ | ✓ |
| T2 empty @ 1440 | ≤ 30 % | 70.5 | 63.7 | 63.7 | 59.6 | **42.2** |
| T2 empty @ 390 | ≤ 20 % | 43.2 | 34.9 | 33.9 | 33.7 | **33.2** |
| T2 empty @ 768 | ≤ 20 % | 55.3 | 31.9 | 33.9 | 36.3 | 34.5 |
| page @ 1440 | ≤ 4 screens | 3.1 | 3.4 | 4.1 | 5.5 | **2.4** |
| page @ 390 | ≤ 8 screens | 5.5 | 4.9 | 5.5 | 8.4 | **3.1** |
| T3 kinds | 4 | 3 | 2 | 3 | 3 | 2 *(3 with a cell selected)* |
| T4 numerals with no comparison | 0 | 0 / 26 | 0 / 27 | 0 / 34 | 0 / 36 | 0 / 13 |
| T5 components with no link | 0 | 2 | 4 | **0** | **0** | **0** |
| T6 reading order against DOM @ 1440 | 0 | 8 | 4 | 5 | 5 | 3 |
| wall on 1,080 px | 1,080 | 1,080 | 1,133 | **1,080** | **1,080** | **1,080** |

H's column is the revised page — the one with the map, the radio and the satellite in it. Before
that revision it measured 58.4 % and 4.4 screens at 1440, and 6.9 at 390; the three additions cost
1.2 points of emptiness and 1.1 screens at 1440, and took it past T3's eight screens on a phone.

**T2 moved, and it is the first time in three rounds that it has.** I is 28 points below C at 1440
and 10 below A-to-F's best. It still misses the target — 42.2 against 30 — and the reason is the same
one raised at the end of Part One: on this fixture, at this width, 30 % is not reachable by a page
that keeps a 24-character measure column and a 60-character comparison under every numeral. Nine
compositions have now been measured against it. **The target is the thing that should move, and only
Tomas can move it.**

Two smaller measured notes. Side-by-side bands were tried on G and rejected on the numbers: they took
1440's empty share from 68.4 % to 66.4 % and took T6 from 3 to 14 — two points of emptiness is not
worth eleven places where the page reads in a different order than it is written. And H's page
measures identically at resolutions 4, 8 and 11: the layout does not move when the dial does, which
is a property worth having and was not designed for.

## What the third round changes about the decision

Nothing in Part Two's list is withdrawn. Three things are added:

1. **Whether the four distances stay in the navigation.** A to F keep them; G, H and I do not. This
   is now the first fork, and it is ahead of the choice between the nine.
2. **Whether `/issues` publishes a value per station.** G and I need it. The street is a fenced
   median today and the fence is deliberate. **This is a STOP: nothing will be built on either
   without an answer.**
3. **Whether the node publishes a plate per cell.** Cheap — `app/ground.py` computes all of it
   already, 3.0 kB a move — and needed by G and H.

Everything else stands: the pick is one of nine, and Phase 2 does not start without it.
