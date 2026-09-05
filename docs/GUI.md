# The dashboard

One HTML file the node serves at `/`. No build step, no framework, no account: it reads the same API everything else
does. Fab City design system — paper and ink, three hues, the hexagon, Funnel Sans and Figtree — and it follows the
machine's light or dark setting.

```bash
planetai ui        # where it is, and the token that unlocks its settings pages
```

## Two pages

**Now.** The page is a zoom: the room, the street, the world — the Index's scale axis made physical. Three
hexagons of the same size, each offset behind the one in front. The front one is the room: it fills with the inside
reading and takes its colour, green, orange or red, one flat hue. The middle one is the street: the outside reading
runs along its exposed edge at 30°, like an inscription. The back one is the world: the isometric mesh clipped inside
it, the way the system uses that texture, with the satellite model along its edge in blue. Beside it, one sentence in
Funnel Sans that says what to do, one line of why, one line of provenance.

Then three bands, descending by distance. **Room**: each indoor sensor of yours as a tile with its reading and a
24-hour trace inside it, plus how it feels. **Street**: your outdoor sensors, then the nearest public ones with their
distance, then the wind as an arrow that points where it blows; under them the 24-hour strip — inside as bars, outside
as a line, the model dashed, the WHO guideline drawn in. **World**: the sea (height, direction as an arrow, period,
temperature, and a line about what the swell means), the satellite model with its gap to your street, the land within
a kilometre as a built/green bar with last year's change, and the weather. Then what the node said, with **I acted**
on every unanswered act-level alert; the Index cells as a honeycomb; the node's vitals.

The one motion is on load: the three hexagons arrive back to front. After that only the pulse dot breathes.
`prefers-reduced-motion` turns both off. Dark mode follows the OS.

The outdoor sensors on your own account are yours, whatever their distance — that is what an account means — and are
listed under Street as such. Public references sit next to them, labelled with how far away they are.

**Set up.** Behind the admin token, once per browser. Grouped by what you are trying to do: sources, alerts and
Telegram, packs (tick to enable, with code packs gated behind one explicit switch), integrations, keys, the node's
place in the tree, and the bootstrap settings shown read-only with the instruction to edit `.env`. A **Send a test
alert** button fires the whole path on every channel. Changes take effect within about twenty seconds, no restart;
a blank field returns a setting to its `.env` value.

## On a small display

```
http://<node>:8080/?kiosk=1
```

The instrument, the verdict and the three stats, centred, no navigation, refreshing every thirty seconds. On a
7-inch screen the hexagon is about the size of a hand. Any browser in kiosk mode, a Raspberry Pi with a display, an old tablet on the wall.

## How settings work, and why it matters

Settings the GUI changes live in a `settings` table in the node's database and overlay `.env`: a value set in the
GUI wins, a blank falls back to the environment. The code reads these keys through `settings.get()` at the moment of
use, so a change is live on the next poll or rule pass, and nothing needs a restart. Bootstrap keys — ports, the
database, which extra containers run — are read once at start and stay in `.env`; the GUI shows them but does not
edit them, and says so.

Reads are open to anyone who can reach the node, exactly like the API and by the same reasoning: the node holds
nothing personal beyond what a sensor at your address already implies, and a household display must not need a
login. **Writes need the admin token**, minted by the installer, shown by `planetai ui`, presented once per browser.
Anyone holding it can change what the node reads and where alerts go, so it is a password. `GET /settings` masks every
secret to *set* or *not set*; the token itself never leaves the node.

## What it is not

Not a charting tool: one strip of 24 hourly means, deliberately. Not a map. Not a place to write rules — those are
YAML in a pack, and the GUI shows which packs are on. Not remote administration: it changes runtime settings and
records actions, nothing on the host.
