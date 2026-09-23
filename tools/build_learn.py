#!/usr/bin/env python3
"""Build app/static/learn.json, the learn layer's marks, out of docs/site.

    python3 tools/build_learn.py            # write app/static/learn.json
    python3 tools/build_learn.py --check    # fail if the committed file is not what docs/site says

The node does not serve docs/site; the site build does. So the marks are extracted here, at build
time, into one small file the page fetches only in learn mode. Every quote is a VERBATIM span of the
page it cites — this tool never writes a word of its own into `quote`, it only cuts. A docs edit that
moves the prose therefore changes learn.json, `--check` fails in `make lint`, and somebody has to look
at the diff. That is the whole point: the tester guide cannot drift from the documentation it claims
to be quoting, because it is not a copy of it, it is a cut of it.

MARKS below names the cut, not the text: page, the `##` section it must sit inside, and the first and
last few words of the span. Short markers survive a reflow; a pasted paragraph does not. Each entry
also carries the page's own `# Title` as `page_title`, so the panel can cite "From <title> · <section>"
the way the site names it, rather than by a path in this repository.

The marks explain what the node is FOR and what it PUBLISHES as well as how to read the ladder: the
purpose and the DIDO rule from introduction.md sit on the foot and on the request ledger, and every
registered section carries at least one mark (tests/test_learn.py holds the page to that).

`more` is the only prose here, and it is the PAGE talking about itself — what this dashboard draws,
in the dashboard's voice — never a paraphrase of the docs. The panel labels it as such.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs" / "site"
OUT = ROOT / "app" / "static" / "learn.json"
DOCS = "https://planetai.fab.city/docs"

# A quote is a counting unit like a sign: it has to be readable on its own, at the size the panel
# gives it. Sixty words is the ceiling the prompt set and it is about right — past that a reader
# stops reading and the mark has failed.
MAX_WORDS = 60

# key · title · page · section (None = the page's lead, above the first heading) · first words · last
# words · the page's own line. The order here is only the order learn.json lists them in, and the
# order Back and Next fall back to for a mark that is not on the view being read. The walk itself
# follows the page: dashboard.js steps through the marks in the order the current view drew them,
# top to bottom. Grouped below by where each mark is drawn.
MARKS = [
    ("dial", "The ladder: one rung per resolution", "dashboard.md", "The lead",
     "The **ladder** sits above the lead", "are struck through.",
     "The rungs that may leave the machine are drawn as a dotted texture rather than the cells "
     "blue, so blue keeps its one meaning on this page: an H3 cell. Under the ladder, a fold draws "
     "one cell at the rung you are on against the rungs either side, to scale, and what each "
     "thing this node speaks for costs to cover at it."),
    ("lead", "The lead", "dashboard.md", "The lead",
     "The first thing on Now", "`live`, `stale` or `cached`.",
     "The node computes and the page draws. A number this page worked out for itself would be a "
     "bug, which is why the sentence, the numeral and the state word all arrive from GET /issues."),
    ("containment", "Exact in the index, approximate on the ground", "dashboard.md", "The lead",
     "At resolution 8 one cell is", "how many of those are its own.",
     "That is the documentation's example resolution line. The one under Decide is tonight's, read "
     "from this node, and when the neighbouring rungs give the same answer the page says so."),
    ("distances", "Four distances, not four resolutions", "concepts.md", "Sources and sensors",
     "**The four distances.**", "sekitar · wilayah.",
     "The page prints them as house, street, ring and region, on one scale, so the eye can answer "
     "whether it is me or everywhere without arithmetic."),
    ("prov", "Provenance words", "concepts.md", "Provenance words on the page",
     "`live`: measured by this node", "the node's own engine.",
     "Provenance is ink only and square on this page, never a coloured pill, and the full H3 id is "
     "printed once per object and never truncated."),
    ("cell", "The cell this node stands in", "concepts.md", "The node and its place",
     "**The H3 cell.** The node stands", "with its edge length beside it.",
     "Resolution 8 is coarser than the rounding already applied to the node's position, so the "
     "cell drawn on the ground puts nothing back that the node had held out."),
    ("tiles", "What a map costs", "dashboard.md", "The ground",
     "Three bases: `plan`, offline", "`osm`, OpenStreetMap tiles.",
     "The request count sits in the tab bar so the price of switching to satellite is visible "
     "before you pay it: live tiles need MAP_TILES=on, and a press may only ever reduce it."),
    ("stages", "The order the loop runs", "dashboard.md", "The sections",
     "Every section is registered with the page contract",
     "observe, decide, act, measure.",
     "Observe, decide, act, measure: the four stages this page is read in. A section whose data "
     "is not on this node prints one honest line in its place, never a blank and never a guess."),
    ("cards", "Four card kinds and no fifth", "dashboard.md", "The sections",
     "Four card kinds and no fifth:", "a factor of a thousand.",
     "The house is the solid line, the ring dotted, the street and the region dashed, the line "
     "itself dashed red. Where a distance has no source its trace is absent and the legend says "
     "which one."),
    ("states", "States, in weight not hue", "dashboard.md", "Issues, states and distances",
     "For every issue the keeper declared", "or `none` (no record).",
     "State is carried by weight, fill and dash, never by hue: act is set at 700 and the other "
     "states at 500. Colour is argument only: blue a cell, green a loop closed, red a line crossed."),
    ("custody", "Custody: who may be counted", "concepts.md", "Sources and sensors",
     "**`custody`.** A generated column", "still never be counted.",
     "Your own instruments are drawn in ink on this page, the borrowed ones faint, and what only "
     "the satellite knows in orange."),
    ("share", "Reach, not publishing", "sharing.md", "`SHARE_LEVEL`",
     "`SHARE_LEVEL` is reach, not publishing", "it is live within 20\nseconds.",
     "The request ledger below is this page confessing what it asked of the world while you looked "
     "at it. The offline plan asks nothing; Telegram is reached by the node, never by this page."),
    ("raw", "Raw readings stay", "how-it-works.md", "What leaves the machine, and what never does",
     "Raw readings stay.", "under CC BY 4.0",
     "The barcode under Observe is hourly means of the house's PM2.5: the finest time step this "
     "page shows, and still not a raw reading."),
    ("levels", "Three levels, one floor", "alerts.md", "Levels",
     "`ALERT_LEVEL` (default `act`) is the floor", "is written from.",
     "An alert's acted_at stays null until a person acts and records it, with this page's button, "
     "the CLI, the bot, a radio or an agent. It is the one measurement the node cannot make itself."),
    ("current", "Conditions that are not events", "alerts.md", "Conditions that are not events",
     "The dashboard marks\nan open act-level alert", "the alert is still open.",
     "A heat alert is a condition that holds for hours; a cooking spike is an event with a "
     "cooldown. The schema does not yet know an alert can clear, so the page says which it is."),
    ("rho", "ρ: the loop closed", "rho.md", None,
     "ρ (rho) is the share", "rather than an app feature.",
     "The page draws it as the alerts answered over the alerts raised, with the median minutes to the "
     "first answer, and counts the rings rather than sizing them."),
    ("refusals", "Refusals that hold at every stage", "how-it-works.md",
     "Refusals that hold at every stage",
     "No raw readings leave the instance", "not declared from above.",
     "The care label under Measure is those refusals as signs. Nothing to press on the wall is the "
     "wall's own refusal: it is an instruction, not a control."),

    # --- Now: the sections that had no mark ------------------------------------------------------
    ("counted", "Yours, here, and counted", "sensors.md", None,
     "Once one is", "`local` and `custody`.",
     "`planetai sensors` prints these stations one line each, with `yours` or `reference` beside the "
     "id, and GET /sensors is the route a script reads them from. Only the ones in this node's "
     "custody can make a cell say live."),
    ("dido", "Data in, data out", "introduction.md", "What it is for",
     "The rule it runs on", "moves between cities.",
     "On this page the rule is small enough to check: every request this page made of anywhere but "
     "this node is in the ledger below, and the plan base makes none. What the node itself sends "
     "upward, and to whom, is on the Network view."),
    ("forecast", "Context, not a prediction", "packs-reference.md", "forecast",
     "Official and model weather for this point", "it never sends an alert.",
     "The card is drawn from GET /forecast: the wind and the rain for the hours ahead, and a "
     "forecast point more than 10 km from the node is said to be another place. Nothing on this "
     "card can raise an alert."),
    ("recommend", "What this node suggests", "packs.md", "Rules",
     "End a message with a paragraph that starts with", "the page will not invent one.",
     "Record the decision posts `stage: decided` to POST /actions with your name and what will be "
     "done; Take its word fills in the rule's own line. The act comes after it, under Act."),
    ("looked", "A decision moves nothing", "first-ten-minutes.md", "When a real alert arrives",
     "A decision closes no alert", "the record that somebody looked.",
     "With DECISION_REQUIRED=1 (Set up → Node) the node refuses an act that has no decision "
     "recorded before it, with 409, however the act arrives."),
    ("agent", "An agent drafts, a person dispatches", "agents.md", None,
     "An agent is a guest on the machine", "a person dispatches.",
     "The `issues` tool an agent holds over POST /mcp returns the same object this card is drawn "
     "from, so it may draft what to do. The decision recorded here carries the name of whoever is "
     "deciding."),
    ("claims", "One number, over how much ground", "dashboard.md", "The sections",
     "\"Whose word, over how much ground\" covers", "that one number has to cover.",
     "The line above the fold names the widest and the narrowest footprint; the fold holds all six. "
     "Each card counts its cells at the rung you are on, so the count moves with the ladder."),
    ("workshop", "The nearest place to make it", "introduction.md", "What it is for",
     "The `make` pack names the nearest fab lab", "is the direction.",
     "Under the alerts in Act, the row with the nearest fab lab is that sentence where the pack is "
     "on: the lab, how far, and the dated archive it came from. With MAKE_ENABLED off, the row is "
     "the node's own help text for that setting instead."),
    ("note", "The note is the record", "cli.md", "Reading the node",
     "`planetai act` is the terminal's way", "record of what was\ndone.",
     "Each row here is one of those records, newest first: who, which stage, how long ago, and "
     "decided first where a decision came before the act."),
    ("bot", "An answer in the household's words", "bot.md", None,
     "Somebody in the house asks", "in\ntheir words, as an act.",
     "An act recorded through the bot lands in this ledger like one pressed on this page, with the "
     "person's own words as its note."),
    ("actions", "The table ρ is counted from", "schema.md", "Tables",
     "The ρ instrument:", "one row per answer.",
     "The note column is shown here only to a reader with a token, because GET /actions is on no "
     "sharing allowlist."),
    ("effect", "Elapsed time, not an effect", "rho.md", "What worked, per rule",
     "It is elapsed time, not an effect.", "and the node cannot tell.",
     "One row per rule, read from GET /effect over the whole record: how many acts, and how many "
     "were followed by the condition stopping. A recovery time in hours appears only for a rule "
     "that declares what it watches."),
    ("figures", "One API, and no private path in", "api.md", None,
     "Every node exposes the same API on port 8080.", "has a private path in.",
     "Every row here arrived in GET /issues as provenance: the figure, its value, where it came "
     "from, the node's word for it and its age. A script or a spreadsheet reads the same route, "
     "with a token, or with none at SHARE_LEVEL=open."),

    # --- Historical ------------------------------------------------------------------------------
    ("shape", "The day this place usually has", "api.md", "Sensors and readings",
     "The day this place usually has: one mean", "(`local`) count.",
     "The page waits for seven local days before it draws a day, and until then says how many it "
     "has. GET /shape?metric=pm25 returns the same hours, with how many hourly means went into each."),
    ("earth", "It says something changed, never what", "packs-reference.md", "earth",
     "The node's own copy of Google's AlphaEarth", "never what.",
     "The years come from files this node already holds, read through GET /earth, and the node "
     "fetches none of them while you look. `planetai run earth fetch` is how a year gets here."),
    ("reach", "Where this node's own line starts", "install.md", None,
     "This page puts the node itself on a machine", "keeps every reading it takes on this machine.",
     "Each row is one kind of source, with the oldest and newest hourly mean this node holds for it, "
     "from GET /reach. The climate normals the node pulled at install are dated years before it was "
     "switched on; its own sensors start on the day they were first polled."),
    ("trust", "Whether its own sensors tell the truth", "packs-reference.md", "trust",
     "Whether the node's own sensors are telling it the truth", "all three\nwere wrong.",
     "The figures here are GET /trust, one row per local sensor: its coverage over seven days, the "
     "channels that stopped moving, and how old the sensor is, which explains a low coverage without "
     "a fault."),

    # --- Network ---------------------------------------------------------------------------------
    ("parent", "One cell in a district's picture", "federation.md", None,
     "With a parent set", "and nothing else.",
     "The wires on the right are what leaves this node: hourly means to a parent, the Index cells "
     "and ρ. A wire with nothing on it is dashed. `planetai config set PARENT_API_URL` and "
     "`PARENT_TOKEN` give this node a parent."),
    ("registry", "What could be measured here", "sources.md", None,
     "A node measures what its adapters read.", "carried inside every node as a\npinned copy.",
     "The counts here are GET /sources, read the first time somebody opens Network: what the pinned "
     "registry lists for this place, how many entries have code on this node, and the places to make "
     "things and the designs to build. `planetai sources` prints the same list."),
    ("presence", "A coarse cell, and never finer", "channels.md", "Reticulum, LXMF",
     "Presence is separate and off by default", "so an exact place never leaves.",
     "The cell drawn here is the one this node would announce, and its area is the whole of what a "
     "stranger on the radio learns. GET /presence answers with enabled false until "
     "RETICULUM_PRESENCE=1."),
    ("mesh", "Where there is no WiFi", "channels.md", "Meshtastic, the LoRa mesh",
     "For sensors and alerts where there is no WiFi.", "when the\ninternet is down.",
     "What this card counts arrives through the gateway radio's MQTT uplink to this node's own "
     "broker. `planetai meshtastic` sets that up; with MESH_ALERTS=1 an act alert's first line goes "
     "back out over the mesh."),
    ("siting", "Named for its place, in a box made nearby", "sensors.md", "Siting",
     "Name it after the place", "Fab Lab Bali\nprints it.",
     "These are the devices on this node's own ground, with their source, indoors or out, what each "
     "measures and when it last spoke. The row for an open hardware manager says what is not here "
     "yet: design files, firmware, and where nearby a device could be made or mended."),

    # --- Set up ----------------------------------------------------------------------------------
    ("settings", "A setting is a decision", "configuration.md", None,
     "A setting is a decision the household makes", "for an online model.",
     "Each value here says where it came from. A value saved here is live within 20 seconds and wins "
     "over .env, a blank returns the key to .env, and every save is a row in actions with the actor "
     "dashboard."),

    # --- the foot, on every view but the wall ----------------------------------------------------
    ("production", "One computer per place", "introduction.md", None,
     "PLANETAI is the hyperlocal compute", "the place already owns.",
     "The foot of every view but the wall opens on this sentence and the purpose that goes with it, "
     "quoted from the documentation rather than rewritten, so this page and the documentation say "
     "the same thing."),
    ("purpose", "What a node is for", "introduction.md", "What it is for",
     "Its purpose is", "around each node.",
     "Every number on this page answers to that purpose. The issues the lead can name are air, heat, "
     "land and coast; water and soil are not among them in this version, so the page draws neither."),
    ("health", "What every screen asks first", "api.md", "Status",
     "What every screen in the house polls.", "outbound request of its own.",
     "The version at the foot is the one GET /health reports. Open it from the foot to read what "
     "every screen here asks first: the node, its version, its cell at resolution 8, its last poll."),
    ("mcp", "The surface an agent holds", "mcp.md", None,
     "This is the surface an agent holds.", "that somebody\nacted.",
     "The foot names POST /mcp for an agent handed this node's address: streamable HTTP, with "
     "Authorization: Bearer and the admin token on every call. `planetai agent` prints the snippet "
     "to paste into a client."),
]


def slugify(value):
    """build_docs.py's own slug, for the page-per-folder build where the prefix is empty."""
    s = re.sub(r"[^\w\s-]", "", value.lower(), flags=re.U).strip()
    return re.sub(r"[\s_-]+", "-", s) or "section"


def section_body(text, heading):
    """The markdown under one `##`, or everything above the first one when heading is None."""
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^## (.+)$", text, re.M)]
    if heading is None:
        end = heads[0][0] if heads else len(text)
        return text[text.index("\n", text.index("# ")):end]
    for i, (at, name) in enumerate(heads):
        if name.strip() == heading:
            stop = heads[i + 1][0] if i + 1 < len(heads) else len(text)
            return text[at:stop]
    return None


def cut(body, first, last):
    a = body.find(first)
    if a < 0:
        return None, f"the span does not start there: {first!r}"
    b = body.find(last, a)
    if b < 0:
        return None, f"the span starts but does not end there: {last!r}"
    return body[a:b + len(last)], None


def build():
    marks, errs = {}, []
    for key, title, page, heading, first, last, more in MARKS:
        src = SITE / page
        if not src.exists():
            errs.append(f"{key}: docs/site/{page} does not exist")
            continue
        text = src.read_text(encoding="utf-8")
        head = re.match(r"# (.+)", text)
        body = section_body(text, heading)
        if body is None:
            errs.append(f"{key}: docs/site/{page} has no section '{heading}'")
            continue
        quote, why = cut(body, first, last)
        if quote is None:
            errs.append(f"{key}: in docs/site/{page} · {heading or 'the lead'}, {why}")
            continue
        n = len(quote.split())
        if n > MAX_WORDS:
            errs.append(f"{key}: the span is {n} words, over the {MAX_WORDS} the panel holds")
            continue
        anchor = slugify(heading) if heading else ""
        marks[key] = {
            "title": title,
            "quote": quote,
            "more": more,
            "page": page,
            # The page's own `# Title`, which is what the site's sidebar calls it and what the panel
            # cites. A repository path means nothing to a household reading the panel.
            "page_title": head.group(1).strip() if head else page[:-3],
            "section": heading or "",
            "anchor": anchor,
            "url": f"{DOCS}/{page[:-3]}/" + (f"#{anchor}" if anchor else ""),
        }
    return {"order": [m[0] for m in MARKS], "marks": marks}, errs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="compare the committed learn.json with what docs/site says now")
    args = ap.parse_args()

    out, errs = build()
    if errs:
        sys.exit("learn marks that no longer have a span in docs/site:\n  "
                 + "\n  ".join(errs)
                 + "\n\nEdit tools/build_learn.py so the markers point at the prose as it reads "
                   "now. Do not paraphrase: the quote is a cut of the page, not a copy.")

    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if args.check:
        have = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if have != text:
            sys.exit("app/static/learn.json is not what docs/site says. Run `make learn` and look "
                     "at the diff: a quote moved because the documentation moved.")
        print(f"  learn.json: {len(out['marks'])} marks, every quote still a span of its page")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"  wrote {OUT.relative_to(ROOT)}: {len(out['marks'])} marks")


if __name__ == "__main__":
    main()
