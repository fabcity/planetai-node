# SPEC: what the Place door works out from open maps

*Asked, 23 October 2026, by Tomas, after reading urban:SCAN (urban-scan.ildar.space): "draft a short spec for the
Place-door analyses worth taking from urban:SCAN, using only sources that pass the open rule, with modelled values
labelled." Read again on 25 November 2026, when Tomas asked which of its analyses could go to the node as a core or a
wild pack.*

**Status: proposed 23 October 2026, revised 25 November 2026. Nothing is built.** The Place door lists these tools
with "not yet". Each step in §7 is its own pull request, run on node #1 before it merges.

## 1 · Where this comes from

urban:SCAN runs 32 urban analyses on any site, in the browser, from open data. Its FAQ says the tool is a commercial
service and its code is not open, so this node copies none of it and takes only the methods, which are published ones
and are named below.

The first read took four analyses. The second, after the terrain, hydro, energy and surface-heat packs and the Place
map had landed, added roof power and what the sky and the street do at the sensor's own point. Every other analysis is in the second table of §2 with the reason it is left out, or in §9
when a wild pack or a city node is where it belongs.

## 2 · What it serves

The pack design record asks every new thing on a node which decision it informs.

| analysis | issue | the decision |
|---|---|---|
| Sun and shade | heat | Which hours the yard, the street and the roof are in sun. Also whether the outdoor sensor itself sits in sun, which is when its temperature reads high. |
| Sky and street at the sensor | heat, air | Why the nights stay warm at the outdoor kit, which the heat pack counts, and how deep the street beside it is, to help read a PM2.5 spike that stays. |
| Roof power | energy | How much electricity the best roof could give in a year, read beside the grid's fossil share from the energy pack. |
| Trees, 3-30-300 | heat, land | Whether three trees stand within 30 m of the home, whether the cell has 30% canopy, whether a park of 1 ha or more is within a 300 m walk, and where one more tree would shade the most. |
| Built form | land | How densely the cell is built, how tall, and how that changed since 1985. |
| Streets and walking | air, land | Which streets near the sensor carry through movement, to help read a PM2.5 spike, and how many everyday places a 15-minute walk along the streets reaches. It reads the network's shape and counts no traffic. |

Left out:

| urban:SCAN analysis | why not |
|---|---|
| Residents and jobs | Floor area divided by an assumed m² per person. A model with nothing measured under it, and nothing on the node decides on it. A city's own census is another case (§9). |
| Housing value | No open source. Its index is stretched ±60% around a city average. |
| Pedestrian flows, car traffic, traffic noise | Models fed by models. Noise needs traffic counts the node does not have. A city that counts its own traffic is another case (§9). |
| Pedestrian wind | A 2D slice, which its own page calls "an estimate, not CFD". The forecast pack already gives the node its wind. Across a district it waits for a city node (§9). |
| Heat island | The surface-heat pack already reads it from Landsat. |
| Satellite, its indices, building growth | The earth-engine pack reads NDVI and the tree, crop and built shares, and the earth pack the change from one year to the next. The 23 October reason, Esri imagery, no longer holds: urban:SCAN now uses national orthophotos and Sentinel-2 cloudless 2016. |
| Water flow and TWI | The terrain pack reads the upslope area and the hollow at the node's point, and "Where the rain goes" waits for its routed grid (SPEC_place_microgis). Wetness classes by percentile are not taken: they rank a square against itself, so every site would have a wettest tenth. |
| Rain and puddles | Kerbs and puddles need ground finer than the 30 m of GLO-30. Where a country opens its lidar it becomes possible (§9). |
| Land use mix, activity points | The place pack already counts the shops, warungs, schools, clinics and temples. A mix index on those counts informs nothing the node decides. |
| Public spaces, walkability | Scores whose weights are the method's, with nothing measured under them. The walk counts in §5 give the parts one by one. |
| View corridors, parking | Nothing a household decides on. |
| Public transport, cycling | City scale (§9). |
| Risks and constraints, cadastral parcels | Sources that only some countries publish (§9). |

## 3 · Sources

Each one checked against the registry's open rule (CONTRIBUTING.md in awesome-fabcity-data) on 23 October 2026,
and the two rows added on 25 November checked that day.

| source | licence | used for | verdict |
|---|---|---|---|
| OpenStreetMap, already in PostGIS through the place pack | ODbL | footprints, `height`, `building:levels`, streets, `natural=tree`, parks | passes; share-alike, see §6 |
| Google Open Buildings V3 and 2.5D Temporal, already fetched by the place pack | CC BY 4.0 | footprints and heights where the map has none, the 2016–2023 series | passes |
| Microsoft Global ML Building Footprints | ODbL | footprints where Open Buildings does not reach (Europe, North America) | passes |
| DLR WSF 3D v2 | CC BY 4.0 | mean building height per ~90 m cell, the last fallback | passes |
| DLR WSF Evolution | CC BY 4.0 | the year the ground was first built up, 1985–2015, at 30 m | passes |
| ESA WorldCover 10 m 2021 | CC BY 4.0 | tree cover share | passes |
| Meta and WRI canopy height, 1 m | CC BY 4.0; source imagery © 2016 Maxar | tree crowns and their heights, for shade | passes; the imagery is years old in most places, so its date is shown |
| PVGIS, EU Joint Research Centre | CC BY 4.0 in the JRC data catalogue; reuse allowed with the source acknowledged | sunlight on a roof's plane, month by month, at the node's point | passes; its API's rate limit is still to read (§8) |
| Copernicus DEM GLO-30 | Copernicus WorldDEM-30 licence: free use and change, its own notice and liability sentence | the ground, for shade on slopes (later, §8) | passes; carry its notice word for word |
| Sun position | NOAA and Meeus formulas | arithmetic | no data |

Not used: Esri World Imagery and Wayback (Esri's terms). Mapterhorn, whose terrain tiles mix many national sources
under licences listed one by one, so the node reads GLO-30 directly. Overture buildings, which merge the sources
above plus Esri Community Maps and add nothing the node needs. Open-Meteo for roof power, because its free API allows
non-commercial use only, while PVGIS's data are CC BY 4.0. WDPA for protected areas, whose terms bar commercial use and
redistribution.

## 4 · Derived or modelled

None of these values is measured here, so no cell they feed is ever `live`. Each value carries one of two words, and
the page shows it with the provenance sign it already has:

- **Derived** (`partial`): a calculation on mapped inputs that adds no assumption. Ground coverage from footprints,
  street integration from the map's network, sun hours and the sky over the sensor where every building's height is
  mapped.
- **Modelled** (`model`): any input is an assumption or a model's output. A height filled from Open Buildings, WSF
  or a default of 3 m per floor, a canopy from the 1 m model, the 2.5D Temporal and WSF Evolution series, and roof
  power always, since the panel and its losses are assumed.

**A value is modelled when any one of its inputs is.** Every figure that rests on heights prints how many were
mapped beside it, as in "heights: 412 mapped, 2,492 filled". Where few heights are mapped, most sun figures will read
`model`, which is correct.

Every output row carries exactly one of the two words, and the test asserts that `derived + modelled` equals the
rows, so a category cannot hide inside the other.

## 5 · The analyses

Each runs on the node, over the place pack's circle (`PLACE_RADIUS_M`), and is recomputed when the place pack
refreshes. The page draws what the node says, as the doors decision requires.

**Sun and shade.** Shadows are cast as polygons on the CPU: each building's footprint is pushed away from the sun by its
height over the tangent of the sun's altitude, every 10 minutes from sunrise to sunset, on today and on the two
solstices and the equinox. Trees cast a disc of their crown at their height. The node keeps sun hours on a 2 m grid
and per roof, and reads three numbers from them: the hours of sun at the outdoor sensor's point today, the share of
the cell's ground in shade at 13:00, and the roofs with the most sun hours in a year. Sun hours on a roof follow §4:
derived when every height and crown that shades the roof is mapped, modelled otherwise. What a roof could give is
Roof power, below. Method: NOAA solar position; the same shadow casting as urban:SCAN's, on a CPU.

**Sky and street at the sensor.** Two numbers at each outdoor sensor's own point, from the buildings with their
heights and the crowns the shade reads, and nowhere else, so no grid is computed. The sky view factor is the share of the sky open
above the sensor, read in 16 directions out to 120 m. A low one means the ground gives back less of its heat at night,
which is what the heat pack's warm nights count (Oke 1981). The street's height to width is the height of the first
buildings on each side of the street nearest the sensor over the distance between them, taken every 12 m along 100 m
of it. The deeper the street, the less of what is emitted in it leaves (Oke 1988), which is one reason a PM2.5 spike
stays. The page gives both numbers and draws no verdict from them.

**Roof power.** A year's electricity, in kWh, that panels could give on each roof in the circle, with the house's own
roof first, beside the energy pack's Today box. PVGIS gives the sunlight on a roof's plane month by month, once for the
node's point, since roofs within a kilometre share a climate. Pitch is not mapped, so every roof is read at PVGIS's
best angle facing the equator, which flatters a roof that faces the other way. The sun grid then takes off the direct
part that buildings and crowns shade, on one day a month. The assumptions are printed beside the figure: panels on
60% of the footprint, modules 21% efficient, and 82% of that reaching the plug, the figures urban:SCAN states. The
figure is always `model` (§4). It is the answer to `fit.roof` in SPEC_place_microgis, which ends in
`produce.electricity.cell`.

**Trees, 3-30-300.** Konijnendijk's rule, three parts read separately. *3*: mapped trees and canopy crowns within 30 m of
the home's point. The rule asks for three trees seen from the home, and the node draws no lines of sight, so the count
within 30 m stands in for it and the page says "within 30 m", never "seen". *30*: canopy share of the node's res-8
cell. *300*: a park of 1 ha or more within a 300 m walk along the street graph (step 6); until the graph exists it is a
straight line, and the page says "straight line" beside it. The rule says 300 m to the nearest park; the 1 ha floor
and the walk are this spec's choices, so a verge of grass does not count and a park behind a wall with no gate is not
near (§8). A tree mapped in OpenStreetMap is derived; a crown from the 1 m model is modelled. Where one more tree would
shade the most is the sun grid's longest-lit ground within 20 m of a path.

**Built form.** Berghauser Pont and Haupt's Spacematrix per res-9 child of the node's res-8 cell: ground space index
(footprint over area), floor space index (floor area over area), open space ratio, and mean floors, with the
Spacematrix class. The 2016–2023 series uses Open Buildings Temporal's counts and heights. Before it, WSF Evolution
gives the share of each child that was built up in each year from 1985 to 2015. Both series are always modelled.

**Streets and walking.** The node has no street graph today: the place pack measures "walk to the nearest" as a
straight line (SPEC_place_microgis). The graph is built from the roads the place pack already holds, with no new
database extension. On it runs angular segment analysis (Turner 2007) of the walking network within 2 km, giving
normalised choice and integration at radius 800 m and at n. One readout: where the street nearest the outdoor sensor ranks by
choice within 800 m ("in the top 10% of through-streets"). It describes the street's place in the network and says
nothing about how many cars use it. On the same graph, at 4.8 km/h, the node measures the walk to the nearest school,
clinic, market and place of worship that the place pack now gives as a straight line, and counts how many of each
kind of place a 15-minute walk reaches, with no score made from the counts.

## 6 · What leaves

Nothing new leaves at first. The sun grid and the per-building and per-segment values are built from OpenStreetMap,
which makes them a derivative database under ODbL, so they stay where `/place/geojson` already is: on the node,
behind the token.

The readouts in §5 are a few numbers per cell, kept as readings on `place-point` with the attribution the place pack
already writes, and roof power adds PVGIS's acknowledgement to it. Whether such numbers can go into the CC BY export
as they are is the question SPEC_inventory.md §7 left open. This spec does not decide it.

## 7 · Steps

1. **Heights with their source.** One height per building with where it came from (mapped, Open Buildings, WSF,
   floors × 3 m) and its word, derived or modelled, plus the "heights: mapped, filled" line. Every other step reads
   this, so it goes first.
2. **Built form**, with the series back to 1985. The cheapest analysis, and the one that checks step 1 against the map.
3. **Sun and shade**, buildings first, with the sky and the street at the sensor in the same pull request, since both
   read the same buildings. The sun on the sensor's own point answers a trust question on its own, before any tree is
   added.
4. **Roof power.** It reads the sun grid, and it comes before trees so the energy pack's Today box has a roof figure
   early. Crowns lower it when step 5 lands.
5. **Trees, 3-30-300**, which adds crowns to steps 3 and 4.
6. **The street graph**, then streets and walking. The 300 m in step 5 becomes a walk.

## 8 · Open

- **Cost on a small node.** About 2,900 buildings × 70 sun positions × 4 days of shadow polygons is unmeasured. Time
  it on node #3, the class 0 bench, before step 3 merges. The sky at one point is a few hundred rays and adds little.
- **The ground.** On a slope the hill shades too. GLO-30 is 30 m, coarse beside a 2 m grid; it waits until the
  flat version has run on node #1. Where a country opens its lidar (§9), the hill can come in at the grid's own scale.
- **The 300 m park.** The 1 ha floor and the walk are this spec's choices (§5). A smaller floor, or a straight
  line, would count more homes as near a park.
- **The ODbL export question** (§6).
- **One pack or two.** This spec puts it in the place pack, which already holds the geometries. Splitting it out is
  open if the place pack grows too large to read.
- **PVGIS.** Its API page names a rate limit, not yet read. One call per node a year should sit far below it.
- **A house with its own panels.** Where Home Assistant reports a house's panels, the energy pack has the measured
  figure. The page should then show the measured one first and the model beside it, which also tests the model.
- **Overture places** as a second source for the place pack's counts, where OpenStreetMap has few warungs. The
  registry entry passed with caveats on 21 November, and in Denpasar almost no place says whether it is still open,
  so a count there is a count of listings.

## 9 · Wild packs, and what waits for a city node

Some of what urban:SCAN does rests on a source only some countries publish. That is a wild pack (docs/PACKS.md), kept in
its own repository and listed at fabcity/planetai-wild-packs, and a node adds the ones it wants.

- **Official flood zones.** FEMA's National Flood Hazard Layer, a US federal work in the public domain, is the pattern
  for a node in the United States, and each country that opens its own flood map gets its own pack. The zone a node
  sits in is a fact the water issue can read beside the terrain pack's hollow.
- **Protected areas.** WDPA is out (§3). OpenStreetMap maps many protected areas, and the place pack can take them from
  the extract it already reads, in core.
- **Cadastral parcels.** urban:SCAN reads them in the Netherlands, France, Berlin, Estonia and Philadelphia. Each is a
  national or city source, so each is a wild pack, written when a node there asks.
- **National lidar.** Spain's PNOA lidar is CC BY 4.0 under Orden FOM/2807/2015, so a node in Menorca could read a
  2 m ground. With it the hill shades at the sun grid's own scale, and Rain and puddles can be drawn, with
  carriageways a kerb below the pavement and roofs draining away.
- **City scale.** Some analyses need more data, more compute or a stronger model than a home node has, and wait for
  a city node. Space syntax over a whole network, public transport frequency and cycling stress need the city's
  territory. Car traffic and noise stay models fed by models until the city's own counters and noise meters feed them,
  and residents and jobs until its census does. Pedestrian wind and rain and puddles across a district need a GPU
  simulation, and the second a lidar ground as well. Tree crowns and roof pitch read from the city's aerial imagery
  need a vision model, and the pitch would end the guess in roof power (§5). None of them is in this spec.
