# Handoff — the earth pack (AlphaEarth)

What shipped in v0.33, what was measured, what was decided and why, and what still needs Tomas. Scope was
E.1 + E.2 + E.4 of `claude/PLANETAI_AlphaEarth_Integration_Plan.md` (6 Sep). E.3, E.5, E.6 and E.7 were not
started.

## Tracker rows for `claude/PLANETAI_Next_Steps_Tracker.md`

| row | was | now |
|---|---|---|
| E.1 the pack | planned | **done** — `packs/earth/`, one `partial` cell, `GET /earth`, one dashboard card, rehearsed on the Lima node |
| E.2 the Kuta Selatan exhibit | planned | **done** — `out/earth/exhibit_kuta_selatan_2023_2025.html`, built from node #1's own coordinates and its published air record |
| E.3 the NAS mirror of `out/earth/` | planned | **done** — `tools/nas/pull.py` archives the results, not the cache |
| E.4 the observatory card | planned | **done, not deployed** — two commits in `fabcity/planetai`, `make check` green |
| E.5 the academic sample application, 15 Oct | planned | **needs Tomas** — see below |
| E.6 | planned | not started |
| E.7 | planned | not started |

## What was measured

Every number below was produced by running the thing, at node #1's coordinates (−8.8271, 115.15709) unless
it says otherwise. Nothing here is extrapolated from the plan's arithmetic.

| | measured |
|---|---|
| anonymous read of `gs://alphaearth_foundations` | works. Listing, HEAD and ranged GET, no credentials, no billing project, about 1.5 GB pulled during this work at no charge to any project of ours |
| the file | 8192×8192 px, 64 bands, `int8`, nodata −128, tiled 1024×1024, **planar-separate**, **zstd**, overviews 2…8192. Exactly what the bucket's README claims |
| de-quantised unit norm | 20,000 real pixels: mean 1.000093, min 0.99242, max 1.00847, σ 0.00203. Every one inside 1e-2. On the raw integers the norms are ≈ 321 |
| tile index | 26 range reads, 189 kB, 30 s to binary-search `aef_index.csv` by UTM zone, then one block: 8.8 MB for 50S, 9.1 MB in the shipped run. 3,351 rows, one tile per year covers the point |
| one AOI-year, 10 km square | **64,000,128 bytes on disk**, **~103 MB over the wire**, **149 s** cold on the laptop (71–184 s under contention) |
| nine years | 576 MB kept, 925 MB pulled, ~22 minutes |
| Bali, three years | 2023, 2024, 2025 in 359 s, 192 MB |
| Santiago (`pai-clean`), two years | 2024, 2025 in 215 s, 128 MB, UTM 19S |
| image growth on `planetai packs install` | **458 MB → 710 MB (+252 MB)**, 8 min 56 s to rebuild on the arm64 Lima node |
| `libexpat1` | 436 kB installed |
| change, Bali 2024→2025 | mean 0.0414, median 0.0393, p95 0.0926, max 0.4286; 1.19 % over 0.15 = 119 ha |
| change, Bali 2023→2025 | mean 0.0650, median 0.0618, p95 0.1490, max 0.6274; 4.92 % over 0.15 = 492 ha |
| change, Santiago 2024→2025 | mean 0.0151, median 0.0128, p95 0.0317; 0.10 % over 0.15 = 10 ha |
| the card | 375 / 768 / 1440 px: contributes no horizontal overflow at any width, the pill stays visible, the 1000 px image renders at 297 / 657 / 643 px inside its card, always inside the card's right edge, the row collapses to one column under 900 px |
| `similar`, four pilots | 39–47 s each, most of it the index lookup. Best in-tile match: Bali 0.986 at 7.8 km, Santiago 0.994 at 7.2 km, Boston 0.972 at 5.2 km, Barcelona 0.942 at 5.6 km |
| between pilots, 2025 | Barcelona↔Boston **0.744**, Bali↔Barcelona 0.501, Bali↔Santiago 0.455, Bali↔Boston 0.430, Barcelona↔Santiago 0.410, Boston↔Santiago 0.391 |

## Decisions, and why

**A centred window, not one aligned to the file's blocks.** The COGs are tiled 1024×1024 internally, so a
1000 px window centred on the node straddles four blocks and GDAL pulls all four: 103 MB to keep 64 MB.
Snapping the window to a single block would cost 14.5 MB, a sevenfold saving, but for node #1 it would put the
node 2.1 km from one edge of its own square and 8.1 km from the other. The product is "the land around here",
so the node stays in the middle and the bandwidth is stated instead of hidden. `EARTH_RADIUS_M` is the knob.

**Band by band, not one `ds.read()`.** Reading all 64 bands in one call took nine minutes; one band at a time
takes 149 s. GDAL's default block cache is smaller than the 256 MB a 64-band window touches, so blocks were
fetched, evicted and fetched again. `GDAL_ENV` in `adapter.py` also raises the vsicurl range chunk from 16 kB
to 256 kB, roughly one internal block, which cut the request count by an order of magnitude.

**Binary-search the CSV index.** There is no GeoJSON index; the forms are GeoParquet (70 MB), GeoPackage
(539 MB) and CSV (798 MB), and `pyarrow` was not approved. The CSV is sorted by UTM zone (1N…60N, then
1S…60S) with years interleaved inside each zone, so ~21 range reads find the zone's block and one read
fetches it. Stdlib `urllib` and `csv` only. The resolved tiles are cached in `meta.json`, so this happens
once per node. If Google ever regenerates the file in a different order the search degrades safely: the
caller filters the returned rows by zone and `resolve()` raises if none match.

**The threshold is 0.15, and it is the only chosen number in the pack.** Reasoning and the calibration
evidence are in `packs/earth/README.md`. Short version: at node #1 it sits at about the 99th percentile of a
consecutive-year comparison, so a normal year flags ~1 % of the square; Santiago, a mature city, flags 0.1 %.
At 0.05 — the threshold the `earth-engine` pack uses on a different quantity — a third of the Bali square is
"changed" every year.

**`Environmental|City`, `partial`, forever.** The node does the arithmetic, but the input is a Google model's
description of a place that nobody here can check against anything. `live` means measured here.

**No `rules.yml` in v0.** `earth-engine` already fires `land_changed`. A second alert for the same event is
the duplication below, not a feature.

**The attribution wording.** The prompt asked for `Satellite Embedding dataset © Google and Google DeepMind,
CC BY 4.0`. The dataset's licence asks for a specific sentence: "The AlphaEarth Foundations Satellite
Embedding dataset is produced by Google and Google DeepMind." The licence's wording ships, plus CC BY 4.0, so
the requirement is actually met. It appears in `pack.yaml`, the README, `GET /earth`, the dashboard card, the
exhibit, the observatory panel, the sensor's `meta`, and inside the PNG as a `tEXt` chunk.

## Resolved in v0.33.1: two numbers for one thing, and no alert for either

`earth-engine` published `land_change_score` — 1 − cosine of the **mean** embedding vector over 1 km, inside
Earth Engine, behind a service-account key — while the earth pack publishes the mean of the **per-pixel**
distances over 10 km, computed on the node from a public bucket. Different quantities, no agreement (0.037
against 0.041 on node #1), both `partial`, both described in words as "the land changed". Tomas chose to
retire the Earth Engine one. Done: the embedding dataset and its block are out of
`packs/earth-engine/adapter.py`, `land_change_score` is out of its `metrics:`, its second
`Environmental|Bioregion` cell is deleted, and that pack's `rules.yml` is gone. It keeps Dynamic World,
Sentinel-2 and VIIRS — what only Earth Engine can give.

**The alert did not move with it, and that was a measurement, not a preference.** The plan was to repoint
`land_changed` at `earth-point` / `land_change_yoy`. Then four pilot squares were measured for 2024→2025:

| place | mean | over 0.15 |
|---|---|---|
| Kuta Selatan, Bali | 0.0414 | 1.19 % |
| Boston | 0.0404 | 3.26 % |
| Barcelona | 0.0164 | 0.15 % |
| Santiago | 0.0151 | 0.10 % |

Boston and Barcelona sit at the same latitude and differ by two and a half times. Boston's change is spread
across built-up land — its harbour is one of the quietest parts of its own map, so this is not water — which
makes snow and deciduous leaf-off between two annual composites a far likelier explanation than 326 hectares
of Boston being rebuilt in a year. That last part is a guess; nothing here separates a season from a
bulldozer. Any threshold that fires in Kuta Selatan, where the land really is being built on, also fires in
Boston every year for nothing, and `AGENTS.md` says not to add alerts a household would ignore. So the pack
ships no rules file, `tests/test_shipped.py` pins that it must not, and the README carries the table and the
reason. A tester who ran `earth-engine` with a key loses a message they had; that is the cost of not having
one we can defend.

**What would make the alert possible.** Either a per-node baseline — fire when this year sits well above this
node's own previous years, which needs four or five cached years and a constant chosen with better evidence
than four squares of one year-pair — or something that separates phenology from structure. The dataset's 64
channels may carry that; nobody here has looked.

## E.3, done: the results, not the cache

`tools/nas/pull.py` now archives every `change_*.json` and its map from `/earth`, alongside the dumps and
exports it already pulls. Not the `.npy` embedding cache: 64 MB a year, and `planetai run earth fetch` remakes
any of it in about two and a half minutes from a public bucket Google has committed to keep publishing. What
cannot be remade once a node is gone is the record of what that node computed and when, and that is a few
hundred kB a pair.

Two small things had to exist first. `GET /earth` returns `changes`, every comparison the node computed rather
than only the latest, each with a `png_url`; and `GET /earth/change.png?pair=2023_2025` serves any of them.
The pair only selects among comparisons that exist — the file name still comes from the pack's own JSON, never
the request, and a malformed pair is rejected by the route's pattern before any file logic runs. Verified:
`?pair=../../etc/passwd` returns 422, an unknown pair 404. Rehearsed against the Lima node: two files pulled,
nothing re-pulled on the second run, and the PNG magic-byte check refuses a JSON body without writing.

## E.4, what the observatory panel does now

One commit in `fabcity/planetai`, `make check` green, **not deployed**. The RQ3 panel was
`MOCK · REAL ARCHITECTURE` with five pre-fetched cities and a "Connect RSFM →" button for a trusted-tester
programme nobody joined. It now reads `observatory/data/alphaearth_similarity.json`, written by
`planetai run earth similar`, and shows the four pilots with their closest in-tile match, the six pairwise
similarities, and one sentence saying the search covers one UTM tile and why it is not global. The pill is
`LIVE · REGIONAL` (`live-pill sm`). Without the file — including when the page is opened from disk, which
blocks the fetch — the pill degrades to `AWAITING DATA` (`partial-pill sm`) and the panel names the command
that writes it, rather than falling back to a made-up result.

Both AlphaEarth connector entries moved off `config`: the embeddings to `ready` (no account needed), Open
Buildings to `testable` (still an Earth Engine key). That raises the page's "connected" headline count by
one, which is correct but worth knowing. The modal template now says what is settled and what is not.

Verified in a browser against a local server: 4 cards of real data, the pill and its class, the scope
sentence, the footer, the modal, both connector cards, and the empty state with the file removed.

## The release, and one thing to know about the branch

`v0.33` is tagged at `fc437f9`, `origin/main` points at the same commit, and the tarball in
`../planetai/node0/get/` is v0.33, 392 kB, 157 files. Rehearsed afterwards on the Lima node: `./update.sh`
took it from v0.32.1 to v0.33 with nothing lost (4,633 readings, 13 alerts, 7 actions), the pack appears in
`planetai packs`, `planetai run earth verify` exits 0, and the card renders in all three of its states —
absent pack (hidden entirely, height 0), loaded but never fetched (the sentence naming `planetai run earth
fetch` and the measured size), and cached (the map).

**A second session was working in this checkout at the same time, and moved it twice.** First it branched
`audit/design-2026-09` off `main` after the pack commit and left the tree there, so three of this work's
commits landed on that branch; `main` was fast-forwarded to them, no rewriting, and v0.33 went out clean.
Then, after the v0.33 release, it branched `audit/design-2026-09-report` from *before* this work's last
commit and committed 209 screenshot files there — which silently reverted the handoff on disk and would have
mixed the v0.33.1 release into a design-audit branch.

So v0.33.1 was built in a separate `git worktree` at `origin/main`, and that checkout was left exactly as the
other session had it. Nothing of this work is on either audit branch that is not also on `main`. Two agents
in one working tree cost about forty minutes here and nearly lost a doc commit; the fix is a worktree per
agent, and it is worth making a rule.

## Also found, not fixed

- **The site had no JavaScript parse gate — fixed in v0.33.1.** An apostrophe inside a single-quoted string
  in the connectors list (`tab's`) broke the whole 11,000-line inline script, so the panel's render function
  was undefined and the panel came up empty, while `make check` said ok. The site's `scripts/check_html.py`
  now runs every inline script through node's parser, and the deploy workflow runs `make check` instead of
  its own copy of the tag parser, which had already drifted. Broken on purpose four ways first — the
  apostrophe, an unclosed brace, an unterminated template literal and a stray `</div>` — and each was
  caught.
- **A 54 px horizontal overflow on the dashboard at 375 px**, from `.bighex` in `app/static/index.html`. It
  is there with the earth card hidden, so it predates this work. Left alone deliberately.
- **`packs/air-quality/cells.yml:25` already publishes `Environmental|City`** (PM2.5, public reference
  stations). Two cells under one key is how the node already works — `Environmental|Bioregion` carries three
  — and `/cells` lists both with their own units. Worth a decision eventually about which cell a consumer
  should read.
- **The observatory still has a button calling `openModal('alphaearth_buildings')`,** a key that does not
  exist, so it opens "Not yet implemented". Line 6325, in the Open Buildings panel. One line. Left alone
  deliberately.
- **The observatory's footer legend and version line** (near lines 9523-9524) describe the page's provenance
  states in prose and still name only SYNTHETIC and MOCK. The AlphaEarth panel is now LIVE. The prompt
  limited the edit to the panel, its modal and the connectors entries, so they were left alone.
- **A design audit ran in this same checkout while this work was in progress** — 209 files of dashboard and
  observatory screenshots, from a second session, now committed on its own branch. Not from this work. See
  the branch note above; it is the reason v0.33.1 was built in a separate worktree.

- **Screenshots of the dashboard could not be captured** from the browser pane used here: every capture came
  back as the page's background colour while the DOM measured as fully rendered. The card was verified by
  measurement (widths, overflow, image geometry, visibility) rather than by eye.

## What E.5 needs from you

**E.5, the academic sample application, 15 Oct.** What exists now that did not before: a working, honest,
reproducible pipeline from a public dataset to a number on a node, with measured costs, and one worked
example over a real place. What does not exist: any node with more than five days of its own air record
(node #1 started measuring on 2 September 2026), so the pairing in the exhibit is deliberately unresolved and
says so. If the application wants to claim a relationship between land structure and local air, it needs a
node with a year of readings, and the earliest that can be true is September 2027. What the application can
claim now is the instrument and the method, not a result. Tell me which of those two the reviewers are being
asked to fund and the text can be written against it.

## The exhibit

Not committed — `out/` is runtime. On this laptop:

- `out/earth/exhibit_kuta_selatan_2023_2025.html` (986 kB, self-contained, the PNG embedded)
- `out/earth/bayu-2/change_2023_2025.png` (733 kB)
- `out/earth/bayu-2/change_2023_2025.json` (1 kB)

It pairs the 2023→2025 change map for node #1's 10 km square with the five days of PM2.5 the node has
actually measured, and the paragraph says in plain words that the two cannot explain each other. Node #1 was
read over the tailnet, read-only, on `GET /health`, `/sensors` and `/aggregates` only; nothing raw moved.
The generator is a one-off script, kept outside the repo because the deliverable list did not include it:
its path is in the session's scratchpad as `make_exhibit.py`. Say the word and it becomes a fifth
script in the pack.

Copy the three files into a tracked directory under docs/ only if you want them in the repo.
