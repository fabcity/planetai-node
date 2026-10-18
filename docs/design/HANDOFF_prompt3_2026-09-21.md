# Prompt 3, and what it stopped on

**21 September 2026 · branch `dashboard-redesign-2026-09` · fixture `node1-2026-09-21d` (node #1, v0.69)**

Prompt 3 asked for four stages, five signs and two closing pieces. All of it is built except one
phrase, recorded below. The page draws **four card kinds and no fifth** — readout · row · series ·
stack — which is the prompt's own test. T4 zero orphan numerals of 90; T5 zero of 84; the overflow
gate green across 108 combinations.

## The one thing dropped, and why

**"The service strip" is undefined.** It appears exactly once in the whole eight-prompt pack — *"Then
the service strip and the Figures ledger generated from `/issues` provenance"* — and nowhere else in
this repository: not in `DATA_CONTRACT_2026-09-20.md`, not in `PICK_2026-09-20.md`, not in
`HANDOFF_dashboard_directions.md`, and not on the page this redesign replaces. The Figures ledger it
is paired with is fully specified and is built.

Tomas's call, 21 Sep: **drop it and record that it was undefined.** It is not in prompt 3's own test
list, and inventing a component from a phrase would put something on the page that nobody specified
and nobody could review against anything.

If it turns out to mean something, the likeliest reading was a foot strip of what this node serves —
its routes, version, schema and which endpoints answer. That is a guess and is written here as one.

## The STOP prompt 3 asks for

> *STOP before adding any field to `/issues` that a section wants and the node does not compute yet
> — other than the two named here — list them and wait.*

One field, and it is not on `/issues`:

**Capability words, per locale, on a facility row.** Prompt 3 says *"The machine names come from the
node in the reader's language (`CAPABILITY_WORDS` en · id · es)"*. They do not. `/sensors` carries
`meta.capabilities` as raw tokens — `three_d_printing`, `cnc_milling` — and `CAPABILITY_WORDS` lives
in `packs/make/adapter.py`, node-side only. The page does **not** translate them: a vocabulary this
file does not own has no business being restated in it.

Nothing is missing from the row as drawn, because `asks.where` already names the top three in the
reader's language inside the pack's own sentence. But the row cannot list capabilities *separately*
until the pack writes translated names onto the rows it stores, or `/sensors` gains them.

## Owed to main

Two node-side commits are on this branch and belong in the next release:

- **`packs.module()`** — the `make` pack's sentence has never reached a node. Both callers built the
  pack path with a `"../packs"` default; it is `/app/packs` in the image, and both swallow import
  failures by design, so `asks.where` was null on node #1 with the pack on and a lab 3.3 km away and
  the morning report's `make` line has never once appeared.
- **`/earth` in `planetai snapshot`** — `engine.replay` passes `snapshot["earth"]` into `compute()`,
  so every fixture ever taken replayed two of the land figures away, silently. Found by the Figures
  ledger counting 16 where the node published 18.

## Watch items, not regressions

- **Emptiness at 390 is 42.6% against a 37.7% baseline.** Inside the gate's +6 margin, but the wrong
  way. `EMPTY_SHIPPED` for 390 is deliberately **not** re-recorded: writing 42.6 there would make the
  regression the new standard. 1440's *is* re-recorded, down from 61.3 to 57.4.
- **`land` and `coast` read alike at 12 px.** On the contact sheet I would not name them apart
  without their labels. They measure below `house`/`sensor`, which the set has carried since it was
  drawn, so by the layer's own threshold they pass — R23 in the design log records the disagreement
  between the eye and the measure rather than redrawing to a threshold nobody agreed.
- **The `fablabs-io` registry pin.** At `85a194c` its `adapter` is `null` although `pack:make` reads
  it. The page reads `adapter` and never infers, so the Network row will say 14 until the registry is
  re-pinned upstream. A re-pin owed, not a page bug.
