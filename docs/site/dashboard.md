# The dashboard

The dashboard is where a node is read. Once it is open, the loop the node runs becomes something a person
can follow and take part in: what it observed about the place, what it suggests, what it has asked of the
people there, and whether that worked. The page's script says it in its own words: a node observes its place, "It
ACTS by asking somebody to do something. It MEASURES whether that worked and how long it took, and the loop
closes." Two of those stages need a person. A decision is written on this page, and so is the note that
says what was done.

The node serves `index.html` and a fixed list of companion files by name from `GET /static/{name}`: three
stylesheets (`tokens.css`, `planetai-theme.css`, `dashboard.css`), `dashboard.js`, two SVGs, `kilometre-cells.json`,
`learn.json` and the self-hosted fonts. The node computes and the page draws. A number the page works out
for itself is a bug.

## A first read

1. **Open it.** `planetai ui` prints the addresses: `On this machine: http://localhost:8080/`, `On your
   network: http://<ip>:8080/`, and the tailnet address once `planetai mesh` has run. It also prints the admin
   token and the act token. Open one of the addresses. At `SHARE_LEVEL=off` a browser with no token gets
   "This node is not sharing its readings with the network"; `planetai config set SHARE_LEVEL open` lets
   every screen in the house read the page (see [Sharing](sharing.md)). What you should see is the header
   (Now, Historical, Network, Wall, Arrange, Set up) and, for about three seconds, the page listing what it
   asked the node and how many milliseconds each answer took. Each row there is one route the page read,
   with its time or `no answer`; a `no answer` row is the part of the node that is not answering, and
   nothing in that panel is a reading yet.
2. **Turn the rail.** The strip of eleven stops above everything is the grain rail (the wall and
   `planetai ui` call the same control the dial). Press 6, then 10. The
   ground, the station groups and the grain figures re-draw at each stop; stops 6 and coarser are dotted
   because a cell that coarse may leave the machine. This is the node telling you how coarse each thing you
   are about to read is.
3. **Read the lead.** The sentence under the rail is the headline issue in the household's language, with
   the four distances as meters. The why line says why this issue leads. The last line says how many asks are
   open, for example `2 asks open · #361 · in 3 Act`, or `nothing open · 3 Act is empty`. The node chose
   this issue, not the page: the why line ends on the node's own `headline_rule`, and the pill at the end
   of the last line (`live`, `stale` or `cached`) says how current it is.
4. **Find the open ask.** The link in that line goes to Act. Under Decide, "What to do about it" shows
   "what was seen" and "what this node suggests" for each issue with an open ask. An open ask is the node
   asking a person to do something; it stays open until somebody records an act against it (step 6).
5. **Decide.** Press **Decide about this**, put your name and what will be done (or press **Take its word**),
   then **Record the decision**. The page answers "Decided. Nothing has moved". A decision is a record, not
   an answer: ρ does not change.
6. **Press "I did this".** In Act, under the ask, press **I did this**, say who and what you did, and
   **Record it**. The page answers "Recorded. The node watches what happens next." If it answers with the
   node's own 401 or 403 sentence instead, go to Set up, paste the act token that `planetai ui` printed, and
   press it again.
7. **Find the row.** "What was decided, and by whom", just below, now has your name at the top with `acted`
   and, if you decided first, `decided first`. The act is in `actions`, the ask is closed, and it counts
   towards ρ in Measure.

## Views

In the order the header draws them:

| view | URL | what it shows |
|---|---|---|
| **Now** | `#now` | the rail, the lead, then the four stages: observe, decide, act, measure. The default view |
| **Historical** | `#historical` | the day this place usually has, what the satellite says year by year, how far back this node can be asked, and what the node doubts about its own sensors |
| **Network** | `#network` | this node in relation to the network and nothing else: what moves through it, what this place could read and where it could go, what leaves by radio, the mesh in the house, the hardware |
| **Wall** | `#wall` | the dark register, for a screen on a wall; see [Wall mode](wall.md) |
| **Arrange** | `#arrange` | Now in another mode: move a section within its stage, hide one, restore it, Default, Done; saved as `UI_LAYOUT`. The rail, the lead and the ground are fixed and carry no controls |
| **Set up** | `#setup` | the settings, behind a token, and every registered section with whether it is drawing |

The rail is Now's (and Arrange's) control and is drawn nowhere else. The resolution still travels in the URL
as `?res=`, so a link into any view keeps its grain. The header also carries the mode switch, the Paper /
Dark register switch (kept in this browser; `?register=` reads first and remembers nothing) and **↻**, "Ask
the node again".

Other query keys: `?view=` works as the hash does, `?fixture=<name>` replays a committed snapshot (see
below), `?state=empty` or `?state=refused` draws those states for a capture, `?worth=1` opens the rail's
fold, and on the wall `?var=` and `?vars=all`.

## Modes

How much of the page is drawn. Three, in the header beside the register:

| mode | what it draws |
|---|---|
| **simple** | offered on Now, Historical and Network only. On Now: the rail, the lead, the **digest** (four sentences, one per stage, each written by the node), then only the sections marked `level: 'simple'`, which on Now is the Decide card "What to do about it". On Historical it draws "What the satellite says"; on Network, "This node, and what moves through it". The digest is Now's alone |
| **advanced** | every registered section, in loop order. The default |
| **learn** | advanced, with a question mark at each part of the page. Pressing one opens a panel that quotes this node's own documentation for that part, says which page and section the words came from, links out, and walks to the next |

A node too old to send a digest gets a note instead: "This node has not sent a digest", naming the version
it is talking to, rather than four sentences composed in the browser.

`UI_MODE` is what the page **opens** as, chosen by the household. A reader who switches is switching their
own copy and nobody else's: the choice is kept in this browser, the way the register is. `?mode=simple` is
read first and remembers nothing. It is how one person sends another the short answer without changing
their page, and how the measuring rig renders all three.

The learn panels are quotations, not summaries. The node does not serve this documentation (the site build
does), so `tools/build_learn.py` cuts the spans out of these pages at build time into `app/static/learn.json`,
which the page fetches only when somebody turns learn mode on. The quote therefore reads on a network with
no route out, and `make lint` fails when a span is no longer in the page it names. Seventeen marks; the bar
under the header says how many are on the view you are looking at, and *walk the page* starts at the first.

## The lead

The **grain rail** sits above the lead: eleven stops, one per H3 resolution from 2 to 12, opening at 8. Stops coarse enough that the cell may leave the machine (resolution 6 and coarser, the presence floor) are dotted rather than blue; stops finer than the node says where it is are struck through.

The zones are texture, not hue, so the cells blue keeps its one meaning and the rail survives being printed.
Each stop names its edge length, and pressing one re-derives the whole page. Under the stops, above 860 px, a
log ruler from 10 m to 200 km runs the same way as the rail, coarse on the left. The key under it names both
zones; its last chip, "one cell here", opens a fold, *What one cell at resolution N is worth*: three hexagons to
true relative scale (the stop you are on, filled, against the stops either side) and a table of what each
thing the node speaks for costs to cover at it. Each stop is about seven times finer by area than the one
above. The fold's state is `?worth=1`, so it survives the rail it is read against.

The first thing on Now is the rail, and under it the lead: the headline issue's kicker, its numeral and pictogram, the sentence, a why line and the four distances as meters. The last line gives the as-of time, how many asks are open and in which stage, and a pill: `live`, `stale` or `cached`.

The meters carry a legend for the red tick, the issue's line. The why line ends on the node's own
`headline_rule`, so a reader can check why this issue is on top. The ground's drawing follows. The ask strip
sits in Act, beside the ledger it belongs to, and the **grain line** opens Decide's "What each grain is
worth", as a readout of the cells occupied at the current stop.

At resolution 8 one cell is 639,778 m² on node #1, about 0.64 km², with an edge of 497 m. The grain line counts the cells this node's stations with a coordinate fall in, how many of those stations sit in the node's own cell, and how many of those are its own.

## The ground

The section behind the lead is the node's own ground at the current stop, drawn under the cells: the node's
own cell in the cells blue, its neighbours as ink hairlines, its own stations filled and other stations
hollow. A node with no `NODE_LAT` and `NODE_LON` draws the grid from `/static/node-ground.svg` and says it
stands for no particular place yet.

Three bases: `plan`, offline, from `/place/geojson`: the building footprints within `PLACE_RADIUS_M`, projected in the browser with every vertex kept, nothing leaving the house; `sat`, Sentinel-2 cloudless tiles; `osm`, OpenStreetMap tiles.

Live tiles need `MAP_TILES=on` and are offered only at resolution 8 and coarser, because from 9 inward the
plan fills the frame. Each base's tab says what it costs before it is pressed: `sends nothing` for the plan,
a count of requests for the others. A press may only ever reduce what leaves the house. The plan needs a
token at every sharing level, because it is the shape of your building. An H3 id is printed in full, once
per object, never truncated.

Three things the grid forces the page to say: a cell is not the thing (three indoor sensors share one
coordinate); containment is exact in the index and approximate on the ground; and the four distances are
not four resolutions.

## The sections

Every section is registered with the page contract: `id`, `pack`, `stage`, `title` and `render` (or `lead`), and optionally `order`, `needs`, `controls`, `wall`, `learn`, `notes`, `level` and `anchor`. The shell draws each one in the stage it belongs to, in the order the loop runs: observe, decide, act, measure.

Each stage has a numbered head and a line saying what it holds, so a reader always knows which part of the
loop they are in. Twenty-four sections are registered, in this order within each stage:

| stage | view | sections (pack) |
|---|---|---|
| **observe** (what is read, seen and heard about this place) | Now | The ground (place) · Every issue, at every distance · The day this place just had · What this page is made of · What the stations read (air-quality) · The day it is about to have (forecast) · What this page asked of the world (place) |
| | Historical | How far back this node can be asked · The day this place usually has · What the satellite says (earth) |
| | Network | This node, and what moves through it · What leaves this house by radio (reticulum) · The mesh in this house (meshtastic) · The hardware in this house (hardware) · What this place could read, and where it could go |
| **decide** (what may be said about it, and at what grain) | Now | What to do about it · Whose word, over how much ground · What each grain is worth |
| | Historical | What the node doubts about its own sensors (trust) |
| **act** (what has been asked, of whom) | Now | What this node has asked · What was decided, and by whom |
| **measure** (whether it worked, and how long it took) | Now | Whether it worked · Which of these worked · Every figure on this page, and where it came from |

Sections with no pack named are `core`. The stages hold observe 15, decide 4, act 2, measure 3. A section a pack
registers that is on none of these lists is drawn on Now, in its own stage and order.

A section whose `needs` are not on this node prints one line in their place, "The <pack> pack has nothing
here yet: … is not on this node.", never a blank and never a guess. A
section that throws prints that it did not render and why, and every other section still draws: a failure
is not an answer. The explanations every section wants to make are gathered into one folded band at the
foot, *Where these numbers come from*: one fold per section, and every note in it names its own subject
(84 labelled notes in `dashboard.js`).

Four card kinds and no fifth: readout, stack, series, row. A gap in a series is a gap in the line, never a ramp across the WHO line nobody measured. The node's own words are never uppercased: `µg/m³` once became `MG/M³` on the hero, a factor of a thousand.

### Observe

What the node read. Nothing here asks anything of a person. "The day this place usually has" averages this
node's own stations hour by hour, inside and outside apart, in the node's own time; it waits for 7 local days
before it draws a day (`GET /shape` needs 14 for a week, 60 for a month, 365 for a year) and until then says
how many days it has. "How far back this node can be asked" gives, per kind of source, the oldest and newest
hourly reading (`GET /reach`). "What this place could read, and where it could go" reads the pinned source
registry (`GET /sources`, fetched the first time somebody opens Network): how many sources are registered,
how many have code on this node, and the places to make things and the designs to build that the registry
lists.

### Decide

What a person adds here is a decision. "What to do about it" shows one card per issue with an open ask: the
first line of what was seen, and the rule's own recommendation (the paragraph its author started with 👉),
or a line saying the rule carries none and the page will not invent one. **Record the decision** posts
`stage: decided` to `POST /actions`. A decision moves nothing: it is not in ρ, not in the funnel, and closes
no ask. With `DECISION_REQUIRED=1` (Set up → Node, off by default) the node refuses an act with 409 unless a
decision was recorded against the same ask first. The two grain sections say at what grain a thing may be
said, and the trust section says which of the node's own sensors it doubts.

### Act

What a person adds here is the act. "What this node has asked" lists the asks with **I did this** beside each
open one. The form posts `stage: acted` with who and what was done. From a browser that needs `ACT_TOKEN` or
`ADMIN_TOKEN`, entered once in Set up; the page shows the node's own refusal sentence if neither is there, and
refuses outright on a fixture, whose asks belong to another node. "What was decided, and by whom" is the
ledger, newest first, all of it in one fold: who, which stage, how long ago, and `decided first` on an
act that had a decision before it. Its head counts how many acts had a decision first. The note somebody
wrote is shown only to a reader with a token, because `GET /actions` is on no sharing allowlist.

### Measure

What the node measures about itself. "Whether it worked" draws ρ as a row of rings, answered first, with the
median minutes from ask to answer, and the funnel beside it: `asked`, `acknowledged`, `acted`, `measured`,
each a count against `asked`. `measured` is derived, not recorded: an act followed by 48 hours of silence
from the same rule on the same sensor, and the funnel says so. A zero says why it is a zero. The care label
under it is the five refusals of [Architecture](architecture.md) section 7, as signs. "Which of these
worked" reports per rule, over the whole record, how many acts there were and how many were followed by the
condition stopping within that window; only a rule that declares `watch: {metric, over}` also gets a typical
recovery time in hours. It is evidence that the condition ended, never that the act ended it. See
[ρ](rho.md).

## Issues, states and distances

`GET /issues` is the whole of what the page knows about the place. For every issue the keeper declared in `NODE_ISSUES` (an undeclared one is still shown, as `watched: false`), the node computes a `state`: `act` (something is asked), `notable` (something changed), `quiet`, `context` (an issue that informs and never asks) or `none` (no record).

With it come the four distances, each with its value and its provenance word. The wire keys are `room`,
`yard`, `ring` and `region`; the page prints them as room, wall outside, street and model. Then the sentence
in three languages, the open asks, the series for the day, the `digest`, the geometry the rail is drawn
from, and the `asks` ledger.

The `headline` is the issue with the highest state. Among issues in the same state, the one that moved most
in the last three hours leads, and an exact tie goes to the declared order. The node sends that rule as
`headline_rule` and the lead prints it. The same object comes back from the `issues` MCP tool, so an agent
and the household describe the same evening in the same words. The declarations are one file per issue in
`app/issues/*.yml`; see [Issues](issues.md).

## Keeping up

The page re-reads `/issues`, `/health` and `/rho` every `POLL_SECONDS`, the node's own polling interval,
clamped to 20 to 600 seconds (60 if the setting cannot be read). Settings, the plan, the satellite record,
the sensor list and the cells are read at load and not on a poll. A poll keeps the scroll position and the
open folds, and holds off while the tab is hidden, while a Set up group has an unsaved edit, and on a fixture.
When a poll gets no answer the figures stay, the pill says `stale`, and the as-of line reads "Read at … · the
node has not answered for N min". **↻** asks again at once.

While the node has not answered, the page shows what it asked and how long each read took. On a load or a
press of **↻** that state is held for at least `--motion-asking-hold` (3 s), so it can be read. A routine poll never
shows it; the first poll after the node stopped answering shows it without the hold. Under reduced motion
it is not held at all.

## Set up

Behind a token, once per browser. The admin token is kept in the browser's local storage as `planetai_admin`;
the act token, the weaker one that can only close a loop, as `planetai_act`. Nine groups: Issues · Sources ·
Alerts · Packs · Integrations · Keys · Agent · Node · Bootstrap (the last read-only). A value set here is live
within 20 seconds and wins over `.env`; the page says so beside it; a blank returns the key to `.env`. Every
change is an `actions` row with `stage='settings'` and the actor `dashboard` (`planetai-cli` from the command
line, the agent's name over MCP). The section list under it names every registered section by pack and
whether it is drawing or has nothing here yet.

## What a reader without a token sees

At `SHARE_LEVEL=off` a browser gets the dashboard shell, the node's name and city from `/health`, and the
refused page: "This node is not sharing its readings with the network", the node's own 403 sentence, and
"Ask whoever set this node up to turn sharing on, or open this page on the machine the node runs on." A
blank would be the node lying about being broken. A browser on the node's own machine counts as a reader on
the network here, because inside Docker it arrives as the bridge gateway. At `open` the whole read API
answers and the page draws; the plan still needs a token at every level. See [Sharing](sharing.md).

> **Gap in v0.72.1.** At `SHARE_LEVEL=off` a browser that has never stored a token draws the refused page
> on every view, Set up included, so there is nowhere on the page to enter one, and the refused page's advice
> to open it on the node's own machine does not get past the refusal. Turn sharing on, store the token in
> Set up, and turn it off again; or read the page at `open`.

## Languages

The page reads the household's language from `/health.locale` (`ALERT_LOCALE`, which answers at every
sharing level) and draws the issue sentences, labels and distances in English, Bahasa Indonesia or Spanish.

## Looking at it without a node

`?fixture=<name>` replays a committed snapshot through the node's own engine, `GET /issues/fixtures/<name>`,
and the pill says `cached`. Four ship: `node1-2026-09-06`, `node1-2026-09-21`, `node1-2026-09-21b` and
`node1-2026-09-21d`; `GET /issues/fixtures` lists them. `planetai snapshot` writes a new one from a running
node. A snapshot missing a table the engine reads comes back with an error in place of the issues rather
than a half-drawn page, and the 6 September capture predates `planetai snapshot`, so some of its cards are
empty.

`python3 tools/shots.py` renders every fixture the node ships, with every request fulfilled from disk, at
375, 768, 1440 and 1920 px. It needs Playwright from the sibling design repository and is not a gate a node
runs. `tests/visual/gate.sh` measures what the section contract cannot enforce: the four card kinds and
numerals carrying `data-num` with a comparison beside them.

> **Gap in v0.72.1.** The ledger's own note in the notes band, "No stage for a decision yet", still says the
> ledger has no `decided` stage. It has one: the Decide card writes it.

## Where this leads

The page answers when somebody is looking at it. [The report](report.md) is the same node speaking at the
hours the household chose, and [Alerts](alerts.md) and [Channels](channels.md) are how an ask reaches a
person who is not looking. What the Measure stage counts is explained in [ρ](rho.md). A screen on the wall
is [Wall mode](wall.md).
