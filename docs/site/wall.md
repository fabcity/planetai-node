# Wall mode

A screen on a wall that nobody is standing at. The wall is the one surface that uses the dark register:
`#wall` sets `data-theme="dark"` on the page — ink ground, paper type, the lifted blue `#7FA5E8` for cells
because Fab Blue is 1.72:1 on ink — and it is laid out to fill one viewport (`min-height: 100vh`), with the foot — node, as-of, stamp — inside it rather than below the fold.

```
http://<node>:8080/#wall
```

A wall screen carries no token, so it needs `SHARE_LEVEL=open`; at `off` the wall draws the refused page in
the dark register — "<node> · refused" and the node's own sentence — because a black screen would be the node
lying about being broken.

## The wall is the grid

Nineteen H3 cells — the node's own and two rings around it — at the current resolution, each holding what
is read in it, with no map under them. One station in a cell: its 15-minute mean of the variable and its
name. Several: how many, and the range low–high. The node's own cell: each of its own stations' values. An
empty cell is drawn and left empty.

The variable strip offers every metric at least one station carries, in the node's declared order; `?var=`
picks one (default `pm25`).

## The dial turns itself

The dial's stops are the resolutions the node's grain table knows, drawn as hexagons: the current stop
filled ink, a stop coarse enough that the cell may leave the machine filled in the cells blue at 0.16, a stop
finer than the published resolution dashed. Every eight seconds the dial steps to the next stop and the grid
re-draws; at the finest it wraps to the coarsest. There is no tween — there is no place between 7 and 8, so
nothing morphs. Pressing a stop or a cell, or an arrow key, holds the dial for thirty seconds and pauses the
clock bar. Under `prefers-reduced-motion: reduce` nothing turns.

## The right column

The headline issue — kicker, sentence, why, the ask — the dial, the variable strip, the grain counts (cells
with a station of the nineteen; stations in this node's own cell; of them, its own) and the ρ row. Under the
field, the fragments each section contributes through its `wall()` in one row, the first five, then
"+N more in Now".

## The foot

The node's name, the as-of time, the version stamp, the word `stale` in bold ink (a fixed label in this version; the page does not yet judge staleness), "Answer on Telegram, not here." and the motion caption. The exit button is drawn first so it is
first in keyboard order.

## What it is for

A household walking past reads one number, one sentence and whether the loop closed. A lab reads which
cells around it have a station and which do not. What it does not do is ask for anything: an act alert is
answered on Telegram, Sideband or the dashboard, not on the wall.

The ρ sign on the wall is the one object that is not a typed number: the closed rings, counted rather than
sized — more signs, never a bigger sign — the rule the FAB26 exhibition faces set and the page keeps.
