# The Place door
<!-- checked: v0.91.0 -->

Place is the ground around the node as a small GIS, built like a layer cake: the sky at the top, the ground at the
bottom, and between them a map drawn from data the node keeps on its own disk and geometry it computes itself. It is
one of the five doors on the [dashboard](dashboard.md). Nothing from inside the house is listed or drawn here.

Five packs feed it. The `place` pack fetches everything within `PLACE_RADIUS_M` (1,000 m) from OpenStreetMap into
PostGIS and summarises it monthly: buildings and the ground they cover, shops, schools, clinics, kilometres of road,
the share of green, the walk to the nearest of each. With credentials, `earth-engine` adds Google Open Buildings
footprints and the yearly building count since 2016; `earth` adds the AlphaEarth year compare, `terrain` the
Copernicus DEM, and `surface-heat` the ground's heat from Landsat and MODIS.

## Turn it on

The place pack runs code, so it needs the switch once. If Set up › Packs loads only some packs, keep `place` among
them first, or the commands below install libraries for a pack that never polls:

```bash
planetai config set PACKS_ALLOW_CODE 1   # or Set up › Packs, which asks once before saving a key that runs code here
planetai packs install                    # builds every loaded pack's libraries into the image, once
planetai restart
planetai run place verify                 # PostGIS, OpenStreetMap, Earth Engine, Open Buildings: each step named
planetai run place basemap                # the street map, kept on the node's disk
```

The first poll fetches the kilometre from the Overpass API; later polls recompute from what is stored, and every
`PLACE_REFRESH_DAYS` (30) it fetches again. `planetai run place refresh` forces one. Every command and setting is in
[the place pack](packs-reference.md#place).

## The head

The head gives the cell's id, resolution, edge and area, and the node's position for a
screen with the token. Under it is a line to ask the node about this place (press `/` to get there; `UI_ASK=off` removes it) and
**Tools**. Below that are the layers on the left and the screen beside them.

Once a Fab City Index place is chosen and read, the head has one more line: the place, its label and its FCI or range,
and **its figures**, which goes down to the full row in the place in figures.

## The layers

On the left is a list of what the node can show about the ground around the house.
The sky is at the top of the list and the ground at the bottom. Its headings, in order, are results, microclimate,
flows, built, animals, plants, soil, water, ground and frame, and each says how many of its rows are on, or none yet. A row is one line, a dot, a name and a word
for where it comes from. A filled dot is on, a hollow one is off, and a dotted one is something this node does not hold
yet, with its source beside it, such as canopy, soil, terrain, geology, the flows log, or samples of soil and water.
Press a row to switch it on or off. The line under the screen then says what the row draws and where it comes from,
and if the row cannot draw, why: **token-only**, **not here**, **live map**, or **zoom in** and **zoom out**. Six rows
start on: this house's outdoor kit, the public stations, the species, the cell the node stands in, the street map
and the images. Once the hydro pack has fetched them (`planetai run hydro fetch`), two more rows wait under water:
Rivers draws them wider with each order and Basins the level-12 basins, the node's own brighter, and a tap on a
river gives its flow, the ground it drains and how far it runs to the sea. Nothing from inside the house is listed or
drawn on Place, and neither are the rooms.

## The screen

In the middle is the map, on a black screen that stays black on the light page and the dark one. It
opens on the satellite where the node holds it, and a switch at the bottom right changes the base. The satellite is
Sentinel-2 at 10 m, so from Block scale in the street map takes over, with a drone flight on top where somebody flew
one. Zoomed out, a pin
marks each drone flight the node holds. The hour is a pill at the top, the node's last reading, or the wind's hour when
the wind is on. The scale rungs, street, block, cell, village and district, are at the bottom left and the credit at the
foot. A cell that may leave the machine is dotted. On the right edge are **Map only**, **Full screen**, back to the
node's cell and **Download**. The keys on the screen are 36 px with a mouse and 44 px on a touch screen. On a narrow
screen the rungs show only their number. Narrower still, the base switch moves above them and the hour above the zoom.

## Drawing

With the token, the keys on the screen's left edge are **Select** (V), **Marker** (M), **Line** (L),
**Area** (A), **Note** (N), **Image** (I) and **Undo** (⌘Z or Ctrl+Z). Each press on the map adds a point, and a marker
or a note is done with one. A line ends on a double press, an area when you press its first corner again. Enter adds a
point at the map's centre, and Enter again without moving finishes the shape, so the keyboard alone can draw. Backspace
takes a point back, Esc drops the shape. The readout beside the keys is a small chip with the tool, the open map, a dot
in the colour and the length or the surface as you draw, then the node's own measure once it is kept. Press the chip
for the six colours and a line on what to do, and press it again or Esc to fold them. With Select, press a drawing
for its label, note, colour and image, and the colours open by themselves. Press a
point and then its new place to move it, or use the arrows, with `.` for the next point. An image stays on this node,
the map only says which one.

## Your maps

**Your maps** sit at the top of the left column. Every drawing goes into one, kept on this node, and each drawing,
change, download and share is a row in the ledger on Data. **Download** gives the screen as a PNG with its credit and a
scale bar, and the open map as GeoJSON for QGIS, KML for Google Earth, or DXF for CAD in metres, in the node's UTM zone.
**Everything on the screen** gives the PNG and each map on the screen in all three. **Share** sends a map to the node
upstream. The first press says what goes, every drawing at its exact place with its labels, notes and measures, and
who can see it upstream. Upstream the node is the map's owner, and who drew each drawing stays here. The second press sends it. If a drawing touches the cell the house stands in, a shared map stops sending until
you press Share again. **Stop sharing** ends it, and this node asks the node upstream to delete the map.

**A photo on a shared map** goes up as words. The node upstream gets what took it, its note, the words you gave it on
Data › Images and the day it was taken, and the picture stays here, with where it was taken and who took it. The node
upstream can ask for the picture. The ask reaches this node within the hour and sits at the top of your maps, with who
asked and for which drawing. **Send** gives them the picture once, **No** keeps it here, and both go in the ledger.
Unshare the map, take the image off the drawing or delete the photo, and the node upstream deletes its copy.

On a node that takes maps from others, a child's drawing with a photo says what the photo is, and **Ask for the photo**
asks for it. It comes when somebody there presses Send, and only the people with this node's token can see it.

To answer an issue from Now, open the drawing's form, choose the issue, say what you did in your own words and press
**Tie it**. The rain garden you drew then counts as what you did about it, as Done does on Now.

## Folding

The layers fold by the arrow on their edge, or `[`, into a strip with their name. `\` or **Map only**
folds them and the screen takes the window, and **Full screen** or F takes the whole display. This browser remembers
the fold. On a phone the keys run along the bottom of the screen.

## What you selected

Under the screen one line says what is in view. Press a station, an image, a place to make or a cell and the line
gives its facts, and with the token how far it is from the node and which cell it is in. A station of this house says
it counts toward the cell; a public one is shown and never counted. Below it is the list around the house, nearest
first, with the distance in metres measured by the node (`GET /geo/measure`, and `GET /nearby` for public stations).

## The tools

**Tools**, beside the ask line, opens a menu of what the node can do with this place. **Rings and
distance** draws the 2, 5 and 15 km rings from the node's point. **From the house** measures from the node's point to
any point you press. The two that run come first, and the rest carry a dotted **not yet**. Choosing one closes the
menu, and so do Esc and a press outside it. A screen without a token reads "Tools run on this node with a token.
Unlock this screen in Set up." in the menu. On a phone the layers open from a bar under the screen as a sheet, and Esc
closes it.

## What changed

Under the screen, across the whole page, is what changed year on year. The satellite then and now sit side by side,
large, with the hectares that changed between them and a bar a year for the buildings it counts. On a phone the two
pictures stack. Below that, the open map's table is on the left and **The place in figures** on the right, with land
and coast, the place's row on the Fab City Index, the Index cells, the rivers, and what is not here yet.

**Rivers** is there once the hydro pack has fetched them, with the screen's token. It says how far the nearest river
is, how much water it carries on average and how far it still runs to the sea, and the same for the largest river in
the square. **on the map ↑** turns on the Rivers and Basins rows and takes the map out to District scale, where the
nearest river is in view. Before the fetch the row says `planetai run hydro fetch`. The same seven figures are in
Data › Models and satellite, under "Rivers within 25 km".

**Fab City Index** is a row in that band, under land and coast. It names the place this node belongs to, which
`planetai place` chooses, with the label the Index gives its score (**Partial** or **Simulated**), and then the Index's own
number for it: the FCI, or, while no cell of the place is measured, a range. Under it come up to three of the place's
indicators, each with its year, its unit and its source line, cut before any link, because two of Barcelona's are both
called "Residual municipal waste per person" and only the source tells them apart. An indicator the Index sent without a
value is left out, and a figure it sent as empty is drawn as a dash. The small line says when the Index's file was read,
in this node's time zone, how many sources the registry files for the place, and links to the place on index.fab.city.
A read that failed says `last read` with the date of the file the node still holds, and when it tried. The numbers come
from the Index's own file for the place, which the `index` pack reads once a day and keeps on the node, so the page asks
the node and never index.fab.city. The node does not recompute them, and a range stays a range and is never drawn as a
score of 0. A portal's numbers are `partial` here, and `cached` when the last read failed; `live` is kept for what this
node measured. The count of sources is the registry's entries that name the place, and says nothing about whether this
node reads them. With no place chosen, or the pack not loaded, the row says **not chosen**, asks you to run
`planetai place` on the node, and links to how the Index counts a place (index.fab.city/method). With a slug the Index
does not track, a typo in Set up for one, the row says **not an Index place** with the slug and the same command. With a
place chosen and nothing read yet it shows the place's name, **not read** and **not read yet**. The row is the same at
every sharing level, and `GET /index/place` is where its source and registry details are.

## What needs the token

The grid, the rings and every distance are the node's own answers from `GET /geo/*`, and the plan is
`GET /place/geojson`; all of them need a token at every sharing level, because together they place the house. Without
the token, the house's marks say **withheld** where they would stand, the rows that need it say **token-only**, and the
map opens on the published cell. The street map comes from `/ground/*` once `planetai run place basemap` has run; until
then Set up lists **The map of this place** under what is left to finish.

## Images and species

**The Image key** (token only) adds a picture. Press the map, or Enter for its centre, and a marker holds the image you
choose from Data › Images or take as **A new photo**. With nothing pressed it also offers **A new photo** on its own.
A new photo opens a dialog with the file, what took it (phone, fixed camera, microscope, drone, balloon or kite), a
note and your name, and whether the image model on this node describes it. The image lands where its own GPS says it
was taken, else in the node's cell; the node strips EXIF and GPS from the file and keeps it.

**Species confirmed here** is the list under the species row: a table of what somebody here confirmed in an image,
how often, where, and GBIF's open records by others in the node's seven cells, token only.

## When the map is thin

Zeroes mean unmapped, not absent. Node #1 in September 2026 held 2,904 buildings, 540 road segments and 37 mapped
places within its kilometre, and no school, which is OpenStreetMap's coverage of the Bukit, not the Bukit.
`planetai run place gaps` writes `out/place-gaps.md`, a briefing for a mapping afternoon at the lab: the untyped
buildings, the categories with nothing, the named places without hours, the unnamed streets. StreetComplete, Every
Door and iD over Bing or Esri imagery fix the map, never Google's. `planetai run place refresh` brings the edits to
the node within minutes.

## Where this leads

The settings and commands behind this door are in [the place pack](packs-reference.md#place). What leaves the
machine, and at which sharing level, is in [Sharing](sharing.md); the answers the screen draws come from `/geo/*` and
`/place/geojson` in [the API](api.md). The other four doors and Set up are on [the dashboard](dashboard.md).
