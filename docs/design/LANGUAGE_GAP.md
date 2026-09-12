# Where the dashboard and the design language disagree

12 September 2026. Read against `planetai-design` at `82e0f62`: `references/planetai-layer.md`
(34 tokens, 12 OPEN items) and `planetai-theme.css` generated from it.

**Nothing here was edited.** This is a reading of `app/static/dashboard.css`,
`app/static/dashboard.js`, `app/static/index.html` and `app/static/node-ground.svg` as they stand.

## The tokens: 0 differ

`app/static/planetai-theme.css` is byte-identical to `planetai-design/planetai-theme.css`, and
`tools/check_theme.py` holds it there — it is in `make lint` and it **fails**, so drift cannot reach
a wall screen. `signs.svg` and `kilometre-cells.json` are held the same way. All three match.

The gap is not in the values. It is in what the page reaches for.

**11 of the 34 tokens are referenced. 23 are not.** Nine of those 23 are the landing hero's global
grid (`--state-*`, `--cell-water-opacity`, `--cell-land-opacity`) and are not this surface's
business. The other **14 are**, and each one is a place the page hard-codes what the layer already
names:

| token | what it names | what the dashboard does instead |
|---|---|---|
| `--ground-cell-fill` `--ground-neighbour-opacity` `--ground-child-opacity` | A4: "the dashboard hero's ground" | baked into `node-ground.svg`, which is loaded as `<img>` — see check 5 |
| `--rho-closed` | a closed ring in the ρ row | `dashboard.css:261` reaches past it to `--rings` |
| `--loop-closed` | the same green, named after its meaning | `--rings` everywhere |
| `--sign-floor` | 12 px, the size every sign must still read at | `dashboard.css:80` draws the pill glyph at 11 px |
| `--wall-line-opacity` | "the two credit lines under a satellite frame" | `dashboard.css:254` uses the page-local `--mute` |
| `--hair-res9-opacity` `--cell-res8-weight` | the kilometre's mesh and its outlined cell | the plan card draws its own |
| `--motion-reading-fade` `--motion-reading-pulse` `--motion-day-curve-step` `--motion-ring-closed` | four motions R6 bound to four datums | not implemented at all — see check 8 |

Today most of these resolve to the same pixel, because `--rho-closed` *is* `var(--rings)` and the
baked opacities *are* the token values. That is the danger: when O8 settles and `--rho-closed`
moves, the ρ row will not follow, and nothing will say so.

---

## The eight checks

| # | check | verdict |
|---|---|---|
| 1 | hexagons — projected, never tiled | **pass** |
| 2 | projection | **pass** |
| 3 | signs — lifted or built on a grid, legible at the floor | **fail** |
| 4 | counted, not sized | **fail** |
| 5 | colour as argument | **fail** |
| 6 | provenance ink-only | **pass** |
| 7 | the stranger | **pass, with one hole** |
| 8 | solid / dashed / hairline for state | **fail** |

### 1. Hexagons — pass

R5's six violations are gone. `clip-path`, `.bighex`, `.bighex2`, `.iso` and `.glow` return zero
matches in `dashboard.css`. Every hexagon on the page comes from `node-ground.svg` and
`kilometre-cells.json`, both computed in the design repo from `h3-js` and both held byte-identical
by `check_theme.py`. Nothing on this surface draws a hexagon.

### 2. Projection — pass

`dashboard.js:1060` projects the kilometre locally:

```js
const px = ([lon, lat]) => [500 + (lon - clon) * 111320 * Math.cos(clat * Math.PI / 180) * S,
                            500 - (lat - clat) * 111320 * S];
```

The `cos(lat)` on longitude is the correction that keeps the plan from squashing on one axis — the
named local exception at kilometre scale, done right. The res-8 ground it sits on is Equal Earth
from the design repo.

### 3. Signs — fail

**`dashboard.css:80` — `.pill svg.sg{width:11px;height:11px}`.**

`--sign-floor` is 12 px: "the size every sign must still read at". The provenance glyph inside a
pill is drawn at 11. It is the most-repeated sign on the page — every figure in the Figures band
carries one — and it is the only sign below the floor. The other six sizes (`13`, `14`, `18`, `20`,
`20`, `1em`) are at or above it.

This lands on the one pair the layer already knows is fragile. O7 records that `prov-cached` is
93.7 % identical to `prov-example` **at 12 px**; O12 records `cell` against `prov-example` at
93.9 %. At 11 px both are worse, and the page is asking a reader to tell "this number was measured"
from "this number is an example" at a size the design repo has never tested.

`.rho.small svg.sg` at 13 px (`dashboard.css:262`) is the next closest and is fine.

### 4. Counted, not sized — fail

**ρ is not the offender.** `dashboard.js:863` draws one sign per ask, answered first:

```js
for (let i = 0; i < Math.min(total, 120); i++)
  s += ctx.sign(i < closed ? 'rho-closed' : 'rho-open', i < closed ? 'closed' : '');
```

That is the rule, kept. The unit row at `dashboard.js:847` is the same shape — one house per unit up
to 200, with a partial glyph for a remainder ≥ 0.25. Both pass.

**The offender is the Fab City Index row.** `dashboard.js:1470–1486`, `cellRings()`, draws four
arc gauges:

```js
const dash = hit.length ? (live ? 198 : 87) : 0;
...
<circle cx="50" cy="50" r="42" fill="none" stroke="var(--cells)" stroke-width="9"
        stroke-linecap="round" stroke-dasharray="${dash} 264" transform="rotate(-90 50 50)"/>
```

A proportion drawn as arc length on a circle — a donut gauge, which check 4 forbids outright. Its
CSS class is literally `.dial` (`dashboard.css:378`).

It is worse than a gauge, because **the arc measures nothing.** `dash` is one of three constants —
0, 87 or 198 against a circumference of 263.9 (33 %, 75 %) — chosen by a boolean. A pillar with one cell and a
pillar with nineteen draw the identical 87° sweep. The arc reads as "this pillar is about a third
answered" and means "this pillar has at least one cell, none of them live". The honest number is
already sitting in the middle of the ring: `hit.length`, at `dashboard.js:1478`.

### 5. Colour as argument — fail

Three findings, in descending order.

**(a) The hero's ground is the dark export, shown on paper.** `node-ground.svg` carries
`data-variant="dark"` on its root element and its own `<style>` block, and it is loaded as
`<img src="static/node-ground.svg">` at `dashboard.js:1322` (the Now hero) and `:1379` (the wall).

An `<img>` is an independent document. Page custom properties do not cross into it — so the file's
own `svg[data-variant="dark"]` rule wins on **both** registers, and its cells draw at `#7FA5E8`
whether the page is paper or ink.

The layer's Guards section is explicit about this exact colour:

> `#7FA5E8` measures **2.29:1** on paper `#F9F5F2`. It may appear only inside the
> `[data-theme="dark"]` block.

Measured here: 2.29:1, the same number. The hero ground on the Now view is a guard violation on
every node, every day, in daylight. It is not a stale asset — `check_theme.py` would catch that —
it is the right asset in the wrong register, reached through an element that cannot carry one.

The file paints no `class="ground"` rect, so the page's background is not overpainted; it is the
cells, the neighbours and the children that are wrong.

**(b) The wall takes the orange off the one thing that earns it.** `dashboard.css:245` sets
`.sat-bar .yr{color:var(--satellite-only)}` — the Sentinel frame's year, which the CSS comment
correctly calls "what only the satellite knows". Then `dashboard.css:256` overrides it:

```css
.wall .sat-bar .yr{color:var(--ink)}
```

On the wall — the surface R6 settled as *the* place the satellite data lives — the satellite year is
ink. The register already has an orange for this (`--satellite-only` is `#FF931E` under
`[data-theme="dark"]`, 8.06:1 on ink and well inside its guard). Orange is otherwise confined
correctly: `.unit .row svg.sat` and `.plan-legend i.sat` are the only other users, both satellite.

**(c) Two bare `#fff` literals on the green.** `dashboard.css:124` (`.askstrip button.go`) and
`:275` (`.ledger .do button`) set `color:#fff` on a `--rings` background. The file's own header says
"there is no colour literal below", and these are two. White on `#00A057` measures **3.41:1** —
below AA for 13 px text. `var(--ink)` on the same green measures 5.26:1 and follows the register.

### 6. Provenance ink-only — pass

`dashboard.css:80`: `border:1px solid var(--prov); color:var(--prov)`, square corners, no
`border-radius`, glyph plus word. `--prov` is `var(--ink)` and no colour token reaches the pill.
R5's violation 5 — `border-radius:999px` with a `--webblue` dot — is gone.

The 11 px glyph inside it is a check-3 failure, not a check-6 one: the pill is the right colour and
the right shape, drawn too small.

### 7. The stranger — pass, with one hole

The surface is built for someone who has not seen it. `index.html` is a skeleton with a comment
saying so; every sentence is written from `GET /issues`, in English, Bahasa and Spanish. The
Figures band lists every number on the page with its source and its provenance word. A refused
`SHARE_LEVEL=off` renders the node's own sentence about why rather than a blank. The plan card says
which of "no token" and "no map" it is, because "a card that goes blank reads as a broken node
rather than a private one". The wall carries an exit button because a laptop that reached it from
the nav has no other way back.

The `live` word is honest: `dashboard.js:1677` calls `staleFor(h.last_poll)`, and
`staleFor` (`:1660`) returns true when the last poll is older than twice `poll_seconds` — the pill
says `cached` past that, and a fixture render says `cached` unconditionally. Nothing wears `live`
that was not read in the last poll.

**The hole is check 4's gauge.** A stranger reads four dials, sees one a third full and one
three-quarters full, and concludes the pillars differ in how well they are answered. They do not — the
arc is a boolean. This is the one place on the page where a reader who trusts the drawing is
misled, and it is the same class of finding as the five the September audit led with.

### 8. Solid / dashed / hairline for state — fail

The state vocabulary is settled: `live` · `quiet` · `registered` · `pilot`, carried by **stroke
weight, fill and dash — never by hue**, "so it survives the ink ground". The layer carries seven
tokens for it.

The dashboard references **none of them**, and the one place it draws state, it draws it as hue and
arc: `cellRings()` again, where `live` picks both the longer sweep and `var(--cells)`. There is no
weight change, no dash, no fill difference. On a node whose cells are all quiet the row is
indistinguishable from one where they are all live except by blue arc length.

`dashboard.css:159–161` shows the page *has* the vocabulary where it does not need it — `.legend i`
draws a 1.5 px rule, `.legend i.dash` a dashed one and `.legend i.dot` a dotted one, for the day chart. It is the four-state cell
row, the place the vocabulary was written for, that ignores it.

**Motion, which R6 folded into the same rule, is inverted.** Five motion tokens name five datums.
One is bound: `--motion-satellite-year`, read properly through `getComputedStyle` at
`dashboard.js:40` rather than retyped. Four are not implemented at all — there is no reading fade,
no reading pulse, no hourly day-curve step, no ring-closing event; `dashboard.css` contains no
`transition` rule of any kind.

Meanwhile the three animations that do exist are the three with no datum behind them — all in the
Network view, all hard-coded (`dashboard.css:368–370`):

```css
svg.net .wire{...animation:netflow 3.4s linear infinite}
svg.net .dot{offset-distance:0;animation:netdot 9s linear infinite}
svg.net .halo{transform-origin:675px 180px;animation:nethalo 5s ease-out infinite}
```

3.4 s, 9 s and 5 s are not the cadence of anything the node measures. R6: "If a motion has no datum
behind it, it is deleted." The reduced-motion block at `dashboard.css:437` does stop all three, so
the frozen-reading requirement holds.

---

## The register, for the record

The wall **does** use the dark register, correctly. `dashboard.js:419` sets
`register: view === 'wall' || QS.get('theme') === 'dark' || KIOSK ? 'dark' : 'paper'`, and the
renderer writes `document.documentElement.dataset.theme = 'dark'`, which is the layer's own switch.
The paper register is the default everywhere else. The four page-local tokens in `dashboard.css`
(`--mute`, `--dim`, `--hair`, `--raise`) are each redefined under `:root[data-theme="dark"]`, and
`--mute` is a measured solid (6.30:1 on paper) rather than ink at an opacity.

The single register failure is 5(a): an asset that cannot follow the switch because of how it is
embedded.

## What to fix first

**The `.dial` arc, at `dashboard.js:1477`.** It is the only finding that makes the page state
something false to a reader who is reading it correctly, it fails three checks at once (4, 5 and 8),
and the honest value is already rendered in the middle of the ring. Deleting the two `<circle>`
elements and keeping `hit.length` fixes all three and removes code.

Then, in order: the 11 px pill glyph (`dashboard.css:80`, one number); the two `#fff`
(`dashboard.css:124`, `:275`, one token each); the wall's ink year (`dashboard.css:256`, delete the
rule). The hero ground needs `node-ground.svg` inlined rather than `<img>`-ed, or exported in both
variants — that one is a design-repo conversation, not a one-line fix.
