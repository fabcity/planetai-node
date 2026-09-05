# The dashboard

One HTML file the node serves at `/`. No build step, no framework, no account: it reads the same API everything else
does. Fab City design system — paper and ink, three hues, the hexagon, Funnel Sans and Figtree — and it follows the
machine's light or dark setting.

```bash
planetai ui        # where it is, and the token that unlocks its settings pages
```

## Three pages

**Display.** Six tiles: inside PM2.5, outside PM2.5, how it feels (apparent temperature from indoor temp and
humidity), the CAMS model with the gap to your street, ρ, and a 24-hour trend. Each tile ends in a sentence a
household can act on — *worse than inside: keep the windows shut* — not a colour scale someone has to learn. Below:
the alert feed, with an **I acted** button on every act-level alert that has not been answered (that button is how ρ
is measured), the node's Index cells drawn as a honeycomb, and the node's vitals.

**Sensors.** Every sensor the node knows, yours first, with what it reads now and when it last spoke. Then the slow
sources: portals, models, the sea, the satellites.

**Set up.** Behind the admin token, once per browser. Grouped by what you are trying to do: sources, alerts and
Telegram, packs (tick to enable, with code packs gated behind one explicit switch), integrations, keys, the node's
place in the tree, and the bootstrap settings shown read-only with the instruction to edit `.env`. A **Send a test
alert** button fires the whole path on every channel. Changes take effect within about twenty seconds, no restart;
a blank field returns a setting to its `.env` value.

## On a small display

```
http://<node>:8080/?kiosk=1
```

Big numbers only, no navigation, refreshes every thirty seconds. Six tiles fit a 7-inch screen; three fit a phone
propped on a shelf. Any browser in kiosk mode, a Raspberry Pi with a display, an old tablet on the wall.

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

Not a charting tool: the trend is three points, deliberately. Not a map. Not a place to write rules — those are
YAML in a pack, and the GUI shows which packs are on. Not remote administration: it changes runtime settings and
records actions, nothing on the host.
