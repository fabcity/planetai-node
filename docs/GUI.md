# The dashboard

One HTML file the node serves at `/`. No build step, no framework, no account: it reads the same API everything else
does. Fab City design system — paper and ink, three hues, the hexagon, Funnel Sans and Figtree — and it follows the
machine's light or dark setting.

```bash
planetai ui        # where it is, and the token that unlocks its settings pages
```

## Three pages

**Now.** One instrument, not a grid of tiles. The Fab City module — a hexagon with its outline offset behind it — is
inside and outside made literal: the inside reading fills the hexagon and colours it (green, orange or red, one hue at
a time, flat), the outside reading sits where the outline peeks out, and the model is a faint dashed third hexagon
with its number in blue. Beside it, one sentence in Funnel Sans that says what to do — *Inside is worse than outside.*
*Keep the windows shut.* *The air is clean.* — and one line saying why, in plain numbers. Then three quiet stats,
hairline-separated, each ending in a sentence: how it feels, street versus model, ρ.

Below: the last 24 hours as it actually happened — hourly bars for inside, a line for the street, a dashed line for
the model, from a new `/series` endpoint over `readings_1h` — with the WHO guideline drawn in and a one-line summary.
Then what the node said (the alert feed, with an **I acted** button on every unanswered act-level alert; that button
is how ρ is measured), the Index cells as a small honeycomb, and the node's vitals.

The one motion is on load: the outline hexagon draws itself and the inside number counts in. After that only the pulse
dot breathes. `prefers-reduced-motion` turns both off.

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
