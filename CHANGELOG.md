# Changelog

## v0.41.1 — 2026-09-08 — one card cannot take the others down

**If your satellite cards went blank after updating to v0.41, this is the fix.** Nothing was deleted: the land,
the plan and the year-over-year pictures were still in the database the whole time. They were not being drawn.

The dashboard paints every card inside one `try`, and its `catch` only writes "node not answering" in the corner.
So anything that threw while drawing an early card silently cost every card below it — and the satellite cards
are drawn last, after the ring and the forecast that v0.41 added in front of them. A node whose `/nearby` or
`/forecast` returned a shape the new code mishandled would lose the land and the plan with no error anywhere.

Each card is drawn inside its own guard now. A card that cannot be drawn says so in its own box, names itself in
the browser console, and leaves every other card alone. Checked by breaking the ring card on purpose and watching
the earth card, the plan, the world tiles and the forecast all still render.

No data changed, no schema changed, and no pack changed. If your satellite cards were blank, they come back on
this update with the history they already had.

## v0.41 — 2026-09-08 — is this me, or is this everywhere

**For testers: two new packs, both quiet until you configure them, and neither one claims to know your city.**
`nearby` answers the only question that changes what you do when the air is bad — is it *your* address or is it
everywhere. `forecast` says where the wind is coming from and when rain is expected, and never sends anything at
all. Update with `./update.sh` as usual. This build also carries v0.40's trust-pack fix, which was tagged on
7 September but never reached the download.

### `nearby` — the ring of sensors around you

One kit cannot tell a fire in the lane from a haze over the island. Other people's sensors can. The pack reads
the public stations around this node from Bali Air Dispatch — which the node has fetched since v0.11 — and adds
three rules:

- **`only_here`** (act) when your address is well above a ring that is not. Go outside and use your nose; if
  something is burning, report it. It also says the enclosure might need a look, because that is the other cause.
- **`everywhere`** (info) when the ring reads it too. There is no fire nearby to find, and moving will not help.
- **`alone`** — no message, never sent. It is the line in your report that says this reading speaks for this
  address and nothing else, because fewer than two neighbours are reporting.

Two cards: where you sit inside the range your neighbours are reading, and who those neighbours are with their
distances. **Bali only for now**, because the archive is. Outside Bali the pack sits idle and says so.

**Your own kit is not in your own ring.** The archive republishes Smart Citizen devices, and this node polls Smart
Citizen directly, so the same box could arrive twice and every comparison would be the node arguing with itself.
Four rules stop it: devices this node already polls, anything within 150 m of the node, `BAD_EXCLUDE` by hand, and
one device arriving under two networks' ids. **`planetai run nearby stations`** prints every station in the
archive with its distance and the reason it is in or out. Read it once.

**The ring is thin here, and the pack says so rather than implying coverage it does not have.** At node #1, after
exclusions: one neighbour within 5 km, three within 10, six within 15. `BAD_RADIUS_KM` now defaults to 15.

**No Index cell**, deliberately. `live` means measured here, and the ring is measured by other people through a
third-party aggregation.

### `forecast` — what is arriving, and when

Wind, rain, temperature, humidity and cloud for the next day, from **BMKG** where the node is in Indonesia and
**Open-Meteo** anywhere. It fetches; it does not predict.

**It cannot send you anything.** One rule, no message, no level, no cell — it gives your daily report one line and
stops. After 7 September we are not shipping a pack that can start talking about tomorrow.

Set `FORECAST_BMKG_ADM4` to your point's village code and run **`planetai run forecast verify`**: it prints which
province, regency, district and village that code actually is, and how far it is from your node. Node #1 is
`51.03.05.2002` — Ungasan, Kuta Selatan — 194 m away. Open-Meteo is **off by default**: its free tier is
non-commercial only, and that is your call, not ours. With both on, the node records how far apart they disagree
and tells you, because neither of them is the truth.

Every value is stored with how far ahead of its own forecast it is, so a forecast that has quietly stopped
refreshing can be told from one that is right.

### new settings

```
BAD_RADIUS_KM=15            # was 8
BAD_MIN_SEPARATION_M=150    # closer than this to the node and a station is assumed to be your own hardware
BAD_EXCLUDE=                # station ids that are yours and the other rules missed
BAD_INCLUDE_INDOOR=0        # stations the archive suspects are indoors are dropped
LOCAL_RADIUS_M=500          # was read by the code and documented nowhere
FORECAST_BMKG=1
FORECAST_BMKG_ADM4=
FORECAST_OPENMETEO=0
FORECAST_POLL_HOURS=6
```

### fixed while we were in here

- Stations the archive suspects are **indoors or malfunctioning** are no longer stored as outdoor references.
- **One device, one row.** The archive does not dedupe OpenAQ against AirGradient: 23 of its 87 stations arrive
  twice under two networks' ids at identical coordinates, which weighted half the ring double.
- The ring was scoped by "not local", which counted **your own kits beyond `LOCAL_RADIUS_M`** as neighbours.
- Three gates were wrong and could not have caught any of it: two extracted a database view by matching to the
  first semicolon, and a semicolon inside a comment truncated it; and the channel-role check read only the core's
  sources, so a pack could never declare its own channels even though the docs tell it to.

## v0.40 — 2026-09-07 — the trust pack needs a week of data before it says anything

**For testers: the trust pack now speaks in the report, not in the alert stream.** At 21:17 tonight it sent node
#1's household three warnings on Telegram and all three were wrong. Every rule in it asked 24 hours and called the
answer an alert. All three now need seven days of a sensor before they will name it, and all three are `info` with
a seven-day cooldown, so what they find belongs in the week's instrument paragraph rather than in your evening.

Nothing else in the node changes: what it measures, when it speaks about the air, the heat, the sea and the land,
and what those alerts say are untouched. Update with `./update.sh` as usual.

**Your node will go quiet about its own sensors for a few days, and that is the fix.** A sensor with under seven
days of readings on this node is never named by this pack. Node #1's oldest local kit reaches a week on
9 September and the other four on 12 September; a node installed this week says nothing here until it has a week
of its own.

### what fired wrongly, and what each rule asks now

- **`channel_dead` fired at dusk on every kit with a light channel.** It asked for six flat hourly buckets out of
  the last 24 with the latest one flat too. Ungasan Kit's light channel reads 0 from dusk to dawn — eleven flat
  hours, ending in the latest bucket — so it matched every evening, as often as its 12-hour cooldown allowed. Any
  channel with a legitimate floor (light, uv, rain, noise) or a steady indoor value tripped it. It now needs a
  whole day: all 24 of the last day's hourly buckets present and flat, none of them moving, while another ambient
  channel on the same kit did move. A flat value of 0 is skipped, because a floor is not a freeze.
- **`peer_disagreement` said that 7.4 and 5.4 µg/m³ disagree, twice.** It compared 24-hour means on a ratio alone
  (0.85–1.15). At 7 µg/m³ that band is ±1 µg/m³, which is the integer resolution of a Plantower-class sensor and
  ten times inside its stated accuracy at low concentration; two identical units in clean air disagree by more
  than that most days. It also fired once for each unit in the pair, which is one fact twice. It now uses
  seven-day means, needs at least 100 of the week's 168 hours from both units, and needs the difference to clear
  an absolute floor as well as the band — 5 µg/m³ for PM, 2 °C for temperature, 5 points for humidity, 0.3 kPa for
  pressure. One alert per pair, naming both units and both numbers.
- **`coverage_low` had not fired yet and was about to.** 60% of 168 hours is unreachable for a node younger than
  about four days, so a new node would have said "missing most of the week" on day one. Same 60%, over seasoned
  sensors only.

### tests

The three rules are now run against node #1's own readings — the real series out of the 7 September dump, through
the rule SQL as it ships — so the light channel at dusk, the 7.4-against-5.4 pair and the four two-day-old kits
are regressions and not prose. See `packs/trust/README.md` for where every number comes from and what has still
never been exercised: none of these thresholds has met a burn season.

## v0.39 — 2026-09-07 — the node knows its version, writes its own report, and draws its own ground

Four parallel sessions of work, released once. v0.37 and v0.38 were written into this changelog but never
tagged and never bundled, and two more branches each wrote a v0.37 of their own — so nothing shipped under
either number and all four land here instead. Nodes update with `./update.sh` as usual.

**Known limitation, not fixed here.** A node still learns its new version one update late: `VERSION` is read
by the installer, not baked into the app image. Closing it means putting the stamp in the image.

### a node installed from the tarball knows which version it is

Every beta tester's node called itself `dev`. Testers install from the tarball, and the installer read the
version with `git describe`, which has nothing to read where there is no repository. A `VERSION` file sat in
the same folder saying `v0.36` and nothing looked at it.

- **`/health`, `planetai status` and the vitals row on the dashboard name the version the node runs.** A
  tester can say which version produced a problem.
- **`planetai version` prints a version.** On a tarball node it printed the node's name and place with an
  empty space where the version goes.
- The version is read from git, then from the `VERSION` file the tarball carries, then `dev`. `install.sh`,
  `update.sh` and `planetai version` had the same line; all three now read the file. A git clone reports what
  it always did.

**The update that brings this fix stamps `dev` one last time.** `update.sh` copies itself to a temporary file
and runs from there, so the script driving your update is the one you already had. Run `planetai update` a
second time and the version appears, or run `./install.sh` in the node folder, which is idempotent and reads
`VERSION` straight away. Nodes installed fresh from the tarball are correct from the first minute.

A household sees no change on the wall screen. This is release metadata: what the node measures, when it
speaks and what it says are untouched.

### one clock, and the node writes the report

Three schedules were sending messages from two containers and none of them knew about the others. Counted from
node #1's own `alerts` table over the 48 hours to 17:37 on 7 September, at the shipped `ALERT_LEVEL=warn`:

| | before | after |
|---|---|---|
| alert messages | 50 | 37 |
| scheduled reports | 2 | 6 sent, 2 written and held at midnight |
| from the agent container | 0 | 0 |
| **total** | **52** | **43** |

Thirteen of the fifty were warn-level — something changed, nothing to do — and they are report lines now.

**The `after` column needs one line from you.** `ALERT_LEVEL`'s *default* moves from `warn` to `act`, and a
default only reaches a fresh install: `update.sh` adds keys your `.env` is missing and never overwrites one it
already has, which is why nothing you chose has ever been changed by an update. Your `.env` says
`ALERT_LEVEL=warn`, so it will go on saying that. To take the thirteen:

```bash
planetai report level act        # or Set up → Alerts → Interrupt me for → "only when something needs doing"
```

The reports, the quiet midnight, the single clock and the act alerts that ask for nothing all arrive on their
own.

Two of those "before" numbers need saying out loud. **The agent container's 07:00 report has never arrived**, from
v0.30 to v0.36. `ask()` returns `(answer, rung)`; the line wrapped that in another tuple, so Telegram was handed
`"text": ["🌅 Good morning…", "local"]`, which the Bot API rejects because `text` must be a string. The handler
logged `brief failed: TelegramError` every morning after spending a full model round trip with tools on text it
threw away. Before v0.30 the unpacking was right and the copy did arrive, an hour after the node's own 06:00
report — which is the duplicate this release was written to remove, and which had already removed itself by
accident. And **`briefing/morning` fired once in five days**: the node's machine does not stay up, and a report
due in a window the node slept through was simply never written.

The 43 is still high because 21 of the 37 are `heat/heat_stress_now` at the 32 °C line node #1 still runs on
v0.34. v0.35 moved that line to 35 °C apparent and replayed 36 firings down to 8 over five days. A node on
v0.35 and this release, over the same two days: **about 27 messages, six of them reports, and nothing at all
between midnight and six.**

#### What a household gets

- **One report every `REPORT_EVERY` hours from `REPORT_ANCHOR`**, in the node's own time zone. Default 6 and 6:
  06:00, 12:00, 18:00, 00:00. `REPORT_EVERY` takes 3, 4, 6, 8, 12 or 24 and refuses the rest.
- **Six parts, under a hundred words**: where the place stands · what changed · anything only the models know ·
  what happened after this window's alerts · the one thing to do before the next report · ask me anything.
- **The node writes it, not a model.** SQL against its own tables. Most nodes have no model and get the same
  report. A model may rewrite it from v0.38, under a rule that refuses any number it was not given.
- **A report due inside quiet hours is written, stored and not sent.** It is on the dashboard the whole time,
  saying so, and the next one folds those hours in and opens with "Overnight and this morning". A node that was
  off for a week reports two days, not a hundred and sixty-eight hours.
- **`ALERT_LEVEL` is `act` by default**, where it was `warn`. Everything below the line is still recorded, still
  on the dashboard, and in the next report.
- **An act alert asks for nothing back.** No `#41` on the end, no button on the hero, no "Still waiting on you"
  in the report. From v0.39 the node watches what the sensors do after an alert and asks once, afterwards, what
  you did — with what it saw in the question.
- **The dashboard** has a new band under the hero: *Here — the last thing the node said*, with the report as you
  received it, the hours it covers, and a Report now button behind the settings token.
- **Spanish.** The report renders in `es` as well as `en` and `id`. It is the first Spanish anything on the node.
  Both the Spanish and the Bahasa Indonesia templates are assistant-written and no native reader has been through
  them; treat them as a draft.

#### If you want the old rhythm back

```bash
planetai report every 12 && planetai report at 6
```

Two reports a day, at six and six. For the warn-level messages as well, set *Interrupt me for* → "also when
something changed" in the dashboard under Set up → Alerts, or `ALERT_LEVEL=warn` in `.env`.

**Nothing you chose is deleted.** On the first start after the update, a node that had `BRIEFINGS`, `BRIEF_MORNING`
or `BRIEF_EVENING` set writes `REPORT_EVERY=12` and `REPORT_ANCHOR=<your old morning hour>` once, logs it, and
leaves the old keys where they are. A node with `BRIEF_MORNING=7` keeps seven o'clock and keeps speaking twice a
day. A fresh install gets 6 and 6.

#### Under it

- `app/report.py`: `bundle()` — every number the node has about a window, as one JSON document capped at 64 kB —
  and `sheet()`, the six parts, with one template dict per language and no wording anywhere in the code.
- **Notability**: a window's mean against the mean of the same local hours on each of the previous seven days, in
  standard deviations of that baseline; null under three days, so a node in its first week claims nothing. It
  decides which two places get a sentence.
- **Trend** is the digest's ±3 read across to each metric's units: 3 µg/m³ for PM2.5, half a degree for a room's
  temperature, 5% of the window's range otherwise. One degree and three micrograms are not the same size of change.
- `reports` table, schema 0.23. The row for the local hour is the scheduler's lock, so a container restarted inside
  the twenty-minute window sends nothing. The old briefings asked `alerts`, which every rule also writes to.
- `insight/digest` carries `contributes: report` and no message: its numbers are in every report and none of it
  interrupts anyone. `contributes:` is documented in `docs/PACKS.md`, and `make lint` refuses a rule with both a
  message and a contribution, or with neither.
- `GET /report/latest` · `GET /report/bundle?hours=` (read-only token) · `POST /report/now` (admin token).
  `/briefing` answers 301 to `/report/latest` for one release and goes in v0.38.
- MCP: `report_latest`, `report_now`, `report_bundle` replace `daily_report`. Nineteen tools.
- CLI: `planetai report`, `report last`, `report every <h>`, `report at <h>`.
- The agent container reads no wall clock at all, and a gate refuses one.
- `notify`'s `force` argument is gone. It never did anything.
- **The pre-commit hook now runs `make test` as well as `make lint`.** AGENTS.md has required both since v0.14 and
  the hook ran one, so a commit in this release removed a function and left `test_shipped.py` red with nothing
  listening. Re-copy it: `cp tools/hooks/pre-commit .git/hooks/`.

#### Not in this release

The 13:03 event on 7 September — one pot, three sensors in one room, six act alerts in five minutes — is still six
alerts. One event, one alert, and ρ measured from the sensors instead of asked for, are v0.39.


### local means here, not just yours

Node #1 moved to Ungasan in August. Three of its six Smart Citizen kits stayed behind at the old address, 1.2 km
away, and one sits 7.8 km away in another town — and every one of them still counted as this node's own
measurement, because `local` had only ever meant "on your account." A kit that measures a different building was
filling this node's indoor cells, feeding its heat alerts, and hiding in its coverage figures next to sensors that
are actually here. This release closes that, and adds a pack whose job is to say when the node's own numbers are
not to be trusted.

- **`local` now means ours *and* here.** A sensor still has to be on your account, and it now also has to sit
  within `LOCAL_RADIUS_M` of the node — 500 m by default. On a node whose sensors are not all at one address, this
  can change what counts as local: a rule or a cell that reads local sensors may change value, or go quiet, where
  it did not before. That is a correction, not a regression — `docs/COVERAGE.md` has always said the node does not
  fill what it cannot measure; now it actually stops. `LOCAL_RADIUS_M` cannot be set until a node has updated to
  this release. At the default 500 m, node #1 keeps only its two outdoor kits (`sc-19236`, `sc-19874`) as local
  and loses all three indoor ones — every indoor rule and the `Social|Community` cell go quiet. Node #1's operator
  has instead chosen 1500, wide enough to keep the old address's three indoor kits without reaching the kit 7.8 km
  away: at 1500 m node #1 keeps its three local indoor sensors and gains its two local outdoor ones, the first
  time it has had both. Nothing on node #1 goes quiet at the radius it is set to run at. If your own sensors sit
  at more than one address, check your radius before you update — the 500 m default may take more of your kits
  out of "local" than you expect.

- **Heat rules are indoor-only now.** The apparent-temperature formula both heat rules use — Steadman's, with no
  wind term — is the indoor form; there is no still air on a street. Both `heat_stress_now` and `heat_danger` now
  read indoor sensors only. A node whose only local sensors are outdoors gets no heat alerts. That is the right
  answer, not a wrong number: the formula, and the 35 °C line the previous release measured with it, were never
  valid for what an outdoor kit reads.

- **Smart Citizen's `aqi` channel is now `bme_iaq`.** It was never an air quality index: it is the BME680 gas
  sensor's own internal index, and it shared a metric name with Bali Air Dispatch's real, vendor-published AQI —
  averaging the two averaged two different quantities together. Four things are true of the change: existing
  `aqi` rows from Smart Citizen stay in `readings` as history; no migration deletes them; no rule reads them any
  longer; and the new `bme_iaq` metric starts fresh, with no history behind it yet. Bali Air Dispatch's `aqi` is
  untouched — it is a real index from a different source and was never the problem.

- **A `channel_roles` registry says what a metric IS**, not just what it is called (schema 0.22). Five roles cover
  it: `ambient` (the air, water or land at a place, comparable between sensors at the same spot), `enclosure` (the
  inside of the instrument's own box, never comparable), `device_health` (the instrument reporting on itself),
  `derived` (computed by us, carrying its inputs' provenance), and `index` (a vendor's own composite number, never
  pooled or averaged with anyone else's). A role is declared once per `(source, metric)` pair, so every sensor
  that comes from one adapter shares it — nothing to set per sensor.

- **A new `trust` pack** watches whether the node's own instruments are telling it the truth. It needs no
  configuration and writes no Index cell of its own — a score for our own equipment invites optimising the score
  instead of fixing the sensor. It says three things: a channel that has stopped moving for six or more of the
  last 24 hours while the rest of its kit keeps reporting (`channel_dead`); a local sensor that has reported for
  under 60% of the last seven days even though its latest reading still looks current (`coverage_low`); and two
  sensors within 50 m of each other whose 24-hour means disagree by more than 15% (`peer_disagreement`), which
  asks you to swap the two units for a day rather than guessing which one is wrong. Two things it cannot see yet,
  because nothing declares their role: PurpleAir's `channel_disagreement` (already computed in the PurpleAir
  adapter, waiting on a rule) and Meshtastic's `altitude_m` (written outside the metrics the registry knows about).

- **`rhythm` stops blaming traffic.** It used to end an evening PM2.5 peak with "that is the burning and the
  traffic, not the weather." The one kit in the fleet with a noise sensor said otherwise: the street is loudest
  through the late morning and afternoon and quietest overnight, while PM2.5 peaks in the evening and again near
  dawn — the loud hours are the clean ones. `rhythm` now reads that noise channel and names the contrast instead
  of guessing a cause. A node with no local outdoor noise sensor gets no `rhythm` alert at all; that is deliberate,
  not a bug.

- **`/trust`, a dashboard card, and a health check** put all of this somewhere you can see it. `/trust` returns one
  row per local sensor: its 7-day coverage, how many of its channels are currently frozen, and its age. The
  dashboard's new card shows only the sensors worth a second look, and says plainly when none need one. The
  agent's health check reads the same endpoint the card does, so the two never drift apart from each other, and it
  names the fix in plain language: power-cycle the kit, and if the number stays frozen, replace that sensor.

Two things this release has not done. The trust pack's three thresholds were chosen against one low-PM week at one
site (6–10 µg/m³, 1–7 September) and have never been tested against a burn season, when PM2.5 swings far wider and
disagreement between units may widen with it. And the new dashboard card has not been checked by eye at 375, 768
or 1440 px — only against the data it renders.


### the ground under the hero is the cell this node stands in

Since v0.36 a map cell has sat behind the sentence on the hero and on the wall. It was the same cell on every
node: node #1's, in Kuta Selatan. On a node anywhere else it looked like that node's own place and was not, so
the line naming it was cut and the drawing said nothing at all.

- **The node draws its own cell**, from the coordinates it was set up with. The resolution-8 cell it stands
  in, the seven smaller cells inside it, and its neighbours' edges running off the frame.
- **The cell is named again, under the hero and on the wall**: `8839446033fffff · RES 8 · 525 M EDGE · THE
  CELL THIS NODE STANDS IN`. That id is the node's place in the index, and it is now true wherever the node
  is. The edge is this cell's own, measured. H3 publishes 531 m for resolution 8; that is an average, and no
  cell is exactly it.
- **`/health` carries the cell**: id, resolution, mean edge in metres. Agents and `planetai status --json`
  read the same thing the screen shows.
- Change the node's coordinates and restart, and the ground follows.

The drawing is computed here, not fetched. A node on a LAN with no route out still draws its own cell. It is
the same picture `planetai-design` draws with d3-geo, to the last vertex, and a test redraws node #1's cell
and compares against the shipped file to keep the two together.

`planetai update` rebuilds the image, which now carries one more library, `h3`. A node that has not been told
where it stands keeps the picture it had, naming nothing.

## v0.36 — 2026-09-07 — the dashboard says what the colours mean

Six things on the dashboard were decoration wearing the clothes of information. They are gone, and a check now
fails the build if they come back.

- **The big green hexagon behind the number is gone.** In its place the node draws the map cell it stands in:
  the cell, the seven smaller cells inside it, and the edges of its neighbours running off the frame. It is
  drawn faint, behind the sentence, and it is computed geometry rather than a shape someone liked. The
  isometric mesh that used to cover the hero has gone with it.
- **The number is the same colour as the words, until it is not.** It used to be green whatever it said. Now
  it is ink, and it turns red when the reading is over the line the sentence names. Nothing else on the page
  is green except a loop that closed.
- **"I did this" is a green button.** Pressing it is the response, and that press is what ρ counts. Orange
  now appears in one place only: the buildings on the plan that the satellite can see and the map has not
  drawn.
- **Numbers are set in JetBrains Mono.** Digits line up between one reading and the next, so a column of
  readings can be compared by eye. The font is on the node, so it looks the same on a house with no internet.
- **The two glows drifting behind the page are gone.** So is every gradient.
- **The label beside the satellite section is a mark and a word, in ink.** It was a rounded blue pill, which
  looked like a verdict on the number next to it. It says where a number came from and nothing about whether
  the number is good.

A household on a wall screen will notice the page got quieter and the number got easier to read. Nothing about
what the node measures, when it speaks or what it says has changed.

Under it:

- `tools/check_ui.py` gained seven rules and fails on each: a six-sided `clip-path` wider than 24px, any hex
  from the website palette, any gradient, a control rounded past 8px or a card past 18px that is not on a dated
  legacy list, a provenance mark carrying a colour, orange anywhere but the satellite layer, and Fab Blue
  `#20388D` on the dark ground where it measures 1.72:1 and cannot be seen. The dark register's blue is
  `#7FA5E8` at 7.21:1.
- `tests/test_check_ui.py` breaks each of those rules against a copy of the real page and requires the check to
  name it. It runs in `make test`.
- The dashboard is still one HTML file with no build step. The two things it cannot hold, the ground and the
  font, are served by name from an allowlist in `app/main.py` and revalidate on every load, so an updated node
  never shows the previous design.

## v0.35 — 2026-09-07 — the heat rule was measuring Bali, not a heatwave

Two thirds of every message node #1's household received was one rule. `heat_stress_now` fired 20 times in the 48
hours of 5–7 September, always reporting 32.0–34.6 °C, and four of those arrived between one and five in the
morning — act-level alerts are the ones quiet hours do not hold. The reports-and-messages release moves
`ALERT_LEVEL` to `act`, which drops the eight warn-level messages and leaves all twenty of these; the quiet nights
it promises would not have arrived on node #1.

- **`heat_stress_now` fires at 35 °C apparent, not 32 °C.** 32 is the bottom of the heat-index "extreme caution"
  band, and in Kuta Selatan that band is the climate. Measured on node #1's own five days of `temp` and `humidity`:
  the hot room was above 32 °C for 86% of every reading, never fell below 28.7 °C, and averaged 33 °C at four in
  the morning — its coolest hour. 35 °C is that sensor's 90th percentile. Replayed over the same record with the
  rule's real cooldown it fires eight times in five days instead of thirty-six, none at night, and nothing at all
  on the two days the weather eased.
- The other three candidate fixes were replayed against the same data and rejected on it. A duration condition
  (over the line for four readings running) changes the count from 36 to 36 — the house is over 32 °C
  continuously, so there is no spike to suppress. Requiring AT to be rising fires on the ordinary morning warm-up
  every day and goes silent on a flat hot night, which is the case that hurts people. A cooldown of 1440 minutes
  reaches the same eight, but every one of the eight is still a false alarm. The cooldown stays at 240; at 35 °C it
  no longer matters.
- The Social cell keeps 32 °C. Counting hours of exposure is not interrupting someone, and 32 °C is the right line
  for a count.
- `packs/heat/README.md` now says which place the numbers were written for, as `docs/PACKS.md` requires, with the
  node #1 distribution the 35 °C came from and how to move it for a temperate flat.
- **New gate:** a pack README's unit-bearing thresholds must appear in that pack's own files. The README is the only
  place a household can learn why a number is that number, and nothing was checking that it still matched the SQL.

The alert texts are unchanged: this release changes when the rule fires, not what it says.
## v0.34 — 2026-09-07 — the years, as pictures you can play

The land card knew about one year pair. Nine years were on the disk beside it and it said nothing about them.

- **`planetai run earth frames`** draws one picture of the place per cached year: the strongest direction
  through the 64 embedding dimensions, mapped to grey. Dark water, bright land, roads and plots legible, the
  node ringed, a 1 km bar, and the year burnt into the corner so a frame that leaves the node still says
  when it is. About 780 kB a frame, nine years in a few seconds, from files already downloaded.
- **The card plays them.** A play button steps through the years, a slider stops on any one, and a second
  button switches to the change map. Pick 2019 and it stays 2019 — the page refreshes every half minute and
  no longer drags you back to the newest year.
- **The narrative now tells the whole record**: how many years are held, what the full span found, and a
  year-by-year list of the share that changed, so the shape of the history is visible. At node #1 that is
  eight years, 8.8 % of the square, 880 hectares — with the two quietest years in the record being
  2020→2021 and 2021→2022.
- **The images are named as files.** The card prints the directory they live in on the node and links the
  ones it is showing. A page cannot open a folder on the machine serving it; browsers do not allow that, so
  it says where they are instead of pretending to a button that cannot work.

**These are not photographs.** This pack has never downloaded imagery: it holds a model's 64-number
description of every 10 m pixel, and a frame is that description flattened to one number and drawn. It looks
like a panchromatic satellite image because the strongest thing in the embedding is the strongest thing in
such an image, but no camera saw these greys, and the card says so. For real Landsat and Sentinel-2 frames,
`planetai run earth-engine timelapse` downloads pictures and needs an Earth Engine key.

The projection is fitted once, over every year cached at the time, and then kept in `meta.json`. When next
year's layer arrives it is drawn through the same projection, so the new frame joins the sequence instead of
silently redrawing every frame before it. `planetai run earth frames --refit` redoes it, which is what a
moved square needs and a new year does not.

## v0.33.8 — 2026-09-07 — the whole satellite history in one command, and an argument it does not know is an error

Reported from node #1: `planetai run earth change --all` printed a perfectly ordinary result for the latest
year pair. The flag did not exist yet, and the way the arguments were read, anything that was not a
four-digit number was dropped — leaving an empty list, which meant "the default". A plausible answer to a
question nobody asked is worse than an error.

- **`planetai run earth change --all`** computes every consecutive cached pair and the span from the oldest
  cached year to the newest, then prints them as one table. Pairs already computed are skipped unless
  `--force`. With nine years cached that is nine comparisons in a couple of seconds; the download is the only
  slow part and it has already happened.
- **An argument the script does not recognise now stops it**, naming the argument and printing the usage.
  A mistyped year (`217`) or a single year does the same.
- **Read the span first.** At node #1 the eight-year span flags 8.80 % of the square and the eight yearly
  steps sum to 8.51 %, so the areas agree. What does not agree is the mean: the yearly means sum to 0.2991
  against the span's 0.0673, four fifths of it cancelling out year to year. The span's p95 sits at 3.65 times
  its median where every single year sits between 2.1 and 2.8, and 92 % of its flagged pixels lie inside
  patches against 82–89 % for the years. The span is the cleaner picture of what was built; the yearly rows
  say when. The pack's README carries the numbers.

## v0.33.7 — 2026-09-07 — one landmark emptied the kilometre

The plan of the kilometre went blank on node #1 the day it moved, and stayed blank through three releases that
each looked like the cause. It was neither the cache nor the coordinates: it was one feature.

- **A poi mapped as an open way stopped the whole plan drawing.** OpenStreetMap carries Garuda Wisnu Kencana as a
  way with a poi tag; the draw took `coordinates[0][0]` as a point, which for a LineString is a bare number, and
  threw. Because the draw is not awaited the rejection was unhandled: an empty band, no message, nothing in the
  node's log. A poi now draws from the first coordinate of any geometry, and each feature is drawn inside its own
  try, so one undrawable object costs that object and nothing else.
- The caption and legend now count what is drawn rather than what was read: it claimed 2,714 buildings where 2,699
  have outlines, because fifteen are mapped as nodes.

If a plan is missing after this, the band now says so instead of disappearing (v0.33.5) and the page follows the
node's version without a hard reload (v0.33.6).

## v0.33.6 — 2026-09-07 — the update reaches the screen

`GET /` sent no cache headers, so after `planetai update` a browser could keep serving the dashboard it already
had — with the bugs the update fixed. An ordinary reload does not always revalidate a document the server said
nothing about. This is why the plan-band fix in v0.33.5 appeared not to work: the node was serving it, the browser
was not running it.

- The dashboard is sent with `cache-control: no-cache, must-revalidate`. One hard reload is needed to get past a
  copy already in a browser; after that, a node's version and its page stay together.

## v0.33.5 — 2026-09-07 — the kilometre came back

The plan of the kilometre disappeared from a dashboard and stayed gone. Nothing was wrong with the node: it was
serving 4,906 features for its new point in 1.3 seconds.

- **The plan band no longer hides itself in silence.** One failed or interrupted `/place/geojson` was cached as
  "no features", and because the cache was then set, nothing refetched for the life of the page — the band vanished
  until a manual reload, with no message. A node whose coordinates had just changed was the way in: the refetch
  takes a while, and a page opened during it never recovered. Now the band stays and says which of the three things
  happened, and a failure is retried on the next refresh. A node whose place pack has never run keeps it hidden.
- **The dashboard no longer scrolls sideways on a phone.** The five buttons of the view switcher are 449 px wide
  with no shrink, so a 375 px screen slid the whole page. The row scrolls inside itself now. Present since v0.28;
  the beta review's "no overflow at 375/768/1440" was a false pass.
- The plan's caption said "1 buildings on the map. Uses: ." where a place has no mapped uses.

## v0.33.4 — 2026-09-07 — moving a node

Both location packs kept their caches when the node's coordinates changed. Found by asking how to regenerate the
plan after editing `NODE_LAT` / `NODE_LON` in `.env`.

- **`place`**: the staleness test read only the radius and the age, and `place_runs` never recorded where the fetch
  was centred. A moved node served the previous neighbourhood's geometry to the plan for up to thirty days while
  computing "nearest school" and "nearest clinic" from the new point against those old features. The run now records
  its point, a move refetches on the next poll and says so in the log, and the satellite footprints and the yearly
  series are cleared with it — they described the old circle and only the Earth Engine step refills them.
- **`earth`**: a moved point or a changed `EARTH_RADIUS_M` re-resolved the tiles but skipped every cached year as
  "already cached", so the node went on comparing a square around the previous address, with `meta.json` claiming
  the new one. Those years are now re-read, with the reason and the count printed first (about 103 MB a year).
- **`earth`, found while rehearsing the move**: a partial re-fetch used to leave one year from each square and
  `change` compared them, reporting the difference between two places as a year of change; and the old square's
  change map stayed on disk, where `/earth`, the dashboard card and the Index cell kept reading it. Both are removed
  with the square now, and `change` refuses a year that has no window recorded for the current square.
- **Both**: a correction smaller than 1% of the radius, never under 25 m, is not a move — retyping a decimal costs
  no download. `planetai run place verify` and `planetai run earth verify` now fail on a cache that belongs to
  another point; earth's step 5 claimed to check this and only measured the window's span.
- To move a node: edit `.env`, `planetai restart`, `planetai run place refresh`, then reload the dashboard. Both
  pack READMEs say it.

## v0.33.3 — 2026-09-07 — `planetai update` ships a pack's code, not its libraries, and now says so

From node #1, after updating to v0.33.2 and running `planetai run earth fetch`: 9 MB of tile index downloaded,
then `ModuleNotFoundError: No module named 'rasterio'` printed once per year, nine times, naming no fix. The
node had the pack and not its libraries, because `app/requirements-packs.txt` is gitignored and only
`planetai packs install` writes it. That split is deliberate — a listing should not rebuild your image — but
nothing told you which side of it you were on.

If you are on a node that has this now: **`planetai packs install`, then `planetai restart`.**

- **A pack script that needs a library it has not got says which command installs it, and stops before doing
  any work.** `planetai run earth fetch` on such a node now prints four lines and exits, instead of
  downloading the index and failing nine times.
- **The same hole existed in two older packs**: `planetai run earth-engine timelapse` and
  `planetai run place satellite` both crashed with a bare `ModuleNotFoundError` if `earthengine-api` was
  missing. Both now name the fix.
- **`planetai update` warns when a pack declares libraries or settings the image does not have**, so you find
  out at the end of the update rather than the first time you run something.
- **`make lint` refuses a pack script that imports something from its own `pip:` list without saying how to
  install it.** Run against the three scripts that had the hole, it names all three.

## v0.33.2 — 2026-09-07 — the satellite card showed a broken image before you fetched anything

Reported from node #1 straight after updating: the land card showed a broken-image box with its alt text
spilling across the card, above the sentence telling you to run `planetai run earth fetch`. Every node that
had not fetched satellite data yet looked like this.

The script hid the image correctly. The CSS did not let it: `#earth-img` sets `display:block`, and any
display rule of ours beats the `hidden` attribute, whose `display:none` comes from the browser's own
stylesheet. The comment one line above it in the same file warned about exactly this — it is how an empty
orange act strip once showed on every node with nothing to act on — and the rule was written anyway.

- **Fixed**: `#earth-img[hidden]` now cancels the display rule, and the empty state also drops the image's
  `src` so nothing is requested. Verified on a node in both states: with no data the image computes to
  `display:none` and occupies nothing; with data it renders the 1000 px map at 643 px inside its card.
- **`make lint` now catches this class of bug.** `tools/check_ui.py` checks that anything the script hides
  with `.hidden` is not un-hidden by a display rule on its id or any of its classes. Run against the two
  bugs that shipped — this one and the 2026 act strip — it names both.

Nothing else changed. The number, the map, the endpoint and the Index cell are the same as v0.33.1.

## v0.33.1 — 2026-09-06 — one number for the land, not two

Found on the way out of v0.33: the new `earth` pack and the older `earth-engine` pack both published a
year-over-year land-change number, both labelled `partial`, both described in words as "the land changed",
and they disagreed. On node #1 Earth Engine said 0.037 and the earth pack said 0.041. They were measuring
different things — Earth Engine took the cosine distance between two years' *mean* vectors over 1 km, the
earth pack takes the mean of the *per-pixel* distances over 10 km, and averaging vectors first cancels the
noise that averaging distances keeps — but nothing on any screen said so.

For a tester, what changes:

- **`earth-engine` no longer reports land change.** Its `land_change_score`, its second
  `Environmental|Bioregion` cell and its `land_changed` alert are gone. It keeps what only Earth Engine can
  give: tree cover and built-up fraction from Dynamic World, Sentinel-2 NDVI, VIIRS night lights.
- **The `land_changed` alert is gone and nothing replaces it yet.** It was going to move to the `earth`
  pack, and then the measurements said not to. Four pilot squares, 2024→2025: Kuta Selatan 0.041, Boston
  0.040, Barcelona 0.016, Santiago 0.015. Boston and Barcelona are at the same latitude and differ by two and
  a half times, and Boston's change is spread over built-up land rather than water, so the likeliest reason is
  snow and leaf-off between two annual composites — not 326 hectares of Boston rebuilt in a year. Any
  threshold that fires in Kuta Selatan, where the land really is being built on, fires in Boston every year
  for nothing. This node does not send messages a household would ignore, so it sends none: the map and the
  number are on the dashboard for a person to look at. If you ran `earth-engine` with a key you lose a
  message you had; that is the cost of not having one we can defend.
- **A NAS now archives what the earth pack computed.** `tools/nas/pull.py` fetches every `change_*.json` and
  its map. Not the embedding cache: that is 64 MB a year and `planetai run earth fetch` remakes any of it in
  about two and a half minutes from a public bucket. What cannot be remade once a node is gone is the record
  of what that node computed and when, and that is a few hundred kB a pair.
- **`GET /earth` lists every comparison, not just the latest**, and `GET /earth/change.png?pair=2023_2025`
  serves any of their maps. The pair only chooses among the comparisons the node actually computed; the file
  name still never comes from the request.

## v0.33 — 2026-09-06 — the node keeps its own square of the planet

Google publishes the AlphaEarth Foundations Satellite Embedding layers — 64 numbers describing every 10 m
pixel of the land surface, one layer a year since 2017 — as Cloud-Optimized GeoTIFFs in a public bucket under
CC BY 4.0. A new pack downloads the square around your node, keeps it on your disk, and compares two years
here. No account, no key, no cloud project. Two vectors for the same pixel point the same way if nothing
happened there and apart if something did, so the arithmetic is one dot product per pixel.

For a tester, what changes:

- **A new pack, `earth`, and it is off until you ask for it.** Like every code pack it needs
  `PACKS_ALLOW_CODE=1` and `planetai packs install`. Nothing downloads on a poll: the pack fetches only when
  you run `planetai run earth fetch`.
- **What it costs, measured, not estimated.** One year of a 10 km square around the node is **64 MB on your
  disk** and **about 103 MB pulled**, and takes **about two and a half minutes**. All nine years is 576 MB
  kept and 925 MB pulled. The first fetch also reads 9 MB of the dataset's tile index, once. Rehearsed at both
  pilot coordinates: Bali 2023-2025 in 359 s, Santiago 2024-2025 in 215 s.
- **What it does not measure.** Land surface and coastal water as seen from orbit. Not air, not water, not
  emissions. One layer a year, published after the year ends, so it is a record and not a warning. And it says
  *something* changed in a place, never *what* — a new building, a widened road, a cleared slope and a flooded
  field all move the number the same way. Someone who walks there can tell you which.
- **A card in the Region band and `GET /earth`.** The map, the year pair, the share of the square that changed
  and the hectares, with a `Derived` pill: this is a Google model's output that your node did arithmetic on,
  not something your node measured. One Index cell, `Environmental|City`, `partial` for good.
- **`planetai packs install` now adds about 250 MB to the image** when the earth pack is present, for
  `rasterio` and `numpy`. Measured on the Lima node: 458 MB → 710 MB, a nine-minute rebuild. That happens
  whether or not the pack is enabled, because the installer takes every pack's `pip:` list; if you do not want
  it, delete `packs/earth/` before you run it.
- **The app image gains `libexpat1`** (436 kB, every node). Without it `pip install rasterio` succeeds and
  `import rasterio` fails, so the installer would report success and the pack would die on its first run.

For someone working on the code: `make test` now runs `tests/test_earth.py`, which imports numpy without a
guard. A dev machine without numpy fails the suite instead of printing "skipped" — deliberately, because the
whole pack is arithmetic and the de-quantisation is easy to get wrong in a way that still looks plausible.

## v0.32.1 — 2026-09-06 — starting over on the same machine

Found while rehearsing v0.32 from the site's install line on a clean VM whose earlier node had been deleted: Docker
had kept the database volume, the new `.env` got a new password, and the app could not log in to its own database
while `pg_isready`, `/health` (200) and the install's doctor all looked fine. A tester who deletes the folder to
start again does exactly this.

- `install.sh` refuses to start a node whose fresh password cannot match an existing database (the `planetai_db`
  volume, or a `DATA_DIR` with a `PG_VERSION` file) and names the two ways out: put the earlier `.env` back, or
  `docker volume rm planetai_db`.
- `planetai doctor` gains "app logs in to the database" and names the same fix.

## v0.32 — 2026-09-06 — the review's open items, decided and closed

The beta review (v0.31) left a list; Tomas decided the three questions on it and this release does the work. Every
change was rehearsed on the Lima node from the review (`planetai update` v0.31 → v0.32, then each behaviour checked
by hand), then pushed to `main`, which is the beta channel.

For a tester, what changes:

- **Nobody on your WiFi can feed your node readings.** `POST /readings` needs the admin token. On the clean node a
  curl from the LAN had created an indoor sensor at 999 µg/m³ and two act-level alerts reached the phone within a
  minute. Nothing shipped used the endpoint without a token, so nothing you have breaks.
- **Dumps no longer carry your Telegram token.** `backup.sh` leaves the rows of the `settings` table out of every
  dump (the table itself stays, empty). Cost, said plainly: dashboard settings do not survive a restore; the node runs
  on `.env` and `planetai telegram` reconnects a bot that was set from the dashboard. `planetai restore` says so.
- **A pack cannot read your secrets.** Rules and cells from `packs/` run as a read-only database role
  (`planetai_ro`, schema 0.21): every table but `settings`, no writes. `planetai update` creates the role; a database
  that predates it is told once in the log and keeps working.
- **What anyone on the network can read of your settings is smaller.** Without the admin token, `GET /settings`
  masks the household's values (chat ids, sensor hosts, accounts, remote URLs) the way it already masked secrets;
  the node's own settings (alert level, hours, language, layout) stay readable so every screen in the house agrees.
  The dashboard's Set up view sends the token once unlocked and tells you at once if it is wrong.
- **Tokens are compared in constant time**, through one helper, on every gate (`/mcp`, `/settings/raw`, `/backups`,
  `PUT /settings`, `POST /test-alert`, `POST /readings`, `POST /aggregates`).
- **`planetai packs` only lists.** It used to append pack settings to `.env` and rebuild the image (350 MB of Earth
  Engine client) when asked what was loaded. `planetai packs install` is now the step that writes; the listing says
  when it is needed. The docs and the two pack READMEs say `packs install`.
- **Every container's log is capped.** `db`, `agent` and `ipfs` were not (the agent logs every tool call). The update
  recreates the `db` container once to apply the cap; the data volume is untouched.
- **`planetai doctor` checks the free space** on the disk the node lives on and names the fix under 1 GB.
- **Reports and the test alert say how to close the loop honestly**: `/act N` only when the bot runs
  (`planetai agent local`), `planetai act N` otherwise. Replying `/act` to a bot that was not there did nothing.
- **Terminal**: `planetai` lists every command (sensors, cells, geocode, version were missing); `planetai config`
  without a terminal says where `.env` is instead of "a: unbound variable"; `planetai telegram` finds your message
  even when the newest update is the bot being added to a group; `planetai run` shows each script's first docstring
  line, not its first import; the setup wizard stops offering "Sant Martí, Catalunya, ES" three times for Poblenou;
  `.planetai-setup.log` is trimmed past 1 MB; a `|`, `&` or `\` in a value no longer breaks the `.env` writer.
- **Gates** (`make test`): a POST that writes must check a token before it opens the database; no `!=` on a token;
  settings rows out of dumps; the read-only role and its use; a log cap on every service; the packs listing free of
  `docker compose build` and `>> .env`; the act hint through one function.

Decided and **not** in this release: the Raspberry Pi (no arm64 PostGIS image; the site stops promising it),
`POST /actions` stays open on the LAN for the household's button (it rejects unknown alerts and foreign stages since
v0.31), and `main` stays the channel `/install` fetches. Spanish for the alerts, the daily reports, the test alert and
the bot is on branch `es-messages` (PR #1) awaiting a native reader's pass before it ships.

## v0.31 — 2026-09-06 — what the beta rehearsal found

A clean Ubuntu machine, two presets (Santiago, Barcelona), no sensor, no credentials, the one line from the site. What
broke for that stranger is fixed here; what needs a decision is in `docs/reviews/BETA_READINESS_2026-09.md`.

For a tester, what changes:

- **The install finishes with the green screen** (dashboard address, token, `[o]`/`[t]`), not the red box. A new node
  always failed its own doctor (no Telegram yet, no backup yet) and the wizard treated that as a failure.
- **Linux, first run**: after installing Docker the script continues instead of dying on the docker socket with the fix
  buried in the log. `backups/` is created by you, not by Docker as root, so backups can be written.
- **Your node keeps its name** on Linux (every Linux node was called "Ubuntu"), and **"None yet" for the sensor no longer
  corrupts `NODE_KIND`**, which made `planetai update` fail and then **delete `.env`**. `update.sh` no longer executes
  `.env` as shell, and a failed update cannot remove it.
- **The 92-day history arrives** on a zero-hardware node: the first-start bootstrap was being killed by the wizard's own
  restart and then skipped for good.
- **`/export`, `/history`, `/readings` work** (they returned 500 on every call, so no nightly export was ever written);
  a negative limit is a 422, not a 500; an impossible export date is a 422.
- **Santiago and Barcelona nodes get their open-data portal**: the wizard now applies the pilot preset it detects.
- **`planetai doctor` checks that the nightly backup is scheduled** and prints the crontab line if it is not. Node #1
  had none.
- **The dashboard's empty orange bar is gone**; "Set up" no longer wraps on a phone.
- **`/settings/raw` needs the admin token**, not the NAS's read-only backup token. `POST /actions` accepts only
  `acknowledged`/`acted` for an alert that exists. The agent loop no longer logs the values a model passes to
  `settings_set`. The tarball update path verifies the published checksum; `.env.before-update` stays at 600.
- **Gates**: the app-import check in `make lint` had never run (a `$"` in the recipe) and could not fail; it does both
  now. `check_docs` compares every "N tools" in words with the code (seventeen, not fifteen).
- **Docs**: Raspberry Pi is marked *not yet* (no arm64 PostGIS image exists); dumps do contain the `settings` table;
  Telegram `/act` needs `planetai agent local`; nine packs; the database grows about 1 MB a day on node #1.
- New: `docs/BETA_TESTER_GUIDE.md`, `docs/reviews/BETA_READINESS_2026-09.md`, `docs/HANDOFF_beta_review.md`.

Not in this release, by decision: an arm64 database image; `POST /readings` still needs no token; dumps still carry
tokens; the `main` branch is still what `/install` fetches.

## v0.30 — 2026-09-06 — when the node speaks

Node #1 sent 60 messages in two days with no shape: "Good morning" at 13:02 (the daily pulse fired on a **UTC** hour),
heat stress fourteen times in an afternoon, the digest ten times. Replaced with a schedule.

- **Two reports a day**, at local hours (`BRIEF_MORNING` 6, `BRIEF_EVENING` 18): what the night or the day did, the
  peak indoors, what is still waiting for a decision with its `/act` number, which sensors have gone quiet. Written by
  the node from the same data the dashboard shows, so the two cannot disagree; the bot passes it through unchanged.
- **`ALERT_LEVEL`** decides what interrupts between reports: `act` only when something needs doing, `warn` also when
  something changed, `info` everything. Below the line an alert is still recorded, still on the dashboard, and summed
  up in the next report.
- **`QUIET_HOURS`** (22:00–06:00): only act-level alerts go out; the rest wait for the morning.
- All hours are the node's own (`NODE_TZ`), never UTC. `tests/test_briefing.py` asserts exactly the reported bug —
  06:00 UTC is 14:00 in Bali, so a "6" schedule must not fire then — plus the midnight-wrapping quiet window and the
  level floor.
- The old `daily_pulse` and the daily `modelled_air_today` are superseded by the reports; heat stress cools down for
  four hours instead of three.
- All of it editable in the dashboard's **Alerts** page: two hour pickers, what to be interrupted for, quiet hours.
  `GET /briefing?kind=morning|evening` returns the report as it would read right now; the bot has a `daily_report` tool.

## v0.29.1 — 2026-09-06

- **Fixed: `/place/geojson` returned nothing.** The app's cursors return rows as dicts; the endpoint indexed them as
  tuples and swallowed the `KeyError`. The plan never drew although the pack had stored 3,510 map features and 7,219
  satellite footprints. Rows read by name now; the endpoint reports its tables, counts and any error.
- **The yearly building series is held back until it is verified.** `verify` on node #1 reported 90→136 buildings for
  2016→2023 beside 7,219 footprints in the same circle: a 50× mismatch that means `yearly()` misreads the
  fractional-count band. The dashboard shows the growth sentence only when the series is within 3× of the footprint
  count; `verify` gained a sixth step that cross-checks against built area.

## v0.29 — 2026-09-06 — from where you stand, outward

The Now view reorganised by distance, which is also the Index's scale axis: **Here** (the sentence and the thing to do),
**Room** (feels like, each indoor sensor), **Street** (your kit outside, the public sensors, the wind, the day chart),
**Neighbourhood · 1 km** (the plan, what is here, what is unmapped, and a **Fix the map** button that opens the
OpenStreetMap editor at the node), **Region · 11 km and beyond** (the model, the land, the sea, the weather), and
**Act here** (ρ and the alerts). Each band names its distance. Cards sit at their natural height on fixed tracks; the
`1fr` rows that stretched short cards are gone. Measured at three widths: zero stretched cards in any band.

## v0.28.1 — 2026-09-06

- **Fixed: `planetai run place gaps` hung.** The satellite-versus-map comparison cast both geometries to geography, which
  bypasses the spatial index; every footprint was compared with every building, millions of distance calculations, in
  silence. Now in geometry with a degree tolerance (0.00003° ≈ 3 m), which the GiST index serves in seconds; the same
  fix in `/place/geojson`. `gaps` prints each step as it goes and gives up after two minutes instead of never.

## v0.28 — 2026-09-06 — the plan, the grid, and Arrange

- **The kilometre around you, drawn.** A figure-ground plan under the World band: buildings on the map in ink, roads as
  hairlines by class, green as green, each mapped use a coloured dot with its name on hover, the buildings only the
  satellite knows in orange, north up, a 200 m scale, the node pulsing at the centre. Legend toggles per layer. Drawn in
  the browser from `/place/geojson` (PostGIS, simplified); no tiles, works offline. Rendered from the real Bukit: 2,969
  shapes, 37 uses.
- **No more holes in the grid.** Explicit tracks instead of auto-fit: six on a desktop (hero two, four tiles), three on
  a laptop, one on a phone; dense flow; equal row heights; the World cards as a two-by-two beside the alerts.
- **Arrange.** A fifth button: every card gets ← → and ✕, hidden cards come back from a menu, Default resets, Done
  saves in the browser and on the node (`UI_LAYOUT`, when Set up is unlocked) so every screen in the house agrees.
  Exercised headlessly: move swaps, hide hides, restore lists.

## v0.27.1 — 2026-09-06 — the satellite's buildings, and the mapping briefing

- **Google Open Buildings** in the place pack, through the earth-engine pack's credentials: V3 footprints within the
  radius into PostGIS, and the Temporal dataset's yearly building count and mean height 2016–2023 as a series on
  `place-point`. The node can say how many buildings the satellite sees, how many the map has, and how the count grew.
  `/history` serves non-hourly series; the bot's `history` tool reads them; the dashboard card says "the satellite sees
  4,100; the map has 2,904 (71%). Since 2016 …".
- **`planetai run place gaps`**: the mapping briefing — satellite footprints with no building drawn, untyped buildings,
  categories with nothing on the map, named places without hours, unnamed streets — written to `out/place-gaps.md`, with
  how to fix it (StreetComplete, Every Door, iD; never Google). **`planetai run place verify`** checks PostGIS,
  Overpass, Earth Engine and both Open Buildings datasets, naming the step that fails.
- Not testable on the dev machine (no Docker, no Earth Engine key): the quadrant geometry and the OSM path are tested
  here; the PostGIS and Earth Engine paths are what `verify` is for, on the node.

## v0.27 — 2026-09-06 — place

**The node knows what is around it.** A `place` pack fetches everything OpenStreetMap has within a kilometre (buildings,
shops, warungs, schools, clinics, temples, roads, green), stores the geometries in **PostGIS** (the database image is now
`postgis/postgis:16-3.4`, same data directory) and answers a fixed set of questions in SQL: buildings and built share,
commercial share, businesses per km², places by category, road kilometres, green share, the walk to the nearest school,
clinic, market and place of worship. Readings on `place-point` (kind `map`), an `Economic|Community` cell (`partial`), a
monthly message, an "Around you" card in the World band, and the bot's `context` tool. Refreshes monthly; recomputes
from storage between. Tested against node #1's coordinates: 2,904 buildings, 540 road segments, 37 mapped places, no
school on the map. Every label says a zero often means unmapped. Google Maps is not a source: its terms forbid it. Open
Buildings and Overture are the next fetches into the same table.

## v0.26.1 — 2026-09-06 — act here

- **The act trigger is on the hero.** When an act-level alert is unanswered, an orange strip under the room's sentence
  names it, quotes its "what to do" line, and carries the **I did this** button. Every such button is now filled, in the
  page's hue. The alerts card is titled "Act here".
- The site's three node pages share the dashboard's tokens (type, eyebrows, pill buttons, radii, accents) and one nav.
  The headline is back to *Observe here. Decide here. Act here.*, and an "Act here" section shows the loop as it
  happens on a phone, beside ρ.

## v0.26 — 2026-09-06 — the frame, and the alpha notice

Air was the first pack and had become the product in every description. Reframed everywhere a person or an agent
reads what this is: **hyperlocal awareness for climate and local challenges, built on distributed design and
production.** The node connects everything measuring one place, from a particle sensor to a satellite, into one
picture sharp enough to act on at the scale of a house, a street, a city, and passes upward what bioregional and
planetary models cannot see from above. README, START_HERE, the agent's own instructions (`agent.py`, `agent_loop.py`,
`AGENTS.md`), the dashboard footer, the install bootstrap.

**Alpha, said plainly.** A band on every page of planetai.fab.city/node0, a note at the top of README and START_HERE,
an `alpha` pill in the dashboard header with the feedback address in the footer, a line on the screen after install, a
line in the install bootstrap: this is an experiment, installing a node makes you part of it, tell **info@fab.city** what
broke, what helped and what did not.

## v0.25 — 2026-09-05

- **The terminal shows its work.** A spinner with the elapsed time on every long step: the install, the image build,
  pulling a model, starting containers, waiting for the node's first answer. ✓ with the seconds when it finishes, ✗ with
  the last log lines when it does not. `planetai update` opens with the logo. Before this, "Installing" went silent for
  two minutes.
- **After the install, a screen.** The dashboard's address on this machine and from your phone, the settings token, the
  three terminal commands that matter, and one key: [o] opens the dashboard, [t] connects Telegram, Enter shows the
  command list.
- **Fixed: the Wall view.** It never laid out as designed (a `display:block` rule beat its flex layout), and reaching it
  from the button hid the header, leaving no way back. The button keeps the header; only `?kiosk=1` hides it, and then a
  small "exit wall" link remains.

## v0.24.1 — 2026-09-05 — the words, again

`README.md` and `docs/START_HERE.md` rewritten as product copy: what you get first (alerts you can act on, a dashboard
that reads like a sentence, a bot you can talk to, a house that learns its rhythm, your data kept, nothing to buy), then
install, the first ten minutes, everyday use, what it will not do, when it breaks. Instructions checked against the
CLI as it is today: the four dashboard views, `planetai agent local`, the Model page, `/act` in Telegram. The rest of
the docs swept for the phrases that read like a machine wrote them.

## v0.24 — 2026-09-05 — the dashboard, redesigned

The design is Tomas's PLANETAI_Node_v5 on the Fab City design system: a warm dark field, Figtree and Funnel Sans, the
brand hues as accents, grain and two slow glows, hexagon marks. Four views: **Now**, **Network**, **Set up**, **Wall**.
Every sentence the designer hand-wrote for one evening's data is now computed from the API: the room's number as a
sentence with its clauses judged against the street, the model and the WHO line; the verb from the last three hours;
a story under every sensor generated from its readings; the day chart annotated from the data ("someone cooked" when
the room beat the street); the sea, the land, the weather and the gap in prose; the Network view drawing flows only
along links that exist. Settings keep their logic (token gate, groups, secrets, packs, the Model page) in the new
markup. Verified headlessly at 1280 and 390: no overflow, no empty region, no `undefined`, fonts loaded.

## v0.23.3 — 2026-09-05

- **The terminal and the dashboard now write Telegram to the same place.** A value saved in the dashboard overrides
  `.env` by design, so `planetai telegram` (which wrote `.env` only) could change the file and change nothing. It now
  writes the dashboard's store too, through the same `/settings` call, with `planetai-cli` in the audit trail. The
  dashboard labels such values "set here · overrides .env" so a shadowed file edit is visible. This is also why a token
  changed in the dashboard did not reach the bot until the loop started reading settings (v0.23.1).

## v0.23.2 — 2026-09-05

- **The bot can now see the sea, the weather, the satellites and the land.** Asked for the swell, it said it had no such
  sensor: true, because no tool reached `/observations`. New tool `context` returns those, grouped and labelled in plain
  words (what the number means, its unit, when it was read); `readings` returns one sensor's hourly history; `sensors` now
  carries every metric a kit reports, not three. Fifteen tools. Tested on node #1's live data: "🌊 The swell is about 1.7 m
  right now, with a period around 11 s and coming from the southwest…"

## v0.23.1 — 2026-09-05 — a leak, closed

- **The agent loop logged a Telegram exception's text, which contains the bot token in its URL.** The token of node #1
  was exposed and has been revoked. Telegram calls now raise a `TelegramError` carrying a status code and advice
  (401: run `planetai telegram`; 409: something else is polling this bot), never the response or URL. `make lint` refuses
  any log call that interpolates a Telegram exception. The app's own `notify()` already followed this rule; the loop did not.
- The loop waits for the node to answer before reading settings, so it does not fall back to a stale `.env` token while
  the app is still starting.

## v0.23 — 2026-09-05 — how the node talks

**Every message rewritten**, both languages, to one shape: an emoji headline (the line the LoRa mesh carries), what is
happening, what it means for the people there, what to do. No means, peaks, correlations, percentages or counts; one
number where it drives the advice. The weekly `agreement` note says the house held back most of the street's air
instead of quoting r; the `digest` reads 🏠 🌳 🛰️ in three lines; the test alert explains itself. "Ask me for the numbers
if you want them" replaces the numbers. The bot's model speaks the same way: explain, emoji, plain text (Telegram shows
Markdown raw, so it is scrubbed too), under 100 words unless asked; the morning brief is a note to the household, not a
status report.

## v0.22.3 — 2026-09-05 — what v0.17 and v0.21–22 claimed, actually shipped

Two edit blocks failed silently on a mismatched anchor and the tool showed no error, so v0.17 shipped without the
compose changes (`DATA_DIR`, the `ipfs` service; `planetai ipfs` would have failed) and v0.21–22 shipped only
`agent_loop.py`: no `agent` service, no `AGENT_*` settings, no Model tab, no `planetai agent local`, no `.env` keys.
Lint passed because nothing inconsistent was present. All of it is in now, verified by count, and:

- **The model ladder is a runtime setting.** `/settings/raw` (admin token) serves unmasked runtime settings to the
  node's own processes; the loop re-reads its ladder from there every minute. The dashboard's **Model** page changes
  which model answers the bot, live, no restart.
- `tests/test_shipped.py` asserts every artifact each version promised, in `make test`.

## v0.22.2 — 2026-09-05

- **Fixed: the image failed to build on the node.** `uvicorn==0.30.*` and `fastapi==0.115.*` were pinned before `mcp` existed; `mcp` needs uvicorn ≥ 0.31.1. Both loosened to `>=x,<1`; the set resolves on Python 3.12 to FastAPI 0.141 and mcp 2.1.1, and the app imports and the MCP round trip pass under exactly that set. `tools/check_requirements.sh` now resolves `requirements.txt` under 3.12 in `make lint`, so a bad pin fails on the dev machine, not in `planetai update`.

## v0.22.1 — 2026-09-05

- `tools/remote-model.sh gptoss | qwen122b`: serve a big local model from a laptop as the node's `remote` rung. llama.cpp with `--jinja` (tool calls), an API key (the model is on the tailnet), the `.env` lines printed for the node. gpt-oss-120b tested through the node's tools: two-second answers, correct tool choice on every question, failures read off `health_check` and ordered.

## v0.22 — 2026-09-05 — a ladder of models

The Telegram bot uses the strongest model it can reach and falls back down: **online** (Anthropic or OpenAI, with a key;
the only rung that leaves your network), **remote** (a bigger local model on your tailnet: a laptop's Ollama, an exo
cluster; no key), **local** (Ollama on the node, always). `AGENT_PREFER=private` never uses online. A failing rung is
skipped for five minutes. `/model` in Telegram shows the ladder and pins one. Every write records `<agent>/<rung>`.
One protocol, OpenAI-compatible chat with tools, which all three serve. Tested: `qwen3:8b` on the remote rung read
three real failures off `health_check` and ordered them; with that rung broken, the loop fell to `qwen3:4b` in seconds.
This is where an AI credential belongs in `.env`, now with code that uses it: `AGENT_ONLINE_KEY`, a secret in the GUI's
Model page. `claude-sonnet-4-6` is the default online model; untested here, no key on this machine.

## v0.21 — 2026-09-05 — a local model runs the node

`planetai agent local`: Ollama on the node's own machine, `qwen3:4b` (or `qwen3:8b` on 16 GB), and `app/agent_loop.py`
in the `agent` compose profile. The model uses the node's thirteen MCP tools, answers the household on the Telegram bot
the node already has, records `/act 23 closed the windows` deterministically without the model, and sends a brief at
`BRIEF_HOUR`. No cloud, no key, no model anywhere but here. Its actions appear in the audit trail as `local-model`.
Tested on this laptop's Ollama against the node's tools: three questions, three correct tool choices, plain answers in
4–11 s. The final answer is requested as constrained JSON, because a 4B model narrates its reasoning as prose even with
thinking off and no instruction fixes that; a schema does. Gemma 3 does not do tool calls in Ollama; 1.7B is too weak
for multi-step tool use.

## v0.20 — 2026-09-05 — agents

**The node as tools for an AI agent.** `app/agent.py`: an MCP server mounted at `/mcp`, behind the admin token, with
thirteen tools over the existing API: status, health_check (each failure names its fix), sensors, alerts, act,
settings_get/set, packs, cells, series, export_day, run_pack_script, maintenance. A remote Claude reaches it over
Tailscale; a local model on the mini reaches it on localhost. Writes record the agent's name (`X-Agent`) in the
actions table; settings changes are audited there too (new stage `settings`). Host operations (update, backup,
restart) are returned as the exact command, since the container has no Docker or git.

- `--json` on `status`, `doctor`, `sensors`, `cells`. Doctor as JSON keeps the fix text and the exit code.
- `planetai setup --answers node.json`: install without a terminal. `install.sh` gained `--sc-user`, `--kind`, `--tz`.
- `planetai agent`: the endpoint, the token, a Claude Desktop/Code config snippet.
- `AGENTS.md` at the root (with `CLAUDE.md` pointing to it): the operating manual for an agent, with the invariants.
- No model on the node, no AI credentials in `.env`: the agent runs where the person already has one and holds the
  admin token. `UPSTREAM_MODEL_URL` returns the day a rule needs a model, with the code that uses it.
- Schema 0.20. `mcp>=2.0` in the image.

## v0.19 — 2026-09-05 — documentation cut by two thirds

29 documents, 28,900 words to 9,900. Plain sentences, no padding, no hedging. Same facts.

- Three Meshtastic guides became one (`MESHTASTIC.md`: radios and jobs, the USB way, the phone app, sensors on radios,
  what went wrong). `START_HERE.md` from 3,600 words to 780. `README.md` from 1,900 to 470.
- `STORAGE.md` and `MAC_MINI.md` now describe the actual setup: the mini keeps the database, TX-NAS-BALI pulls the dumps
  hourly with the read-only token, since 5 September 2026. `tools/nas/README.md` is the two-file recipe.
- The docs gate exempts the changelog from file-existence checks; it is a record and files move.

## v0.18.2 — 2026-09-05

- **Fixed: `planetai storage` stopped halfway** — before the exports, IPFS and the NAS token — on a node with no exports yet. `nex="$(ls exports/x/*.json | wc -l)"`: `ls` fails, `pipefail` fails the assignment, `set -e` ends the function silently. Counts use a `nullglob` array now. Verified by running the real function against a folder with no exports.

## v0.18.1 — 2026-09-05

- **Fixed: the backup check rejected good dumps.** `gunzip | grep -q` under `pipefail`: `grep -q` exits on the first match, `gunzip` gets a broken pipe, the pipeline reports failure, and a valid dump read as "no readings table" — which made `planetai update` refuse to run, correctly, for the wrong reason. Counting matches instead lets the pipeline finish. The same race was in the **mount check**, where it could have refused a real NAS mount, and in five other places across `update.sh`, `install.sh` and the CLI; all now capture the producer's output first and grep the string. `make lint` refuses `| grep -q` under `pipefail` from here on.

## v0.18 — 2026-09-05

**A NAS that pulls.** The node serves `/backups` and `/backups/<file>` behind a new read-only `BACKUP_TOKEN` (minted
by install and update, shown by `planetai storage`), and `/exports` openly. `tools/nas/pull.py` — 60 lines, stdlib,
one 128 MB container — runs on the NAS, asks hourly, fetches what it lacks, and opens every dump to confirm it is a
database before keeping it; nothing is ever deleted there. Pull rather than push: the schedule and the copies live on
the machine meant to survive, the node never holds NAS credentials or a mount, and no folder can silently turn out
to be local. Installed on TX-NAS-BALI for node #1.

## v0.17.1 — 2026-09-05

- **Fixed:** two `.DS_Store` files were committed with `git add -A`; the node had its own untracked copies and `git pull` refused to overwrite them, so `planetai update` failed. Removed from the repo, gitignored, blocked by the pre-commit hook and by `make lint`; `update.sh` sweeps Finder litter before pulling.
- **Fixed:** the schema version was read with `max(version)`, a text comparison, so `'0.4'` beat `'0.14'` and every update since v0.14 reported "schema 0.4 → 0.4" while the database was actually at 0.14. Now the latest applied version, in `update.sh` and `/health`.

## v0.17 — 2026-09-05 — storage

**Where the data lives, where copies go, and what the node gives away.** `docs/STORAGE.md`, `planetai storage`.

- **The live database stays on a local disk**, and the doc says why: Postgres over SMB/NFS corrupts on a power cut. `DATA_DIR` moves it to another internal disk or partition; a NAS is what backups are for.
- **`backup.sh` rewritten**: refuses if `BACKUP_DIR` is on an unmounted `/Volumes`, `/mnt` or `/media` path instead of creating a local folder with the drive's name (the same trap that bit Mosquitto); verifies the dump is a valid gzip containing a readings table before keeping it; `BACKUP_KEEP` days; `LAST_OK`. **Fixed a silent killer found while testing**: `env_get` on a key missing from `.env` made `grep` fail and `set -e` end the script with no output — the first new key would have stopped every nightly backup. The same helper pattern hardened in `update.sh` and the CLI.
- **`BACKUP_REMOTE`**: an rclone destination — S3, B2, R2, Drive, SFTP, WebDAV, Nextcloud — copied after each backup. One binary, no code of ours.
- **`/export?day=`**: one day as open data — hourly means/min/max per sensor and metric, cells, alerts, ρ. Your sensors named by role, not device id; node coordinates to three decimals; no raw, no secrets; CC BY 4.0 stated in the file. Written nightly to `exports/<node>/`. This is data in, data out, made literal.
- **IPFS** as the commons layer: an `ipfs` compose profile (Kubo), `planetai ipfs`, each export added and its CID recorded in `CIDS.txt`. Only exports go — everything on IPFS is public and nothing persists unpinned, which is exactly the right shape for aggregates and exactly the wrong one for backups.
- `planetai storage` (one screen: database size, backup destination and mount state, last run, remote, exports, IPFS; `set backups|remote|keep`), `planetai backup`, `planetai restore <dump>` (safety backup first, typed confirmation).
- `planetai doctor` checks the backup destination is mounted and a backup ran in the last two days.

## v0.16.1 — 2026-09-05 — after the first look

Seven things from seeing it rendered, in the order they mattered.

- **`MG/M³` was a bug**: `text-transform: uppercase` turned µ into M and micrograms into milligrams. The unit line is no longer transformed.
- **The rotated inscriptions are gone.** Outside and model readings are horizontal, right-anchored at the exposed vertices, at 36 and 24 px instead of 28 and 22. The geometry only admits that with a deeper offset (48/96 instead of 36/72), which also gives the stack more depth. Placement proven by pushing the true glyph corners through the SVG transform and testing point-in-polygon against all three hexagons, at three widths.
- **The phone cropped the world hexagon.** The overflow check measured element boxes, not SVG content spilling past them; the SVG now clips to its box and its viewBox carries a margin.
- **One threshold.** Good/moderate at 12 (US) contradicted the WHO 15 line drawn on the strip beneath it. WHO everywhere now: 15 and 35.
- An empty sensor tile said "–". It now says what it is waiting for.
- The world hexagon's mesh read as compression noise in dark mode; hairline, lighter, crisp-edged.
- The header shows the place, from `/health`.

## v0.16 — 2026-09-05

**The dashboard is a zoom: room, street, world.** Three hexagons of the same size offset behind one another: the
room fills and takes its colour; the outside reading runs along the street hexagon's exposed edge at 30°; the world
hexagon carries the isometric mesh inside it and the satellite model along its edge. Then three bands by distance —
each indoor sensor as a tile with a 24-hour trace (`/sparks`), your outdoor sensors and the nearest public ones with
their distance and the wind as an arrow, and the world: the sea with its swell arrow and a sentence about what it
means, the model and its gap to your street, the land as a built/green bar, the weather. The ocean, the land and the
weather were in a table on a second page called "slow sources"; now they have a place.

**Your account's outdoor kits are yours**, whatever their distance. `SC_LOCAL_KM` is gone; `SC_EXCLUDE` leaves out a
kit that belongs to another site. Public references are a separate class and are labelled with how far away they are.

Layout proven headlessly at 1280, 1024 (kiosk) and 390 px: fonts load, the inside texts sit within the room polygon,
the rotated outside and world readings sit inside their own hexagon's band and intrude on nothing (true rotated-glyph
corners, point-in-polygon), no overflow, 24 bars, every band populated. pyflakes joins `make lint`.

## v0.15.1 — 2026-09-05

Three things node #1 showed on a Saturday evening.

- **"Outside" now means your own outdoor sensors first**, then the three *nearest* public references, then the model — the same order in the air-quality rules, the insight digest and the dashboard, pinned by a test. Before, every station within 15 km was averaged equally, so an Uluwatu AirGradient reading 3 sat alongside the street's 15 and the dashboard said 6. The node's coordinates are handed to SQL as `planetai.lat`/`planetai.lon` so rules can rank by distance.
- **Account kits within 2 km are yours** (`SC_LOCAL_KM` default 0.5 → 2): a neighbourhood, not a doorstep. The outdoor kit 1.1 km up the road was being classed as someone else's. `BAD_RADIUS_KM` default 15 → 8.
- **Two spike rules**: `indoor_spike` and `outdoor_spike` fire when PM2.5 is 2.5× today's mean and above 12 (indoor) or 15 (outdoor) — *something changed*, before anything is unhealthy. Inside tripled from 5 to 15 at 18:00Z and only the inside-worse-than-outside rule spoke; a household wants to hear the jump.
- Mesh confirmed working: the gateway carries a BME680 and reports temperature, humidity, pressure, gas and IAQ every 15 minutes. The "silent 90 minutes" alert was the app outage.

## v0.15 — 2026-09-05

**The dashboard, designed.** The grid of six tiles is gone. In its place the Fab City module — a hexagon with its
outline offset behind — made literal: inside fills the hexagon and colours it, outside sits where the outline peeks
out, the model is a faint dashed third hexagon. One verdict sentence in Funnel Sans, one line of why, three quiet
stats that each end in a sentence. A real 24-hour strip from a new `/series` endpoint (hourly indoor bars, outdoor
line, model dashed, the WHO guideline drawn in). Alerts as plain sentences with a hexagon dot for level. Cells as a
honeycomb with the numbers inside. Set up restyled on the system: 8 px controls, switches, blue focus ring, the
token gate with a hexagon behind it. One motion moment on load; reduced-motion respected. Dark mode follows the OS.
Verified headlessly at 1280, 1024 (kiosk) and 390 px: fonts load, every hexagon text stays inside the hexagon,
nothing overflows, 24 bars render.

## v0.14.2 — 2026-09-05

- **Fixed: the app did not start after v0.14.** Turning `PARENT` into a settings-backed function left a module-level `PARENT.startswith(...)` check, which raised `AttributeError` at import and stopped uvicorn before it listened. Passed syntax checks and pyflakes because the name was defined. `TG()` was likewise called but never defined (the definition edit did not match), which would have broken every notification.
- **Fixed: the admin token was never generated.** `.env.example`'s line carried an inline comment, the merge copied it verbatim, and the "is there a value" check saw the comment as a value. The check now reads the value with comments stripped, and the comment moved above the line — the rule set yesterday after the same class of bug.
- **New gate:** import the app with its real dependencies, as uvicorn does, and count routes. In CI always; in `make lint` when the deps are installed.

## v0.14.1 — 2026-09-05

- **Fixed a latent hazard in every update since v0.4:** `update.sh` pulls new code while bash is still reading the file it is executing. Bash reads scripts incrementally, so after the pull it continues from a byte offset in a *different* file — steps skipped, garbage executed, whichever line happens to sit at that offset. Reproduced in a controlled test: the old script ran the new file's final step instead of its own. `update.sh` now copies itself to a temp file on entry and runs from the copy, which the pull cannot touch. This is the likely cause of the v0.14 update leaving the schema at 0.4 and the admin token empty.
- Token generation falls back to `/dev/urandom` if `openssl` is absent, and both `update.sh` and `planetai ui` refuse to continue with an empty token rather than printing a blank.

## v0.14 — 2026-09-05

**A dashboard.** One HTML file the node serves at `/`, on the Fab City design system, no build step.

- **Display**: six tiles that end in a sentence — inside and outside PM2.5, apparent temperature, the CAMS model with the gap to your street, ρ, and a 24-hour trend — plus the alert feed with an **I acted** button on unanswered act-level alerts (that button is how ρ is measured), the node's Index cells as a honeycomb, and vitals. `?kiosk=1` for a small display: big numbers only, 30-second refresh.
- **Sensors**: everything the node knows, yours first, and the slow sources.
- **Set up**, behind an admin token: sources, alerts and Telegram, packs (tick to enable; code packs behind one explicit switch), integrations, keys, the node's place in the tree, bootstrap read-only. A test-alert button. Live within ~20 s, no restart.
- **The settings layer that makes it possible**: a `settings` table overlays `.env`; runtime keys are read through `settings.get()` at use time, so the GUI's changes take effect on the next poll. Bootstrap keys stay in `.env` by design. `GET /settings` (secrets masked), `PUT /settings` (token), `POST /test-alert` (token). `/alerts` now returns each alert's id and whether it was acted on.
- `ADMIN_TOKEN` minted by the installer and added by `update.sh` to older nodes; `planetai ui` shows it and the URLs.
- `tools/check_ui.py`: the script parses, every element id the script touches exists, every API path it calls exists, every field it reads is a real column. Verified by breaking an id and watching it fail.
- Schema 0.14.

## v0.13 — 2026-09-05

**A node can be installed without access to this repository**, so beta testers need no GitHub account.

- `tools/bundle.sh` builds the tarball the website serves: everything git tracks minus CI, dev tooling and tests, plus a `VERSION` file. It refuses to emit a bundle containing `.git` or `.env`, and publishes a SHA-256 alongside.
- `install` now has two paths. With repository access it clones as before; without, it downloads the tarball from `planetai.fab.city/node0`, verifies the checksum, and unpacks it while keeping the operator's `.env`, backups and packs.
- `update.sh` does the same: a node with a `.git` pulls, a node with a `VERSION` re-fetches the published tarball.
- The public setup guide lives at `planetai.fab.city/node0/setup/` — what you need, the four questions, connecting alerts, the five everyday commands, and a troubleshooting table where every row is something that actually happened to a real node.

## v0.12.1 — 2026-09-05 — documentation audit

- **`tools/check_docs.py`**: checks every claim in the docs that a machine can check — files, `planetai` commands, environment variables, relative links, HTTP endpoints, pack names, size claims, and whether README's index matches `docs/`. Runs in `make lint` and CI. Verified by removing an entry from the index and watching it fail.
- **Corrected**: "two containers, four adapters, five rules" (now two containers by default, nine adapters, two domain-blind core rules plus packs); "about 700 lines" (about 1,400); ARCHITECTURE's Stage 0 description.
- **README's docs index** was missing `DEVELOPING.md` and had become a flat list of fifteen names; it is now grouped by what you are trying to do.
- **SPEC §6**: the fired triggers are struck through rather than deleted, `UPSTREAM_*` records why the settings were removed while the contract stands, and the notifier row notes that four channels now exist and the trigger was always an auth lifecycle, not a channel count.
- **`docs/DEVELOPING.md`** gained a table of what `make lint` checks and which real failure caused each gate, plus the two habits: test the artifact rather than a transcription of it, and break something on purpose before trusting a new gate.

## v0.12 — 2026-09-05

**Packs can make things you look at, not only numbers.**

- `out/` is mounted read-write into the app container as `/app/out` — the one writable path a pack has, for images, charts and briefs. Gitignored.
- **`planetai run <pack> <script> [args]`** runs a script a pack ships, inside the container where its dependencies are. With no arguments it lists what is available.
- **`packs/earth-engine/timelapse.py`**: four satellite images of the same place, five years apart, plus a side-by-side HTML page. Each frame is the annual median of clear pixels, so clouds are gone and what you see is the year. Landsat by default (the only archive reaching back far enough with one instrument family — 2010, 2015, 2020, 2025 out of the box); Sentinel-2 for 2016 onward at three times the resolution. `--years`, `--n`, `--gap`, `--km`, `--px`, `--lat/--lon`, `--dry-run`.
- Fixed while building it: `COPERNICUS/DEM/GLO30` in the verifier was an ImageCollection used as an Image, and deprecated. Replaced with SRTM, and a step 6 now probes the four datasets the pack actually reads.

## v0.11.5 — 2026-09-05

- **Fixed:** `planetai packs` treated a pack's `env:` comment lines as settings, so it appended four bare comments to `.env` and reported them as four added settings (the real settings were already present and correctly skipped). A comment now travels only with the setting it explains, and only when that setting is actually added.
- Verified by running the real function from `bin/planetai` against a temporary `.env`, not a retyped copy — retyping it the first time introduced an escaping bug that made the test lie.

## v0.11.4 — 2026-09-05

- **Fixed:** pack `env:` declarations padded the value column for alignment, so a value pasted after the padding produced `VAR=   value`. The shell reads that as "run `value` with VAR empty", and `update.sh` sources `.env` — so filling in the Earth Engine service account made `planetai update` try to execute an email address. Declarations now put the explanation on its own comment line and leave nothing after `=`.
- **Added:** `update.sh` checks `.env` for a space after `=` before sourcing it and names the offending line; `planetai doctor` checks the same thing. A file this central should not fail with "command not found".

## v0.11.3 — 2026-09-05

- **Fixed:** a pack's settings had no route into `.env`. The earth-engine pack documented `EE_PROJECT`, `EE_SERVICE_ACCOUNT` and `EE_KEY_FILE` in its README only, so they appeared in no config file and could not be found. Packs now declare `env:` in `pack.yaml` alongside `pip:`, and `planetai packs` appends the missing ones under a dated marker without overwriting anything. Also added to `.env.example` so a plain `planetai update` picks them up.
- `packs/earth-engine/verify.py`: checks library, settings, key file, credentials and a real query, and names the step that failed.

## v0.11.2 — 2026-09-05

- **Fixed:** `planetai packs` printed a `SyntaxError` instead of the pack list. The `json` helper wrapped snippets after a semicolon, where a `for` loop is a syntax error. The snippet now goes on its own line, so any statement works.
- **Fixed the gate that missed it:** `check_cli_python.py` compiled each snippet standalone, where `for p in d: print(...)` is perfectly valid. It now compiles them as the helper actually wraps them. Verified by injecting a broken snippet and watching the gate fail.

## v0.11.1 — 2026-09-05

- **Fixed:** `planetai packs` read `pack.yaml` with PyYAML, which a node's Apple Python does not have, so the command crashed on node #1. It now parses the one line it needs with awk. Nothing else in the CLI needed a third-party library and nothing should: `tools/check_cli_python.py` now fails the build if a CLI snippet imports one.
- **Fixed:** when the API did not answer, the command printed "(node not answering)" and carried on. It now says so as a warning, points at `planetai doctor`, and lists what is on disk while making clear that is not what is running.

## v0.11 — 2026-09-05

**Ten pack ideas, three built.** `docs/PACK_IDEAS.md` lists ten packs someone could write this month, each with its
Index cell, what it needs, its size and a natural author. Three ship as prototypes:

- **`heat`** (data): Steadman apparent temperature in SQL from any local temp + humidity; heat-stress and danger
  alerts; nights that never cool below 28 °C; a `Social|Community` cell of heat-exposure hours — one honest number for
  the Index's emptiest column.
- **`coast`** (code, key-free): waves, swell and sea temperature from Open-Meteo Marine at the nearest ocean cell,
  refusing to run if that cell is more than 30 km away. Tested live: 1.7 m at 11.8 s off the Bukit, sea 27.4 °C.
- **`earth-engine`** (code, needs a Google Earth Engine project): tree, built, crop and water fractions from Dynamic
  World, Sentinel-2 NDVI, VIIRS night lights, and a land-change score from consecutive AlphaEarth annual embeddings,
  all computed server-side over a 1 km buffer. The worked example of a pack with a dependency and a credential: it
  logs once and idles until configured, and cannot take the node down. Logic tested with a fake `ee`; not yet run
  against a live account.

**Mechanics that came with them**
- `pip:` in `pack.yaml` + `planetai packs`: code-pack Python dependencies are installed into the image once, on
  demand, never at runtime.
- `long_cooldown_ok: true` lets a rule declare a deliberately long cooldown to the rule checker, which otherwise
  flags anything over a fortnight (the test-alert bug).
- `tests/test_packs.py` covers both code packs offline.

## v0.10.1 — 2026-09-05

- **Fixed:** a Smart Citizen kit the node polls directly also arrived through Bali Air Dispatch as `bad-sc-<kit>`, so it was counted twice in the ambient average — and BAD's indoor/outdoor metadata disagreed with Smart Citizen's own on two of your kits. Kits read directly are now skipped from BAD. Seen on node #1 once account discovery was on.
- **Fixed:** `update.sh` pulled a named branch, which skips tags, so the version stamp stuck at `v0.7-N`. Tags are fetched first now.

## v0.10 — 2026-09-05

**The node reads your whole account, tells you more, and hands automations to Home Assistant.**

- **Smart Citizen account discovery** (`SC_USER`): every kit that has published recently, indoor from the API's `exposure` field, local if within `SC_LOCAL_KM` of the node, otherwise a reference station you own. Node #1's account turned out to hold six live kits; it was reading one.
- **`insight` pack**: `digest` every three hours (inside / outside / model / 24h mean / peak / trend); `agreement` daily (Pearson r between indoor, outdoor and CAMS, how much the house filters, the model's bias); `rhythm` daily (the street's worst and cleanest hours, when to open the windows). Pure SQL; Postgres has `corr()`.
- **Home Assistant** via MQTT discovery: local sensors and the latest alert appear as HA entities with no configuration on the HA side. `planetai homeassistant` sets it up. HA does automations; the node never addresses a device.
- **`NODE_KIND`** (`home | business | community | district`): a fourth setup question that sets defaults. Not an Index scale — a house is a Community-scale observation.
- **`docs/USE_CASES.md`**: three things node #1 can say today, with the real numbers from seven days of data: indoor tracks the street at r = 0.55 and the house filters ~30%; the CAMS model tracks the street at r = 0.51 and reads high; it tracks indoor air at r = −0.18. Also: one kit in the account has a dead PM sensor.

## v0.9 — 2026-09-05 — audit

Six defects found by auditing rather than by hitting them in the field. Each has a gate now.

**Wrong, silently**
- `POST /aggregates` stored a child's hourly means as `kind='sensor'`, so they entered the `stats` view and could be averaged into "nearby public sensors" as ambient reference. Children are `kind='child'` and belong in `observations`. Found before the district node made it matter.
- `NODE_TZ` was written by setup and **read by nothing**, while `.env` claimed daily buckets used it. Postgres defaulted to UTC, so `current_setting('TimeZone')` put local midnight and local hours eight hours out in Bali: the WHO exceedance-day cell split days at 08:00 WITA, and the cooking-hours rule fired at dawn. The database session timezone now comes from `NODE_TZ`.
- `packs/air-quality` declared its 24h-mean cell `partial` with a comment saying the core would promote it. The core only ever demotes. The cell could never be `live` while `COVERAGE.md` and `START_HERE.md` both promised it would be. It now declares `live` and is demoted until 12 hourly buckets exist.
- Any loop's exception overwrote `state["last_error"]`, which `poll_once` clears when its sources succeed — a permanently broken rules thread looked healthy. Each loop keeps its own key.
- The poll loop was an anonymous lambda, so its thread and every error it logged were named `<lambda>`.
- MQTT ingest counted every reading as new, including duplicates dropped by `ON CONFLICT`.

**Closed while it is free**
- `POST /aggregates` accepted anything that could reach the port. It now requires `Authorization: Bearer <AGGREGATE_TOKEN>` and refuses outright when no token is set. No child exists yet, so nothing breaks.

**Removed**
- `UPSTREAM_MODEL_URL` and `UPSTREAM_COMPUTE_URL` from `.env.example`: no code reads them. The contract stays described in `ARCHITECTURE.md`; the setting comes back with the code that uses it.

**New gates**
- `tools/check_rules.py`: parses `init.sql` for every table and view, then checks each rule and cell — unknown columns, message placeholders the SQL never returns, cells with no `value` column, and cooldowns over a fortnight. The last of those is exactly the bug that made `test-alert` report a dead node for 69 days. Verified against four deliberately broken rules.
- `tests/test_logic.py`: cell provenance (demote a `live` claim below `min_buckets`, never promote `partial`, show the shortfall in the note) and per-loop error isolation.
- Both run in `make lint` / `make test` and in CI.

## v0.8.2 — 2026-09-05

**First real packet from the gateway reached node #1**, and the day-long silence had one cause: the fleet channel was
a secondary, and radios send telemetry on the primary. `mesh-provision.sh` now makes the fleet channel the primary.
Also documented: enabling the XIAO's serial console and debug log to read the radio's own output over USB; the
Mosquitto config that was missing for a day; connection logging on the broker.

## v0.8.1 — 2026-09-04

**First radios provisioned; the failures documented.**

- `tools/mesh-provision.sh`: one command per radio over USB (region, preset, names, role, telemetry and position intervals, fleet channel; first radio creates the channel and saves its URL, the rest import it). No pairing, no PIN.
- `docs/MESHTASTIC_FLEET.md`: the laptop procedure, naming and roles, the channel file as a key, the CLI's enum values, and field notes: region `0` explained last week's silence; UF2 drag fails on macOS 26 (FSKit) regardless of bootloader version and serial DFU is the working path; the flasher offered a non-release 2.8.1, the fleet is on stable 2.7.26; Seeed's verified Grove list excludes the BME680.
- `docs/MESHTASTIC_APP.md`: Part 0 fast path; the -36 paragraph corrected (the earlier "update the bootloader" explanation was wrong for this case); a sensor on the gateway; two symptom rows.
- First Tracker L1 flashed to 2.7.26 over serial DFU and provisioned as `SENSOR` on channel `planetai`, `SG_923`.

## v0.8 — 2026-09-04

**Meshtastic and Reticulum ready.** Both behind compose profiles, off by default; node #1 stays two containers until
you turn one on.

- **`planetai meshtastic`**: creates broker credentials, starts Mosquitto (`mqtt` profile, password required, LAN-reachable on 1883), restarts the node with its MQTT thread on, prints the exact gateway settings (region for your city, address, credentials, JSON output on, uplink/downlink on), waits for the first packet, lists the sensors it saw.
- **Meshtastic adapter** (`sources.meshtastic_message`): pure function, tested offline against 2.x payload shapes. `telemetry` → readings (environment + air quality + battery/LoRa health), `position` → sensor coordinates from GPS, `nodeinfo` → name. Protobuf topics ignored; unknown fields logged once. Pressure converted hPa → kPa to match the rest of the node.
- **Alerts over the mesh**: `MESH_ALERTS=1` + the gateway's node number; act-level alerts go out on the downlink topic, first line only, capped at ~200 bytes.
- **DIY pods**: the same broker takes `planetai/sensors/<id>/<metric>` from anything on the WiFi.
- **`planetai reticulum`**: a bridge container with an LXMF address. Inbox: `act <id> [note]` from Sideband records the action (closing the loop with no internet). Outbox: act-level alerts to `RETICULUM_ALERT_DESTINATIONS`. TCP server on 4242 now; RNode LoRa is a commented block in `config/reticulum/config` plus a device mapping (Linux).
- `/health` gains `mesh` (root topic, gateway, packet count) when MQTT is on; doctor checks the broker, packets and bridge when their profiles are on.
- Found by the new tests: the root topic parse included the protocol version segment, which would have doubled `/2/` in every downlink. Fixed before it shipped.
- `docs/NETWORKING.md` and `docs/sensors.md` updated; SPEC §6 marks the MQTT trigger fired and splits Reticulum into shipped (bridge) and parked (node-to-node transport).

## v0.7 — 2026-09-03

- **`planetai mesh`**: joins the node to a Tailscale tailnet with its own name and Tailscale SSH on, so `ssh bayu-2` and `planetai update` work from anywhere with no ports opened and no keys managed. Uses the Homebrew daemon on macOS so a headless mini stays reachable with nobody logged in. `TS_AUTHKEY` for unattended joins. `MESH_NAME` recorded in `.env`.
- **`docs/NETWORKING.md`**: the three-layer evaluation. Tailscale for reachability (shipped, Headscale as the recorded exit). Meshtastic for sensors and alert delivery off-grid (next; it is the missing pipe in the FAB26 six-month program, and the gateway must point at the node's own broker, not the public default). Reticulum parked with a precise trigger.
- SPEC §6: the Tailscale and MQTT triggers are marked fired; Reticulum added with its trigger.

## v0.6 — 2026-09-03

**One command to a running node.** Applied the Omarchy install pattern: a URL that does everything, a form that
asks only what it cannot detect, phased steps logged to a file, a plain error screen, and one CLI so operators never
touch a Makefile, a flag list or a YAML file.

- `install`: `curl -fsSL planetai.fab.city/install | bash`. Gets git if missing, clones or updates `~/planetai`, hands off to `planetai setup`. Re-runnable.
- `bin/planetai setup`: three questions. Name. **A place name** (Open-Meteo geocoding, with OpenStreetMap as fallback for neighbourhoods and sub-districts) → coordinates, time zone, country, and whether the location falls inside one of the four pilot bounding boxes, which sets the city key and turns the Bali archive on or off. Sensor, or none. Then a summary, a confirm, and the install with a log.
- `planetai telegram`: validates the token with `getMe`, waits for your message, reads the chat id from `getUpdates` itself, writes `.env`, sends a hello, restarts. No JSON to read.
- `planetai test-alert`: a temporary pack with a rule that always fires; waits, removes itself, hands you the alert id. Your rules are untouched.
- `planetai act <id> [note]`: records the action and prints ρ.
- `planetai status | doctor | sensors | cells | logs | update | backup | config | start | stop | restart`. Doctor names the fix next to each failing check.
- `planetai geocode <place>` to try the lookup without installing.
- README and START_HERE now lead with the one-liner; the flag and by-hand routes remain below it.

## v0.5 — 2026-09-03

**Location independence.** Read the docs as someone setting up in Delhi or Santiago and most of it did not work.

- **Functional, not editorial:** the indoor/outdoor comparison, the flagship service, only fired in Bali. It looked for nearby public reference *sensors*, which exist in the node's data only where a network adapter supplies them. CAMS ships globally but lives in `observations`, so the rule could never fire elsewhere. The two comparison rules now resolve "outside" in order of preference (nearby public sensors, then the CAMS model point sample) and the message names which one it used. Added `outdoor_pm25_high` for nodes whose own sensor is outside.
- `docs/START_HERE.md` rebuilt around **your five inputs**: coordinates, time zone, city key, sensors or none, and what "outside" means where you are. Includes how to find each, how to test whether your city runs a CKAN portal, and what to expect when there are no `bad-` rows (everywhere except Bali). Bali is now a labelled worked example rather than the spine.
- `presets/delhi.env` — a non-pilot site, so the docs' own counter-example is real.
- Bali-specific claims corrected across README, `sensors.md`, `PREFILL.md`, `PLATFORMS.md`, `MAC_MINI.md` (the UPS advice now says where it applies), `ARCHITECTURE.md` (the cell table is labelled an example) and `PRODUCT.md` (states that its numbers are one market's and not portable).

## v0.4.3 — 2026-09-03

- **Security fix:** httpx logs every request URL at INFO, and Telegram carries the bot token in the URL path — so a live credential was written into the container logs, and therefore into any log someone pasted for support. Found when exactly that happened during node #1's update. httpx/httpcore loggers are now set to WARNING, the notifier logs `telegram -> <chat> ok` instead, and exception text is never interpolated (it contains the URL too).
- The installer and updater now scan the container logs for an exposed token and tell you to revoke it.
- `docs/START_HERE.md` gained a short section on treating the token as a password, and the "send this when you ask for help" block now says to scan the log first.

## v0.4.2 — 2026-09-03

- **Fixed:** `app/Dockerfile` listed modules explicitly (`COPY main.py sources.py index.py ./`), so `packs.py` (v0.2) and `bootstrap.py` (v0.4) were never in the image and the app crashed on import after updating. Now `COPY *.py ./`.
- **Added:** `make lint` fails if the Dockerfile enumerates modules; the installer and updater doctors compare the number of modules on disk with the number inside the running container, so a missing file is caught before "done" is printed rather than after.

## v0.4.1 — 2026-09-03

Both found by running `./update.sh` on node #1 — the update path's first real use.

- **Fixed:** a stray comment injected into the `stats` view's `FILTER (WHERE …)` clause swallowed a closing bracket, so the schema failed to apply on any node. Comments no longer sit inside SQL expressions.
- **Fixed:** `backup.sh` read `BACKUP_DIR` and `NODE_NAME` from `.env` without stripping inline comments, so the backup path became `./backups                   # or a NAS mount, e.g. …`. It now strips comments and quotes.
- **Added:** CI spins up a real Postgres and applies `init.sql` **twice**, then selects from every view. A schema that doesn't parse, or isn't idempotent, can no longer be released. The paren-balance check in `make lint` catches it earlier and offline.

## v0.4 — 2026-09-02

**Updating a running node actually works now.** Found while planning node #1's upgrade: Postgres runs `init.sql` only
when the data volume is created, so every schema change since v0.1 would have silently missed an existing node, and
`stats` could not be swapped with `CREATE OR REPLACE` because columns moved.

- `init.sql` is now the complete schema, fully idempotent, applied on both fresh install and update.
- **`update.sh`** — backup (refuses to continue if it fails) → preserve local `rules.yml`/`.env` → pull → apply schema → add new `.env` keys without overwriting yours → rebuild → verify readings/alerts/actions survived, with counts.
- `schema_version` table; `/health` reports code version and schema version, and says `pre-0.4 (run ./update.sh)` when they've diverged.
- `make bootstrap` backfills CAMS history and NASA POWER normals onto a node that predates v0.4.
- `docs/UPDATING.md` — the workflow, rollback, tarball updates, and why editing `config/rules.yml` is the wrong place to tune a threshold.

**A node is useful before it has a sensor.** Coordinates are the only requirement.

- **First-run bootstrap** (`app/bootstrap.py`): 92 days of hourly Copernicus CAMS PM2.5/PM10, NASA POWER monthly climatology (satellite-derived, 1981–present), and one OpenStreetMap reverse geocode so messages name a place. ~2,200 rows, about a minute, no key, anywhere on earth. Runs once when `readings` is empty; `BOOTSTRAP=0` opts out.
- **`openmeteo_air` adapter** — Copernicus CAMS current PM2.5, PM10, dust, aerosol optical depth, CO, NO₂, O₃, UV. Free, key-free, global, every poll.
- **`cold-start` pack** — three rules that need no hardware: today's modelled air, today vs 40 years of normals, and (once a sensor exists) the weekly sensor-vs-model gap. That gap is the local signal a global grid cell cannot see.
- **Site presets** — `--preset bali|barcelona|boston|santiago` sets coordinates, timezone, language and the city's CKAN portal in one flag. Anywhere else works with `--lat --lon`.
- **`docs/PREFILL.md`** — what arrives free, what needs a key (OpenAQ now requires one; Flood Hub and Sentinel need accounts), and what I refused to embed: static datasets that go stale in git, and any pre-seeded demo data.
- Installer now *requires* coordinates and no longer warns about a missing sensor as if it were a problem.

## v0.3 — 2026-09-02

**The node reaches past its own address.** Evaluated against the Fab City Index's 4 pillars × 5 scales using the
registry's own 32 sources; the node was filling one corner of it.

- **Schema:** `sensors.kind` (`sensor | portal | model | survey | child`), `sensors.scale`, `sensors.cadence`. Additive — a v0.2 node updates in place. New `observations` view (latest value per slow source); `stats` is now sensors-only, because a city statistic has no business in a 24-hour rolling mean.
- **`ckan` adapter** — reads any CKAN portal, which covers four of the registry's `governance|city` sources (Barcelona, Boston, Santiago, Bali) with one function. Publishes datasets total, updated-in-90-days, and the share.
- **`openmeteo` adapter** — global model point sample at the node's coordinates. Free, key-free, works anywhere on earth: a node with no sensors at all still has something true to say. Planet scale, boundary condition, never aggregated upward.
- **`open-data-health` pack** — turns portal maintenance into a `Governance|City` cell and warns when a portal goes quiet.
- **`docs/COVERAGE.md`** — the full matrix, what fills today, and the seven empty cells. Finding worth stating: `governance|community` has no source in the registry, and ρ is that source.

## v0.2 — 2026-09-02

**The core is now domain-blind.** Air moved out of `app/` and `config/` into `packs/air-quality/`.

- `config/rules.yml` keeps two rules that work whatever a node measures (dead sensor, daily pulse). The three PM2.5 rules are now `air-quality/indoor_pm25_high` etc.
- `app/index.py` no longer mentions PM2.5. It computes ρ (Governance, every node, every domain) and evaluates cell SQL that packs declare — policing provenance, including refusing a `live` claim before the data supports it (`min_buckets`).
- The test: no threshold, message or pillar mapping in `app/`. Adapters still name metrics, because devices do — that's a driver translating fields into the schema.
- New: `docs/DOMAINS.md` — what a node measures today, and what water, energy, fabrication, noise, comfort and soil packs would look like, with the decision each drives.
- **Updating a v0.1.1 node:** your three air rules move into the shipped `air-quality` pack and keep working; ids gain the `air-quality/` prefix, so existing alert cooldowns reset once. Nothing else changes.

## v0.1.1 — 2026-09-02 (same night as v0.1)

Fixes from the first live install at Fab Lab Bali, and the first two asks from the field.

**Fixed**
- `last_error` in `/health` now clears when every source succeeds on a poll. It used to show the last failure forever. Several failing sources are joined with ` | `.
- Installer: scripts shipped without exec bits; `COPY` syntax failed on Docker's legacy builder; `index.py` wasn't copied into the image; a port clash with another container failed ten seconds in instead of before building. All fixed; `APP_PORT` in `.env` moves the host port.
- `.env`: inline comments after empty values confused the parser (phantom `PARENT_API_URL`). Comments now sit on their own lines; values are stripped in code; a parent URL without `http(s)://` is ignored with a warning.
- Rules are mounted as a directory (`config/`) so editors that save-by-replace (TextEdit) don't break the mount.
- `make restart` applies `.env` changes; `daily_pulse` prints integers and says "no public sensors in range" instead of a dash.

**Added**
- **AirGradient** and **PurpleAir** adapters — both read directly over the LAN, no cloud. EPA 2021 correction applied; raw stored beside corrected. PurpleAir path reproduces Bali Air Dispatch's published Klungkung example.
- Installer flags `--airgradient`, `--purpleair`, `--indoor`, `--no-bad`; env `AIRGRADIENT_HOSTS`, `PURPLEAIR_HOSTS`, `SENSOR_INDOOR`.
- Linux: installer installs `make`/`curl` if missing. Windows: WSL2 detected; uses Docker Desktop's engine instead of trying to install one.
- `docs/PLATFORMS.md` — Linux, Raspberry Pi, Windows (WSL2), Intel Mac: only what differs.
- `docs/START_HERE.md` — choose-your-sensor, pre-flight checks for each, multi-sensor install examples.

**Added — packs (community extension point)**
- `app/packs.py`: scan `packs/`, merge `rules.yml` (ids namespaced), `cells.yml` (extra Index cells), and optionally load `adapter.py`. `GET /packs` lists what's loaded.
- **Data packs** (rules/cells, no code) load automatically. **Code packs** (`adapter.py`) stay off until `PACKS_ALLOW_CODE=1` — the node logs the file to read first.
- Worked example: `packs/example-cooking-hours/`. Model and tiers: `docs/PACKS.md`.

**Repository**
- `LICENSE` (Apache 2.0 full text), `NOTICE`, `CONTRIBUTING.md`, issue templates (node problem / new source), CI lint + offline adapter tests (`tests/test_sources.py`, `make test`), README rebuilt for the public repo, banner on the Fab City design system.
- Landing page for `planetai.fab.city/node0/` (in the planetai site repo, not here) — rebuilt v0.2 with the packs section.

**Not changed**
- Rules, schema, Index contract, ρ ledger. A v0.1 node updates in place: `git pull && docker compose up -d --build`.

## v0.1 — 2026-09-02

First running node. Smart Citizen 19880 + Bali Air Dispatch → Postgres → five SQL rules → Telegram. `GET /cells` (fci-cells-v0), `POST /actions` (ρ). Node #1: "Bayu 2 – Indoor", Kuta Selatan.
