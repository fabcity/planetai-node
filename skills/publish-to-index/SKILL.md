---
name: publish-to-index
description: Decide whether a node may publish cells to the Fab City Index, and prepare the row if it may.
---

# Publishing to the Fab City Index

Most nodes never do this, and that is the correct outcome for most nodes. Read the contract before you
prepare anything.

## The tier contract

**One node per pilot writes to the Index. A home node never does.**

A pilot city has one City-tier node, run by the partner who is accountable for that city's numbers. It is
the only node in that city whose cells reach the Index. Every other node — every home, lab, classroom and
community centre — computes its own cells, shows them on its own dashboard, and passes them no further.
That is not a lesser rung; it is the whole architecture. Readings stay where they were made, and exactly
one identified operator per city stands behind what the Index publishes.

So: before anything else, ask the person which node this is. If the answer is "my house", the work is
done — their cells are already correct, on their own dashboard, and there is nothing to publish. Say that,
and stop.

## What a cell is

`planetai cells --json` shows what this node can honestly compute right now. The row shape is
`fci-cells-v0` and it is written down in `ARCHITECTURE.md` and `SPEC.md`; read the shape there rather than
from this file.

The one field to get right is `state`. `live` means measured here. A model or a portal is `partial`,
whatever its quality. Aggregation never upgrades a state. A cell with no source is absent, not zero — do
not fill what cannot be measured.

Check the cells before you talk about publishing them. A City-tier node publishing a `partial` cell it has
labelled `live` is worse for the Index than a city with no row at all.

## The last mile is not in this repository

The writer is `cells-ingest`, and it lives with the Index's own code, not here. It refuses to run unless
`FCI_PUBLISHER=1` and it holds a **per-pilot write token, issued by hand by Tomas**. There is no way to
publish from this repository, no way to self-serve a token, and no automation that will grant one. That is
deliberate: the only thing that can write to the Index is a City-tier node whose operator somebody knows.

What you can do from here:

1. Confirm the tier with the person.
2. Run `planetai cells --json` and read every row's `state` with them.
3. If a row is wrong, fix the source or the pack, not the label. `docs/PACKS.md` for a cell's SQL.
4. Then tell them to write to **info@fab.city** for a pilot token, with the node's name, the city, and the
   output of `planetai cells --json`.

Do not draft a workaround, do not propose a direct write to the Airtable base behind the Index, and do not
open a PR that adds a publishing path here. When three pilots are publishing, the ingest script may move
into `tools/` — still refusing to run without the flag and the token. Not yet.

## Reach settings are not the same question

A node has its own settings for how far its data travels. The one arriving in v0.43, `SHARE_LEVEL`, does
not exist in this tree today, and when it does it will control the node's own reach — its export, its
dashboard, what a neighbouring node can see. **It has nothing to do with writing cells to the Index.**
Publishing is not the top rung of that ladder; it is a different act, gated by the tier contract and a
token issued to a person. Turning a reach setting up will never make a home node a publisher, and nothing
in this repository should imply that it could.

## When a doc and this file disagree

The doc wins and this file has a bug. Say so, and open an issue.
