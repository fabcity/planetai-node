#!/usr/bin/env python3
"""Build app/static/learn.json — the learn layer's seventeen marks — out of docs/site.

    python3 tools/build_learn.py            # write app/static/learn.json
    python3 tools/build_learn.py --check    # fail if the committed file is not what docs/site says

The node does not serve docs/site; the site build does. So the marks are extracted here, at build
time, into one small file the page fetches only in learn mode. Every quote is a VERBATIM span of the
page it cites — this tool never writes a word of its own into `quote`, it only cuts. A docs edit that
moves the prose therefore changes learn.json, `--check` fails in `make lint`, and somebody has to look
at the diff. That is the whole point: the tester guide cannot drift from the documentation it claims
to be quoting, because it is not a copy of it, it is a cut of it.

MARKS below names the cut, not the text: page, the `##` section it must sit inside, and the first and
last few words of the span. Short markers survive a reflow; a pasted paragraph does not.

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
# words · the page's own line. Order is the order the panel walks, which is the order of the page.
MARKS = [
    ("dial", "The rail: one stop per grain", "dashboard.md", "The lead",
     "The **grain rail** sits above the lead", "are struck through.",
     "The stops that may leave the machine are drawn as a dotted texture rather than the cells "
     "blue, so blue keeps its one meaning on this page: an H3 cell. Under the rail, a fold draws "
     "one cell at the stop you are on against the stops either side, to scale, and what each "
     "thing this node speaks for costs to cover at it."),
    ("lead", "The lead", "dashboard.md", "The lead",
     "The first thing on Now", "`live`, `stale` or `cached`.",
     "The node computes and the page draws. A number this page worked out for itself would be a "
     "bug, which is why the sentence, the numeral and the state word all arrive from GET /issues."),
    ("containment", "Exact in the index, approximate on the ground", "dashboard.md", "The lead",
     "At resolution 8 one cell is", "how many of those are its own.",
     "That is the documentation's example grain line. The one under Decide is tonight's, read "
     "from this node, and when the neighbouring grains give the same answer the page says so."),
    ("distances", "Four distances, not four resolutions", "concepts.md", "Sources and sensors",
     "**The four distances.**", "jalan · model.",
     "The page prints them in the household's words — room, wall outside, street, model — on one "
     "scale, so the eye can answer whether it is me or everywhere without arithmetic."),
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
     "Observe, decide, act, measure — the four stages this page is read in. A section whose data "
     "is not on this node prints one honest line in its place, never a blank and never a guess."),
    ("cards", "Four card kinds and no fifth", "dashboard.md", "The sections",
     "Four card kinds and no fifth:", "a factor of a thousand.",
     "Room is the solid line, the street dotted, the model dashed, the line itself dashed red. "
     "Where a distance has no source its trace is absent and the legend says which one."),
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
     "The barcode under Observe is hourly means of the room's PM2.5 — the finest grain this page "
     "shows, and still not a raw reading."),
    ("levels", "Three levels, one floor", "alerts.md", "Levels",
     "`ALERT_LEVEL` (default `act`) is the floor", "is written from.",
     "An alert's acted_at stays null until a person acts and records it — this page's button, the "
     "CLI, the bot, a radio, or an agent. It is the one measurement the node cannot make itself."),
    ("current", "Conditions that are not events", "alerts.md", "Conditions that are not events",
     "The dashboard marks\nan open act-level ask", "the ask is still open.",
     "A heat alert is a condition that holds for hours; a cooking spike is an event with a "
     "cooldown. The schema does not yet know an alert can clear, so the page says which it is."),
    ("rho", "ρ: the loop closed", "rho.md", None,
     "ρ (rho) is the share", "rather than an app feature.",
     "The page draws it as the asks answered over the asks raised, with the median minutes to the "
     "first answer, and counts the rings rather than sizing them."),
    ("refusals", "Refusals that hold at every stage", "how-it-works.md",
     "Refusals that hold at every stage",
     "No raw readings leave the instance", "not declared from above.",
     "The care label under Measure is those refusals as signs. Nothing to press on the wall is the "
     "wall's own refusal: it is an instruction, not a control."),
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
        body = section_body(src.read_text(encoding="utf-8"), heading)
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
