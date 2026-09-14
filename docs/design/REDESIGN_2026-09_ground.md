# The ground the redesign starts from

**14 September 2026.** Phase 0 of the dashboard redesign. It changes nothing. It records what is on
`main`, measures the shipped page against the targets the redesign will be judged by, lists what the
page will have to hold that it does not hold today, and reads every pack for what it already
declares that a page could draw.

Three complaints are being answered, and they are read here as three measurements rather than as
three moods:

| the complaint | the measurement | where it is |
|---|---|---|
| too much empty space | pixels in the first viewport inside nothing that carries a number, a sentence, a sign or a control | T2 |
| data not understandable | numerals with no unit, no source, no age and nothing to compare them against | T4 |
| everything disconnected | components with no link to anything that explains them or that they explain | T5 |

## Header

| | |
|---|---|
| Branch | `dashboard-redesign-2026-09`, cut from `main` |
| Main | tag **v0.53**, commit **`a06655a`** ("CHANGELOG: v0.53, the page stops saying what the node did not") |
| 5b Release 1 | **present.** `app/issues/` is a package (`schema.py`, `engine.py`, `api.py`, four `*.yml`), `GET /issues` and `GET /issues/fixtures/{name}` are mounted, one fixture ships, `planetai snapshot` is in the CLI. Branch: **[issues present]** — nothing to land first. |
| The UX walk and the skeleton | **present**, both on `main`: `docs/design/UX_REVIEW_2026-09.md` (64 findings) and `docs/design/UX_REVIEW_2026-09_skeleton.md` (26). Branch: **[ux-review present]** |
| Where it ran | **pai-clean** (Lima VM), the September review's two containers: `:8081` bootstrapped with `SHARE_LEVEL=open`, `:8082` fresh (`BOOTSTRAP=0`). Node #1 and node #2 were not contacted, read or written. Nothing on the VM was changed: no setting, no restart. |
| What was served | The containers answer the API. Every request for the document and for `/static/*` is intercepted and fulfilled from **this branch's `app/static/`**, so what is measured is v0.53's page against a live node's answers. |
| Browser | Playwright + the Chromium in `planetai-design/node_modules` (1.55.1), one device pixel, `prefers-reduced-motion: reduce`, JPEG. axe-core 4.10.2 from the same place. |
| The script | `tests/visual/measure.mjs`, committed on this branch. It is the September skeleton review's script moved into this repo and extended; its header says so. There is one measuring script. |
| Renders | `now` and `wall`, populated / empty / refused, at 375 · 390 · 768 · 1440 and 1920 dark. |

---

## 0.1 · What is on main

### 5b Release 1, line by line

| 5b asks for | on main | where |
|---|---|---|
| 1.1 `app/issues/` package, `schema.py` with `place_of` / `is_open`, a CONTRACT asserted against `init.sql`, one YAML per issue | yes — four issues (`air`, `heat`, `land`, `coast`), `CONTRACT` in `app/issues/schema.py`, asserted by `tests/test_issues_schema.py` | `app/issues/` |
| 1.2 the engine: stack, line, attribution, five states, open asks, 24 h series, sentences in three locales, per-figure provenance | yes, all of it, and `fenced_median` and `apparent` live here rather than on the page | `app/issues/engine.py` |
| 1.3 `GET /issues` + `/issues/fixtures/{name}`, `/issues` on `_SHARE_OPEN` and never on `_SHARE_OFF`, two one-line touches in `app/main.py` | yes — `app/main.py:697` carries the prefix, `:750` the `include_router`. Exactly two lines. | `app/issues/api.py` |
| 1.4 `planetai snapshot` | yes, twelve endpoints, `--out FILE`, no token written | `bin/planetai:1636` |
| 1.6 the committed fixture | yes — `app/issues/fixtures/node1-2026-09-06.json`, node #1 at 2026-09-06 14:08 UTC. **Not** under `docs/design/fixtures/`: it moved so the issues router could serve it, which is what keeps it off `/static/`. | `app/issues/fixtures/` |
| 1.5 `NODE_ISSUES` in settings, presets, docs | yes — `app/settings.py:34`, first key in `RUNTIME`, in `PUBLIC` | |

**So Phase 2 lands no part of 5b Release 1.** The third `app/main.py` touch 5b 2.3b reserved — a route
for the Sentinel frames — is also already spent: `/earth/frame.png` exists at `app/main.py:1278`.
That budget is used, and a fourth touch is a STOP.

### What the fixture actually carries, which bounds every measurement below

`node1-2026-09-06.json` is a `planetai snapshot` of node #1: `health`, `rho`, `cells`, `stats`,
`alerts`, `actions`, `observations`, `readings_1h`. It carries **no** `earth`, `sensors`, `trust`,
`nearby`, `forecast`, `place` or `report`. On a fixture render those cards therefore draw their
empty states, and the page under test is thinner than a live node's.

Replayed through the engine it gives: order `air, coast, heat, land`; headline **air**, state
`quiet`; heat `quiet`; coast `context`; land `none`; **zero open asks on any issue**. So the fixture
exercises "nothing to do" and never exercises `act`, the ask strip, or a red numeral.

### Findings inherited, by id

Not re-opened and not re-argued. This is what is still open on the surface the redesign replaces.

**Part 1, the walk.** 44 of 64 closed, 2 half (N9, L3), 1 withdrawn (R1), 1 routed to Tomas (R3),
**16 open**, plus **X1** which is filed in §2.6 rather than in a view table.

| id | P | what is still true | the redesign's answer |
|---|---|---|---|
| **L2** | **P0** | the wall shows a model estimate in 120 px type and never names a source or says `model`. `ANATOMY.wall` carries no `chips` and `miniStack` is not on it | composition: T3 and T4 make a numeral without a source undrawable |
| H3 | P2 | no skip link | the new skeleton |
| H8 | P2 | the header is not sticky, so the node's name, version and freshness are unreachable below the fold | Phase 1 decides; the as-of is a T1 leg |
| N13 | P2 | the REGION source chip wraps inside its own border at 390 | the chip's own measure |
| N14 | P2 | index rows' accessible names run together; unwatched rows are `aria-disabled` and still focusable | the index is Phase 1's argument |
| N15 | P2 | nav buttons 32 px tall and **I did this** 76×36 — above the 24 px floor, under the 44 pt advisory | advisory |
| N16 | P2 | every dot on the scale and every POI on the plan names itself in an SVG `<title>` only — hover, so not on a phone, not by keyboard, not on the wall | T5: a mark with no reachable name has no link |
| W5 | P2 | an em dash where a zero belongs on the Index row | |
| W6 | P2 | the network figure's six facts are `<text>` inside one `role="img"`; `.netlist` is hidden at width | |
| S10 | P2 | Save has no in-flight state and can fire two PUTs | 2.5 |
| S13 | P2 | Set up is not a `<form>` | 2.5 |
| L5 | P2 | the wall's empty states are bare fragments where a photograph belongs | T7 and the wall's own floor |
| L6 | P2 | the wall prints the res-8 cell caption where a street can read it | Decisions to revisit 6 — Tomas's |
| A6 | P2 | entering Arrange re-lays the hero it is arranging | 2.5 |
| A7 | P2 | three vocabularies for one action (`Move up` / `←` / "← and → move a band") | 2.5 |
| A8 | P2 | Arrange runs with no token and only says so at Done | 2.5 |
| X1 | P2 | `GET /static/fonts/jetbrains-mono-latin.woff2` 404s on every load, from `planetai-theme.css:27`. Silent, and forgiven by name in both gates | stays forgiven |
| N9 | half | the loop band's empty states are translated fragments with no instruction, beside bands that name the exact command | |
| L3 | half | the wall says *when* now; how loud `stale` is at three metres is a size decision | **T7** |

**Part 2, the skeleton.** S-01, S-02, S-04, S-07, S-11 and S-12 closed. **Twenty are open**, and
these are the ones the redesign is accountable for:

| id | P | what is still true | measured again here |
|---|---|---|---|
| **S-01** | **P0** | closed at 1920 and at 390; **open at 1440** | measured on this branch: the wall is **1,052 px on a 900 px viewport**, and five runs fall below a fold that does not scroll — the ρ caption, `bayu-2`, `As of 22:08`, **`stale`**, and "Answer on Telegram, not here" |
| S-03 | P1 | ten of the wall's thirteen text roles under the three-metre floor | **T7**: issue line 7.5 mm, ρ caption 5.7 mm, against a 9 mm floor |
| S-05 | P1 | the loop band is the tallest thing on the page | now **23.9 %** at 390 and **22.4 %** at 1440, against air's 21.5 / 20.0 — still the tallest at 1440 |
| S-06 | P1 | 193 of 199 prose runs under 16 px on a phone | |
| S-08 | P1 | the hero's ground drawing is the largest mark on the phone's first screen | **T2**: the gap between the two empty readings is this finding with a number on it |
| S-09 | P1 | 72 type combinations; sixteen sizes carry more than one meaning | |
| S-10 | P1 | the outline begins at h2 with the second largest thing on the page | |
| S-13 | P1 | 28 of 41 spacing values off the 4 pt measure, 60 % of instances | the layer names no scale; Phase 1 says whether it should |
| S-14 | P1 | six views, five left edges at 1440 | |
| S-15 | P1 | the wall carries the laptop's word count at 12.2 % unmarked ground | **T2 read**: 81.1 % of the wall carries no reading |
| S-16 … S-26 | P2 | rhythm, z-index, the save bar over the gate, the anatomy's four vocabularies, `unitRow` and `readout` sharing a class, `.btn` two ways, the missing `<footer>`, two container systems, Arrange's relayout, wrappers with no layout role, butted nav targets | S-19 and S-20 are what T3 and T5 are about |

### Which improvement-plan PRs touched `app/static/`

| PR | what it was | status |
|---|---|---|
| PR 5 | Cancel means cancel; `layoutReset` writes the same empty `UI_LAYOUT`; `esc()` gains `'` | **landed inside the renderer.** `act()` returns on `note === null` (`dashboard.js:1981`), `layoutSave(reset)` writes the same empty `UI_LAYOUT` (`:2086`), `esc()` escapes `'` (`:404`) |
| PR 11 | wrap every card in `card()` inside `refresh()` | **superseded.** `refresh()` no longer exists; `piece()` (`dashboard.js:1364`) draws every component inside its own guard, which is the same guarantee structurally. 5b's realignment note 6 predicted exactly this |
| PR 3 | three string sites at `index.html:459`, `:1038`, `:1049` | superseded with the file |

Nothing from the improvement plan is pending against the page. The last two commits to
`app/static/` are the design-language fixes (#44–#48) and the UX review's fixes (#57).

---

## 0.2 · The shipped page against the targets

Every number from `tests/visual/measure.mjs` against `?fixture=node1-2026-09-06` on `:8081`.
Screenshots: `now_populated_{390,1440}`, `wall_populated_{390,1440,1920_dark}`, fold and full page.

| target | what it asks | shipped | file:line that causes the miss |
|---|---|---|---|
| **T1** @ 390 | sentence · numeral · state word · the ask **or "nothing to do"** · as-of, all without scrolling | ✓ ✓ ✓ **✗** ✓ | `dashboard.js:965` — with no open ask `askStrip` returns a `hidden` div. The page has no words for "nothing to do"; `WORDS` has `noAsks` and it is only ever the ρ row's empty state |
| **T1** @ 1440 | the same, plus every declared issue's row and the mini stack | ✓ ✓ ✓ **✗** ✓ · 4 of 4 rows ✓ mini ✓ | same |
| **T2** empty @ 1440 | ≤ 30 % | **36.2 %** as written · **69.5 %** discounting the page's own decoration | `dashboard.js:1406` puts a full-bleed `node-ground.svg` behind the hero inside `aria-hidden`; `dashboard.css:173` gives the hero a 1.5fr/1fr grid whose right column holds only the ρ row |
| **T2** empty @ 390 | ≤ 20 % | **21.3 %** · **56.3 %** discounted | same |
| **T2** height @ 1440 | ≤ 4 viewports | **5.7** (5,115 px / 900) | loop 22.4 % and figures 11.4 % of the page |
| **T2** height @ 390 | ≤ 8 viewports | **8.9** (7,978 px / 900) | loop 23.9 %, air 21.5 %, figures 17.3 % |
| **T3** | four card kinds, named and counted by `check_ui` | **0 declared.** No `data-kind` anywhere. Counted from the code, the interface has **24 distinct grammars** (below) | `dashboard.js:737` — `COMPONENTS` names parts, not kinds |
| **T4** | every numeral carries unit, source, age and a comparison, or the pack's stated reason | **0 of 0 declared**, against **26 numerals drawn** at 1440 | no `data-num` / `data-cmp` exists. The Stack does carry source + pill per column (`:788`); `readout` carries source and pill (`:936`); nothing carries a *comparison* except the sentence's `{cmp}` |
| **T5** | every `[data-component]` except header and hero links in or out | **47 of 47 orphaned** at 1440, 5 of 5 on the wall | no `data-ref` exists anywhere. `indexRow` is the one real link on the page and it is an `href="#band-…"` (`:1040`), which no gate can read as a link |
| **T6** | reading order = DOM order in the first viewport | **19** elements at 1440, **14** at 390, out of rank | `dashboard.css:173` — the two-column hero puts the ρ row 13th by position and 28th in the DOM (the skeleton's own reading) |
| **T7** | sentence, numeral, every issue line and the ρ row ≥ 9 mm at 1920 | sentence 34.0 ✓ · numeral 80.9 ✓ · **issue line 7.5** ✗ · **ρ caption 5.7** ✗ | `dashboard.css:571–572` (`.wall .wi .st`, `.wall .wi .ln` clamp to 12/17 px) and `:340` (`.rhocap` inherits `.note`'s 13 px) |
| **T9** weight | under 60 kB per refresh | **28.3 kB / 16 requests** live · **79.4 kB / 3** under `?fixture=` | the fixture path refetches the whole 75 kB snapshot every twenty seconds. On the live path `/settings` is 15 kB of the 28 and `/static/node-ground.svg` is 4 kB, re-sent every render because the route builds the SVG and sends no ETag (`app/main.py:1526`) |
| **T9** axe | zero serious/critical | **0** on Now at 390 and 1440 and on the wall at 1920 dark | — |
| **T9** SVGs | every one named or `aria-hidden` | **0 unnamed** of 95 on Now, of 123 on the wall | — |
| **T9** motion | reduced motion stops everything, SMIL included | **0** still moving | — |

**T2 is reported twice on purpose.** The target counts a pixel as full if it sits inside anything
carrying "text, a mark, a sign, an image or a control", and a decorative full-bleed background *is*
an image — so a page can pass T2 by putting a picture behind everything and saying nothing. The
second reading drops what the page itself marked `aria-hidden`, which is the page's own statement
that a mark carries no reading. On this page the two readings are 36.2 % and 69.5 % at 1440, and the
thing between them is the hero's ground. **Phase 2 must beat the target as written and report both.**

**The card grammars, counted again from the code.** The review found six on the page this replaces.
Today, counting distinct root containers that hold a value and its explanation: `stack` (and its
`mini` variant), `unit` as `readout`, `unit` as `unitRow` (two grammars, one class — S-20),
`sensorCard`, `indexRow`, `ledger .al`, `figs tr`, `rhoRow`, `ring`, `stations`, `forecast`,
`trustCard`, `satellite`, `planCard`, `report`, `day`, `scale`, `vitals .vit`, `cellrow .pillar`,
`peer`, `netMap`, `field`, `pack` — **24**. Twenty carry `data-component` on Now; seven composites
carry none (S-19).

**Two things the fixture cannot show**, and no claim below rests on them: the plan, the satellite
loop, the ring card, the forecast strip and the sensor cards all draw empty states, because the
snapshot carries no `place`, `earth`, `nearby`, `forecast` or `sensors`. And no issue is in state
`act`, so the ask strip, the green button and the red numeral are unexercised.

---

## 0.3 · What the page will have to hold

From the release ladder and the packs that are specified but not built. **Two inputs named in the
brief were not reachable from this machine**: `PLANETAI_Response_Funnel_Briefing_2026-09-10.md` and
`PLANETAI_Models_by_Node_Class_2026-09-14.md` live in the PLANETAI project and are on neither disk
nor any branch here. The funnel's four stages and 2×2 below are taken from the brief's own wording
and from `ARCHITECTURE.md §3`'s four action stages; anything finer in those memos is unread.

| thing | release | issue it belongs to | the slot it needs | a place for it today |
|---|---|---|---|---|
| the ρ funnel: reached / acknowledged / deployed / closed, four latencies, the 2×2 | v0.46 (named), unbuilt | the loop, not an issue | `loop.funnel` — a wall object as well as a page one | **no.** `rhoRow` draws one ring per ask and a caption; there is no stage, no latency and no 2×2 |
| `kind: condition` alerts that never drive `act` | reports Release 3 | every sensed issue | no new slot; the engine's state machine | **no.** `_state()` has no notion of a condition kind; the current-condition test stands in for it |
| `hazard` pack — GloFAS, FIRMS, LHASA, sea level. Display-only, region column only, external, never `act` | unbuilt | a new issue, or a region-only column on existing ones | `stack.region` with an external provenance word, and a rule that it can never reach the ask strip | **partly.** `stack.region` exists; nothing marks a column as never-actionable |
| `noise` pack — NoiseModelling, community node | designed (`PACK_IDEAS.md`) | a fifth issue | its own `issue.yml` + `stack.*` | **yes**, by construction: a fifth issue is a fifth YAML |
| `make` pack — a design and a nearest facility named on an ask | proposed (`docs/proposals/make-pack.md`) | the issue whose rule carries `fabricable:` | `ask.line` — one sentence under an ask | **no.** `askStrip` renders the alert's first line and one `how`; nothing can add a line |
| Chronos-2 quantile band in `forecast` | unbuilt | air and heat | `band.series` with a `derived` quantile band, never a verdict | **no.** `day` draws polylines and one threshold rule; it has no band |
| TESSERA embeddings beside AlphaEarth | unbuilt | land | a second `band.media` with its own pill | **partly.** `satellites` already draws two records with two pills (`dashboard.js:1312`); a third is a code change |
| `PEERS` — other nodes, display-only, a Network row and possibly a ring value marked `peer` | v0.48 shipped the announce; the row exists | the Network view; the ring | `network.row`, and a stack cell carrying `peer` | **partly.** `peers()` draws Reticulum peers on Network. A `peer` value in a stack column has no word: the provenance vocabulary is live/partial/model/cached/example |
| custody children rolling up to a community node | v0.50 | every issue | a sub-index, or a column per child | **no.** `DISTANCES` is four and `place_of` returns `child` as a fifth place that no column draws |
| airRohr and other people's sensors | unbuilt adapters | air | more sensor rows, a kind chip | **yes.** `sensorCard` carries a chip and `sources` lists what the engine used |
| `SHARE_LEVEL` rungs `cell` and `means` | reserved, refused today | — | a page that shows less, and says which rung it is on | **partly.** The refused page draws the node's own sentence; there is no intermediate state |
| Set up → Issues pane: drag order → `NODE_ISSUES` | 5.24, unbuilt | — | the Set up row grammar plus an ordering control | **no.** `NODE_ISSUES` renders as a free-text box like any other key |
| Bahasa and Spanish on every string | shipped, unread | — | — | **yes**, and unverified: several hundred assistant-written lines rendered for the first time in v0.53 and read by nobody who speaks them |
| the plan with the res-9 mesh and res-8 outline | `NODE_DASHBOARD_PLAN_SPEC.md`, ~15 lines | the place band | `place.layer` | **no.** `planCard` draws buildings, roads, green, sat and poi; `kilometre-cells.json` is served and never read by the page |
| a `water` pack from a stranger | the extension contract itself | a new issue it declares | every slot in 2.1 at once | **no.** This is what Phase 2 builds |

---

## 0.4 · What every pack already declares that the page could use

Read from `packs/*/pack.yaml`, `rules.yml`, `cells.yml` and the scripts each ships. This is the raw
material for the `ui:` block: a pack that already names its domain, its metrics and its thresholds
should not have to name them twice.

| pack | kind | domain | metrics declared | thresholds | cells | scripts / `out/` | what a `ui:` block could fill from it today |
|---|---|---|---|---|---|---|---|
| air-quality | data | air | pm25, pm10, pm1, humidity | prose: US EPA / WHO 2021 | `Environmental\|Community` ×2, `Environmental\|City` | — | `stack.*` for pm25 (the four distances are already in `air.yml`); `band.readout` for pm10/pm1 |
| nearby | data | air | pm25, pm25_raw, pm10, pm1, temp, humidity | — | none, by design | `stations.py`, `backfill.py`, `verify.py` | `stack.ring`; `band.unitrow` for stations counted; the ring's shape is a `band.series` candidate |
| heat | data | heat | temp, humidity | prose, and the numbers are in the rules: 35 °C AT, 28 °C overnight, 32 °C for the Social cell | `Social\|Community` | — | `stack.*` for apparent temperature; `band.readout` for the night minimum |
| coast | code | coast | wave_height_m, wave_direction, wave_period_s, swell_height_m, swell_period_s, sea_surface_temp | — | `Environmental\|Bioregion` | adapter | `band.readout` ×3 (this is what `coast.yml`'s `readouts:` already does); `compare: none` with a reason, since a swell has no line |
| posidonia | data | coast | sea_surface_temp | **28.4 °C**, Marbà & Duarte (2010), measured 90 km away | `Environmental\|Bioregion` | — | `band.readout` with a real `compare: line`; the only pack whose threshold was measured in the same water |
| earth | code | land | land_change_yoy, land_change_since_2017, years_cached | — | `Environmental\|City` | `fetch`, `change`, `frames`, `similar`, `status`, `verify` → PNG frames in `out/earth/` | `band.media` (the frames, with `model`), `stack.region` (the share over threshold — `land.yml` already reads it) |
| earth-engine | code | land | tree_frac, built_frac, crop_frac, water_frac, ndvi_median, night_lights | — | `Environmental\|Bioregion` | `timelapse.py` → Sentinel frames, `verify.py` | `band.unitrow` for built and trees at one sign per share; `band.media` for the Sentinel loop |
| forecast | code | weather | fc_temp, fc_humidity, fc_wind_speed, fc_wind_direction, fc_cloud, fc_rain, fc_lead_hours, fc_temp_gap, fc_wind_speed_gap | — | none, by design | `fetch`, `status`, `verify` | `band.series` on air and heat with a 24 h horizon; this is where a Chronos-2 quantile band would go |
| place | code | place | 22, from `sat_buildings` to `nearest_worship_m` | — | `Economic\|Community` | `refresh`, `gaps`, `satellite`, `verify` | `place.layer` (the geojson the node already serves), `band.unitrow` for mapped vs orbit-only |
| trust | data | cross-domain | — | 60 % coverage, a week of data | none, by design | — | a finding beside the sensor it doubts — which is a `data-ref`, not a slot |
| insight | data | cross-domain | — | — | none | — | `band.readout` from `bundle.<rule id>`; its rules are claimed one by one in `air.yml` |
| cold-start | data | cross-domain | — | — | none | — | the region column on a node with no sensors; claimed by `air.yml` and `heat.yml` |
| open-data-health | data | governance | — | 90 days | `Governance\|City` ×2 | — | the Network view's Index row, not an issue band |
| example-cooking-hours | data | air | — | — | none | — | a worked example of a rule that belongs to an issue by name |

**What no pack declares today, and the `ui:` block will have to carry:** a unit's decimal places, a
source word in three locales, which of its metrics is the headline, and what to compare a number
against. `pack.yaml`'s `thresholds:` is prose in every pack that has one — which is why `air.yml`
writes WHO 15 itself and `tests/test_issues.py` greps the rule's SQL to stop the two drifting.

---

## Blockers

**None for Phase 1.** Two things are recorded rather than solved:

- **The two PLANETAI-project memos are unreachable** (funnel, models by node class). The funnel's
  shape in 0.3 is the brief's own wording. If either memo says something finer, 0.3's funnel row and
  Phase 2's `loop.funnel` slot are the rows to re-read against it.
- **The committed fixture has no `act` state and no open ask**, and carries none of `place`,
  `earth`, `nearby`, `forecast`, `sensors`, `trust` or `report`. Phase 1's directions are drawn on a
  hand-extended copy of it (the three synthetic contributions), and a direction that shows an ask
  strip, a plan or a satellite loop is showing something this fixture cannot prove. Each direction
  says which of its parts are drawn from the fixture and which are drawn from the extension.
