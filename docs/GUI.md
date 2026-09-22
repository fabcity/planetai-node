# The dashboard

One page the node serves at `/`. No build step, no framework, no account, and no connection to
anywhere else — a node hands this page to the machine you are reading it on, and if the house has no
route to the internet it still works.

```bash
planetai ui        # the URLs, and the token that unlocks Set up
```

## The shape of it

The page is read in the order the node works, and the node works in a loop of four:

1. **Observe** — what is read, seen and heard about this place.
2. **Decide** — what may be said about it, and at how coarse a grain.
3. **Act** — what has been asked, of whom.
4. **Measure** — whether it worked, and how long it took.

Every part of the page belongs to one of those four and is drawn under it, numbered. If a part has
nothing to show — no sensor for it, a pack you have not installed — it prints one line saying which,
and never a blank or a zero standing in for a reading nobody took.

## The first screen

**The rail, across the top.** Eleven stops, one per grain your node knows: resolution 2 is 172 km to
an edge, resolution 12 is 10 m, and the one you are standing on is lit. Stops coarse enough that the
cell could leave your machine are textured; stops finer than your node is willing to say where it is
are struck through. Press one and the whole page re-answers at that grain.

Under the rail, folded shut, is what one cell at that stop is worth: three hexagons to scale — the
grain you are on against the one above and the one below — and what each thing your node speaks for
costs to cover at it. Open it and turn the dial: at resolution 4 the sea takes five cells and your
room takes one, and so does everything in between. That is the whole argument for grain in one
table.

**Then the thing that matters.** The issue with most to say, as a sentence in your language, with its
number beside it at the size of a headline — *"It feels like 33.9 °C in the room, under the line."*
Under it, in smaller type, why that issue and not another. Then the four distances as bars on one
scale: the room, the wall outside, the street, the model, with a red tick where the line is. One
scale for all four, so you can see at a glance whether it is you or whether it is everywhere.

Beside it, the ground: the map cell this node stands in, its six neighbours and the seven smaller
cells inside it, with the buildings and roads of your own square kept on your own disk. The line
under it is the cell's id — `8839446033fffff · RES 8 · 497 M EDGE` — which is how this node's
readings find their place without anybody being told where you live.

## What you will find further down

- **Every issue at every distance**, as a table. Where a cell is empty it says why: *no kit on the
  wall outside*, *no public station reporting*.
- **The day this place just had** — twenty-four hours of the room, the street and the model, with the
  hours it was over the line marked under the axis, because eight hours over is the thing you act on
  and a curve does not tell you that.
- **What this page is made of** — your own stations, the borrowed ones faint, what only the satellite
  knows in orange, counted in signs rather than drawn as a chart.
- **What this page asked of the world while you looked at it.** The offline plan asks nothing.
  Switching the map to satellite asks twelve times, and tells that server which five kilometres of
  the planet you are looking at. Your node's own polls are counted apart, because they happen
  whether or not anybody is at the screen.
- **What has been asked, of whom** — every alert that asked a person to do something, whether anybody
  answered, and the button that records it when you do. And, when your node knows one, the nearest
  place to make or fix something.
- **Whether it worked** — the share of asks that got an answer, drawn as one ring per ask rather than
  one long bar, with the median minutes to the first answer. It is the one number on the page that
  comes from a person.
- **What this node will not do, at any stage** — five refusals, as signs, at the foot.

Everything that wants to explain itself is folded into one band at the very bottom, *Where these
numbers come from*. A household that wants to know why is one scroll away; one that does not is never
interrupted.

## The six tabs

| tab | URL | what it answers |
|---|---|---|
| **Now** | `/` | What is the air, the heat, the land and the coast doing here, this hour? |
| **Historical** | `#historical` | What has this place looked like over the years the satellite has watched it, and how far back does each source go? |
| **Network** | `#network` | What is this node connected to, what does it hear, and what could it read? |
| **Wall** | `#wall` | The same node at three metres, for a screen on a wall. Dark, and it stays dark. |
| **Arrange** | `#arrange` | Which sections Now shows, and in what order. Saved on the node. |
| **Set up** | `#setup` | Every setting, what it does, and where its value came from. Needs the token. |

## How much of it you want to see

Three modes, in the header:

- **Simple** — four sentences, one per stage, and your node writes all four. Nothing on the page
  composes them; if your node is too old to send them, the page says so and names the version rather
  than making them up.
- **Advanced** — the whole page. This is the default.
- **Learn** — the whole page with a small question mark at each part. Press one and a panel opens
  that quotes your node's own documentation for that part, word for word, says which page the words
  came from, and offers to walk you to the next. Seventeen marks. The words are built into the page,
  so it works with no way out to the internet; the link is an offer, not the answer.

The mode is remembered by the browser you chose it in, so a phone and a wall screen can disagree.
`?mode=simple` on the end of any URL shows one without remembering it, which is how you send somebody
the short answer without changing their page.

## Paper or dark

Beside the modes: **Paper** or **Dark**. Paper is the default, because most of the time this is read
in a room with light in it.

The page does not guess. It does not follow the operating system and it does not watch the clock — if
you want it dark at noon it stays dark. The choice is remembered by the browser you made it in and
changes nothing for anybody else in the house.

The Wall is the one exception: it is always dark, because a lit white rectangle in a dark room is a
lamp, and nobody chose a lamp. There is also nothing to press on the wall. That is deliberate: the
wall is an instruction, not a control.

## Changing the order

**Arrange** is Now in another mode. Each section grows three controls — move it within its stage,
hide it, restore it — and *Done* saves the order to the node, for every screen in the house. The
rail, the lead and the ground do not move, and the bar says so.

That changes the order of the *sections*. To change which issues your node watches at all, and in
what order, that is `NODE_ISSUES` under **Set up → Issues** — a list, most important first.

## If something moves, it is because a reading moved

Nothing on this page animates for its own sake. A number that has just arrived fades in over 120 ms
and pulses once; a ring closes when somebody answers an ask; a satellite year holds for four seconds
before the next. Every one of those durations is named after the thing that drives it, and if you
have asked your machine for less motion, all of them stop. The list is on the
[Design](site/design.md) page.

While the page is waiting for your node to answer, it draws the one motion that is not about a
reading: a globe of the sixteen characters a map cell id is written in, turning inside your own cell,
with the list of things it is asking for and how many milliseconds each took. It settles into the
plane of that cell the moment the answer arrives, and leaves.

## Seeing it without a node

Every view can be drawn from a committed snapshot, which is how the page is reviewed and how a
problem gets looked at on somebody else's machine:

```bash
python3 tools/preview.py     # http://127.0.0.1:8123
```

`?fixture=<name>` replays a snapshot through the node's own engine and the pill says `cached`.
`?state=empty` shows a node with nothing on it yet; `?state=refused` shows what a reader with no
token sees. None of those four remember anything, so any of them can be sent to somebody without
changing their own page.
