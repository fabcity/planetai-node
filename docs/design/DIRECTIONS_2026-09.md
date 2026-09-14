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
| the wall at three metres | the same rows, larger. Four issue lines at 10.2 mm cap height, over the 9 mm floor, and the whole wall fits one screen. |
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

**What it costs.** The column is long: **8.4 screens at 390**, the worst of the three, and only two
issues are named with a number on the first screen at 1440, because the lead takes the whole fold.
A is the direction that answers "what is happening" fastest and "is it me or is it everywhere"
slowest — the comparison is inside a row you have to open.

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
| the wall at three metres | the matrix, dark. It does **not fit**: 1.4 screens at 1920, so the ρ row and the footer carrying `stale` are below a fold that does not scroll. That is the shipped page's own S-01 failure, reproduced by a composition that wants one more row than the wall has. |
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
| the wall at three metres | the best wall of the three, and it fits exactly one screen: four columns, every issue at every distance, `stale` legible, the ρ row and its caption on it. |
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
| **T1b** issues named with a number on the first screen @ 1440 | all five | — (marks none) | air water | air coast heat water | air heat water |
| **T1b** the same @ 390 | | — | air water | air water | air heat water |
| **T2** empty @ 1440, as written / discounted | ≤ 30 % | 35.3 / 64.4 % | 69.0 / 69.0 % | 71.9 / 71.9 % | 71.1 / 71.4 % |
| **T2** empty @ 390, as written / discounted | ≤ 20 % | 21.4 / 46.8 % | 45.5 / 45.5 % | 51.6 / 51.6 % | 43.3 / 43.3 % |
| **T2** page height @ 1440, in viewports | ≤ 4 | 5.7 | 5.1 | **4.1** | **3.1** |
| **T2** page height @ 390 | ≤ 8 | 8.9 | 8.4 | **7.0** | **5.5** |
| **T3** card kinds declared | 4 | 0 (24 grammars, undeclared) | **4** | 3 | 2 |
| **T4** numerals with no comparison | 0 | 0 of 0 declared (26 drawn) | **0 of 70** | **0 of 47** | **0 of 26** |
| **T5** components with no link in or out | 0 | 47 of 47 | 2 of 52 | 1 of 31 | 2 of 25 |
| **T6** reading-order swaps in the first viewport @ 1440 / 390 | 0 | 3 / 3 | 11 / 5 | 7 / 7 | 8 / 2 |

### The wall, 1920 dark

| | target | shipped | A | B | C |
|---|---|---|---|---|---|
| fits one screen | 1.0 | 1.0 (**1.2 at 1440**) | **1.0** | **1.4** | **1.0** |
| the sentence | ≥ 9 mm | 34.0 | 31.2 | 28.4 | 29.1 |
| the numeral | ≥ 9 mm | 80.9 | 73.6 | 66.2 | 69.2 |
| every issue line | ≥ 9 mm | **7.5** | **10.2** | **8.4** | **8.4** |
| the ρ row's caption | ≥ 9 mm | **5.7** | **8.9** | **8.9** | **8.9** |
| issues named with a number | all | — | all four | all four | all four |

### Empty and refused

| | shipped | A | B | C |
|---|---|---|---|---|
| empty @ 390, page height in viewports | — | 2.0 | 3.8 | **1.7** |
| empty @ 1440, empty share | — | 67.6 % | 74.5 % | 75.8 % |
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
best first screen measured is 43.3 % empty, against a target of 20 %. The shipped page appears to
pass at 21.4 % only because a decorative full-bleed drawing counts as a mark — discount it and it is
46.8 %, which is the same neighbourhood as all three drawings. So one of three things is true, and
only Tomas can say which: the targets should be restated against the measure that discounts
decoration (and set near 45 % at 390, 65 % at 1440, which every direction already beats); or the page
should be materially denser than any of these three; or the hero's ground drawing comes back, and the
first screen is filled by a picture rather than by readings. The third is what the shipped page does
today, and it is what the complaint calls too much empty space.

**3 · Whether the wall carries a table.** B's wall is the only one that does not fit its screen, and
the reason is structural rather than a size to tune. A's wall and C's wall both fit at 1920 and both
put every issue's provenance on it. If the matrix is the pick, the wall is not the matrix.

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
