# Handoff: three directions, and the question

**14 September 2026.** Phase 1 of the dashboard redesign is done and this session stops here. Phase 2
builds the one that is picked; it starts from this file, in this session if Tomas answers, else in a
fresh one.

Branch: `dashboard-redesign-2026-09`, cut from `main` at **v0.53** (`a06655a`). Nothing on the node's
own surface has changed: the four commits on it are a measuring script, a Phase 0 reading, the three
drawings and this. `make lint` and 33/33 after each.

---

## What to open

The drawings are **served, not opened** — from a `file://` page Chromium refuses the sign sprite and
two of the three faces fall back silently, which makes a drawing judged on type and signs unreadable.

```bash
cd ~/Documents/Claude/Projects/FAB\ CITY/planetai-design/prototypes/dashboard-directions
python3 -m http.server 8090
```

| | at 1440 | at 390 | the wall |
|---|---|---|---|
| **A** the index is the page | http://127.0.0.1:8090/a/ | same, narrow the window | http://127.0.0.1:8090/a/?view=wall |
| **B** the matrix | http://127.0.0.1:8090/b/ | | http://127.0.0.1:8090/b/?view=wall |
| **C** the ground | http://127.0.0.1:8090/c/ | | http://127.0.0.1:8090/c/?view=wall |

Add `?state=empty` for a fresh node and `?state=refused` for a phone with no token. The
wireframes are `?view=network`, `?view=setup`, `?view=arrange`.

Every render is also a JPEG, at one device pixel, in
`planetai-design/prototypes/dashboard-directions/shots/<a|b|c>/` — `_fold.jpg` is the first screen
and `_full.jpg` the whole page. The shipped page, measured the same way on the same afternoon, is the
baseline in [`docs/design/REDESIGN_2026-09_ground.md`](design/REDESIGN_2026-09_ground.md).

The argument, reader by reader, and every number:
[`docs/design/DIRECTIONS_2026-09.md`](design/DIRECTIONS_2026-09.md).

---

## The table, short

| | target | shipped | A | B | C |
|---|---|---|---|---|---|
| the first screen says everything, at 390 | five of five | four | **five** | **five** | **five** |
| issues named with a number, first screen at 1440 | all five | none marked | 2 | **4** | 3 |
| empty share at 1440 · as written / discounting decoration | ≤ 30 % | 35.3 / 64.4 | 69.0 / 69.0 | 71.9 / 71.9 | 71.1 / 71.4 |
| empty share at 390 | ≤ 20 % | 21.4 / 46.8 | 45.5 | 51.6 | **43.3** |
| page height at 1440, in screens | ≤ 4 | 5.7 | 5.1 | **4.1** | **3.1** |
| page height at 390 | ≤ 8 | 8.9 | 8.4 | **7.0** | **5.5** |
| card kinds | 4 | 0 declared, 24 grammars | **4** | 3 | 2 |
| numerals with nothing to compare them to | 0 | 26 drawn, none marked | **0 of 70** | **0 of 47** | **0 of 26** |
| components with no link in or out | 0 | **47 of 47** | 2 | **1** | 2 |
| the wall fits its screen | yes | 1.0 at 1920, **1.2 at 1440** | **1.0** | **1.4** | **1.0** |
| every issue line on the wall ≥ 9 mm | yes | **7.5 mm** | **10.2** | 8.4 | 8.4 |

---

## The three real choices

**1 · Is the page read by issue, or by place?** A and B organise by issue; C organises by distance.
It decides what a household is taught to ask — *which issue is loud*, or *which part of my place is
the problem*. C's cost is the mirror of its claim: air appears in three zones, so reading one issue
end to end means walking the page.

**2 · T2's 30 % and 20 % do not survive contact with any composition.** The best first screen
measured is 43.3 % empty against a target of 20 %. The shipped page reads 21.4 % only because a
decorative full-bleed drawing counts as a mark; discount it and it is 46.8 %, the same neighbourhood
as all three. So: restate the targets against the measure that discounts decoration and set them
near 45 % at 390 and 65 % at 1440 — which every direction already beats — or make the page
materially denser than any of these, or put a picture back behind the first screen, which is what
the page does today and what the complaint calls too much empty space. **This one needs answering
before Phase 2 starts**, because it is the difference between building a page and building a table.

**3 · If the matrix wins, the wall is not the matrix.** B's wall is 1.4 screens at 1920, so `stale`
and the ρ row fall off a surface that cannot scroll — the shipped page's own S-01, reproduced. A's
wall and C's wall both fit and both put a provenance word on every wall number, which closes **L2**,
the one P0 still open from the September walk.

Two smaller ones, recorded so they are not decided by accident: **the stack may not be a card** (B
and C dissolve it, which takes T3's four kinds down to three or two), and **the plan only explains
something in C**, where it is the ring's own drawing rather than a card in a band.

---

## The question, in one paragraph

Three drawings of the same evening, on the same frozen layer, from the same file: A makes the page
one column of rows and the hero the row that won; B makes it a table of issues against distances and
answers *is it me or is it everywhere* before anybody reads a sentence; C makes it four places —
room, wall outside, street, model — and hangs every issue off the distance its evidence lives at. All
three put a comparison beside every number and a link on every component, which the shipped page does
for none; all three fit the first screen at 390, which the shipped page does not; and none of them
comes near the 20 % empty-space target, which the shipped page only appears to meet because a
decorative map counts as a mark. **Which one should be built** — and, whichever it is, **do the
emptiness targets move to the measure that discounts decoration (45 % at 390, 65 % at 1440), or does
the page have to get denser than any of these three?** Name anything from the other two you want
carried over; Phase 2 builds one page, not a merge of three.

---

## If the answer is A

Then: the stack stays a card; the index is deleted as an object; the hero is the first row with a
`lead` class and not a component of its own; the loop band keeps the funnel; and the open problem to
solve first is that only two issues are named on the first screen at 1440 — the lead takes the whole
fold and the rows start below it.

## If the answer is B

Then: `ANATOMY` gains a `matrix` band and loses `stack`; the wall needs its own composition, because
the matrix does not fit it; the per-row sentence at 14 px is the first thing to check at 390; and
`check_ui`'s card-kind count becomes three.

## If the answer is C

Then: `layout()` orders by distance and not by issue, which is the one change that touches the
renderer's own shape rather than its lists; the plan gets drawn from `/place/geojson` with the res-9
mesh and the res-8 outline rather than being an artboard; every reading keeps its link to the same
issue at the next distance, which is C's answer to the scatter; and `check_ui`'s card-kind count
becomes two unless the row and the stack come back somewhere.

---

## What Phase 2 inherits whichever it is

The four shared findings in `DIRECTIONS_2026-09.md` — the as-of under the ask, "nothing has been
asked" as a sentence of its own, a pack's own unit and comparison travelling with its contribution,
and the line's source named once — are not part of the choice. Nor are the four card kinds, the
`data-num`/`data-cmp` pair, the `data-ref` link, or the refused page saying three things.

`tests/visual/measure.mjs` is the one measuring script and it already computes T1–T7 and T9. Phase
2's gates read the same numbers.

**Three things to fix in Phase 2 that all three drawings get wrong.** The ρ caption is 8.9 mm on
every wall, a tenth of a millimetre under the floor. `data-num` on a readout was a label before it
was a key, and a gate that walks `[data-num]` has to be able to tell which issue a numeral belongs
to. And the wireframe views carry one component and one link, so they pass T5 by being almost empty
— a real Network view will not.

---

## Not done, and not claimed

No live data: node #1 and node #2 were not contacted, and nothing on pai-clean was written — no
setting, no restart. `en` only. No real wall in a real room. The committed fixture carries no open
ask, so no drawing shows the green button in use. The funnel's 2×2 axes are inferred, because
`PLANETAI_Response_Funnel_Briefing_2026-09-10.md` and
`PLANETAI_Models_by_Node_Class_2026-09-14.md` are in the PLANETAI project and on neither disk nor any
branch here.
