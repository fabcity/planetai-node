# How the documentation site is written

The pages in this folder are the source of `planetai.fab.city/docs`. `tools/build_docs.py` renders them,
together with a few pages taken as they are from `docs/`, into static HTML on the programme layer's tokens.
Nothing here is served by a node, with one exception: `tools/build_learn.py` cuts short quotes
out of these pages into `app/static/learn.json`, which the dashboard's learn mode shows. Move one of those
spans and `make lint` says so.

## What a page is for

A person reads these pages to build a node one part at a time. The node is the local unit of
PLANETAI, hyperlocal compute and intelligence for distributed production, and its purpose is fixed: clean
air, water and soil for the people and the other living things around it. It measures its place, acts on
what it measures, keeps its raw readings at home and sends upward only what a district, a bioregion and
the Fab City Index need. The canonical wording is the lead and "What it is for" in `introduction.md`;
the README, `llms.txt`, `AGENTS.md`, the dashboard's footer and the programme page quote it, and
`tools/check_site.py` checks that they still do. So every page that has steps says, in its first
lines, which part of the node the reader is adding and what the node can do once it is there. Steps are
numbered when the order matters, and each one says what to do, what the screen shows when it worked, and
what that means for the node. A step the reader cannot check is not a step. The page ends by naming the
next part to add.

The path the pages follow: run a node → connect what measures your place → read it → let it ask, and
answer → measure whether it worked → extend it with packs and sources → join the network → put an agent
on it.

## Voice

Written for the person installing at 9 pm with a sensor that just went quiet. Plain words. Say what to do.
Short declaratives mixed with longer ones; never a march of same-length sentences. Sentence case
everywhere; no emoji, no hype, no "simply", no "robust", no "seamless". No em dashes: a comma, a colon, a
full stop or a bracket does the work. No "it's not X, it's Y" unless a real misconception is being
corrected and the replacement is named. A page states what the node does in this version, not what it
will do. Where the code and an older document disagree, the code wins and the page says which version it
read. The mission is stated in specifics (what stays, what goes up, which cell, who may be counted), never
in slogans.

Only facts that are in the code or in the canonical documents (`ARCHITECTURE.md`, `SPEC.md`, `AGENTS.md`,
`docs/*.md`). No line numbers in the prose. No first person. A gap or a known bug is stated plainly: "In
v0.72.1 the AirGradient adapter exists and is tested but is not registered for polling."

## Conventions the renderer understands

- One `# Title` per page, first line. The sidebar uses it.
- `## ` and `### ` headings make the right-hand "On this page" list. Keep them short.
- Endpoints are `### GET /path` (method in capitals, then the path). The renderer draws the method as a chip.
- The line right after an endpoint heading may be `Access: public` · `Access: open` · `Access: token` ·
  `Access: admin` · `Access: loopback or token` and so on. The renderer draws it as an ink chip.
- Settings, commands, files, metric names, cell names and values are in backticks.
- Tables are GitHub tables. A table is for parallel facts (settings, routes, rules); prose is for everything else.
- A note is a blockquote starting with a bold word: `> **Note.** …`, `> **Careful.** …`, `> **Gap in v0.72.1.** …`.
- Link to another page by its file name: `[the API](api.md)`. The renderer turns it into the right URL.
- Link to a repository file with its path from the repo root: `[init.sql](../../init.sql)`; the renderer
  turns paths that leave `docs/` into GitHub links at the built commit.
- Numbers, units and ids as the node writes them: `µg/m³`, `°C`, `pm25`, `Environmental|Community`.
