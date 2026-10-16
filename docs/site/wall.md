# Wall mode
<!-- checked: v0.82.1 -->

A screen on a wall that nobody is standing at. With the wall, the node is read by people walking past: a
household sees one number, one sentence and whether the loop closed, and a lab sees which cells around it
have a station and which do not. It observes and measures. It asks nothing, because an answer belongs where
somebody can write one.

```
http://<node>:8080/?layout=classic#wall
```

This page describes the classic dashboard's wall. The doors' **Wall** (`/#wall`, the default) is described in
[the dashboard](dashboard.md#the-five-doors): it is read from three metres, so nothing on it is smaller than 28 px at
1920×1080 and its controls show only under a pointer or the keyboard (always, as 44 px targets, on a touch screen);
it names no sensor, room, kit or person, and says the readings are old only when the node's last poll is more than 15
minutes old. At `SHARE_LEVEL=off` with no token it draws one line, "This screen needs sharing turned on.", never a
token form.

`planetai ui` prints "On a wall screen: add #wall — the dark register, moves its own ladder;
needs SHARE_LEVEL=open". The node opens the five doors by default, so `#wall` alone opens the doors' Wall (see the
end of this page); `?layout=classic` keeps this one.

## Putting one up

1. **Let the house read the node.** A wall screen carries no token, so it needs `SHARE_LEVEL=open`:
   `planetai config set SHARE_LEVEL open`, or Set up → Sharing. At `off` the wall draws the refused page in the
   dark register ("This node is not sharing its readings with the network" and the node's own sentence),
   because a black screen would be the node lying about being broken.
2. **Open `#wall` on the screen.** You should see the top bar, the grid of nineteen cells on the left and
   the headline issue on the right, all inside one viewport, in the dark register. The grid is the node's
   own cell and the cells around it, each holding what is read there; an empty cell means no station the
   node hears is reading there.
3. **Check the foot.** The as-of line should read "As of" and a time. If it reads "Read at … · the node has
   not answered for N min", the screen is up and the node is not answering it.
4. **Leave it.** The top bar says "the ladder moves every 8 s" and the foot "the ladder moves by itself
   every 8 s". Watch one step: the filled rung moves on and the grid re-draws at the next resolution, so the
   stations gather into fewer cells at a coarse rung and spread out at a fine one. The page re-reads the
   node on its own `POLL_SECONDS`, as every view does. If the bar says "the ladder stands still", the screen
   has reduced motion on and the ladder moves only when a rung is pressed.

## The register

The wall is always dark, whatever register the rest of the page is in: `#wall` sets `data-theme="dark"` on
the page. Ink ground, paper type, and the lifted blue `#7FA5E8` for cells, because Fab Blue is 1.72:1 on ink.
It is laid out to fill one viewport (`min-height: 100vh`), so nothing a passer-by needs sits below the fold.

## The top bar

The bar answers the questions asked before any reading is read. From the left: a **back** button, drawn first
so it is first in keyboard order; up to four variable chips; the node's name, its city, `#wall`, a share
level (always `off` in v0.82, because `/health` carries no share level) and how often the ladder moves
("the ladder moves every 8 s", or "the ladder stands still" under reduced motion); and at the right what the numbers are: the variable, its unit, and `15-min means`.

The chips offer only metrics at least one station on this node carries. The one being shown is always first,
then the node's own order, four at most; a "+N more" link opens `?vars=all`. `?var=` picks one directly
(default `pm25`). A metric no station reads is not offered, because an empty field would claim a measurement
the node does not make.

## The wall is the grid

Nineteen H3 cells (the node's own and two rings around it) at the current resolution, each holding what is
read in it, with no map under them. One station in a cell: its 15-minute mean of the variable and its name.
Several: how many, and the range low to high. The node's own cell: each of its own stations' values. An
empty cell is drawn and left empty.

## The ladder moves itself

The ladder's rungs are the resolutions the node's table knows, drawn as hexagons: the current rung filled
ink, a rung coarse enough that the cell may leave the machine filled in the cells blue at 0.16, a rung finer
than the published resolution dashed. Every eight seconds the ladder steps to the next rung and the grid
re-draws; at the finest it wraps to the coarsest. There is no tween: there is no place between 7 and 8, so
nothing morphs. Pressing a rung or a cell, or an arrow key, holds the ladder for thirty seconds and pauses the
clock bar. Under `prefers-reduced-motion: reduce` nothing moves.

## The right column

The headline issue: kicker, title, tagline, why and the alert. The title is the sentence's qualitative head — what is happening, in the household's words, with no number and no indicator in it ("The house is keeping the street's dust out") — and the tagline is the explanation set smaller and muted beneath it ("Inside it is under the WHO line, and the street is past it."): the readings arrive a beat later. The full sentence stays for prose. Under the alert, "Answer on Telegram, not here." The
wall shows an alert and never the button that answers it. It draws no alert event either: on a node whose alert engine is `shadow` or `events` the old heat and air alerts are not
open asks, so under the headline the strip can read "Nothing has been asked." while Decide has an event open. Then the ladder, with its key under it
("the ladder · current rung filled ink · may-leave rungs filled `--cells` at .16 · finer than published,
dashed"), the counts ("Cells with a station" of 19 drawn; "In this node's cell" of n stations; "Of them,
its own") and the ρ row. Under the field, the fragments each section contributes through its `wall()`, in
one row: the first five, then "+N more in Now".

The ρ row is the one object that is not a typed number: the rings are counted, never sized. More signs, never
a bigger sign. When there are too many alerts to count at three metres the unit changes instead: one ring per
alert up to 40, one per 10 up to 400, then one per 100, and the caption under the row names the unit and gives
the exact counts.

## The foot

The as-of time, the version stamp, the word `stale` in bold ink, and the motion caption. The bold word is a
fixed label in v0.82. The as-of time beside it does judge: when the page's last poll got no answer it reads
"Read at … · the node has not answered for N min".

If the wall throws while it draws, the screen says "The wall did not render:" and the reason, rather than
going black.

## Where this leads

The wall only shows the alert. The answer is given on Telegram, over the radio or on the dashboard, and all of
them write the same row in `actions`: see [Channels](channels.md) and [the dashboard](dashboard.md). What the
ρ row counts is [ρ](rho.md). The Wall of the five doors, at `/#wall`, is another screen: a map that walks
out from the house a scale at a time, house, street, ring and region, with each scale's figures, its day, the land
around and what the satellites see, and the node thinking aloud, on [the dashboard](dashboard.md#the-five-doors).

## What the doors' Wall says aloud

The doors' Wall asks `POST /ask` with `prompt: wall` every ten minutes, and the node tells its model only public
facts, each a short labelled line with its unit and where it comes from (`live`, `model` or `satellite`): the time
of day; each watched issue's day sentence ("The air is clean now, after a dusty morning", and how many hours were
over the line today), its values inside the home, on the street, in the neighbourhood and in the wider area, its
line (the WHO guideline, 15 µg/m³, for the air) and its trend; every issue's readouts, such as the land's built
and tree share seen by satellite and the sea's swell; how many public stations nearby read fine dust and how many
of them are over the WHO line; what is usual for the place (the outdoor sensors' learnings, never the house's); the
next six hours of forecast; and every section a pack declares with `wall: true`. It never carries what the house
learned, its diary, its things, a room, a sensor's or a person's name, an alert's words or a position. Each
narration starts from an angle those facts can carry (the day so far, the stations around, what is usual here, the
next hours, the land and the sea, fires around, the ground's heat), and an angle with no facts is skipped.
