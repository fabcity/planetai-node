# The node dashboard, measured as a skeleton

**14 September 2026.** Part 2 of the September UX review. Part 1 walked `app/static/` as five
readers; this measures the same page as a drawing — wireframe, grid, spacing, alignment, hierarchy,
space, density and DOM, per view and per width. It changes nothing. Every number below came out of
one script, and the script is committed.

Part 1's findings are not re-opened, re-enumerated or re-argued. Where a measurement belongs to one
of its ids it is added to that id in **Measured, against Part 1's ids** and no new finding is filed.

## Header

| | |
|---|---|
| Under review | `planetai-node` `main`, tag **v0.52**, commit **`43d508d`** — Part 1's commit. `main` has not moved since Part 1: `git log 43d508d..main` is empty, so there is no delta to record. |
| What the containers serve | The two pai-clean containers now serve the **fixed** static files from `ux-p0-fixes-2026-09`, not v0.52's. Measured: `dashboard.js`, `dashboard.css` and `index.html` all differ from the working tree by hash. So every request for the document and for `/static/*` is intercepted and fulfilled from the v0.52 tree, and only the API is the containers'. `tokens.css` and `planetai-theme.css` are byte-identical either way. |
| Fixture | `?fixture=node1-2026-09-06` on `:8081`, as Part 1. Populated on `:8081`, empty on `:8082`, refused by fulfilling `/issues` with the exact 403 body `app/main.py:744` builds at `SHARE_LEVEL=off` — no setting on either node was touched. |
| Data states | Populated is measured. Empty and refused get one wireframe each at 390 and 1440 and no measurements, as the brief asks. |
| Widths | 375 / 390 / 768 / 1440, and the wall also at 1920 in the dark register. The breakpoint walk steps 320 → 1920 in 20 px steps. |
| **The spacing measure** | **The skill's 4 pt/8 dp scale.** Part 1 settled this in *Where the skill and the language disagree*: the layer names no spacing scale — "spacing comes from the programme layer and `clamp()`, not from a modular scale" — and the HANDOFF records that layout, spacing and the type scale were deliberately left alone. Read against the layer itself, `references/planetai-layer.md`'s token table carries colour, opacity, weight, dash, sign and motion tokens and **not one spacing or grid token**. The layer is silent, so by Part 1's precedence the skill's rule stands. §5 `spacing-scale`. The measure is not re-argued here; it is applied. |
| The script | `planetai-design/design/audit/2026-09/ux-review/skeleton/measure.mjs`, branch `ux-review-2026-09` |
| **Fixed since** | branch **`ux-skeleton-fixes-2026-09`** off `ux-p0-fixes-2026-09`, six commits, `0441653` at the head. **S-01, S-02, S-04, S-07 and S-11 closed.** S-12 is not, and S-01 closes at 1920 and 390 but not at 1440 — both are marked at their findings. Touched: `app/static/index.html`, `app/static/dashboard.css`, `app/static/dashboard.js`, `tools/check_ui.py`, `tests/test_check_ui.py`. `make lint` and 32/32 after every commit. The numbers in this document are v0.52's and are not rewritten; where a fix changed what a finding says, the finding carries a dated correction. |
| **One correction** | **S-11's mechanism is wrong as first filed** and is corrected in place, under its finding in Phase 1 and in the ranked table. It was filed as three undeclared widths on one node; it is a header whose shape is set by the node's own name and place string, and the correction was found by trying the fix the row recommended and watching it work on one node out of six. |
| The sheets | the same folder: **29 wireframes, 25 guide overlays, 6 contact sheets, 25 element tables** (`.json`), the breakpoint walk (`steps.json`) and the stall test |
| Browser | Playwright + the Chromium in `planetai-design/node_modules`, one device pixel, `prefers-reduced-motion: reduce` so the geometry is stable. Part 1 measured zero running animations under that flag, so nothing is hidden by it. |
| Cap height | measured from the rasterised face, not assumed from a ratio: `actualBoundingBoxAscent` of "H" on a canvas set to the element's own computed font shorthand. |
| Nothing was written | Node #1 and node #2 were not contacted. On pai-clean nothing was written: no setting was changed, no container restarted. |

---

## Ten lines

1. **At 1440 the wall puts the word `stale` below a fold nobody can scroll.** `.wall` is on two
   nested elements and `min-height:100vh` plus `padding` applies to both, so the document is
   **1,168 px on a 900 px screen**. Four things fall off the bottom: the ρ caption, the node name,
   **`stale`**, and "Answer on Telegram, not here". §5 `fixed-element-offset` is the nearest id and
   it does not fit; check written here. **S-01, P0**
2. **The wall is 128 px taller than the screen it is for at 1920, and 268 px at 1440.** Same cause:
   the wall's outer padding is double what `dashboard.css:425` declares — 115.2 px measured at 1440
   against a declared 57.6. **S-02, P1**
3. **Ten of the wall's thirteen text roles are under the three-metre floor.** `stale` has a cap
   height of **6.0 mm** and reads to 2.0 m; the four issue lines 7.5 mm, 2.5 m; the kicker 6.4 mm,
   2.1 m. Only the sentence (34.0 mm), the numeral (80.9 mm) and the why line (10.6 mm) clear 9 mm.
   **S-03, P1**
4. **The ledger's message column is 52 pixels wide on a phone.** `dashboard.css:294` drops the grid
   to `52px 1fr` and pins the button to column two; the message auto-places into the 52 px column.
   Measured at 390: text **52 px**, button **288 px**, nine lines of six to twelve characters.
   §5 `line-length-control`. **S-04, P1**
5. **So the loop band is 36.6 % of the phone page** — 3,487 px of 9,527, against the headline air
   band's 1,686 px. The least important band is twice the tallest thing that matters. **S-05, P1**
6. **No prose on the phone reaches 16 px but the hero's why line.** 193 of 199 prose text runs at
   390 are under it: `.note` 13, `.help` 13, the ledger message 14, the Figures table 12.5.
   §5 `readable-font-size`, High. **S-06, P1**
7. **The largest mark on the phone's first screen is a background drawing.** The hero's ground SVG
   is 352 × 531.8 = **187,197 px², 53.3 % of the fold**; the headline sentence is 39,977 px², 11.4 %.
   §5 `visual-hierarchy`. **S-08, P1**
8. **The type scale is 72 distinct size × weight × line-height × family combinations, and sixteen
   sizes carry more than one meaning.** 14 px carries six; 15, 13, 12.5, 12 and 11 carry three each.
   §6 `font-scale`. **S-09, P1**
9. **The header's shape is set by the node's own name and place string, not by the width.** It is a
   wrapping flex row with no query of its own, so it reflows where the content stops fitting: twice
   on the fixture, **five times** on the same node with its registry place line, and at **1,260 px**
   on a node whose name and place are both long. On three of six node shapes it gets *taller* as the
   viewport widens. §5 `breakpoint-consistency`. **S-11, P1**
10. **28 of the 41 distinct spacing values are off the 4 pt measure, and they are 60 % of all
    8,764 instances.** The largest offenders are 7 px (1,100), 6 px (1,044), 10 px (1,000) and
    14 px (708). §5 `spacing-scale`. **S-13, P1**

---
## The contact sheets

One per view, every measured width side by side, **at one scale**, drawn from the wireframes rather
than the screenshots. They live on branch `ux-review-2026-09` in
`planetai-design/design/audit/2026-09/ux-review/skeleton/`.

**[now_contact.png](../../../planetai-design/design/audit/2026-09/ux-review/skeleton/now_contact.png)** — 375 / 390 / 768 / 1440, drawn at 48 %.
The screenshot hides the proportion: drawn, two thirds of the phone page is a column of stubs six
to twelve characters wide, which is the ledger's 52 px text column: fourteen rows, ninety-four line boxes. The
same page at 1440 is 5,065 px and the same ledger reads as full lines.

**[network_contact.png](../../../planetai-design/design/audit/2026-09/ux-review/skeleton/network_contact.png)** — drawn at 77 %.
The figure that carries the whole view at 768 and 1440 is one hatched box; below 700 px it is gone
and the six facts it held return as text, which doubles the page. Drawn, the view's left edge is
visibly inboard of the header's — 35 px against 18 — at every width.

**[setup_contact.png](../../../planetai-design/design/audit/2026-09/ux-review/skeleton/setup_contact.png)** — the locked gate, drawn at 77 %.
The gate is four bars and two outlines in the top fifth of an otherwise empty page: at 1440 the
first viewport is **87.9 % unmarked**. The save bar that belongs to the pane behind the gate is
drawn at the bottom of every one of these four sheets, because it is sticky and it is not hidden.

**[setup-unlocked_contact.png](../../../planetai-design/design/audit/2026-09/ux-review/skeleton/setup-unlocked_contact.png)** — the Alerts pane, drawn at 77 %.
Below 820 px the tab rail unstacks into a row and the form becomes one column; above it the rail
takes 190 px and every field starts at 358 px while the view's own title stays at 128. Drawn, the
page has two left margins and the eye can see both.

**[wall_contact.png](../../../planetai-design/design/audit/2026-09/ux-review/skeleton/wall_contact.png)** — 375 / 390 / 768 / 1440 / 1920 dark, drawn at 47 %.
Every one of these five drawings is taller than its own viewport; the white band under the last mark
is the doubled padding. At 1920 the wall's marks occupy 87.8 % of the screen — the surface meant to
be the emptiest is the least empty one measured.

**[arrange_contact.png](../../../planetai-design/design/audit/2026-09/ux-review/skeleton/arrange_contact.png)** — drawn at 46 %.
Set beside `now_contact.png` at the same scale, the hero is 171 px taller and its sentence has
crossed into the right-hand column; the nine band bars are the only new marks and they are full
width. The page grows from 5,065 to 5,621 px at 1440 and the bar that ends the mode is the last
43 px of it.

---
## Phase 1 — the grid

### 1.1 / 1.4 The grid as rendered

Left margin is the content's own left edge, not the container's. Content width is the container
minus its inline padding. Header height is measured, and its position is the computed one.

| view | width | cols | track px | gutter | left margin | content w | header h/pos | main top | doc h |
|---|---|---|---|---|---|---|---|---|---|
| now | 375 | 1 | 297 | 18 | 18 | 339 | 148.8 static | 164.8 | 9566 |
| now | 390 | 1 | 312 | 18 | 18 | 354 | 148.8 static | 164.8 | 9527 |
| now | 768 | 1 | 672 | 23 | 26.9 | 714.2 | 71 static | 87 | 5343 |
| now | 1440 | 2 | 640 + 427 | 43.2 | 128 | 1184 | 71 static | 99 | 5065 |
| network | 375 | 1 | 339 | 12 | 18 | 339 | 148.8 static | 148.8 | 1685 |
| network | 390 | 1 | 354 | 12 | 18 | 354 | 148.8 static | 148.8 | 1666 |
| network | 768 | 1 | 714 | 12 | 26.9 | 714.2 | 71 static | 71 | 1177 |
| network | 1440 | 2 | 583 + 583 | 18 | 128 | 1184 | 71 static | 71 | 1339 |
| setup | 375 | — | — | — | 18 | 339 | 148.8 static | 148.8 | 900 |
| setup | 390 | — | — | — | 18 | 354 | 148.8 static | 148.8 | 900 |
| setup | 768 | — | — | — | 26.9 | 714.2 | 71 static | 71 | 900 |
| setup | 1440 | — | — | — | 128 | 1184 | 71 static | 71 | 900 |
| setup-unlocked | 375 | 1 | 339 | 18 | 18 | 339 | 148.8 static | 148.8 | 2587 |
| setup-unlocked | 390 | 1 | 354 | 18 | 18 | 354 | 148.8 static | 148.8 | 2566 |
| setup-unlocked | 768 | 1 | 714 | 23 | 26.9 | 714.2 | 71 static | 71 | 2309 |
| setup-unlocked | 1440 | 2 | 190 + 954 | 40 | 128 | 1184 | 71 static | 71 | 1746 |
| wall | 375 | 1 | 263 | 24 | 56 | 263 | — | 0 | 1076 |
| wall | 390 | 1 | 278 | 24 | 56 | 278 | — | 0 | 1041 |
| wall | 768 | 1 | 645 | 30.7 | 61.4 | 645.1 | — | 0 | 961 |
| wall | 1440 | 2 | 691 + 461 | 57.6 | 115.2 | 1209.6 | — | 0 | 1168 |
| arrange | 375 | 1 | 297 | 18 | 18 | 339 | 148.8 static | 164.8 | 10037 |
| arrange | 390 | 1 | 312 | 18 | 18 | 354 | 148.8 static | 164.8 | 9998 |
| arrange | 768 | 1 | 672 | 23 | 26.9 | 714.2 | 71 static | 87 | 5794 |
| arrange | 1440 | 2 | 640 + 427 | 43.2 | 128 | 1184 | 71 static | 99 | 5621 |

The header is `position: static` on every view and every width. Nothing on the page is `fixed`;
two things are `sticky` and both are in Set up. `main` starts below the header everywhere, so
§5 `fixed-element-offset` has nothing to fail against in the chrome — it fails inside Set up
instead (S-18).

### 1.2 The declared grid

Every `grid-template-columns`, container `max-width`, flex row and media query in `app/static/`.
`tokens.css` and `planetai-theme.css` declare no layout: the only media query in either is
`prefers-reduced-motion`. So every line below is `dashboard.css`.

| declared | file:line |
|---|---|
| `.wrap{max-width:1280px;padding-inline:clamp(18px,3.5vw,48px)}` — the one container for five of six views | `dashboard.css:63` |
| `.wall{min-height:100vh;padding:clamp(28px,4vw,64px)}` — the sixth, with **no max-width** | `dashboard.css:425` |
| `.bandhead` `minmax(0,1fr) minmax(0,38ch)` | `:100` |
| `.g2` `repeat(2,minmax(0,1fr))` · `.g3` `repeat(3,…)` · `.g21` `minmax(0,1.25fr) minmax(0,1fr)` | `:107`–`:109` |
| `.hero` `minmax(0,1.5fr) minmax(0,1fr)` | `:117` |
| `.askstrip` `minmax(0,1fr) auto` | `:134` |
| `.stack` `repeat(4,minmax(0,1fr))` · `.stack.mini` `repeat(4,auto)` | `:144`, `:161` |
| `.unit` `minmax(0,120px) minmax(0,1fr)` | `:176` |
| `.index .row` `110px 92px minmax(0,1fr) auto` | `:191` |
| `.sensors` `repeat(3,minmax(0,1fr))` | `:205` |
| `.ledger .al` `52px 74px minmax(0,1fr) auto` | `:281` |
| `.setup` `minmax(0,190px) minmax(0,1fr)` | `:324` |
| `.field` `minmax(0,1fr) minmax(0,300px)` | `:339` |
| `.pack` `auto minmax(0,1fr)` | `:353` |
| `.cellrow` `repeat(4,minmax(0,1fr))` | `:400` |
| `.wall .row2` `minmax(0,1.2fr) minmax(0,.8fr)` | `:426` |
| `.wall .wi` `repeat(auto-fit,minmax(200px,1fr))` — the only auto-fit in the file | `:438` |
| **34 flex rows**, of which 16 carry `flex-wrap:wrap` and therefore reflow at widths no query names | `:73`, `:74`, `:80`, `:84`, `:101`, `:123`, `:130`, `:131`, `:138`, `:154`, `:170`–`:171`, `:180`, `:198`, `:211`, `:216`, `:218`, `:225`, `:242`, `:259`, `:263`, `:275`, `:304`, `:323`, `:332`, `:336`, `:346`, `:351`, `:408`, `:413` |
| **five media queries**: `max-width:560` (5 rules), `640` (1), `700` (1), `820` (1), `900` (5) | `:78`, `:294`, `:376`, `:357`, `:103` |
| text measures, in `ch`: `.sub` 56, `.why` 52, `.help` 52, `.pack .help` 60, `.rep` 62, `.hero p.big` 24, `.wall p.big` 20, `.wall .why` 44, `.bandhead` col 2 38 | `:69`, `:129`, `:342`, `:355`, `:297`, `:125`, `:434`, `:437`, `:100` |
| **`.note` — no measure at all** | `:70` |
| **`.arrbar` — no rule at all** | — |
| **`footer .wrap` — styles an element that does not exist** | `:304` |

### 1.3 The real breakpoints

Stepped 320 → 1920 in 20 px steps on Now and Wall; the width printed is the first step at which the
value has changed, so a query at `max-width:560` shows as 580.

| observed | what changes | declared query | verdict |
|---|---|---|---|
| **500** | header **149 → 112 px** | — | **undeclared** |
| 580 | `.sensors` 1 → 2, `.unit` 1 → 2, the place line appears, header 112 → 108 | `max-width:560` `:78`, `:186`, `:208` | declared |
| **640** | header **108 → 112 px** — taller as the viewport widens | — | **undeclared** |
| 660 | `.ledger .al` 2 → 4 tracks | `max-width:640` `:294` | declared |
| **740** | header **112 → 71 px** | — | **undeclared** |
| 840 | `.index .row` 2 → 4 tracks | `max-width:820` `:200` | declared |
| 920 | `.hero` 1 → 2, `.sensors` 2 → 3, `.bandhead` 1 → 2, `.wall .row2` 1 → 2 | `max-width:900` `:103`, `:110`, `:118`, `:206`, `:427` | declared |

**No declared query is dead.** The 700 query governs Network only and was checked there separately:
`svg.net` is absent and `.netlist` present at 375 and 390, both reversed at 768 and 1440, exactly as
`:376` says. The 820 query governs Set up only and does what it says.

What fails is the other direction. **Three of the seven widths at which the skeleton changes are
named by nothing**, and all three are the header, which is a wrapping flex row (`:73`) with no query
of its own. §5 `breakpoint-consistency` asks for systematic breakpoints; the page has five good ones
and three accidents. **S-11, P1** — and the three widths above are only this node's three: see the
correction under S-11 in the findings below, which measures six node shapes, finds up to seven, and
ends with the finding closed.

The declared set — 560 / 640 / 700 / 820 / 900 — is also not the set the rule names (375 / 768 /
1024 / 1440), but it is internally consistent and derived from content, which is the better reason.
Not filed.

### Findings, Phase 1

**S-02 · P1 · High · §5 `container-width`, `viewport-units` · wall · every width.**
The wall's page padding is applied twice and its minimum height is applied twice. `index.html:99`
puts the class `wall` on both `<section class="view wall" id="wall">` and its child
`<div class="wall" id="wallbox">`, and `dashboard.css:425` sets `min-height:100vh` and
`padding:clamp(28px,4vw,64px)` on `.wall`. Measured at 1920: outer box `h=1208 pad=64 min-height
1080px`, inner box `h=1080 pad=64 min-height 1080px`. The document is therefore one viewport plus
two paddings.

| width | viewport h | document h | overflow | declared side padding | measured |
|---|---|---|---|---|---|
| 375 | 900 | 1,076 | **176** | 28 | **56** |
| 390 | 900 | 1,041 | **141** | 28 | **56** |
| 768 | 900 | 961 | **61** | 30.7 | **61.4** |
| 1440 | 900 | 1,168 | **268** | 57.6 | **115.2** |
| 1920 dark | 1,080 | 1,208 | **128** | 64 | **128** |

Fix in one sentence: scope the rule to `#wallbox` so the class is on one box.
Evidence: `wall_contact.png`, `wall_populated_1920_dark.json`; `index.html:99`, `dashboard.css:425`.

**S-01 · P0 · — · no rule fits; check written here (nearest §5 `fixed-element-offset`) · wall ·
375, 390, 1440.**
Because of S-02 the wall scrolls, and a wall does not scroll. Four text runs fall below the fold at
1440 and at 390: the ρ caption **"14 of 28 asks answered"**, the node name **`bayu-2`**, the word
**`stale`**, and the instruction **"Answer on Telegram, not here"**. At 1920 nothing is cut — the
overflow there is 128 px of empty ground — so the surface the wall was designed at is the only one
where this does not happen. A household standing in front of a laptop on the wall reads a number and
is not shown the word that says it is old. That is the P0 test: it misleads a household about its
own conditions. Cross-reference: Part 1's **L3** filed the same word as too small; this is the same
word, off the screen.
Fix in one sentence: see S-02 — one box, and the footer comes back.
Evidence: `wall_populated_1440.json` (`doc.h 1168`, `doc.vh 900`), `wall_contact.png`.

**S-11 · P1 · Medium · §5 `breakpoint-consistency` · header · content-dependent.**
See the table in 1.3. The header is the one piece of chrome present on four of six views and it
changes shape at widths nothing declares.

**Corrected on 14 September, after an attempt to fix it.** As filed above this reads as three
undeclared widths — 500, 640 and 740 — and that is what one node measures. It is the wrong
mechanism. `header .wrap` is a wrapping flex row (`dashboard.css:73`) with three children, so it
reflows where the **content** stops fitting, and two of the three children are strings the node's
own config supplies. Stepping 320 → 1400 in 10 px steps across six node shapes
(`measure.mjs header`):

| node | place chars | place px | the header reflows at | and grows at |
|---|---|---|---|---|
| node #1, as the fixture ships it | 4 | 20 | 500 730 | — |
| node #1's registry place | 37 | 222 | 500 570 590 750 940 | **570 750** |
| a long place line | 51 | 316 | 500 570 590 850 1050 | **570 850** |
| a very long place line | 78 | 317, clipped | 500 570 590 850 1050 | **570 850** |
| a longer node name | 37 | 222 | 590 910 1110 | **910** |
| both long | 51 | 316 | 570 590 660 1070 1260 | **570 1070** |

(That is the table before either cap. With both in place the last row reads **590 1040 1230**,
growing at 1040; every other row is unchanged.)

Three things follow, and none of them is in the row as filed.

**The widths are not a property of the page.** They move from 500/730 to 1,260 with the node's own
data. No media query can name them, because they are not the same number on two nodes. The fix in
the row above — "give the header a breakpoint" — was tried, at 900, an existing breakpoint: it gave
node #1 exactly one declared reflow and left the other five shapes with two to seven. It was
reverted rather than shipped.

**The growth is worse than filed, not better.** The 108 → 112 step at 640 is gone on
`ux-p0-fixes-2026-09` — `47beab1` made the node name an `<h1>` and changed the brand's height — so
on node #1 the header now never grows. It only looks fixed because `bayu-2` is a short name against
an empty place line. On the same node with its registry place string the growth returns at 570 and
750, and on a longer-named node at 910.

**Both unbounded inputs are now bounded.** Two of the header's three children are strings a keeper
types into `.env` at setup: `.brand .s` is `[city, kind]` from `/health`, and the `<h1>` is
`NODE_NAME`. (A first pass bounded only the place line, on the claim that the name was "a slug
reviewed in a pull request" — that describes `registry.json`, not what the header renders, and it
was wrong. `NODE_NAME` is a bootstrap setting like `NODE_CITY`.) The other two children are bounded
already: the five nav labels are the product's own words and the pill is one of five.

The place line is capped at 38ch — `.bandhead`'s second column — which is 316.57 px against node
#1's 222. The name is capped at 24ch — `.hero p.big`'s measure — which is 223 px against node #1's
5.7ch and node #2's 6.8ch; a descriptive `ungasan-rooftop` is 14.0ch. Neither cap clips anything
anyone has typed, and the name's clip is visual only: checked against the accessibility tree with a
31-character name, the box clips to 224 px and the heading still reads in full.

What the two caps buy, measured on the same six shapes:

| node | before both caps | after |
|---|---|---|
| a very long place line | 500 570 590 620 1030 1220, grows at 570 1030 | 500 570 590 850 1050, grows at 570 850 |
| both long | 570 590 660 1070 1260, grows at 570 1070 | 590 1040 1230, grows at 1040 |

Every other shape is unchanged, because nothing realistic reaches either cap. That is the point of a
bound rather than a fix: no `.env` value can reshape the header past 1230 again.

**Bounding was not enough, and that is the second thing this finding got wrong.** A slot that is
*sometimes* narrower than its cap is still a variable: with both strings capped the row still
reflowed at 500 and 730 on a short name and at 590, 1040 and 1230 on a long one, and still grew on
four of the six shapes. A bound moves the worst case; it does not make the geometry constant.

**S-11 is closed by giving all three children fixed slots** (`0441653`). `.brand` is 460 px — the
widest brand that still leaves room for the nav and the status inside `.wrap` at 1200. `.status`
reserves 255 px, its own widest state: `example` or `partial` beside `As of HH:MM`, measured across
the five provenance words at 151–172 px and 255 px with the timestamp. `nav.views` needed nothing:
its five labels are hardcoded English in `index.html`, which Part 1 §2.5 recorded as deliberate, so
it is 362 px in every locale. The two widths the row then reflows at are declared rather than left
to emerge from those three numbers.

| | measured across six node shapes |
|---|---|
| before | 500 730 · 500 570 590 750 940 · 500 570 590 850 1050 · 590 910 1110 · 590 1040 1230, growing as the viewport widened on four of the six |
| after | **800 and 1210 on every one of them**, three heights, and it never grows |

The header's shape is a function of the viewport width and nothing else. **S-11 closed.**

Two costs, both recorded rather than hidden. A long `NODE_NAME` now squeezes the place line inside
the fixed slot instead of widening the header — the place clips at 219 px rather than 317 px on a
25-character name — and both strings keep their full text in `title`. And the 460 px slot is mostly
empty on node #1, whose brand needs 113 px.

**This does not touch S-12.** The slots reserve width, not height: at 390 the three rows stack and
the status row still goes from nothing to 25 px when `/health` lands, taking the page with it. That
was briefly written into the CSS as a claim that this closed S-12; it was measured and it does not.

Fix in one sentence: done — `.brand` 460 px, `.status` 255 px, the two reflows declared.
Evidence: `an_header.txt` (`measure.mjs header`); `dashboard.css:91`, `:99`, `:113`.
Closed: `0441653` on `ux-skeleton-fixes-2026-09`.

**S-14 · P1 · Medium · §5 `container-width` · all · 1440.**
Six views, five left edges. Now and Arrange start at 128, Network and locked Set up at 153, unlocked
Set up at 358, the wall at 115. Measured against the header's own inner edge:

| view | 375 | 390 | 768 | 1440 | why |
|---|---|---|---|---|---|
| now, arrange | 0 | 0 | 0 | 0 | content is a direct child of `.wrap` |
| network, setup (locked) | **+17** | **+17** | **+17** | **+25** | content sits inside `.card{padding:clamp(16px,2vw,24px)}` `:97` plus its 1 px border |
| setup (unlocked) | 0 | 0 | 0 | **+230** | the tab rail takes column one `:324`; the view's own `<h2>` and blurb stay at 128 while every field starts at 358 |
| wall | — | — | — | — | no header, and its own container — see S-23 |

Switching Now → Network moves every line on the page 17 px right on a phone and 25 px on a laptop.
The unlocked Set up case is a sidebar and is defensible; its title and blurb staying behind at 128 is
not, because they belong to the pane.
Fix in one sentence: put the view's own heading in the column its content is in, and let a card's
padding not stand in for a page margin.
Evidence: `network_contact.png`, `setup-unlocked_contact.png`, the guide overlays at 1440.

**S-23 · P2 · Medium · §5 `container-width` · wall · every width.**
Two container systems. `.wrap` caps content at 1,280 px (`:63`); the wall has no cap, so its content
is **1,209.6 px at 1440** against every other view's 1,184, and **1,792 px at 1920**. A sentence
capped at `20ch` does not notice; the four wall index columns, which are `repeat(auto-fit,
minmax(200px,1fr))` (`:438`) inside a 1,100 px cap, do.
Fix in one sentence: one container rule, or say in the CSS why the wall has its own.
Evidence: the grid table above; `dashboard.css:63`, `:425`, `:438`.

---
## Phase 2 — spacing and rhythm

### 2.1 The histogram

Every `margin`, `padding`, `row-gap` and `column-gap` on every visible element, over all 25
populated renders. Zero is not counted.

**41 distinct values. 13 sit on the 4 pt measure and 28 do not. Of 8,764 instances, 5,265 — 60 % —
are off it.**


| px | n | on 4 pt | where (first few) |
|---|---|---|---|
| 2 | 624 | ✗ | pill prov·pt, pill prov·pb, chip·pt, chip·pb, tabs·rg, tabs·cg |
| 2.9 | 8 | ✗ | mono·mr, mono·ml |
| 3 | 48 | ✗ | src·mt |
| 3.2 | 8 | ✗ | mono·mr, mono·ml |
| 4 | 356 | ✓ | rho small·rg, rho small·cg, src·mt, small·ml, kits·rg, rho·rg |
| 4.6 | 2 | ✗ | mono·mr, mono·ml |
| 5 | 200 | ✗ | v·rg, v·cg, cap mono·pt |
| 5.4 | 4 | ✗ | mono·mr, mono·ml |
| 6 | 1044 | ✗ | pill prov·pl, pill prov·rg, pill prov·cg, v·mt, i·mr, dot·mr |
| 7 | 1100 | ✗ | pill prov·pr, button·pt, button·pb, td·pt, td·pb, mono·pt |
| 8 | 1282 | ✓ | on·pt, on·pb, button·pt, button·pb, chips·rg, chips·cg |
| 8.6 | 2 | ✗ | mono·mr, mono·ml |
| 9 | 80 | ✗ | button·pt, button·pb, on·pt, on·pb, btn ghost·pt, btn ghost·pb |
| 9.6 | 2 | ✗ | big·mt |
| 10 | 1000 | ✗ | status·rg, status·cg, row·rg, col·pr, col·pb, scale·mt |
| 10.8 | 2 | ✗ | cellrow·rg, cellrow·cg |
| 11 | 8 | ✗ | cap mono·pb |
| 12 | 1049 | ✓ | brand·rg, brand·cg, k·rg, k·cg, index·mt, row·pt |
| 12.3 | 1 | ✗ | net·mt |
| 12.8 | 3 | ✗ | why·mt |
| 14 | 708 | ✗ | big·mt, why·mt, k·rg, k·cg, sensor·pr, sensor·pl |
| 16 | 550 | ✓ | wrap·rg, wrap·cg, on·pr, on·pl, button·pr, button·pl |
| 18 | 296 | ✗ | wrap·pt, wrap·pr, wrap·pb, wrap·pl, hero·rg, hero·cg |
| 18.4 | 1 | ✗ | why·mt |
| 20 | 45 | ✓ | hero·pt, hero·pr, hero·pb, hero·pl, net·mt, cellrow·rg |
| 22.5 | 1 | ✗ | big·mt |
| 23 | 23 | ✗ | hero·rg, hero·cg, bandhead·cg, setup·rg, setup·cg, rho·mt |
| 24 | 108 | ✓ | card ringcard·pt, card ringcard·pr, card ringcard·pb, card ringcard·pl, card·pt, card·pr |
| 26 | 12 | ✗ | gate card·mt, setup·mt |
| 26.9 | 20 | ✗ | wrap·pr, wrap·pl |
| 28 | 22 | ✓ | hero·mt, view wall on·pt, view wall on·pr, view wall on·pb, view wall on·pl, wall·pt |
| 30 | 42 | ✗ | band quiet·pt, band·pt |
| 30.7 | 12 | ✗ | view wall on·pt, view wall on·pr, view wall on·pb, view wall on·pl, wall·pt, wall·pr |
| 32 | 4 | ✓ | wi·cg |
| 36 | 8 | ✓ | hero·pt, hero·pr, hero·pb, hero·pl |
| 40 | 19 | ✓ | bandhead·cg, setup·rg, setup·cg, rho·mt |
| 43.2 | 4 | ✗ | hero·rg, hero·cg |
| 48 | 34 | ✓ | wrap·pr, wrap·pl, band quiet·pt, band·pt |
| 56 | 2 | ✓ | wi·mt, foot·mt |
| 57.6 | 10 | ✗ | view wall on·pt, view wall on·pr, view wall on·pb, view wall on·pl, wall·pt, wall·pr |
| 80 | 20 | ✓ | wrap·mr, wrap·ml |

**Per view**

| view | distinct | off-measure distinct | off-measure instances |
|---|---|---|---|
| now | 26 | 15 | 2135 |
| network | 17 | 9 | 150 |
| setup | 17 | 9 | 123 |
| setup-unlocked | 20 | 11 | 408 |
| wall | 22 | 13 | 82 |
| arrange | 26 | 15 | 2367 |

Read it in three groups.

**Integers that are simply off the scale.** 7 px (1,100 instances), 6 px (1,044), 10 px (1,000),
14 px (708), 2 px (624), 5 px (200), 18 px (296), 3, 9, 11, 26, 30. Where they come from:

| px | n | set at |
|---|---|---|
| 7 | 1,100 | `.pill{padding:2px 7px 2px 6px}` `dashboard.css:86` · `table.figs td{padding:7px 10px 7px 0}` `:302` · `.ledger .do button{padding:7px 12px}` `:292` · `.tag{padding:2px 7px}` `:356` |
| 6 | 1,044 | `.pill{gap:6px}` `:86` · `.unit{gap:6px 14px}` `:176` · `.stack .v{margin-top:6px}` `:154` · `.sensor .story{margin-top:6px}` `:215` · `.sensor .kits{margin-top:6px}` `:218` · `.field .help{margin-top:6px}` `:342` |
| 10 | 1,000 | `.status{gap:10px}` `:84` · `.stack .col{padding:12px 10px 10px 0}` `:145` · `.scale{margin-top:10px}` `:166` · `.index .row{gap:10px 18px}` `:191` · `.sensor .top{gap:10px}` `:211` · `.switch{gap:10px}` `:346` · `.peer{padding:10px 0}` `:413` · `.plan-legend{padding:10px 12px}` `:242` |
| 14 | 708 | `.hero p.big{margin-top:14px}` `:125` · `.hero .why{margin-top:14px}` `:129` · `.askstrip{padding:14px 16px}` `:134` · `.unit{gap:6px 14px}` `:176` · `.bandhead .k{gap:14px}` `:101` · `.index .mini{gap:14px}` `:198` · `.sensor{padding:12px 14px}` `:210` · `button{padding:8px 14px}` `:61` |
| 2 | 624 | `.pill{padding:2px …}` `:86` · `.chip{padding:2px 8px}` `:95` · `.tabs{gap:2px}` `:332` · `.peers .k{margin-top:2px}` `:412` |
| 5 | 200 | `.stack .v{gap:5px}` `:154` · `.plan .cap{padding:5px 12px}` `:240` · `.pack .help{margin-top:5px}` `:355` |
| 18 | 296 | `.wrap{padding-inline:clamp(18px,…)}` `:63` at 375/390 · `.hero .side{gap:18px}` `:131` · `.index .row{gap:10px 18px}` `:191` |
| 3 | 48 | `.field .src{margin-top:3px}` `:341` |
| 9 | 80 | `.tabs button{padding:9px 12px}` `:333` |
| 11 | 8 | `.plan .cap:last-child{padding-bottom:11px}` `:241` |
| 26 | 12 | `.gate{margin-top:26px}` `:319` · `.setup{margin-top:26px}` `:324` · `footer .wrap{padding-block:26px 40px}` `:304` |
| 30 | 42 | `.band{padding-top:clamp(30px,…)}` `:99` at 375/390 |

**Fractional values, which are a `clamp()` caught between its ends.** 2.9, 3.2, 4.6, 5.4, 8.6, 9.6,
10.8, 12.3, 12.8, 18.4, 22.5, 23, 26.9, 30.7, 43.2, 57.6. There are **30 distinct `clamp()`
expressions** in `dashboard.css` and no two share a triple. A clamp is one declaration, so this is
not thirty mistakes; it is one decision — the page interpolates its spacing rather than stepping it
— and the consequence is that at 768 the hero's gutter is 23 px and at 1440 it is 43.2 px and
neither is a value anyone chose.

**Values that are on the measure.** 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 80. Thirteen of
them, and they carry 3,499 of the 8,764 instances.

**S-13 · P1 · Medium · §5 `spacing-scale` · all views, all widths.**
The rule asks for a 4 pt incremental system. The page has one for 40 % of its spacing and a second,
denser system — 2, 3, 5, 6, 7, 9, 10, 11, 14, 18, 26, 30 — for the other 60 %, plus sixteen values
that exist only at one viewport width. The layer names no scale, so nothing here contradicts the
language; it contradicts the only measure available.
Fix in one sentence: name a scale in `planetai-layer.md`, or state in `dashboard.css` that spacing
is interpolated and not stepped.
Evidence: the table above; every `_guides.png`.

### 2.2 Vertical rhythm


**band to band (the next band pads itself)** — 2 distinct values: 30, 48 px
| px | n | occurrences (first 5) |
|---|---|---|
| 30 | 42 | now@375 band-air; now@375 band-coast; now@375 band-heat; now@375 band-land; now@375 place |
| 48 | 14 | now@1440 band-air; now@1440 band-coast; now@1440 band-heat; now@1440 band-land; now@1440 place |

**band to band (box gap)** — 1 distinct value: 0 px
| px | n | occurrences (first 5) |
|---|---|---|
| 0 | 33 | now@375 band quiet -> band; now@375 band -> band quiet; now@375 band quiet -> band quiet; now@375 band quiet -> band; now@375 band -> band |

**kicker to sentence** — 5 distinct values: 8, 9.6, 12, 14, 22.4 px
| px | n | occurrences (first 5) |
|---|---|---|
| 8 | 32 | now@375 bandhead; now@375 bandhead; now@375 bandhead; now@375 bandhead; now@390 bandhead |
| 9.6 | 4 | wall@375 view wall on; wall@375 wall; wall@390 view wall on; wall@390 wall |
| 12 | 2 | wall@768 view wall on; wall@768 wall |
| 14 | 8 | now@375 hero; now@390 hero; now@768 hero; now@1440 hero; arrange@375 hero |
| 22.4 | 2 | wall@1440 view wall on; wall@1440 wall |

**sentence to why** — 4 distinct values: 8, 12.8, 14, 18.4 px
| px | n | occurrences (first 5) |
|---|---|---|
| 8 | 12 | now@375 bandhead; now@375 bandhead; now@390 bandhead; now@390 bandhead; now@768 bandhead |
| 12.8 | 6 | wall@375 view wall on; wall@375 wall; wall@390 view wall on; wall@390 wall; wall@768 view wall on |
| 14 | 8 | now@375 hero; now@390 hero; now@768 hero; now@1440 hero; arrange@375 hero |
| 18.4 | 2 | wall@1440 view wall on; wall@1440 wall |

**value to source line** — 1 distinct value: 4 px
| px | n | occurrences (first 5) |
|---|---|---|
| 4 | 64 | now@375 stack .col; now@375 stack .col; now@375 stack .col; now@375 stack .col; now@375 stack .col |

**hero to index** — 2 distinct values: 12, 18 px
| px | n | occurrences (first 5) |
|---|---|---|
| 12 | 6 | now@375; now@390; now@768; arrange@375; arrange@390 |
| 18 | 2 | now@1440; arrange@1440 |

**card to card in a row** — 3 distinct values: 10, 14, 18 px
| px | n | occurrences (first 5) |
|---|---|---|
| 10 | 4 | now@768 sensor; now@768 sensor; arrange@768 sensor; arrange@768 sensor |
| 14 | 8 | now@1440 sensor; now@1440 sensor; now@1440 sensor; now@1440 sensor; arrange@1440 sensor |
| 18 | 3 | now@1440 card fc; network@1440 card; arrange@1440 card fc |

Read as relationships rather than as values:

| relationship | values | one rule? | where |
|---|---|---|---|
| band to band | **0 px between the boxes; 30 or 48 px inside the next band's own padding** | yes — `.band{padding-top:clamp(30px,3.6vw,48px)}` `:99` | clean |
| value to its source line, in the Stack | **4 px**, 64 occurrences, one value | yes — `.stack .src{margin-top:4px}` `:159` | clean |
| hero to index | 12 px below 1333, 18 above | yes — `.index{margin-top:clamp(12px,1.5vw,18px)}` `:190` | clean |
| **kicker to sentence** | **8, 9.6, 12, 14, 22.4** | **no — three rules** | `.hero p.big{margin-top:14px}` `:125`; `.bandhead{gap:8px …}` `:100`; `.wall p.big{margin-top:.3em}` `:434` of a clamped size |
| **sentence to why** | **8, 12.8, 14, 18.4** | **no — three rules** | `.hero .why{margin-top:14px}` `:129`; the bandhead's own 8 px row gap `:100`; `.wall .why{margin-top:.8em}` `:437` |
| **card to card in a row** | **10, 14, 18** | **no — two rules** | `.sensors{gap:clamp(10px,1.2vw,14px)}` `:205`; `.grid{gap:clamp(12px,1.5vw,18px)}` `:106` |

**S-16 · P2 · Medium · §6 `whitespace-balance`, §5 `spacing-scale` · all views.**
Three of the six recurring relationships are expressed with more than one value, and in each case
the reason is that the same relationship is set by a different rule in a different container rather
than by one rule about the relationship. The kicker-to-sentence distance is 14 px in the hero, 8 px
in a band head immediately below it, and an em multiple on the wall. A reader moving down the Now
page meets both the 14 and the 8 within 700 px.
Fix in one sentence: name the relationship once and let the containers inherit it.
Evidence: the rhythm tables above; `dashboard.css:100`, `:125`, `:129`, `:205`, `:106`, `:434`.

### 2.3 Line length and line height

Measured per text block, per width, with the exact break offsets — the characters on each line are
counted by walking the range, not estimated. 243 wrapping blocks. `line-length-control` wants 35–60
characters on mobile and 60–75 on desktop. `line-height` is applied to prose only, as the brief
scopes it: sentences, why paragraphs, help lines, the ledger message, the report, table cells.
Kickers, chips, numerals, state words and display sentences are excluded.

**Line height: no prose block fails.** Every one measures 1.5, 1.55 or 1.6. `:69`, `:70`, `:129`,
`:286`, `:297`, `:300`, `:342` all sit in the band.

**Line length: 123 of the 243 blocks fall outside it.** The worst by block:

| block | worst max cpl | where | measure declared |
|---|---|---|---|
| **`.note`** | **120** | Now @ 768 | **none** — `dashboard.css:70` |
| `.sub` | 80 | Set up @ 768 | 56ch `:69` |
| `#pblurb.sub` | 77 | Set up unlocked @ 768 | 56ch `:69` |
| `.help` | 77 | Set up unlocked @ 768 | 52ch `:342` |
| `.big` | 65 | Now @ 768 | 24ch `:125` |
| `.wall .ln` | 57 | Wall @ 768 | none |
| `.line` (index row) | 57 | Now @ 375 | none |
| **`.txt`** (ledger) | **12, over 9 lines** | Now @ 375 | none — and see S-04 |

**S-07 · P1 · Medium · §5 `line-length-control` · Now, Network · 768 and 1440.**
`.note` is the class every empty state, every instruction and every source line uses, and it is the
one text class with no measure. `.sub` has 56ch, `.why` 52ch, `.help` 52ch, `.pack .help` 60ch,
`.rep` 62ch. `.note` has nothing, so it fills whatever box it is in: **120 characters per line** at
768 on Now, **118** on Network, 94 at 1440. Sixty-two blocks on the four widths.
Fix in one sentence: give `.note` the measure the four classes beside it already have.
Evidence: `lines.txt`; `dashboard.css:70` against `:69`, `:129`, `:297`, `:342`, `:355`.

**S-04 · P1 · High · §5 `line-length-control`; §5 `content-priority` · Now · 375, 390.**
At 640 px and below, `dashboard.css:294` drops the ledger row to `grid-template-columns:52px 1fr`
and `:295` pins the action to column two. The row has four children — `.when`, `.iss`, `.txt`,
`.do` — and only the last is placed, so the third auto-places into **column one, which is 52 px
wide**. Measured at 390: `.txt` width **52 px** on all fourteen rows, `.do` width **288 px**;
94 line boxes at 6 to 12 characters. The button gets five and a half times the room the sentence
gets.
Fix in one sentence: place `.txt` in column two, spanning, the way `.do` already is.
Evidence: `now_contact.png` (the stub column is the lower two thirds of the 375 and 390 drawings),
`now_populated_390_wire.png`, `now_populated_390.json`; `dashboard.css:294`.

**S-06 · P1 · High · §5 `readable-font-size` · all views · 375, 390.**
The rule is a 16 px floor for body text on a phone. Measured at 390 over Now, Network, Set up and
the wall: **193 of 199 prose text runs are under it**, and the six that are not are the hero's why
line.

| prose class | px | runs at 390 | file:line |
|---|---|---|---|
| `.story` | 12.5 | 6 | `:215` |
| `.note` | 13 | 50 | `:70` |
| `.help` | 13 | 21 | `:342` |
| `.sub` | 14 | 13 | `:69` |
| **`.txt`** (the ledger message) | 14 | **94** | `:286` |
| `.line` (index row) | 14.5 | 6 | `:196` |
| `.why` | 15.5 | 2 | `:129` |
| `.why` (hero) | **16** | 6 | `:129` |

Counting every text run and not only prose, it is 609 of 623 — 98 %. The Figures table is 12.5 px
(`:300`), every pill and kicker 11 px (`:86`, `:65`), the ledger timestamp 12 px (`:283`).
Fix in one sentence: raise the body classes to 16 px on the phone and let the mono labels stay small.
Evidence: `now_populated_390.json`, `network_populated_390.json`, `setup-unlocked_populated_390.json`.

---
## Phase 3 — alignment

### 3.1 Edges

A guide is drawn at every left edge three or more elements share. The dominant edge is the one the
most elements sit on.

| view | 375 | 390 | 768 | 1440 | shared edges at 1440 |
|---|---|---|---|---|---|
| now | 18 (233 els) | 18 (233) | 27 (177) | 128 (126) | **36** |
| network | 35 (55) | 35 (55) | 44 (36) | 153 (31) | 8 |
| setup (locked) | 18 (13) | 18 (13) | 27 (8) | 153 (7) | 5 |
| setup (unlocked) | 18 (105) | 18 (106) | 27 (98) | 358 (66) | 5 |
| wall | 56 (29) | 56 (29) | 61 (20) | 115 (15) | 6 |
| arrange | 18 (249) | 18 (249) | 27 (193) | 128 (142) | **40** |

**At 390 there is one left margin on Now and it holds.** 233 of 596 elements sit on 18 px and the
next-largest edge is 33 px (46 elements), which is the inside of a card. Five elements sit at 19 px
— the active nav button and the hero's ground drawing — and all five are one pixel inboard because
their parent has a 1 px border. That is correct behaviour, measured and not filed.

The misses that matter are between views, not within one, and they are S-14 in Phase 1.

Thirty-six distinct shared edges on Now at 1440 is the number worth holding: with a 2-column hero, a
4-column stack, a 4-column index row, a 3-column sensor grid and a 4-column figures table, the page
does not have a column grid at all — it has nine independent grids that happen to share an outer
margin. Nothing in the layer asks for a column grid, so this is recorded and not filed.

### 3.2 Baselines

Clean, and worth saying because it is the one thing in this document that is exactly right.

| check | measured | rule |
|---|---|---|
| the Stack's numeral against its unit label | **0.0 px** across all 22 rows at 390 and at 1440 — `19.2px "5"` and `11px "µg/m³"` share a baseline to the tenth of a pixel | `.stack .v{align-items:baseline}` `dashboard.css:154` |
| the wall's kicker, state word and reason | **0.0 px** — all three on one baseline at 1920 | `.wall .k{align-items:baseline}` `:433` |
| the provenance pill against the text beside it | the pill box spans y..y+20 and its own text baseline sits at y+14, consistently, at every occurrence | `.pill{align-items:center;vertical-align:middle}` `:86` |
| the index rows' state word | **one column**: every row's state word starts at x=132 at 390 and x=256 at 1440 | `.index .row` `:191` |

No finding.

---

## Phase 4 — hierarchy

### 4.1 The type scale in use

**72 distinct size × weight × line-height × family combinations across the six views and four
widths**; 50 at 375 and 390, 53 at 768, 57 at 1440. The count is inflated by `clamp()` — fourteen of
the 30 distinct clamps in the file set a type size — but the sizes below are what a reader actually meets.

| px | weight | line-height | family | instances | on (first few) |
|---|---|---|---|---|---|
| 172.8 | 900 | 134.8 | JetBrains Mono | 1 | B.mono |
| 92.16 | 900 | 71.9 | JetBrains Mono | 1 | B.mono |
| 89.6 | 700 | 69.9 | JetBrains Mono | 2 | B.mono |
| 74.88 | 700 | 83.9 | Funnel Sans | 5 | P.big |
| 64 | 900 | 49.9 | JetBrains Mono | 2 | B.mono |
| 53.76 | 700 | 41.9 | JetBrains Mono | 2 | B.mono |
| 48 | 700 | 37.4 | JetBrains Mono | 4 | B.mono |
| 40 | 700 | 48 | Funnel Sans | 10 | P.big |
| 39.94 | 700 | 44.7 | Funnel Sans | 5 | P.big |
| 34 | 700 | 34 | JetBrains Mono | 4 | SPAN.num |
| 32 | 700 | 35.8 | Funnel Sans | 11 | P.big |
| 29.6 | 800 | 33.2 | Funnel Sans | 21 | P.big, H2.t, H3.t, H3#ptitle.t |
| 29.6 | 900 | 33.2 | JetBrains Mono | 6 | B.mono |
| 27.2 | 400 | 27.2 | JetBrains Mono | 4 | SPAN.num |
| 27.2 | 700 | 27.2 | JetBrains Mono | 12 | SPAN.num |
| 26 | 700 | 26 | JetBrains Mono | 12 | SPAN.num |
| 24.8 | 700 | 29.8 | Funnel Sans | 30 | P.big |
| 23.04 | 400 | 35.7 | Figtree | 2 | P.why |
| 21.6 | 800 | 24.2 | Funnel Sans | 79 | P.big, H2.t, H3.t, H3#ptitle.t |
| 21.6 | 900 | 24.2 | JetBrains Mono | 18 | B.mono |
| 20.8 | 400 | 20.8 | JetBrains Mono | 12 | SPAN.num |
| 20.8 | 700 | 20.8 | JetBrains Mono | 36 | SPAN.num |
| 19.2 | 700 | 19.2 | JetBrains Mono | 48 | SPAN.num |
| 18.72 | 700 | normal | Funnel Sans | 4 | SPAN.name |
| 18.4 | 400 | 18.4 | JetBrains Mono | 8 | SPAN.num |
| 18.4 | 700 | 18.4 | JetBrains Mono | 24 | SPAN.num |
| 17 | 700 | 26.4 | Funnel Sans | 2 | text |
| 17 | 800 | normal | Funnel Sans | 20 | B#nodename |
| 16.56 | 400 | 25.7 | Figtree | 10 | SPAN.ln |
| 16 | 400 | 24.8 | Figtree | 170 | P.why, BUTTON#btn-unlock.btn, BUTTON#btn-back.btn, BUTTON#btn-save.btn, BUTTON |
| 16 | 700 | 16 | JetBrains Mono | 32 | SPAN.num |
| 15.5 | 400 | 24 | Figtree | 13 | P.why |
| 15 | 400 | 23.3 | Figtree | 12 | text |
| 15 | 600 | normal | Figtree | 48 | LABEL |
| 15 | 700 | normal | Funnel Sans | 34 | SPAN.name, DIV.netnode |
| 14.5 | 400 | 22.5 | Figtree | 42 | SPAN.line |
| 14 | 400 | 21 | Figtree | 444 | SPAN.txt |
| 14 | 400 | 21.7 | Figtree | 88 | DIV.sub, P.sub, SPAN#savenote.sub, P#pblurb.sub |
| 14 | 400 | 21.7 | monospace | 12 | CODE |
| 14 | 500 | normal | Figtree | 36 | BUTTON, BUTTON.btn |
| 14 | 500 | 19.6 | JetBrains Mono | 3 | SPAN.issue, SPAN.state, SPAN |
| 14 | 700 | normal | Figtree | 4 | BUTTON.on |
| 14 | 700 | normal | Funnel Sans | 12 | SPAN.name |
| 13.5 | 400 | 20.9 | Figtree | 40 | SPAN |
| 13.5 | 500 | normal | Figtree | 100 | BUTTON.on, BUTTON |
| 13.5 | 600 | normal | Figtree | 58 | SPAN.n |
| 13.33 | 400 | 20.7 | Figtree | 32 | SMALL |
| 13 | 400 | 19.5 | Figtree | 276 | P.note, P#index-note.note |
| 13 | 400 | 20.2 | Figtree | 112 | SPAN#nodeplace.s, DIV.help, SPAN.ln |
| 13 | 600 | 20.2 | Figtree | 16 | BUTTON |
| 13 | 700 | 19.5 | JetBrains Mono | 2 | SPAN.note |
| 12.96 | 500 | normal | JetBrains Mono | 3 | SPAN, SPAN.st |
| 12.5 | 400 | 18.1 | Figtree | 48 | DIV.story |
| 12.5 | 400 | 19.4 | Figtree | 382 | TD |
| 12.5 | 400 | 19.4 | JetBrains Mono | 104 | TD.mono |
| 12.5 | 600 | normal | Figtree | 32 | SPAN.done |
| 12 | 400 | 17.4 | Figtree | 80 | DIV.src |
| 12 | 500 | 19.2 | JetBrains Mono | 224 | SPAN.when |
| 12 | 500 | normal | JetBrains Mono | 44 | SPAN, SPAN.st |
| 12 | 600 | normal | JetBrains Mono | 14 | B |
| 11 | 400 | 17.1 | JetBrains Mono | 18 | text |
| 11 | 500 | 14.3 | JetBrains Mono | 312 | SPAN.pill, SPAN.chip |
| 11 | 500 | 15.4 | JetBrains Mono | 247 | SPAN.state, SPAN, SPAN.issue, DIV.k, DIV.lab |
| 11 | 500 | normal | JetBrains Mono | 485 | SMALL, SPAN.state, SPAN, SPAN.more, SPAN.meta |
| 11 | 500 | 17.6 | JetBrains Mono | 64 | SPAN.iss |
| 11 | 700 | 15.4 | JetBrains Mono | 8 | SPAN.issue |
| 11 | 700 | 17.6 | JetBrains Mono | 48 | SPAN.iss |
| 10.5 | 400 | 16.3 | JetBrains Mono | 2 | text |
| 10.5 | 500 | 14.7 | JetBrains Mono | 96 | DIV.k |
| 10.5 | 500 | normal | JetBrains Mono | 72 | TH, SPAN.src |
| 10 | 400 | 15.5 | JetBrains Mono | 56 | text |
| 10 | 500 | normal | JetBrains Mono | 12 | SPAN.st |

**One size, more than one meaning**

**S-09 · P1 · Medium · §6 `font-scale`; Typography/Heading Clarity in the skill's dataset (there is
no `heading-clarity` id in the Quick Reference) · all views.**
The rule wants a consistent scale — the example given is 12 14 16 18 24 32 — where a size means one
thing. Sixteen sizes carry more than one weight-and-family combination. **14 px carries six**:
Figtree 400 (the ledger message, `.sub`), Figtree 500 (a button), Figtree 700 (the active nav
button), Funnel Sans 700 (an index name), JetBrains Mono 500 (the wall kicker), and a `monospace`
fallback (`<code>` in the Set up blurb, which reaches no declared family at all). 15, 13, 13.5, 12.5,
12 and 11 carry three each. In the other direction, one thing gets two sizes: `.k` is 11 px on Now,
10.5 px inside a stack column (`:153`) and 14 px on the wall (`:433`).
Fix in one sentence: name the levels, and make the exceptions say which level they are an exception
to.
Evidence: the table above; `dashboard.css:65`, `:69`, `:81`, `:153`, `:193`, `:286`, `:433`.

### 4.2 Heading structure

The accessibility tree against the visual outline, at 390 and 1440.

| view | the browser's outline | the visual outline, largest first |
|---|---|---|
| **now** | *(no h1)* → h2 → h2 → h2 → h2 | the hero numeral **89.6 px `<b>`**, the hero sentence **40 px `<p>`**, the four band sentences 29.6 px `<h2>`, the stack numerals 27.2 px `<span>` |
| **network** | *(no h1)* → h2 | the four Index tallies **34 px `<span>`**, the view title 29.6 px `<h2>` |
| **setup** | *(no h1)* → h2 → h3 | the view title 29.6 px `<h2>`, the gate title 21.6 px `<h3>` |
| **wall** | *(no h1, no heading of any level)* | the numeral 176 px, the sentence 80 px, both `<p>`/`<b>` |
| **arrange** | as Now | as Now |

**S-10 · P1 · Medium · §1 `heading-hierarchy` · Now, Network, Wall · all widths.**
Part 1's **H2** already holds that there is no `<h1>` and it is fixed on the fix branch; this is the
part of the structure that survives that fix. On Now the outline begins at h2 with the *second*
largest thing on the page and the largest — the hero sentence, 40 px with an 89.6 px numeral inside
it — is a `<p>` outside the outline entirely. The four band sentences are sibling h2s with nothing
above them. On Network the largest type on the view, the four Index tallies at 34 px, are `<span>`s.
On the wall there is no heading of any level at all, so a screen reader given the wall view is given
a document with no structure.
Fix in one sentence: the hero sentence is the page's heading; make it one, and make the band
sentences the level under it.
Evidence: `an_headings.txt`; `dashboard.js:` the `sentence` component writes `<p class="big">`.

### 4.3 Reading order

The first viewport at 390 and 1440: the order a reader meets elements by position — rows first, then
left to right within a row — against DOM order, against the language's order of importance (the
headline condition, the ask under it, when this was last true, then everything else).

**At 390.** Position and DOM agree for the first eleven elements and then swap two: the numeral
(`B.mono`, DOM 13) is met before the sentence that contains it (`P.big`, DOM 12), because the
numeral is set at `line-height:.78` and `vertical-align:-.06em` (`dashboard.css:126`) and its line
box starts 13 px above the paragraph's. That is the intended effect and not a divergence worth
filing. Against the language's order: the headline condition arrives first, **the ask does not
arrive at all** — the ask strip is `hidden` on this fixture — and *when* arrives only in the header
pill, which Part 1 filed as H7.

**At 1440.** Two real divergences. The ρ row (`DIV.rho`) is met **13th by position and 28th in the
DOM** — it is in the hero's right column, level with the kicker, and fifteen elements later in
source order. The index note (`P.note`) is met 16th and is 29th. Both are the two-column hero
placing later markup higher on the screen.

**S-08 · P1 · Medium · §5 `visual-hierarchy`, `content-priority` · Now · 375, 390, 768, 1440.**
The rule says establish hierarchy by size. Ranked by pixel area clipped to the first viewport, with
the document scaffold excluded:

| 390 | element | px² | share of the fold |
|---|---|---|---|
| 1 | **the hero's ground drawing** (`.hero .bg img`) | **187,197** | **53.3 %** |
| 2 | the hero's left column | 118,657 | 33.8 % |
| 3 | `#index` | 67,044 | 19.1 % |
| 4 | **the headline sentence** (`P.big`) | **39,977** | **11.4 %** |
| 5 | one index row | 35,025 | 10.0 % |

At 1440 the same drawing is 41.7 % and the sentence 8.7 %. The largest thing on the phone's first
screen is a decorative map of the node's own cell at 53.3 % of the screen, and the sentence the page
exists to deliver is less than a quarter of its area. The type inside the sentence is right — 48 px
for the numeral at 390 — but the rule is about the mark, and the biggest mark carries no reading.
Fix in one sentence: the ground is a background; give it the weight of one.
Evidence: `now_populated_390_wire.png` (the hatched box is the drawing), `an_order.txt`;
`dashboard.css:120`–`:121`.

---
## Phase 5 — distribution and density

### 5.1 The first viewport

Share of the fold's pixels. "Unmarked ground" is the union of everything drawn — text line boxes,
drawings, controls — rasterised on a 4 px grid and subtracted, so a line of text inside a bordered
box counts once.

| view | w | header % | hero % | index % | first band % | unmarked ground % |
|---|---|---|---|---|---|---|
| now | 375 | 16.5 | 53.6 | 19.0 | 0.0 | 22.1 |
| now | 390 | 16.5 | 53.8 | 19.1 | 0.0 | 22.0 |
| now | 768 | 7.9 | 43.0 | 31.7 | 6.0 | 18.6 |
| now | 1440 | 7.9 | 41.9 | 17.4 | 10.4 | 34.4 |
| network | 375 | 16.5 | 0.0 | 0.0 | 0.0 | 62.3 |
| network | 390 | 16.5 | 0.0 | 0.0 | 0.0 | 62.9 |
| network | 768 | 7.9 | 0.0 | 0.0 | 0.0 | 57.3 |
| network | 1440 | 7.9 | 0.0 | 0.0 | 0.0 | 57.7 |
| setup | 375 | 16.5 | 0.0 | 0.0 | 0.0 | 64.1 |
| setup | 390 | 16.5 | 0.0 | 0.0 | 0.0 | 65.1 |
| setup | 768 | 7.9 | 0.0 | 0.0 | 0.0 | 78.6 |
| setup | 1440 | 7.9 | 0.0 | 0.0 | 0.0 | 87.9 |
| setup-unlocked | 375 | 16.5 | 0.0 | 0.0 | 0.0 | 48.5 |
| setup-unlocked | 390 | 16.5 | 0.0 | 0.0 | 0.0 | 49.8 |
| setup-unlocked | 768 | 7.9 | 0.0 | 0.0 | 0.0 | 52.1 |
| setup-unlocked | 1440 | 7.9 | 0.0 | 0.0 | 0.0 | 70.2 |
| wall | 375 | 0.0 | 0.0 | 0.0 | 0.0 | 17.3 |
| wall | 390 | 0.0 | 0.0 | 0.0 | 0.0 | 16.5 |
| wall | 768 | 0.0 | 0.0 | 0.0 | 0.0 | 10.2 |
| wall | 1440 | 0.0 | 0.0 | 0.0 | 0.0 | 13.5 |
| arrange | 375 | 16.5 | 59.7 | 12.9 | 0.0 | 25.2 |
| arrange | 390 | 16.5 | 60.0 | 13.0 | 0.0 | 25.0 |
| arrange | 768 | 7.9 | 49.8 | 33.0 | 0.0 | 17.8 |
| arrange | 1440 | 7.9 | 57.6 | 14.0 | 0.0 | 30.2 |
| wall (dark) | 1920 | 0.0 | 0.0 | 0.0 | 0.0 | 12.2 |


**The ask is below the fold at 390**, as Part 1 found by eye. Measured: on this fixture the ask
strip is `hidden` (the headline issue has no open ask), so on a fixture that *does* carry one the
strip renders at the foot of the hero's right-hand column, and the hero ends at y=698.6 on a 900 px
viewport with the header taking 148.8 of it. The strip fits only if the sentence wraps to three
lines or fewer. Not filed as new: this is Part 1's read of `now_populated_390_fold.jpg`, and it now
has the geometry behind it.

**The first band does not appear at all on the phone.** At 375 and 390 the fold ends inside the
index; the first issue band starts at y=1,101. At 1440 it is 10.4 % of the fold.

### 5.2 The whole page, band by band


Now @ 390 — page 9527 px

| order | band | top | height | % of page |
|---|---|---|---|---|
| 1 | #hero.hero | 164.8 | 533.8 | 5.6 |
| 2 | #index.index | 710.6 | 351.8 | 3.7 |
| 3 | #band-air.band | 1101.4 | 1686 | 17.7 |
| 4 | #band-coast.band | 2787.4 | 302 | 3.2 |
| 5 | #band-heat.band | 3089.4 | 971.8 | 10.2 |
| 6 | #band-land.band | 4061.2 | 399.3 | 4.2 |
| 7 | #place.band | 4460.6 | 198.7 | 2.1 |
| 8 | #loop.band | 4659.2 | 3486.6 | 36.6 |
| 9 | #figures.band | 8145.9 | 1381 | 14.5 |

Now @ 1440 — page 5065 px

| order | band | top | height | % of page |
|---|---|---|---|---|
| 1 | #hero.hero | 99 | 459 | 9.1 |
| 2 | #index.index | 576 | 190.9 | 3.8 |
| 3 | #band-air.band | 786.3 | 972.2 | 19.2 |
| 4 | #band-coast.band | 1758.5 | 165.3 | 3.3 |
| 5 | #band-heat.band | 1923.9 | 519.2 | 10.3 |
| 6 | #band-land.band | 2443 | 240.8 | 4.8 |
| 7 | #place.band | 2683.9 | 632.8 | 12.5 |
| 8 | #loop.band | 3316.6 | 1167.9 | 23.1 |
| 9 | #figures.band | 4484.5 | 580.6 | 11.5 |

**S-05 · P1 · Medium · §10 `data-density`; §5 `content-priority` · Now · 375, 390, 1440.**
The loop band is the tallest thing on the page at every width: **36.6 % at 390** (3,487 px of 9,527)
and 23.1 % at 1440, against the headline air band's 17.7 % and 19.2 %. It is tallest because of S-04
— fourteen ledger rows each wrapping their message into a 52 px column, at nine lines a row. On the
phone a household scrolls past two and a half screens of six-character stubs to reach the Figures
band. Correct the 52 px column and the band's height falls with it.

The brief's second test — a Figures band taller than the band it explains — holds too: **Figures is
1,381 px at 390**, taller than place (199), coast (302), land (399) and heat (972), and taller than
four of the six bands whose numbers it lists. At 1440 it is 580.6 px and taller than three. Filed
under S-05 as the same shape of problem rather than separately: the page's total height is set by
its two least-consequential bands.

The third test — a quiet issue taller than the headline issue — does **not** hold. `band-coast`
(302 px) and `band-land` (399 px) are `quiet`/`none` and are the two shortest issue bands; air is
1,686. Decision 11's collapse rule works where it applies. Part 1's Decisions-to-revisit item 3 — a
`none`-state issue getting a full band — is visible at 1440 in `band-land`'s 240.8 px and is its
call, not a finding here.

### 5.3 Density

| view | w | els in fold | els / 1000 px² (fold) | words in fold | els on page | doc h | els / 1000 px² (page) |
|---|---|---|---|---|---|---|---|
| now | 375 | 95 | 0.281 | 215 | 596 | 9566 | 0.166 |
| now | 390 | 97 | 0.276 | 203 | 596 | 9527 | 0.160 |
| now | 768 | 115 | 0.166 | 240 | 597 | 5343 | 0.145 |
| now | 1440 | 126 | 0.097 | 272 | 607 | 5065 | 0.083 |
| network | 375 | 55 | 0.163 | 283 | 101 | 1685 | 0.160 |
| network | 390 | 55 | 0.157 | 283 | 101 | 1666 | 0.155 |
| network | 768 | 57 | 0.082 | 251 | 79 | 1177 | 0.087 |
| network | 1440 | 45 | 0.035 | 263 | 79 | 1339 | 0.041 |
| setup | 375 | 37 | 0.110 | 177 | 37 | 900 | 0.110 |
| setup | 390 | 37 | 0.105 | 177 | 37 | 900 | 0.105 |
| setup | 768 | 38 | 0.055 | 150 | 38 | 900 | 0.055 |
| setup | 1440 | 38 | 0.029 | 150 | 38 | 900 | 0.029 |
| setup-unlocked | 375 | 60 | 0.178 | 176 | 128 | 2587 | 0.132 |
| setup-unlocked | 390 | 60 | 0.171 | 176 | 128 | 2566 | 0.128 |
| setup-unlocked | 768 | 69 | 0.100 | 207 | 129 | 2309 | 0.073 |
| setup-unlocked | 1440 | 79 | 0.061 | 261 | 129 | 1746 | 0.051 |
| wall | 375 | 66 | 0.196 | 232 | 71 | 1076 | 0.176 |
| wall | 390 | 67 | 0.191 | 223 | 71 | 1041 | 0.175 |
| wall | 768 | 71 | 0.103 | 220 | 71 | 961 | 0.096 |
| wall | 1440 | 37 | 0.029 | 250 | 71 | 1168 | 0.042 |
| arrange | 375 | 99 | 0.293 | 193 | 637 | 10037 | 0.169 |
| arrange | 390 | 99 | 0.282 | 193 | 637 | 9998 | 0.163 |
| arrange | 768 | 112 | 0.162 | 197 | 638 | 5794 | 0.143 |
| arrange | 1440 | 113 | 0.087 | 202 | 648 | 5621 | 0.080 |
| wall (dark) | 1920 | 71 | 0.034 | 262 | 71 | 1208 | 0.031 |

**The expectation fails in both directions.** The brief's test: the wall should be the sparsest by
an order of magnitude and Set up the densest.

- **The wall is not sparse by an order of magnitude.** At 1920 dark it measures **0.034 elements per
  1,000 px²** against Now's 0.097 at 1440 — a factor of **2.9**, not ten. And it has the *least*
  unmarked ground of any surface measured: **12.2 %**, against Set up's 87.9 % and Now's 34.4 % at
  1440.
- **Set up is not the densest; it is the sparsest.** Locked at 1440 it is 0.029 per 1,000 px² and
  unlocked 0.061. Now is 0.097 and Arrange 0.087. On the phone, Set up unlocked (0.171) is below
  Now (0.276).
- **By words, the three surfaces are the same page.** The wall's only screen at 1920 carries **262
  words**; Now's first screen at 1440 carries 272; Set up unlocked carries 261. Four per cent apart.

**S-15 · P1 · Medium · §10 `data-density` · wall · 1920.**
The wall is a surface for one room at three metres with nobody touching it, and it is carrying the
same word count as the laptop page, in a screen that is 12.2 % empty. Combined with S-03 — ten of
its thirteen text roles under the legibility floor — the composition is a page that has been scaled
up rather than a wall that has been composed. The two things that do read at three metres, the
sentence and the numeral, are the two the design intended; everything else on the screen is there
and unreadable.
Fix in one sentence: decide what the other 250 words are for, at that distance, and cut what has no
answer.
Evidence: `wall_contact.png`, `wall_populated_1920_dark.json`, the density table above.

**S-26 · P2 · Medium · §5 `touch-density` · header · 375, 390.**
Density has one failure that is not about crowding a page but about crowding a finger. The five nav
buttons measure 62, 86, 73, 59 and 81 px wide on a 32 px row at 390, and the four gaps between them
are **0, 0, 0 and 0 px** — `nav.views{gap:0}` (`dashboard.css:80`) with a shared 1 px divider
(`:81`). The rule asks for 8 px between adjacent touch targets. Part 1's **N15** measured these same
buttons against the size floors and found them above 24 px and below the 44 pt advisory; this is the
other half of the same row. The whole nav is 354 px wide, so there is no room to add a gap without
giving something up.
Fix in one sentence: keep the segmented look and separate the hit areas, or make the row taller.
Evidence: `now_populated_390.json`; `dashboard.css:80`, `:81`.

### 5.4 The wall, measured in millimetres

At 1920 on a 55-inch 16:9 panel, 1 px = 0.63 mm. The floor is about 3 mm of cap height per metre of
viewing distance, so 9 mm at three metres. Cap height is measured from the rasterised face, not
derived from a ratio.

| element | font px | cap px | cap mm | max distance m | at 3 m | text |
|---|---|---|---|---|---|---|
| B.mono | 176 | 128.48 | 80.9 | 27.0 | ✓ 3 m | 5 |
| P.big | 80 | 54 | 34.0 | 11.3 | ✓ 3 m | Holding at |
| P.why | 24 | 16.8 | 10.6 | 3.5 | ✓ 3 m | WHO 2021 global air quality guidelines,  |
| SPAN.name | 19 | 12.82 | 8.1 | 2.7 | only 2.7 m | Air |
| SPAN.ln | 17 | 11.9 | 7.5 | 2.5 | only 2.5 m | Holding at 5 µg/m³ in the room, under th |
| SPAN.issue | 14 | 10.22 | 6.4 | 2.1 | only 2.1 m | Air |
| SPAN.state | 14 | 10.22 | 6.4 | 2.1 | only 2.1 m | quiet |
| SPAN | 14 | 10.22 | 6.4 | 2.1 | only 2.1 m | · quiet; the day's high was 17 µg/m³ at  |
| SPAN | 13 | 9.49 | 6.0 | 2.0 | **only 2.0 m** | bayu-2 |
| SPAN.st | 13 | 9.49 | 6.0 | 2.0 | **only 2.0 m** | stale |
| P.note | 13 | 9.1 | 5.7 | 1.9 | **only 1.9 m** | no frames yet |
| SPAN.st | 12 | 8.76 | 5.5 | 1.8 | **only 1.8 m** | quiet |
| BUTTON.exit | 11 | 8.03 | 5.1 | 1.7 | **only 1.7 m** | Now |

**S-03 · P1 · — · no rule for this reader; check written here · wall · 1920.**
Ten of the thirteen distinct text roles on the wall are under the three-metre floor, and the two
that matter most for trust are the worst: **`stale` at 6.0 mm reads to 2.0 m** and the four issue
index lines at 7.5 mm read to 2.5 m. The exit control is 5.1 mm. Part 1's **L3** said the same thing
from a quarter-scale render and called it half-fixed; this is the number. It is also compounded by
S-01: at 1440 the word is not merely small, it is off the screen.
Fix in one sentence: size the wall's type from the distance, not from the viewport.
Evidence: the table above; `dashboard.css:442`, `:443`, `:445`, `:446`.

---
## Phase 6 — structure

### 6.1 The DOM skeleton

At 1440. A wrapper with no layout role is an element with exactly one child, no text of its own, no
grid or flex, no border, no padding and static position — and not a drawing.

| view | landmarks | `<section>` | roles in use | elements | deepest nesting | wrappers with no layout role |
|---|---|---|---|---|---|---|
| now | header, nav#views, main | 8 | group, img | 607 | 12 | **21** |
| network | header, nav#views, main | 1 | img | 79 | 8 | 3 |
| setup (locked) | header, nav#views, main | 1 | — | 38 | 7 | 3 |
| setup (unlocked) | header, nav#views, main, nav#tabs | 1 | — | 129 | 10 | **15** |
| wall | **main only** | 1 | img | 71 | 8 | 1 |
| arrange | header, nav#views, main | 8 | group, img | 648 | 12 | **21** |

**No `<footer>` exists on any view.** `grep -c '<footer'` is 0 in both `index.html` and
`dashboard.js`, and no FOOTER landmark appears on any of the 25 renders. `dashboard.css:304` styles
`footer .wrap` regardless. **S-22, P2.**

**Visual grouping against DOM grouping.** Checked on the three things that read as one object:

| what reads as one | in the DOM | verdict |
|---|---|---|
| an issue band | one `<section class="band" id="band-air" data-band="issue:air">` with its head, its stack and its cards inside | **matches** |
| a source card | one `<div class="sensor" data-component="sensorCard">` | **matches** |
| the wall | **two nested elements both carrying `class="wall"`** — `section#wall.view.wall` and `div#wallbox.wall` (`index.html:99`) | **does not** — and this is the cause of S-01 and S-02 |
| a band's title and its sub-line | one `.bandhead`, two columns | matches |
| the locked Set up screen | the gate **and** the whole hidden pane, because `#setup-body[hidden]` is un-hidden by `.setup{display:grid}` (`:324`) | **does not** — see S-18 |

### 6.2 Anatomy against specification

Every `data-component` rendered, in DOM order, under the band that owns it — ancestry reconstructed
from DOM order and depth, so a component in the hero's right column is attributed to the hero and
not to whatever it overlaps on screen.


**now @ 1440**

| band | rendered |
|---|---|
| hero | kicker → sentence → why → chips → stack → rhoRow |
| index | indexRow → indexRow → indexRow → indexRow |
| issue:air | kicker → sentence → why → stack → scale → day → ring → stations → forecast → sensorCard → sensorCard → sensorCard |
| issue:coast | kicker → sentence → readout → readout |
| issue:heat | kicker → sentence → why → stack → scale → day → sensorCard → sensorCard → sensorCard |
| issue:land | kicker → sentence → readout → readout → satellite → satellite |
| place | planCard → trustCard |
| loop | rhoRow → report → ledger |
| figures | figures |

**network @ 1440**

| band | rendered |
|---|---|
| netbody | netMap → peers → radios → vitals → cellRings |

**setup @ 1440** and **setup-unlocked @ 1440** — **no `data-component` anywhere on this view.**
Set up is not assembled from `COMPONENTS`; it is built from the groups `/settings` returns. Its
observed anatomy is written out below.

**wall @ 1440**

| band | rendered |
|---|---|
| wallbox | kicker → sentence → why → satellite → rhoRow |

**arrange @ 1440**

| band | rendered |

Against `ANATOMY` (`dashboard.js:1136`):

| band | declared | rendered | verdict |
|---|---|---|---|
| hero | kicker, sentence, why, chips, **miniStack**, askStrip, rhoRow, stamp | kicker, sentence, why, chips, **stack**, rhoRow | order matches. `askStrip` and `stamp` are absent because the fixture carries no open ask and no cell — data, not anatomy. `miniStack` renders as `stack` (see below). |
| issue.sensed (air) | kicker, sentence, why, stack, scale, day, ringCards, forecastStrip, sources | kicker, sentence, why, stack, scale, day, **ring, stations**, **forecast**, **sensorCard ×3** | **matches** — `ringCards` writes the `ring` and `stations` cards, `forecastStrip` writes `forecast`, `sources` writes the sensor cards. Three of the nine names in the DOM are not the names in the list. |
| issue.sensed (heat) | as above | kicker, sentence, why, stack, scale, day, sensorCard ×3 | `ringCards` and `forecastStrip` absent — data |
| issue.context (coast, land) | kicker, sentence, why, readouts, satellites | kicker, sentence, readout ×2 (+ satellite ×2 on land) | `why` absent on both — data |
| place | planCard, **units**, trustCard | planCard, trustCard | **`units` renders nothing on this fixture.** The four `.unit` elements on Now are `readout`s from the coast and land bands, not `unitRow`s. |
| loop | rhoRow, report, ledger | rhoRow, report, ledger | **matches** |
| figures | figures | figures | matches |
| wall | kicker, sentence, why, satellite, **wallIndex**, rhoRow, stamp | kicker, sentence, why, satellite, rhoRow | order matches. `wallIndex` **does render** — `.wi` is on the page with four rows — but carries no `data-component`, so it is invisible here and to anything else that reads the attribute. `stamp` absent — data. |
| index | indexRow | indexRow ×4 | matches |

Nothing is missing that the data does not explain, and nothing is out of order. What the comparison
turns up is a naming problem, which is S-19.

**Observed anatomy, for the views that have no list.** Written so the next round has one.

| view | observed, in order |
|---|---|
| **network** (`#netbody`) | `netMap` → `peers` → `radios` → `vitals` → `cellRings`. Below 700 px `netMap`'s SVG is replaced by `.netlist`, which carries no `data-component`. |
| **setup, locked** | `h2.t` → `p.sub` → `.gate` (h3.t, p.sub, input#tok, p.sub, input#acttok, `.row`(Unlock, Back)) → **and behind it the whole `#setup-body`**: `nav#tabs`, `h3#ptitle` (empty), `p#pblurb` (empty), `#pane` (empty), `.savebar`. **Zero `data-component` on this view.** |
| **setup, unlocked** | `nav#tabs` (9 group buttons + `.acts`(Lock)) → `h3#ptitle` → `p#pblurb` → `#pane` (one `.field` per key: label, `.src` marker, control, `.help`; or one `.pack` per pack) → `.savebar` (Save changes, `#savenote`). Built from `/settings` groups, not from `COMPONENTS`. |
| **arrange** | Now's anatomy unchanged, plus one `.arr` control bar prepended as a grid child inside each of the nine bands (1,184 × 43 at band level; **640 × 436 inside the hero**), plus `#arrbar` appended to `<body>`. |
| **wall** | as `ANATOMY.wall`, with `wallIndex` unattributed. |

**S-19 · P2 · — · no rule; check written here · all views.**
The anatomy is two tables and four vocabularies. `COMPONENTS` (`dashboard.js:681`) defines 21
functions and each writes `data-component="<its own name>"`. `COMPOSITES` (`dashboard.js:1168`)
defines seven more — `sources`, `ringCards`, `forecastStrip`, `readouts`, `satellites`, `units`,
`wallIndex` — and **not one of them writes the attribute**. Three of them render children that carry
a *different* name: `ringCards` → `ring` and `stations`, `sources` → `sensorCard`, `forecastStrip` →
`forecast`. `miniStack` delegates to `stack` (`:749`) and inherits its name, so the hero's mini stack
and a band's full stack are indistinguishable in the DOM. And three `COMPONENTS` keys — `unitRow`,
`readout`, `sensorCard` — appear in no `ANATOMY` list at all and are reachable only through a
composite. The file's own comment says a component "returns markup whose root carries
`data-component="<name>"`"; for seven of the 28 it does not.
Fix in one sentence: make a composite carry its own name, or say in `ANATOMY` that seven entries are
groups.
Evidence: the anatomy tables above; `dashboard.js:681`, `:749`, `:1136`, `:1168`.

**S-20 · P2 · — · no rule; check written here · Now.**
`unitRow` (`dashboard.js:849`) and `readout` (`:855`) both render `<div class="unit">`. They are
different components with different data and one class, so `dashboard.css:176`–`:188` styles both
and nothing in the DOM tells them apart but the attribute. On the populated fixture only `readout`
renders, which is why `ANATOMY.place`'s `units` looks absent.
Fix in one sentence: one class per component, or one component.

### 6.3 The same component across views

At 1440. A difference the layer does not name as a variant is a finding.

| component | view | n | padding t r b l | font px | radius | heights | border w |
|---|---|---|---|---|---|---|---|
| .pill | now | 28 | 2 7 2 6 | 11 | 0px | 20 | 1 1 1 1 |
| .pill | network | 1 | 2 7 2 6 | 11 | 0px | 20 | 1 1 1 1 |
| .pill | setup | 1 | 2 7 2 6 | 11 | 0px | 20 | 1 1 1 1 |
| .pill | setup-unlocked | 1 | 2 7 2 6 | 11 | 0px | 20 | 1 1 1 1 |
| .pill | arrange | 28 | 2 7 2 6 | 11 | 0px | 20 | 1 1 1 1 |
| **.pill** | **5 views** |  | one padding | one size |  |  |  |
| .k | now | 24 | 0 0 0 0 | 11, 10.5 | 0px | 15 | 0 0 0 0 |
| .k | network | 5 | 0 0 0 0 | 11 | 0px | 15 | 0 0 0 0 |
| .k | wall | 1 | 0 0 0 0 | 14 | 0px | 20 | 0 0 0 0 |
| .k | arrange | 24 | 0 0 0 0 | 11, 10.5 | 0px | 15, 43 | 0 0 0 0 |
| **.k** | **4 views** |  | one padding | **3 sizes** |  |  |  |
| .chip | now | 9 | 2 8 2 8 | 11 | 0px | 20 | 1 1 1 1 |
| .chip | arrange | 9 | 2 8 2 8 | 11 | 0px | 20 | 1 1 1 1 |
| **.chip** | **2 views** |  | one padding | one size |  |  |  |
| .num | now | 22 | 0 0 0 0 | 18.4, 27.2, 19.2, 16 | 0px | 18, 21, 26, 27 | 0 0 0 0 |
| .num | network | 4 | 0 0 0 0 | 34 | 0px | 34 | 0 0 0 0 |
| .num | arrange | 22 | 0 0 0 0 | 18.4, 27.2, 19.2, 16 | 0px | 18, 21, 26, 27 | 0 0 0 0 |
| **.num** | **3 views** |  | one padding | **5 sizes** |  |  |  |
| .card | now | 4 | 24 24 24 24 | 16 | 0px | 85, 104, 143, 181 | 1 1 1 1 |
| .card | network | 5 | 24 24 24 24 | 16 | 0px | 124, 159, 220, 330, 506 | 1 1 1 1 |
| .card | setup | 1 | 24 24 24 24 | 16 | 0px | 353 | 1 1 1 1 |
| .card | arrange | 4 | 24 24 24 24 | 16 | 0px | 85, 104, 143, 181 | 1 1 1 1 |
| **.card** | **4 views** |  | one padding | one size |  |  |  |
| .sensor | now | 6 | 12 14 12 14 | 16 | 0px | 206, 240 | 1 1 1 1 |
| .sensor | arrange | 6 | 12 14 12 14 | 16 | 0px | 206, 240 | 1 1 1 1 |
| **.sensor** | **2 views** |  | one padding | one size |  |  |  |
| .unit | now | 4 | 8 0 8 0 | 16 | 0px | 41, 42 | 0 0 0 0 / 1 0 0 0 |
| .unit | arrange | 4 | 8 0 8 0 | 16 | 0px | 41, 42 | 0 0 0 0 / 1 0 0 0 |
| **.unit** | **2 views** |  | one padding | one size |  |  |  |
| .btn | setup | 3 | 8 14 8 14 | 16 | 0px | 43 | 1 1 1 1 |
| .btn | setup-unlocked | 2 | 9 12 9 12 / 8 14 8 14 | 14, 16 | 0px | 35, 43 | 0 0 0 2 / 1 1 1 1 |
| .btn | arrange | 2 | 8 14 8 14 | 16 | 0px | 43 | 1 1 1 1 |
| **.btn** | **3 views** |  | **2 paddings** | **2 sizes** |  |  |  |

`.pill`, `.chip`, `.card`, `.sensor` and `.unit` are identical wherever they appear: one padding,
one size, one radius, square, 1 px. That is the layer holding.

**S-21 · P2 · Medium · §4 `state-clarity` (nearest) · Set up · all widths.**
`.btn` renders two ways. In the pane it is 43 px tall with a 1 px box, 16 px type and 8/14 padding.
In the tab rail the same class is captured by `.tabs button` (`dashboard.css:333`) and becomes 35 px
tall, no box, 14 px type, 9/12 padding and a 2 px left border. The **Lock** button is a `.btn ghost`
sitting inside `.tabs .acts`, so the one control that ends a privileged session is the one that does
not look like a button.
Fix in one sentence: scope `.tabs button` to the tabs, not to everything inside the rail.
Evidence: the table above; `setup-unlocked_populated_1440.json`; `dashboard.css:333`, `:61`.

`.k` carries three sizes (11, 10.5, 14) and `.num` five (16, 18.4, 19.2, 27.2, 34) — both covered by
S-09 rather than filed again.

### 6.4 Stacking

**Every positioned element and every z-index in use**

| element | position | z-index | seen in |
|---|---|---|---|
| DIV#hero.hero | relative | auto | now@375, now@390, now@768, now@1440, arrange@375, arrange@390 +2 |
| DIV.bg | absolute | auto | now@375, now@390, now@768, now@1440, wall@375, wall@390 +6 |
| IMG | absolute | auto | now@375, now@390, now@768, now@1440, wall@375, wall@390 +6 |
| DIV | relative | auto | now@375, now@390, now@768, now@1440, arrange@375, arrange@390 +2 |
| DIV.side | relative | auto | now@375, now@390, now@768, now@1440, arrange@375, arrange@390 +2 |
| DIV.plan | relative | auto | now@375, now@390, now@768, now@1440, arrange@375, arrange@390 +2 |
| DIV.card | relative | auto | network@375, network@390, network@768, network@1440 |
| DIV.savebar | sticky | auto | setup@375, setup@390, setup@768, setup@1440, setup-unlocked@375, setup-unlocked@390 +2 |
| SPAN.tr | relative | auto | setup-unlocked@375, setup-unlocked@390, setup-unlocked@768, setup-unlocked@1440 |
| NAV#tabs.tabs | sticky | auto | setup-unlocked@1440 |
| SECTION#wall.view | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| DIV#wallbox.wall | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| DIV.row2 | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| DIV.wi | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| DIV.rho | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| P.note | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| DIV.foot | relative | auto | wall@375, wall@390, wall@768, wall@1440 |
| DIV.arr | relative | auto | arrange@375, arrange@390, arrange@768, arrange@1440 |
| BUTTON.exit | absolute | 2 | wall@375, wall@390, wall@768, wall@1440 |

**Overlaps**

| render | positioned element | elements under it | which |
|---|---|---|---|
| setup@375 | DIV.savebar (sticky, z auto) | 1 | SPAN.sub |
| setup@390 | DIV.savebar (sticky, z auto) | 1 | SPAN.sub |
| setup-unlocked@768 | DIV.savebar (sticky, z auto) | 1 | LABEL |
| setup-unlocked@1440 | DIV.savebar (sticky, z auto) | 1 | DIV.help |

**S-17 · P2 · High · §5 `z-index-management` · Set up, Wall · all widths.**
The rule wants a declared scale. `app/static/` contains **one z-index**: `.wall .exit{z-index:2}`
(`dashboard.css:446`). Nineteen elements are positioned; eighteen of them are `z-index:auto` and
resolve by source order, including the two `sticky` elements — `.tabs` (`:332`) and `.savebar`
(`:351`) — which are the only two things on the page that are meant to sit over content. They work
today because they happen to be late in the document. Nothing records that, and `2` records nothing
either.
Fix in one sentence: three named levels — content, sticky, overlay — and put the wall's exit on one.

**S-18 · P2 · Medium · §5 `fixed-element-offset` · Set up · all widths.**
The sticky save bar covers content at four renders, and one of them is the **locked** view: at 375
and 390 the bar is pinned to the bottom of the viewport in front of the unlock card and over the
gate's last help line. It is there because `#setup-body` carries `hidden` and `.setup{display:grid}`
(`:324`) beats it — which is Part 1's **S11**, filed there as an accessibility-tree problem and
closed as a side effect of the `[hidden]` guard. This is the same cause with a layout consequence,
and it is measured. Nothing reserves space under the bar at any width: at 1440 unlocked it sits over
a `.help` line.
Fix in one sentence: see P1-S11; and give the pane bottom padding the height of its own bar.
Evidence: the overlap table above; `setup_populated_390.json`, `setup-unlocked_populated_1440.json`.

### 6.5 Stability across the first response

Rendered with every API call stalled, then released.

| | 1440 | 390 |
|---|---|---|
| document height | 900 → **5,065** | 900 → **9,527** |
| `#figures` | y 288 → 4,485 (**+4,197**) | y 254 → 8,146 (**+7,892**) |
| `#loop` | y 240 → 3,317 (+3,077) | y 224 → 4,659 (+4,435) |
| `#place` | y 192 → 2,684 (+2,492) | y 194 → 4,461 (+4,267) |
| `#index` | y 191 → 576 (+385) | y 193 → 711 (+518) |
| **the header** | no change | **+26 px** — `main`, `#now` and `#hero` all move from y 139 to y 165 |
| `nav#views` | no change | **+1 px** |

**S-12 · P1 · High · §3 `content-jumping` · Now · 375, 390.**
The mounts moving is by design: `index.html` ships empty boxes and the renderer fills them, and
nothing above the fold depends on what arrives below it. The header is different. At 390 the node's
place line arrives with `/health`, the header's wrapping flex row (`dashboard.css:73`) gains a row,
and **the chrome the reader is already looking at grows 26 px under them** — the nav shifts 1 px and
the hero and everything below it shift 26. On a phone that lands mid-tap. Above 560 px the place
line is hidden (`:78`) and the header does not move, so this is a phone-only effect.
Fix in one sentence: reserve the place line's row, or keep the header one row at every width — the
same cause as S-11, and see the correction there for why a width alone will not do it.
Evidence: `stall_now_populated_390.json`, `stall_now_populated_1440.json`.

**S-25 · P2 · — · no rule; check written here · Now, Set up.**
Now carries 607 elements, of which **21 wrap exactly one child and contribute no layout**, and
nesting reaches **12**. Arrange carries 648 and the same 21. Set up unlocked carries 15 in 129
elements — one in nine. Nothing breaks; it is the cost of assembling markup as strings, and it is
recorded because the next round will want the baseline.

---
## The findings, ranked

Ranked by how much a finding misleads a household or blocks a task. P0 misleads a household about
its own conditions or shows the stranger too much; P1 blocks a task or contradicts the frozen
language on a daily screen; P2 is polish. "Skill" is the severity the rule's own row carries; "—"
means no rule fits and the check is written here.

| id | P | skill | rule | view | width | measurement | evidence | fix in one sentence | collides |
|---|---|---|---|---|---|---|---|---|---|
| **S-01** | **P0** | — | check written here (nearest §5 `fixed-element-offset`) | wall | 1440, 390, 375 | document 1,168 px on a 900 px viewport; `stale`, the node name, the ρ caption and "Answer on Telegram, not here" all below the fold, on a surface that does not scroll | `wall_populated_1440.json`, `wall_contact.png`; `index.html:99`, `dashboard.css:425` | Scope `.wall` to one box so the wall fits its screen. | no — compounds P1-L3 |
| **S-02** | **P1** | Medium | §5 `container-width`, `viewport-units` | wall | all | `min-height:100vh` and `padding` applied to two nested boxes: measured padding 115.2 px at 1440 against a declared 57.6; overflow 61–268 px | `wall_populated_*.json`; `index.html:99`, `dashboard.css:425` | The same one-box fix as S-01. | no |
| **S-03** | **P1** | — | check written here | wall | 1920 | 10 of 13 text roles under the 9 mm floor; `stale` 6.0 mm (2.0 m), issue lines 7.5 mm (2.5 m), kicker 6.4 mm (2.1 m) | `wall_populated_1920_dark.json`; `dashboard.css:442`, `:443`, `:445`, `:446` | Size the wall's type from the distance, not from the viewport. | no — is P1-L3's number |
| **S-04** | **P1** | High | §5 `line-length-control` | Now | 375, 390 | ledger message column **52 px** on all 14 rows while the button gets 288; 94 line boxes at 6–12 characters | `now_populated_390.json`, `now_contact.png`; `dashboard.css:294` | Place `.txt` in column two, spanning, as `.do` already is. | no |
| **S-05** | **P1** | Medium | §10 `data-density`, §5 `content-priority` | Now | 375, 390, 1440 | loop band **36.6 %** of the phone page (3,487 of 9,527 px) against air's 17.7 %; Figures 1,381 px, taller than four of the six bands it explains | `an_dist.txt`, `now_contact.png` | Fix S-04 and the band's height falls with it. | no |
| **S-06** | **P1** | High | §5 `readable-font-size` | all | 375, 390 | **193 of 199** prose runs under 16 px; only the hero's why line reaches it | `*_populated_390.json`; `dashboard.css:70`, `:215`, `:286`, `:300`, `:342` | Raise the body classes to 16 px on the phone; leave the mono labels small. | no |
| **S-07** | **P1** | Medium | §5 `line-length-control` | Now, Network | 768, 1440 | `.note` has no measure: **120 characters per line** at 768, 62 blocks affected | `lines.txt`; `dashboard.css:70` | Give `.note` the measure `.sub`, `.why`, `.help` and `.rep` already have. | no |
| **S-08** | **P1** | Medium | §5 `visual-hierarchy`, `content-priority` | Now | all | the hero's ground drawing is **53.3 %** of the phone's first screen (187,197 px²); the headline sentence is 11.4 % | `now_populated_390_wire.png`, `an_order.txt`; `dashboard.css:120` | The ground is a background; give it the weight of one. | no |
| **S-09** | **P1** | Medium | §6 `font-scale` | all | all | **72 distinct type combinations**; 16 sizes carry more than one weight-and-family; 14 px carries six | `an_type.txt`; `dashboard.css:65`, `:81`, `:153`, `:193`, `:286`, `:433` | Name the levels, and make each exception say which level it departs from. | no |
| **S-10** | **P1** | Medium | §1 `heading-hierarchy` | Now, Network, Wall | all | Now's outline is four sibling h2s with the page's largest type (40 px `<p>`, 89.6 px numeral) outside it; the wall has no heading of any level | `an_headings.txt` | Make the hero sentence the page's heading and the band sentences the level under it. | no — P1-H2 covers the missing `<h1>` |
| **S-11** | **P1** | Medium | §5 `breakpoint-consistency` | header | content-dependent | **corrected 14 Sep, then closed** — the reflow widths were set by the node's name and place string, not by the page: 500/730 on the fixture, 590/1040/1230 on a long-named node, growing as the viewport widened on four of six shapes. Fixed slots make it **800 and 1210 on every shape, never growing** | `an_header.txt` (`measure.mjs header`); `dashboard.css:91`, `:99`, `:113` | done — `.brand` 460 px, `.status` 255 px, both reflows declared | no — and see the note in Phase 1 |
| **S-12** | **P1** | High | §3 `content-jumping` | Now | 375, 390 | the header grows **26 px** when `/health` lands; the nav moves 1 px and everything under it moves 26 | `stall_now_populated_390.json`; `dashboard.css:73`, `:78` | Reserve the place line's row — the same cause as S-11. | no |
| **S-13** | **P1** | Medium | §5 `spacing-scale` | all | all | **41 distinct values, 28 off the 4 pt measure, 5,265 of 8,764 instances (60 %)**; the largest are 7 px (1,100), 6 px (1,044), 10 px (1,000) | the histogram in 2.1; `dashboard.css:86`, `:145`, `:154`, `:176`, `:302` | Name a scale in the layer, or say in the CSS that spacing is interpolated and not stepped. | no — the layer names no scale |
| **S-14** | **P1** | Medium | §5 `container-width` | all | all | six views, five left edges at 1440 (128 / 153 / 358 / 115); Network and locked Set up start 17–25 px right of the header's own inner edge | the guide overlays; `dashboard.css:97`, `:324` | Do not let a card's padding stand in for a page margin; keep a view's heading in its content's column. | no |
| **S-15** | **P1** | Medium | §10 `data-density` | wall | 1920 | **262 words** on the wall's only screen against Now's 272; **12.2 % unmarked ground**, the least of any surface; density 2.9× Now's, not an order of magnitude | `an_dist.txt`, `wall_contact.png` | Decide what the other 250 words are for at three metres, and cut what has no answer. | no |
| S-16 | P2 | Medium | §6 `whitespace-balance`, §5 `spacing-scale` | all | all | kicker-to-sentence is 8 / 9.6 / 12 / 14 / 22.4 px from three rules; card-to-card is 10 / 14 / 18 from two | the rhythm tables; `dashboard.css:100`, `:125`, `:205`, `:106`, `:434` | Name the relationship once and let containers inherit it. | no |
| S-17 | P2 | High | §5 `z-index-management` | Set up, Wall | all | one z-index in the whole of `app/static/` (`.wall .exit{z-index:2}`); 18 positioned elements on `auto`, including both sticky bars | `an_stack.txt`; `dashboard.css:446`, `:332`, `:351` | Three named levels — content, sticky, overlay. | no |
| S-18 | P2 | Medium | §5 `fixed-element-offset` | Set up | all | the sticky save bar covers content at four renders, including the **locked** view at 375 and 390 where it sits over the gate | `an_stack.txt`, `setup_populated_390.json`; `dashboard.css:324`, `:351` | See P1-S11; and pad the pane by the height of its own bar. | no — same cause as P1-S11 |
| S-19 | P2 | — | check written here | all | 1440 | 7 of 28 named parts (all of `COMPOSITES`) emit no `data-component`; three of their children carry a different name; `miniStack` renders as `stack`; 3 `COMPONENTS` keys appear in no `ANATOMY` list | the anatomy tables; `dashboard.js:681`, `:749`, `:1136`, `:1168` | Make a composite carry its own name, or say in `ANATOMY` that seven entries are groups. | no |
| S-20 | P2 | — | check written here | Now | all | `unitRow` and `readout` both render `<div class="unit">` | `dashboard.js:849`, `:855` | One class per component, or one component. | no |
| S-21 | P2 | Medium | §4 `state-clarity` (nearest) | Set up | all | `.btn` is 43 px / 1 px box / 16 px in the pane and 35 px / no box / 14 px in the tab rail; **Lock** is the one caught by it | `an_components.txt`; `dashboard.css:333` | Scope `.tabs button` to the tabs. | no |
| S-22 | P2 | — | check written here | all | all | `footer .wrap` (`dashboard.css:304`) styles an element that exists in neither `index.html` nor `dashboard.js`; no FOOTER landmark on any of 25 renders | `grep -c '<footer'` = 0; `an_dom.txt` | Delete the rule, or add the footer it was written for. | no |
| S-23 | P2 | Medium | §5 `container-width` | wall | all | `.wrap` caps at 1,280 px; the wall has no cap, so its content is 1,209.6 px at 1440 and 1,792 px at 1920 | the grid table; `dashboard.css:63`, `:425` | One container rule, or a line in the CSS saying why the wall has its own. | no |
| S-24 | P2 | Medium | §5 `content-priority` | Arrange | 1440, 390 | entering Arrange moves the hero's sentence from x=165 (528 px wide) to **x=848** (427 px wide) and grows the hero 459 → 630 px | `arrange_contact.png` beside `now_contact.png`; `dashboard.js` `arrangeControls()` | Overlay the bar rather than adding a grid child — P1-A6's fix. | no — is P1-A6's number |
| S-25 | P2 | — | check written here | Now, Set up | 1440 | 21 wrappers with no layout role in 607 elements; nesting depth 12 | `an_dom.txt` | — recorded as a baseline, no action asked | no |
| S-26 | P2 | Medium | §5 `touch-density` | header | 375, 390 | the five nav buttons are butted: gaps **0, 0, 0, 0 px** on a 32 px row, against the rule's 8 px minimum between adjacent targets | `now_populated_390.json`; `dashboard.css:80`, `:81` | Keep the segmented look and separate the hit areas, or make the row taller. | no — P1-N15 is about size, this is spacing |

**Twenty-six findings: one P0, fourteen P1, eleven P2.** Six of them are two edits. S-01, S-02,
S-03 and S-15 are all the wall, and the first two are `index.html:99`; S-04 and S-05 are both
`dashboard.css:294`. Two lines close six rows, including the only P0.

---

## Measured, against Part 1's ids

No new finding is filed for any of these. Each is Part 1's, with the number this pass adds.

| Part 1 id | what Part 1 said | measured |
|---|---|---|
| **H2** | no `<h1>` on any view; the node's name is a `<b>` | confirmed at v0.52 on all 25 renders. The outline on Now is four sibling `h2`s at 29.6 px; on Network one `h2`; on the wall **none at any level**. See S-10 for what survives H2's fix. |
| **H8** | the header is not sticky | confirmed: `position: static` on every view at every width, and `main` begins at the header's own height everywhere. Measured heights: 148.8 px at 375/390, 71 px at 768/1440. |
| **L3** | `stale` is 11 px muted mono and illegible at a quarter scale | measured: cap height **6.0 mm** at 1920, readable to **2.0 m** against a 3 m floor. And at 1440 it is not on the screen at all — S-01. |
| **N13** | the REGION chip wraps to two lines at 390 | measured: `SPAN.chip` wraps at 39 characters over 2 lines at 390 and 33 at 375, inside an 11 px/1.3 box. The rule's band starts at 35. |
| **N6** | the Figures table scrolls horizontally at 390, 435 px in a 390 box | measured: `table.figs{min-width:420px}` (`dashboard.css:300`) inside a 354 px content column; the table's cells run to 12 characters a line over 7 to 9 lines at 390. |
| **S11** | the locked Set up screen puts its hidden pane in the accessibility tree, because `.setup{display:grid}` beats `[hidden]` | measured as geometry: the pane's **sticky save bar is pinned over the unlock card** at 375 and 390, covering the gate's last help line. Same cause, a second consequence. See S-18. |
| **A1** | `.arrbar` has no CSS rule, so it sits at the foot of the page | confirmed at v0.52 on the populated fixture: `#arrbar` is `position: static` at **y=5,579 on a 5,621 px page** at 1440, and at y=9,930 on a 9,998 px page at 390. |
| **A6** | entering Arrange moves the hero's sentence into the right column and orphans the numeral | measured: the sentence moves **683 px right** (x=165 → x=848), loses 101 px of width (528 → 427), and the hero grows **171 px** (459 → 630). See S-24. |
| **L6** | the wall prints the cell caption | not reproducible on this fixture: `stamp` renders nothing because the fixture's `/health` carries no `cell`. Part 1 saw it on the empty node, which does. |
| **Decisions 3** | a `none`-state issue gets a full band at 1440 | measured: `band-land` is **240.8 px at 1440 and 399.3 px at 390**, 4.8 % and 4.2 % of the page. It is the third shortest band, not a screen. The cost is smaller than the decision note implies. |

---

## Decisions to revisit — additions only

Part 1's eight stand. Two more, both from the measurements above.

9. **The page interpolates its spacing instead of stepping it.** Thirty `clamp()` expressions, no two
   sharing a triple, produce sixteen spacing values that exist at exactly one viewport width. It is
   a coherent choice — the layout breathes with the viewport and never lands on a wrong step — and
   it is also why 60 % of the spacing is off any measure and why one relationship has five values.
   The layer names no spacing scale, so nothing is being violated; the question is whether the
   programme layer should name one. §5 `spacing-scale`. Evidence: the histogram in 2.1.

10. **The wall's composition is the Now page scaled up.** Measured: 262 words against Now's 272,
    12.2 % unmarked ground against Now's 34.4 %, and ten of thirteen text roles below the distance
    they are read at. The two things that work — the sentence and the numeral — work because they
    were designed for the wall. Everything else on it is the laptop's content at a larger size.
    Whether the wall should carry an index, a ρ row, a satellite card and a footer at all is a
    composition decision, and it is the same decision L2 is waiting on. Evidence: `wall_contact.png`,
    5.3 and 5.4.

---

## What could not be measured

- **A real wall in a real room.** The millimetre table converts angular size on a 55-inch 1920 panel
  and says nothing about room light, viewing angle, glare or a glossy screen. It is a floor, not a
  verdict. The layer's O2 and O10 record the same gap.
- **The `id` and `es` type sizes.** The fixture is `en` and a fixture renders in its own captured
  locale, so no Bahasa or Spanish string was laid out. Every line-length and wrap number in Phase
  2.3 is English only, and the three headline sentences are the ones most likely to change length.
- **The ask strip.** It is `hidden` on `node1-2026-09-06`, so its geometry, its position against the
  390 fold and its two-column reflow at 560 are all unmeasured. Part 1 measured it on a fixture
  render that carried one; this pass could not.
- **`unitRow`, `askStrip` and `stamp`.** Three of the 28 named parts render nothing on this fixture,
  so their boxes are absent from every table here.
- **The plan legend and the satellite controls.** Unchanged from Part 1: neither pack had data on
  pai-clean, so the legend's five toggles and the loop's three controls have no measured geometry.
- **What the script cannot see.** Anything inside an `<svg>`: the walk stops at the SVG element and
  draws it as one hatched box, so the day chart's polylines, the scale's dots and the network
  figure's wires have no measurements here — only their containers do. SVG `<text>` *is* measured,
  because it produces text line boxes. Pseudo-elements are not measured at all, which means the
  switch's knob (`.switch .tr::after`, `dashboard.css:348`) is a box this document does not contain.
- **Scrolled states.** Every render is at scroll 0. A sticky element's behaviour once stuck is
  inferred from its computed position and its resting overlap, not from a scrolled render.

---

## Appendix A — the script

```
planetai-design/design/audit/2026-09/ux-review/skeleton/measure.mjs     branch ux-review-2026-09

node measure.mjs render all          25 populated renders + 4 wireframe-only (empty, refused)
node measure.mjs steps               320 -> 1920 in 20 px steps on Now and Wall
node measure.mjs stall <job>         layout with the API stalled, then released
node measure.mjs sheets              one contact sheet per view, all widths at one scale
node measure.mjs header              the header's shape against the node's own name and place
node measure.mjs analyse <table>     grid spacing rhythm lines align type headings order
                                     dist wall dom anatomy components stack
node measure.mjs list                the job table

PAI_ADMIN_TOKEN is read from the environment for the two setup-unlocked renders only. It is never
printed and never written into any output file.
```

Per render it writes the element table (`<name>.json`: tag, role, `data-component`, `data-band`,
box, margin, padding, gap, font-size, weight, line-height, family, cap height, baseline, z-index,
position, border widths, radius, min-height, depth, child count — plus every text line box with its
exact per-line character counts, the heading outline and the landmark list), the wireframe
(`<name>_wire.png`) and the guide overlay (`<name>_guides.png`).

## Appendix B — the searches run

One query per concern, one outcome each, `--domain ux -n 5` and `--domain chart -n 5`, as the
contract requires. No `--design-system`; no `style`, `color`, `typography`, `landing`, `gsap`,
`icons` or `google-fonts` domain.

| query | domain | top result | verdict |
|---|---|---|---|
| `spacing-scale` | ux | Touch / Touch Spacing (Medium) | **off-topic, dropped** — matched a touch rule. §5 `spacing-scale` read from `quick-reference.md:101` instead |
| `container-width` | ux | Layout / Container Width (Medium) | used — S-14, S-23 |
| `breakpoint-consistency` | ux | Responsive / Breakpoint Testing (Medium) | used — S-11 |
| `visual-hierarchy` | ux | Interaction / Hover States (Medium) | **off-topic, dropped** — `quick-reference.md:110` used instead for S-08 |
| `content-priority` | ux | Content / Truncation (Medium) | **off-topic, dropped** — `quick-reference.md:109` used instead |
| `touch-density` | ux | Touch / Touch Spacing (Medium) | used — S-26 |
| `line-length-control` | ux | Typography / Line Length (Medium) | used — S-04, S-07 |
| `fixed-element-offset` | ux | Layout / Fixed Positioning (Medium) | used — S-18 |
| `z-index-management` | ux | Layout / Z-Index Management (**High**) | used — S-17 |
| `content-jumping` | ux | Layout / Content Jumping (**High**) | used — S-12 |
| `heading-hierarchy` | ux | Accessibility / Heading Hierarchy (Medium) | used — S-10 |
| `heading-clarity` | ux | Typography / Heading Clarity (Medium) | used — S-09. **There is no `heading-clarity` id in the Quick Reference**; the row exists only in the CSV, and the nearest ids there are `font-scale` and `weight-hierarchy` |
| `font-size-scale` | ux | Typography / Font Size Scale (Medium) | used — S-09. The Quick Reference spells it **`font-scale`** (`:119`); the brief's `font-size-scale` has no id |
| `line-height` | ux | Typography / Line Height (Medium) | used, and **nothing found** — every prose block measures 1.5, 1.55 or 1.6 |
| `readable-font-size` | ux | Responsive / Readable Font Size (**High**) | used — S-06 |
| `orphan heading line balance` | ux | Typography / Heading Line Balance (Medium) | used, and **nothing found** — `.hero p.big` and `.wall p.big` both carry `text-wrap:balance` with a bounded measure (`dashboard.css:125`, `:434`), which is what the rule asks for |
| `compact-label-overflow` | ux | Content / Compact Label Overflow (**High**) | used — the measurement added to Part 1's **N13** |
| `chip-collection-reflow` | ux | Layout / Chip Collection Reflow (**High**) | used, and **nothing found** — `.hero .chips` is `flex-wrap:wrap` with no clip (`:130`) and every chip stays whole; the failure at 390 is inside one chip, which is N13 |
| `axis-readability` | chart | Cumulative Changes / Waterfall Chart | **off-topic, dropped** — the chart dataset answers with a chart type, not a rule, exactly as Part 1 found |
| `data-density` | chart | Heatmap / Intensity | **off-topic, dropped** — same reason; §10 `data-density` read from `quick-reference.md:248` and used for S-05 and S-15 |
| `responsive-chart` | chart | Performance vs Target / Gauge | **off-topic, dropped** — same reason |

Three of the twenty-one queries were dropped on the chart domain and four on the ux domain, one
retry each, as the contract allows. Where a query was dropped the rule was read from
`references/quick-reference.md` by id, which is the file Part 1's 217-id appendix was extracted
from; the rows are cited by line above.

---

## Not asked for

The wireframes are drawn from the real line boxes, so `now_contact.png` is, incidentally, a picture
of how much of this page is a list. Ninety-four of the 494 text runs at 390 are inside fourteen
ledger rows and another 82 inside the Figures table's 52 cells. The index is four rows. Set against
that, the hero — the thing the whole product is for — is 28 runs. The drawing gives a ratio nobody asked for: **the page spends 5.6 % of its height saying what is happening and 51 % listing
what happened.** That is not a finding, because there is no rule it breaks and no measurement that
says what the ratio should be. But it is the first thing the drawing shows that the screenshot
never did, and it is worth a sentence in the round that decides what the phone page is for.
