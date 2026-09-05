# The dashboard

One HTML file the node serves at `/`. No build step, no framework, no account.

```bash
planetai ui        # the URLs, and the token that unlocks the settings pages
```

## Now

The page is a zoom: room, street, world. Three hexagons offset behind one another. The front one is the room: it fills
with the inside reading and takes its colour, green under 15, orange to 35, red above (WHO). The middle one is the
street, with the outside reading at its exposed corner. The back one is the world, with the satellite model. Beside
them, one sentence saying what to do, and one line of why.

Then three bands by distance. **Room**: each indoor sensor of yours with its reading and a 24-hour trace; how it feels.
**Street**: your outdoor sensors, the nearest public ones with their distance, the wind as an arrow; the day's strip,
inside as bars, outside as a line, the model dashed, the WHO line drawn in. **World**: the sea and what the swell means,
the model and its gap to your street, the land within a kilometre as a built/green bar, the weather.

Below: what the node said, with **I acted** on every unanswered act-level alert (that button is how ρ is measured), the
Index cells as a honeycomb, and the node's vitals.

"Outside" is your own outdoor sensors if you have any, else the three nearest public references. The same order the rules
use.

## Set up

Behind the admin token, once per browser. Sources, alerts and Telegram, packs (a switch each; code packs behind one more
switch), integrations, keys, the node's place in the tree, and the bootstrap settings read-only. A test-alert button.
Changes are live within twenty seconds. A blank field returns a setting to `.env`.

Settings live in a `settings` table that overlays `.env`; the code reads them at the moment of use. Ports, the database
and the extra containers stay in `.env` because they are read once at start.

## On a shelf

`http://<node>:8080/?kiosk=1`: the hexagons and the sentence, nothing else, refreshing every thirty seconds. A 7-inch
screen or an old tablet.

## Access

Reads are open on your network, like the API: a household display cannot need a login. Writes need the token. It is a
password.
