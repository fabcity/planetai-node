# The dashboard

One HTML file the node serves at `/`. No build step, no framework, no account.

```bash
planetai ui        # the URLs, and the token that unlocks the settings pages
```

## Now

The design is PLANETAI_Node_v5 on the Fab City design system: a warm dark field, Figtree for words, Funnel Sans for
numbers and headings, the three brand hues as accents, the hexagon as the only mark. Every sentence on the page is
computed from the API; nothing is typed in.

The room's number is a sentence: "Falling to 9 micrograms — under the street, under the model, under the line", each
clause computed against the outside reading, the satellite model and the WHO guideline, with the verb from the last
three hours. Beside it, why, and what to do. Four headline tiles with a day's sparkline: the street (your kit outside,
or the nearest public sensors), the model and its gap to your street, how it feels indoors, the wind. Then the day: an
annotated 24-hour chart with the WHO line, the indoor peak named ("someone cooked" if the room beat the street), the
street's peak, and now. Then every sensor with a story generated from its readings. Then what the node said, with the
ρ ring and **I did this** on every unanswered act-level alert. Then the world: the sea, the land, the weather, the gap.

## Network

The house as one node of a larger instrument: this room, the neighbourhood, the planetary models, the parent (or "not
linked yet"), the Index cells as rings, the agent's model ladder. Flows animate along real links only. Below, what
leaves the house and the machine in the corner.

## Wall

`?kiosk=1`, or the Wall button: the sentence and the three numbers, for a shelf or a tablet, refreshing every thirty
seconds.

## Set up

Behind the admin token, once per browser. Sources, alerts and Telegram, packs (a switch each; code packs behind one more
switch), integrations, keys, the node's place in the tree, and the bootstrap settings read-only. A test-alert button.
Changes are live within twenty seconds. A blank field returns a setting to `.env`. A value set here **overrides** the
same key in `.env`, and the page says so next to it; `planetai telegram` writes both places so they cannot disagree.

Settings live in a `settings` table that overlays `.env`; the code reads them at the moment of use. Ports, the database
and the extra containers stay in `.env` because they are read once at start.

## Access

Reads are open on your network, like the API: a household display cannot need a login. Writes need the token. It is a
password.
