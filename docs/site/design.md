# Design

What a PLANETAI surface is made of, and why each part is the way it is. This page is the programme
layer written out: the colours and what each one means, the type, the four card kinds, the signs,
every motion with the datum that drives it, and the refusals that hold at every stage.

It is not a style guide in the sense of a preference. Every value here is generated from one table —
`planetai-design/references/planetai-layer.md` — into `app/static/planetai-theme.css`, and
`tools/check_theme.py` holds the copy a node ships byte-identical to the one the design repository
published. To change a value you change the table and regenerate; there is nowhere else to change it.

> **Note.** This page says nothing the layer does not. Where the layer records a value as unsettled,
> this page says so and names the item. Nothing below is an aspiration.

## The plate

Paper by day, dark on a wall and by a keeper's switch. `--ground` is `#F9F5F2` on paper and `#171717`
in the dark register; `--ink` is the reverse. Everything drawn is ink on ground — buildings, roads,
labels, provenance — and the register is one attribute on `<html>`, so a page carries both and no
drawing is exported twice.

Square corners. No gauges, no dials with needles, no rounded verdict. A reading is a number and a
comparison, not a speedometer.

## Colour is argument, never decoration

Four colours, one meaning each. A surface that uses one of them for anything else is wrong, and that
is the whole of the rule.

| token | paper | dark | what it means, and nothing else |
|---|---|---|---|
| `--cells` | `#20388D` | `#7FA5E8` | an H3 cell. Also data and identity, which are the same claim: this is where the reading is from |
| `--rings` | `#00A057` | `#00A057` | a loop closed — somebody was asked and somebody answered |
| `--signal-worse` | `#E62038` | `#E62038` | a signal got worse, or crossed a line the issue declares |
| `--satellite-only` | `#DB7200` | `#FF931E` | what only the satellite knows, and nothing else |

`--loop-closed` and `--rho-closed` are both `var(--rings)`: a closed ring means the same thing in the
ρ row as it does anywhere else, so it is the same green by name rather than by coincidence.

**State is carried by weight, fill and dash — never by hue.** A live node is a 2.5 stroke, a
registered one a 1.5 dashed `5 4`, a pilot a 1 at 45% opacity. On the dashboard the same rule reads
as type weight: `act` is set at 800 and `quiet` at 400, and nothing in the table is tinted. A reader
who cannot separate blue from grey still sees three zones.

Provenance is ink only and square — `--prov` is `var(--ink)` — never a coloured pill. The words are
`live`, `partial`, `model`, `cached`, `stale` and `refused`; see [Concepts](concepts.md).

### Two numbers that are rules

Contrast decides which register a colour may appear in, and the generator enforces it.

- `#7FA5E8` measures **2.29:1** on paper. It may appear only inside the dark block.
- `#20388D` measures **1.72:1** on ink. It may never appear inside it. A dark export still carrying
  `#20388D` is a stale asset, not a style choice.
- `#DB7200` is the paper register's satellite orange at **3.02:1**; `#FF931E` is **2.05:1** on paper,
  under the 3:1 floor for a graphical object, and **8.06:1** on ink. Neither crosses into the other's
  block.

## Type

Three faces, three jobs.

| role | face | where |
|---|---|---|
| display | Funnel Sans | headings, the stage names, a band's title |
| body | Figtree | the node's own sentences — the lead, the reason, a caption |
| mono | JetBrains Mono (`--mono`) | every number, unit, timestamp, cell id and chip label |

All three are self-hosted and served from the node, because a node serves its page to a household
network that may have no route out at all; a webfont from a CDN is a page with no typography.

`--num-face` is the one numeral big enough to be a piece of typography rather than a reading — the
monument figure on the lead. It defaults to `var(--mono)` and exists so that the open question, mono
or Funnel Sans, is one line either way. Recorded as **O13**.

**The node's own words are never uppercased.** `µg/m³` once became `MG/M³` on a hero, which is a
thousandfold error in a unit, on a wall, silently: `µ` uppercases to `M`. Any rule that shouts is
checked by `tools/check_ui.py`, which keeps a list of the elements allowed to, and every one of them
carries the page's own vocabulary rather than a sentence from the node.

## Spacing

There is no spacing scale in this layer, and that is worth saying rather than leaving a reader to
look for one. The foundation tokens (`--fc-` prefixed, from the Fab City design system) carry the
type scale; the dashboard's own rhythm is `clamp()` in `app/static/dashboard.css`, set against the
three widths the page is measured at — 390, 768 and 1440 px. Every value the programme layer adds is
unprefixed and additive, and the generator fails if a row would redefine an `--fc-` token.

## Four card kinds and no fifth

Everything on a node's page is one of four things. A fifth would mean the page had learned a new way
to be read, which is a decision and not a detail.

| kind | what it is for |
|---|---|
| **readout** | one figure, with its comparison beside it |
| **stack** | the same quantity at several distances, on one scale |
| **series** | a quantity over time |
| **row** | a list of like things, counted in signs |

A drawing is a drawing *inside* a card, not a fifth kind. A gap in a series is a gap in the line,
never a ramp across a line nobody measured. Every numeral carries its comparison; a numeral with
nothing to compare it to says so in words.

## Signs

Two families, two rules, and each is audited by its own.

A **counting sign** is 24×24 on a whole-unit grid, fill only, `currentColor`. It is repeated to show
quantity — more signs, never a bigger sign — so it has to survive `--sign-floor`, which is **12 px**,
and tile in a row of ten without fusing. At that size the only discriminator that can be relied on is
solid mass against hollow ring.

A **pictogram** is 15×11, drawn once at hero size beside the issue it names. The 12 px floor is a rule
about a use it does not have.

Distinctness is measured, not judged: every pair is rasterised at 12 px and compared cell for cell,
and over 90% identical fails unless the layer records it as an open item. Two pairs are recorded —
**O7** (`prov-cached` against `prov-example`, 93.7%) and **O12** (`cell` against `prov-example`,
93.9%) — and both are redraws waiting to happen, not exceptions. The audit reproduced both
hand-measured numbers independently, which is why it is trusted; the next closest pair is 88.9%.

A pack cannot contribute a sign in this version. Nothing needs to yet.

## Motion, and the datum behind each one

Every motion is named after the thing that drives it. A motion with no datum behind it is deleted
rather than tokenised — there is no easing for its own sake anywhere on a PLANETAI surface, and
nothing counts up, nothing eases between two readings, nothing moves without a reason.

| token | datum | value |
|---|---|---|
| `--motion-reading-fade` | a reading lands | `120ms`, opacity only |
| `--motion-reading-pulse` | a reading lands | `3s`, once |
| `--motion-ring-closed` | a person answered | `320ms` |
| `--motion-meter-fill` | a stack arrives | `40ms` per bracket cell |
| `--motion-day-curve-step` | the day curve steps | `3600s` — once an hour |
| `--motion-satellite-year` | the year changes | `4s` per frame, no tween |
| `--motion-land-change-yoy` | the datum changes once a year | `0s`, so it does not animate |
| `--motion-mark-float` | learn mode is on | `3.2s`, 4 px, transform only |
| `--motion-asking` | the node has not answered yet | `until-data` |

Transform and opacity only, never layout. One `requestAnimationFrame` loop for the whole page, which
surfaces subscribe to and which stops when the tab is hidden, when the element is off screen, and
when nobody is subscribed.

**A motion is not always a duration.** `--motion-asking` is a word. The loading state lasts exactly as
long as the node takes to answer, which is a fact about the network and not a design decision.

**Reduced motion.** One `@media (prefers-reduced-motion: reduce)` block sets every *timed* token to
`0s`, and every surface has to read frozen. `--motion-asking` is not restated there: it has no number
to remove, so under reduced motion the loading state still happens and simply stops moving. There is
no SVG `<animate>` anywhere on a node's page, and that is a gate rather than a habit — reduced motion
reaches CSS animation and nothing else, so SMIL keeps moving after a household has asked the machine
to stop, and no stylesheet can switch it off.

## Refusals that hold at every stage

The layer is not only what a surface may draw. It is also what it may not.

- No raw readings leave the instance that recorded them.
- No cell is upgraded from `partial` to `live` by aggregation.
- No agent dispatches without a human row in `actions`.
- No layer requires a cloud provider to function.
- No scale is skipped: a city aggregator is built from nodes, not declared from above.

On the dashboard these five are drawn as the care label at the foot of the page, as signs, in the
node's own words. There is nothing to press on a wall: the wall is an instruction, not a control.

The longer form, with the staging from one node to a bioregion, is
[Architecture](architecture.md); the privacy half — what leaves the machine and how coarse — is
[Sharing and security](sharing.md).

## What is unsettled

The layer records twelve open items against ten tokens, each one emitted into the CSS as a comment at
the token it affects, so a reader of the stylesheet sees them without coming here. They are the values
that were set by eye, or on one screen, or in one room, and have not been measured since. The list
lives in `planetai-design/references/planetai-layer.md`; `O7`, `O12` and `O13` are named above.

## Where this comes from

- `planetai-design/references/planetai-layer.md` — the token table, the guards and the open items.
- `planetai-design/decisions/design-log.md` — which round settled what, and why.
- `app/static/planetai-theme.css` — generated from the first, held to it by `tools/check_theme.py`.

The node's page is three static files and stays so. `planetai.fab.city` may use a framework; the two
never share code, and both read this layer.
