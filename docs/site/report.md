# The report

The node's one scheduled message. One every `REPORT_EVERY` hours from `REPORT_ANCHOR`, in the node's own
time zone, six parts, under a hundred words, written by the node itself from SQL against its own tables — so
a node with no model reachable anywhere still gets it. `app/report.py` holds both halves: `bundle()`, every
number the node has about the window, and `sheet()`, the report.

## When

`REPORT_EVERY` takes 3, 4, 6, 8, 12 or 24: each divides 24, so the rhythm does not walk round the clock, and
anything else falls back to 6. `REPORT_ANCHOR` is the local hour it counts from (0–23). The defaults are 6 and
6: 06:00, 12:00, 18:00 and 00:00 where the node is. `planetai report every 12` and `planetai report at 7`
change it without a restart; so does the dashboard's Set up view.

The rules loop checks once a minute. In the first twenty minutes of a due hour it writes the report, and the
`reports` row for that local hour is the lock: a container that restarts inside the window does not send
twice. A report due inside quiet hours is written and stored with `held_quiet` and not sent; it appears on
the dashboard, saying so, and the next report to go out folds every held hour in and opens with "Overnight and
this morning." A node that was off for a week reports two days (the cap is 48 hours), not a hundred and
sixty-eight.

## The six parts

Deterministic, plain text, in `ALERT_LOCALE` (English, Bahasa Indonesia or Spanish), each part a sentence or
two, an empty part left out:

1. **Where the place stands.** Heat first if an open heat alert is act-level; else the worst indoor PM2.5
   against 35 (unhealthy) and 15 (the clean line); or that there is no sensor yet.
2. **What changed.** Up to two of the node's own sensors whose window was unusual: "the kitchen: the air
   ran higher than usual".
3. **What only the models know.** One clause if its rule is loaded and crossed — a heavy swell, or the
   satellite model reading the district over 35.
4. **What happened after this window's act alerts.** For each rule with a threshold: "{place} is back under
   {n}" or "still above {n}", at most two.
5. **The one thing to do before the next report.** A room still over the line; a sensor gone quiet; the first
   failing health check's own fix; or nothing.
6. **The invitation.** "Ask me anything about the air, the heat, the sea or what is around here."

Parts 2 and 3 share a paragraph; 4 and 5 share another.

## Two numbers behind it

**Notability** is the window's mean for a sensor and metric against the mean of the same local hours on
each of the previous seven days, in standard deviations of that baseline. It is null until three days
exist, so a node in its first week claims nothing. It decides which two places get a sentence in part 2,
which is how the report can say "the kitchen ran higher than usual" without anyone reading a chart.

**Trend** is the digest's ±3 rule read across to each metric's own units — 3 µg/m³ for PM2.5, half a degree
for a room's temperature, 5% of the window's range for a metric with no line of its own — comparing the second half of the window with the first.

## The bundle

Everything the sheet was written from, as one JSON document, SQL only, run as the read-only role: `meta`
(node, locale, local time, window, held hours), `series` per sensor and metric (min, max, mean, n, trend,
notability, the usual value and how many baseline days), `observations` (sea, weather, satellite air, place,
land, with yesterday's value), `now` (the `stats` view), `alerts` in the window, `open_act` (unanswered act
alerts in 24 hours, at most five), `sensors_quiet`, `rho` now and a week ago, `previous` (the last sent
report), `cells` with what changed, `rules`, the first row of every pack's `contributes: report` rule under
its own id (`digest`, `alone`, `ahead`), and `health`. The bundle is trimmed to 64 kB — what the smallest
model rung can hold — by dropping the least notable series first.

`GET /report/bundle?hours=` returns it behind the read-only or admin token; the MCP tool `report_bundle`
reads it too. Numbers in any sentence about the node must come from here.

## A model in the path

The schema is ready for one and this version ships without it. Every report row carries `sheet` (always the
node's own text) and `text` (equal to `sheet` until a model rewrites it), `depth` (`sheet` today; `brief`,
`standard`, `deep` reserved — `REPORT_DEPTH` is declared and changes nothing yet), `rung` (`node` today;
`local`, `remote`, `online` reserved) and `fallback_reason`, for the day a model's text is refused because it
invented a number, timed out, or there was no agent. The rule when it comes: the model is handed the bundle
and the sheet, and anything it writes is checked against the numbers in them before it is allowed out. The
sheet is what the node falls back to.

## Delivery and endpoints

The report goes to Telegram and Home Assistant. The mesh and Reticulum do not carry it.

| | |
|---|---|
| `GET /report/latest` | the last report row: `id, ts, due_local, window_hours, depth, rung, text, sent, held_quiet, fallback_reason`; open at `SHARE_LEVEL=open` |
| `GET /report/bundle?hours=` | what it was written from; read-only or admin token |
| `POST /report/now` | write one now and send it; admin token. Written without a `due_local`, so the scheduled one still happens |
| `planetai report` · `report last` · `report every N` · `report at H` | the same from the command line |
| `report_latest` · `report_now` · `report_bundle` | the same over MCP |

## Contributing to it from a pack

A rule with `contributes: report` and no message is never sent; its first row lands in the bundle under
the rule's id, where the sheet may read it and a model may quote from it. The `insight` pack's `digest`
(inside, outside, modelled, the day's mean and peak, the trend), `nearby`'s `alone` (a ring of fewer than
two stations, or none within 10 km) and `forecast`'s `ahead` (wind and rain for the next day) are the three
that ship. See [Packs](packs.md).
