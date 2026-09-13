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
| 4 | counted, not sized | **pass** — the Index gauges are gone |
| 5 | colour as argument | **fail** — (a) fixed, (b) and (c) stand |
| 6 | provenance ink-only | **pass** |
| 7 | the stranger | **pass** — the hole was the gauge |
| 8 | solid / dashed / hairline for state | **fail** — motion only, now |

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

### 4. Counted, not sized — pass (was a fail; fixed)

**ρ was never the offender.** `dashboard.js` draws one sign per ask, answered first:

```js
for (let i = 0; i < Math.min(total, 120); i++)
  s += ctx.sign(i < closed ? 'rho-closed' : 'rho-open', i < closed ? 'closed' : '');
```

That is the rule, kept. The unit row is the same shape — one house per unit up to 200, with a
partial glyph for a remainder ≥ 0.25. Both pass.

**The offender was the Fab City Index row**, `cellRings()`, which drew four donut gauges:

```js
const dash = hit.length ? (live ? 198 : 87) : 0;
...
<circle ... stroke="var(--cells)" stroke-dasharray="${dash} 264" transform="rotate(-90 50 50)"/>
```

A proportion drawn as arc length, which check 4 forbids outright; the CSS class was literally
`.dial`. And the arc measured nothing — `dash` was one of three constants (0, 87, 198 against a
circumference of 263.9) chosen by a boolean.

**On node #1's own numbers it was not merely uninformative, it was inverted.** Environmental had
**5** sources and drew the 87 arc; Social and Governance had **1** each and drew 198. A reader
comparing the four rings would conclude the pillar with five times the coverage was the worst
served. The number contradicting the ring was sitting inside it the whole time.

Fixed by deleting the two `<circle>` elements and keeping `hit.length`, which is now a `.num` at the
size the old numeral could not have inside a 92 px ring. The `live` half of the arc is deliberately
not carried over — see check 8.

### 5. Colour as argument — fail (one of three fixed)

Three findings, in descending order.

**(a) The hero's ground was the dark export, shown on paper — FIXED, see below.** `node-ground.svg`
carried `data-variant="dark"` on its root element, and the page loaded it as
`<img src="static/node-ground.svg">` at `dashboard.js:1322` (the Now hero) and `:1379` (the wall).

An `<img>` is an independent document, so page custom properties do not cross into it and the
file's own `svg[data-variant="dark"]` rule won on **both** registers. Its cells drew at `#7FA5E8`
whether the page was paper or ink. The layer's Guards section is explicit about this exact colour:

> `#7FA5E8` measures **2.29:1** on paper `#F9F5F2`. It may appear only inside the
> `[data-theme="dark"]` block.

Two things about the original diagnosis were wrong, and both matter:

- **The `<img>` is deliberate, not an oversight.** `app/main.py:1459` says an inlined ground would
  leak its own `:root` paper variables into the page. Isolation is the point; the consequence — it
  cannot inherit a register — was the cost.
- **The file on disk was not the artifact at fault on most nodes.** Since v0.37,
  `GET /static/node-ground.svg` never reaches disk on a configured node: `app/main.py:1503`
  intercepts it and returns `ground.svg(lat, lon)`, drawn from `NODE_LAT`/`NODE_LON`. That
  generator's signature was `svg(lat, lon, variant="dark")` and the route called it with no
  variant. So the live path was hard-coded dark too, in the same way and for the same reason.

**The fix.** The register is now a query parameter — the only channel an `<img>` has. The three
call sites ask for the register they are in (`?variant=${ctx.register}`), the route coerces the
value to one of two literals before it reaches `data-variant="..."`, and the shipped fallback gets
its root attribute swapped for a node that has no coordinates yet. Geometry is untouched; only the
palette moves. `tests/test_ground.py` §6 holds it, and `tools/shots.mjs` mirrors the route so a
design round does not look at a stale picture.

What this changed is not only a contrast number. On the paper register most of the A4 drawing was
not visible at all — the six neighbours and seven res-9 children rendered at 2.29:1 on paper and
disappeared, leaving one ghost outline. The Fab Blue brings back the drawing that was specified.

The file paints no `class="ground"` rect, so the page's background was never overpainted; it was
the cells, the neighbours and the children that were wrong.

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

**The hole was check 4's gauge**, and it is closed. A stranger read four dials, saw one a third
full and one three-quarters full, and concluded the pillars differed in how well they were
answered — while the ring drawn smallest sat around the largest number. That was the one place on
the page where a reader who trusted the drawing was misled, and the drawing is gone.

### 8. Solid / dashed / hairline for state — fail

The state vocabulary is settled: `live` · `quiet` · `registered` · `pilot`, carried by **stroke
weight, fill and dash — never by hue**, "so it survives the ink ground". The layer carries seven
tokens for it.

The dashboard references **none of them**. It used to draw state in the forbidden way — `cellRings()`
picked a longer blue sweep when any cell in a pillar was `live` — and that is now gone rather than
translated. Nobody could read 198-against-264 as a state, so removing it costs a reader nothing;
putting it back properly needs a mark a stranger can decode, which needs a legend in three
languages, and the layer's `--state-*` tokens are stroke weights and dashes for H3 cells on a map,
not rules under a numeral. Borrowing them here would invent a dialect. **That makes this a design
round's decision, not a bug**: the dashboard still does not speak the state vocabulary anywhere.

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

**The 11 px pill glyph** (`dashboard.css:80`, one number). It is the most-repeated sign on the page
— every figure in the Figures band carries one — it is the only sign under the 12 px `--sign-floor`,
and it lands on the one pair the layer already knows is fragile: O7 and O12 record `prov-cached`,
`prov-example` and `cell` as 93.7–93.9 % identical **at 12 px**. At 11 the page asks a reader to
tell "measured" from "example" at a size the design repo has never tested.

Then: the two bare `#fff` on the green buttons (`dashboard.css:124`, `:275` — white on `#00A057` is
3.41:1, under AA for 13 px text; `var(--ink)` is 5.26:1 and follows the register), and the wall's
ink satellite year (`dashboard.css:256`, delete the rule).

**Two are done.** The `.dial` arcs are gone — they were the only finding that made the page state
something false to a reader reading it correctly, and removing them took code out. The hero ground
is done too; it needed only a register the `<img>` could be told about, not the design-repo
conversation it looked like it needed.

**What is left after those three is not a bug list.** Check 8 stands because the dashboard does not
speak the state vocabulary at all, and giving it one is a design round — a mark a stranger can read,
in three languages, not a token borrowed from a map and pointed at a numeral.

## What the guards could not see

Worth recording, because it is why this document had to be written by reading rather than by
running something. Both node-side gates were green the whole time 5(a) was true:

- **`tools/check_ui.py`** enforces the register rule — "the dark register's blue is the one that can
  be seen" — but opens exactly three files: `index.html`, `dashboard.js`, `dashboard.css`. It never
  opened `node-ground.svg`, and it cannot open `ground.py`, which draws the real one.
- **`tools/check_theme.py`** holds three frozen files byte-identical to the design repo.
  `node-ground.svg` is not one of them, and **cannot be**: the node's copy is a deliberately
  generalised placeholder (53 lines) and the design repo's names node #1's cell and stamps it
  (67 lines). Freezing it would ship `8895a4c86bfffff · THE CELL THIS NODE STANDS IN` to every node
  as a claim about where that node stands. `tests/test_ground.py` already asserts the opposite.

So "lint is green" and "the page obeys the language" are not yet the same statement. Checks 3, 4, 6
and 8 above are all outside what either gate reads.
