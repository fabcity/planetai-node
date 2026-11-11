# SPEC: the Place report, a sheet and a few pages to print

*Asked, 11 November 2026, by Tomas: "I want to build a tool for the place section to provide the options for people to
download their place analysis similarly to this tool that is published online here: https://urban-scan.ildar.space/app.
I also want for the place section to be able to provide the download of reports, similarly as we do in the index page
per city, when we allow people to download a report as pdf." Of the two scopes offered, he chose the small one: "Spec the
one page". It goes in v0.93, after v0.92 is cut.*

**Status: proposed 11 November 2026, its four open questions decided by Tomas the same day (§10). Nothing is built.**
Each step in §9 is its own pull request, run on node #1 before it merges.

## 1 · What it serves

Place already lets a household download what is on its screen: a PNG with the scale and the credits drawn into it, and
each of its named maps as GeoJSON, KML and DXF (SPEC_place_microgis §4). None of that is something you can hand to the
neighbours, the banjar, a council or a funder. The Fab City Index has that for a city: a report page that prints, or
saves as a PDF, from the browser (index.fab.city/report).

This spec gives Place the same. One page on the node, opened from the Download menu, holds:

- **the sheet**, the map on the screen drawn as a plan, with a frame, a grid in metres, a scale bar, a north arrow, a
  legend, the coordinates and the credits;
- **the report**, a few pages after it, with the place in figures, what the node holds about its place and what it
  does not, what changed year on year, and the sources with how to cite them.

The browser's own print turns it into paper or a PDF. The node's server gets nothing new, and no PDF library comes in.

## 2 · What urban:SCAN does, and what this takes

urban:SCAN (urban-scan.ildar.space) is a site analysis tool in four steps: territory, analysis, graphics,
download. Its Graphics step is the reference here, because what you set on its map is what its PDF uses.

| urban:SCAN, Graphics | Here |
|---|---|
| Thirteen graphic styles (Neon, Paper, Nolli, Noir…) | Two registers: **Paper**, the node's light palette (`PAL.light`, already in doors-placemap.js), and **Screen**, the black one Place draws in. Paper is the default because it prints. |
| Layers on, off and in order | The cake's switches as they are on the screen. The sheet draws what the screen draws. |
| Grid, frame, scale bar, north arrow, legend, coordinates | All of them, fixed, always on. There are no switches for them. |
| Markers with captions | Already on Place: the drawing keys (marker, line, area, note) and the named maps. |
| Colour editor | Left out. |
| Sun path | Left out until Sun and shade is a tool (SPEC_place_analyses step 3). |
| 3D scheme, exploded layers | Left out. It needs a 3D view Place does not have (the map is flat, `maxPitch: 0`) and its own spec. |
| PDF, SVG, PNG, TIFF, KMZ | PDF through the browser's print. PNG, GeoJSON, KML and DXF stay where they are. SVG, TIFF and KMZ are left out: KML already opens in Google Earth, and a GeoTIFF is a raster the node does not compute. |
| Its analyses (heat island, flows, housing value…) | Not taken. SPEC_place_analyses decided which analyses Place runs and turned the others down under the open rule. Each one that lands later adds its colour ramp to the legend (§4). |

## 3 · The page

**Where it opens.** The Download menu on the screen's right edge gets one more line, under Everything on the screen:
**Report, to print or save as PDF**. It opens `#place/report`, a view inside doors.html, so the page keeps the node's
data, its token and its helpers.

**What happens on the press.** The page takes the picture first, then opens the view:

1. It switches the map to the register chosen (Paper the first time), waits for the map's `idle`, and keeps a copy of
   the canvas, the drawings included, as the PNG download already does (`screenImage()`, without its dark strip).
2. It puts the map back in the black register, so Place looks the same when you come back.
3. It opens `#place/report` with that picture and the map's bounds, zoom and scale rung.

The sheet is whatever the screen was showing: the rung in view (Street, Block, Cell, Village, District), the layers on,
the satellite or the streets, and the maps shown. There is no separate extent picker. To print the seven cells, go to
Village and press Report.

**On screen**, the view has one bar at the top: **Paper · Screen**, **Print or save as PDF**, and **Back to Place**.
Under the bar are the pages, as sheets on a grey ground, as the Index's report shows them. A change of register goes
back to the map, takes the picture again and returns. On a phone the sheets fit the width and the bar wraps.

**In print**, the bar, the doors' top line, the side menu and the Ask pane are hidden. The sheet is A4 landscape and the
report pages are A4 portrait, through named pages (`@page sheet { size: A4 landscape }`, `page: sheet`). A browser
without named pages prints everything portrait and the sheet scales to fit, which is acceptable.

## 4 · The sheet

One page, laid out like urban:SCAN's Map tab: the map on the left in a black frame, a column on the right.

- **The map**, the picture from §3. It is north-up, because Place never rotates.
- **The grid in metres.** Lines across the map at a round step (1, 2 or 5 × 10ⁿ m) that gives five to eight lines on
  the longer side. Each line is labelled from 0 m along the left and the bottom edges, with a small cross where two
  lines meet. The metres come from the map's own figure for the zoom (`mPerPx`), already used for the scale bar.
- **The scale bar**, under the map: the same round length the PNG uses, drawn as alternating black and white blocks.
- **The north arrow**, fixed, because the map is north-up.
- **The legend**, in the right column, top to bottom:
  - the title, the node's name, then "Place" and the rung ("Cell, res 8");
  - each layer that is on, grouped under its cake section in the cake's order (doors-cake.js `cakeSections`), with
    its name and its source;
  - each named map shown, with its colour from the node's palette;
  - an analysis's colour ramp, its unit and its two ends, once Place has an analysis (none yet).
- **The coordinates line**, under the legend: the centre of the node's res-8 cell to four decimals (the point
  `/health` publishes), the sheet's width in kilometres, the grid step, and the cell's id.
- **The credits**: `creditList()`, the same words the screen and the PNG carry, plus "Made on PLANETAI <version>,
  <date>" and the node's name.

The sheet is drawn as HTML and one SVG over the picture (the grid, its labels, the crosses, the scale bar and the
arrow). The picture is the canvas at the screen's pixel ratio, about 150 to 200 dpi from a laptop screen. If a large print
looks soft, the next step is to render the canvas off-screen at print size.

## 5 · The report

Up to four pages after the sheet, each with a head line (node name · Place report · page n of N), as the Index's pages
have. A page with nothing to say is left out, so N is counted from what is there.

1. **The place in figures.** The rows of Place's lower band (`#pfigures`): the issues' yearly figures, Rivers, and the
   city's Fab City Index row with its link to the city's own Index report
   (`index.fab.city/report?locality=<place>`), which says the rest about the city. The rows come from the same
   functions that fill the band, called into the report. They are not copied as HTML.
2. **What the node holds about its place.** The cake, section by section (`cakeSections(LAYERS, PM.on)`): each row
   held, held in part or not yet, with its source and, where a row is empty, the command that fills it, as the cake
   says it on screen. This is the inventory, and it shows its gaps the way the Index's DIDO shows a city's.
3. **What changed, year on year.** The satellite then and now and the hectares that changed (`#pchange`, from
   `GET /earth`), and the buildings the satellite counts, a bar a year (`GET /history`). Left out on a node with no
   satellite years.
4. **Sources and how to cite.** Every credit the sheet and the pages owe, with its licence as the node already words
   it (`creditList()`, `D.earth.credit`, the hydro and Index lines). One short line says that a map made from
   OpenStreetMap is a Produced Work under the ODbL, so it carries the credit and nothing more. Then a citation line:
   "<node name>, Place report, cell <res-8 id>, PLANETAI <version>, made <date>."

Each figure keeps its provenance word (live, partial, model, cached) as `prov()` draws it on screen. A report that
dropped them would be making the numbers look surer than they are.

## 6 · Privacy

A report is made to leave the house, so it follows SPEC_eyes §2: the house's own res-10 cell blurs on anything that
leaves. It holds less than the PNG of the screen, which still draws the kit at its point.

- **With the token**, the sheet draws what the screen draws, except at the house. The outdoor kit, and any image taken
  inside the house's res-10 cell, are drawn as that cell, filled, never as points (Tomas, 11 November 2026: yes, blur
  it even with the token). The cell's outline comes from `GET /geo/cell?res=10`, since the page carries no h3-js.
  Drawings stay as they were drawn: a marker someone placed on the house is their own choice.
- No text on any page is closer than the res-8 cell: the coordinates line is the cell centre, never the house's point.
- **Without the token**, Place draws no map of the house (SPEC_place_microgis §8). The sheet says so in the node's own
  sentence, where the map would be, and the report pages carry what a tokenless screen sees: the cake's rows with
  their sources and the yearly figures.
- **Never on any page**: rooms, indoor sensors, the species list (token-only and the household's), the photos' own
  locations, `.env` values or the node's key. The node ID may appear, since `/health` publishes it.
- Nothing is sent anywhere. The PDF is made by the browser, on the household's own machine.

## 7 · What exists and is reused

- `app/static/doors-placemap.js`: `screenImage()`, `creditList()`, `mPerPx`, `SCALES`, `LAYERS`, `PAL.light` and
  `style(p)`, the Download menu (`dlMenu`).
- `app/static/doors-cake.js`: `cakeSections`.
- `app/static/doors-place.js`: the figure rows (`figures()`, `indexRow`, the hydro row), `layer()` for what changed.
- The Index's report (fci-3-prototype `report.html`, `js/report.js`, `css/report.css`) for the page layout and the print
  CSS: the sheets on screen, `break-after: page`, the head line on each page. Only the approach is copied: the node's
  CSS uses its own tokens.
- Nothing new on the server. No endpoint, no table, no schema change, no setting.

## 8 · Tests

- A lifted-function test under tests/, named for this page (test_place_report.py): the grid step for widths from 50 m to 40 km, which must give
  five to eight lines; the legend's rows and their order for a fixed `LAYERS` and `on`; the page count when pages are
  empty; that no page's text holds the house's point (node #1's capture as the fixture); and that the sheet's layers
  hold no kit or image point inside the house's res-10 cell, only the cell. The JSON goes in through
  stdin, never argv, because of the 128 KB limit on Linux CI. Its line goes in `tests/all` and the count goes up by one.
  Only one branch at a time may change that count (NEXT_RELEASE rule 1), and the energy and seven-cells branches both
  add suites, so this one waits its turn.
- The visual gate gets a `report` stage: `#place/report` with print media emulated, checked at A4 for the sheet's
  frame inside the page, the legend not clipped, and no page overflowing onto a blank one.
- Node #1 on the branch before merge (the standing rule): print it to PDF from its own screen, at Cell and at Village,
  on Paper and on Screen, with the satellite and with the streets, and once without the token.

## 9 · Steps

1. **The sheet.** The Download line and a Tools menu row (`place.report`, opening the same view), the register switch with the picture taken, `#place/report` with the sheet, the
   print CSS, the test, the visual gate stage, the docs.
2. **The report pages.** The four pages of §5 under the sheet, and the test's page-count cases.
3. **Asking for it.** "Make me the place report" in the Ask pane. Place's command registry (`GET /place/tools`,
   SPEC_place_microgis §6) is not built yet, so the first form is one pane tool, `place.report`, in
   `agent_loop.PANE_TOOLS` with its `TOOL_CLASS`. It is offered only on a screen holding the token, takes the register
   (Paper unless asked otherwise), and answers with the link to `#place/report`, which the pane draws as a button. The
   person still presses Print: the agent never makes the PDF. When the registry lands, the tool moves into it. The
   Tools menu on Place lists it from step 1, with its id, so the command is visible before the agent can call it.

Each step lands with its line in the CHANGELOG, a section in `docs/site/place.md` ("Print the place, or save it as a
PDF") with a picture of the sheet taken from node #1, and the milestone v0.93.

The one non-goal line in SPEC_place_microgis §2 that said "no print layouts" now says what it meant: no layout
designer. Place has this one fixed sheet. A designer, if one is wanted, is the fab lab node's (SPEC_fablab).

## 10 · Decided, 11 November 2026

Tomas answered the four open questions of the first draft: "1. yes, 2 light, 3, yes, yes".

- **The house on a sheet that leaves:** blurred to its res-10 cell even with the token (§6).
- **The default register:** Paper, the light one (§3).
- **Asking for it:** yes, as step 3 (§9).
- **3D:** its own spec, later. urban:SCAN's 3D scheme is a tilted, exploded view of the layers; on the node it would be
  the cake's sections on deck.gl, then a PNG of it on a page of the report. Nothing in this spec waits for it.
