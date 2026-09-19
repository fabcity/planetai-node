# The dashboard

One HTML file the node serves at `/`. No build step, no framework, no account.

```bash
planetai ui        # the URLs, and the token that unlocks the settings pages
```

## Now

The page reads from where you stand, outward. Each band names its distance.

**Here.** The room's number as a sentence ("Falling to 9 micrograms, under the street, under the model, under the
line"), why, and, when an act-level alert is unanswered, an orange strip naming it with the button that closes the loop.
Behind the sentence is the ground: the map cell this node stands in, the seven smaller cells inside it, and its
neighbours' edges running off the frame. It is drawn on the node from the coordinates it was set up with, and the line
under it names the cell — `8839446033fffff · RES 8 · 525 M EDGE`. That id is how this node's readings find their place
in the index. The same ground and the same line are on the wall.

**Room.** How it feels indoors, then each indoor sensor with a note on what it is doing and a day's trace.

**Street, a few hundred metres.** Your kit on the wall, the nearest public sensors with their distance, the wind as a
direction. Then the day: a 24-hour chart of inside, the street and the model, with the WHO line and the peaks named.

**Neighbourhood, 1 km.** The plan: buildings on the map in ink, roads as hairlines, green as green, every mapped use a
dot, the buildings only the satellite knows in orange. Beside it, what is here in numbers, what is unmapped, and one
button: **Fix the map**, which opens the OpenStreetMap editor at your coordinates.

**Region, 11 km and beyond.** The satellite air model and its gap to your street, the land within a kilometre from
orbit, the sea, the weather.

**Act here.** ρ, and every alert with **I did this** beside the ones that asked for something.

Cards sit at their natural height on fixed tracks (four across on a desktop, two on a laptop, one on a phone). Every
sentence is computed from the API; nothing is typed in.

## The kilometre around you

When the place pack has run, the Neighbourhood band appears: a figure-ground of the radius around the node.
Buildings on the map in ink, roads as hairlines weighted by class, green as green, every mapped use a dot coloured by
kind, and the buildings only the satellite knows in orange, so the mapping gap is visible. North up, a 200 m scale bar,
the node pulsing at the centre. Legend buttons toggle each layer; hovering a dot names the place. Drawn in the browser
from `/place/geojson`, no map tiles, works offline.

## Arrange

The Arrange button puts the Now view into edit mode: every card gets ← → to move it within its row and ✕ to hide it;
a menu restores hidden cards; Default resets. Done saves the layout in the browser and, when Set up is unlocked, on the
node as `UI_LAYOUT`, so every screen in the house shows the same arrangement.

## Network

The house as one node of a larger instrument: this room, the neighbourhood, the planetary models, the parent (or "not
linked yet"), the Index cells as rings, the agent's model ladder. Flows animate along real links only. Below, what
leaves the house and the machine in the corner.

## Wall

`#wall`, or the Wall button: the dark register for a screen nobody is standing at — the nineteen cells around the
node at the current resolution, the headline sentence, the ρ row, and a dial that turns itself every eight
seconds. It needs `SHARE_LEVEL=open`, because a wall carries no token.

## Set up

Behind the admin token, once per browser. Sources, alerts and Telegram, packs (a switch each; code packs behind one more
switch), integrations, keys, the node's place in the tree, and the bootstrap settings read-only. A test-alert button.
Changes are live within twenty seconds. A blank field returns a setting to `.env`. A value set here **overrides** the
same key in `.env`, and the page says so next to it; `planetai telegram` writes both places so they cannot disagree.

Settings live in a `settings` table that overlays `.env`; the code reads them at the moment of use. Ports, the database
and the extra containers stay in `.env` because they are read once at start.

**Model.** Which model answers the household, and the one setting on this page that decides whether anything leaves
your network at all. Three values, offered in this order:

- **private** — nothing leaves your network. The node answers from the model on this machine, or from one you run
  yourself elsewhere on your tailnet. **This is what a node does until somebody here chooses otherwise**, including a
  node where an online key has been set: setting a key does not by itself start using it.
- **fallback** — your own remote model first, then the online one, then the small local model as the floor that still
  works with no internet. Online sits above local on purpose — a rung is skipped only when it *fails*, and a 4B model
  never fails, it answers badly.
- **strongest** — online first, so every question goes to the online model whenever a key is set. The report bundle
  that goes with it is 64 kB of this house: its numbers, its room names, its own sentences.

Changing this needs a restart of the agent container; the page says so.

## Access

Reads are open on your network, like the API: a household display cannot need a login. Writes need the token. It is a
password.
