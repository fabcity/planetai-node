# How the documentation site is written

The pages in this folder are the source of `planetai.fab.city/docs`. `tools/build_docs.py` renders them,
together with a few pages taken as they are from `docs/`, into static HTML on the programme layer's tokens.
Nothing here is served by a node.

## Voice

Written for the person installing at 9pm with a sensor that just went quiet. Plain words. Say what to do.
Short declaratives. Sentence case everywhere; no emoji, no hype, no "simply", no "robust". A page states what
the node does in this version, not what it will do. Where the code and an older document disagree, the code
wins and the page says which version it read.

Only facts that are in the code or in the canonical documents (`ARCHITECTURE.md`, `SPEC.md`, `AGENTS.md`,
`docs/*.md`). No line numbers in the prose. A gap or a known bug is stated plainly: "In v0.57 the AirGradient
adapter exists and is tested but is not registered for polling."

## Conventions the renderer understands

- One `# Title` per page, first line. The sidebar uses it.
- `## ` and `### ` headings make the right-hand "On this page" list. Keep them short.
- Endpoints are `### GET /path` (method in capitals, then the path). The renderer draws the method as a chip.
- The line right after an endpoint heading may be `Access: public` · `Access: open` · `Access: token` ·
  `Access: admin` · `Access: loopback or token` and so on. The renderer draws it as an ink chip.
- Settings, commands, files, metric names, cell names and values are in backticks.
- Tables are GitHub tables. A table is for parallel facts (settings, routes, rules); prose is for everything else.
- A note is a blockquote starting with a bold word: `> **Note.** …`, `> **Careful.** …`, `> **Gap in v0.57.** …`.
- Link to another page by its file name: `[the API](api.md)`. The renderer turns it into the right URL.
- Link to a repository file with its path from the repo root: `[init.sql](../../init.sql)`; the renderer
  turns paths that leave `docs/` into GitHub links at the built commit.
- Numbers, units and ids as the node writes them: `µg/m³`, `°C`, `pm25`, `Environmental|Community`.
