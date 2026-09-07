# trust

Whether the node's own sensors are telling it the truth. Three rules, no Index cell: this pack says something about
our instruments, not about the place.

**A week, or silence.** Every rule joins the same `seasoned` gate: a sensor with under seven days of readings on
this node is never named. A statement about an instrument needs a week — a day of one says more about the weather
and the hour than about the sensor. All three rules are `info` with a seven-day cooldown, so the pack speaks in the
week's instrument paragraph rather than interrupting a household in the evening.

**What it adds**
- `channel_dead` — a channel flat (max − min = 0 within the hour) for every one of the last 24 hourly buckets,
  with all 24 present and none of them moving, while at least one other `ambient` channel on the same kit did move
  in the same day. A flat value of 0 is skipped: a floor is not a freeze. Fires only under a kit that has reported
  at all in the last 2 hours, because a channel on a kit that has gone fully silent is `coverage_low`'s problem.
- `coverage_low` — a seasoned local ambient channel that reported for under 60% of the last 7 days (under 60% of
  168 hours). A kit can be at 3% coverage and still show a reading from four minutes ago; this rule is what says so.
- `peer_disagreement` — two seasoned local ambient sensors within 50 m of each other whose seven-day means differ
  both relatively and absolutely: a ratio outside 0.85–1.15 **and** a difference of at least a per-metric floor
  (5 µg/m³ for pm1, pm25 and pm10; 2 °C for temp; 5 points for humidity; 0.3 kPa for pressure; anything else,
  15% of the pair's own mean). Both units need at least 100 of the week's 168 hourly buckets. One row per pair, so
  A ≠ B and B ≠ A are one alert, naming both units and both numbers; the cooldown is keyed on the pair.

**Silence is defined by value change, not by a timestamp.** Smart Citizen's per-reading `recorded_at` is null on
every kit node #1 reads, so the adapter stamps every channel with the kit's own `last_reading_at` at poll time. A
channel that has stopped producing new values still gets a fresh timestamp on every poll, and its frozen value is
re-inserted under that new timestamp. That pulls the 24-hour mean toward the frozen number and shrinks its
variance, so a dying channel's own statistics make it look steadier, not worse. A timestamp check would never
catch this; `channel_dead` looks at the value instead.

**It reads local sensors only.** Every rule filters on `sensors.local`: a node reports on its own instruments, not
on a public reference station's or another node's. Coverage and disagreement are facts about equipment this
household owns and can act on.

**It writes no Index cell.** A trust score is a fact about our instruments, not about the place, and a cell that
scores our own competence invites us to optimise it rather than fix the sensor. This pack ships no `cells.yml` at
all; `channels.yml` is present but empty, for the same reason it exists in the first place: to say plainly that
this pack declares no metric of its own, rather than leaving a reader to wonder.

**What it does not know.** `peer_disagreement` cannot tell a badly sited sensor from a badly calibrated one — two
units 3 m apart that disagree could have one behind a wall of incense smoke, or one with a fouled inlet. That is
why its message asks the reader to swap the two units' positions for a day rather than naming which one is wrong:
if the gap follows the box, it is the sensor; if it stays with the spot, it is the siting. The pack cannot do that
diagnosis itself, only point at it. It also cannot group like with like beyond `channel_roles.reference`, which is
per source: node #1's SENX unit is a different sensor model from the kits beside it, and to this pack all three are
`smartcitizen`.

**Two things this pack does not see yet.** Found while building the channel registry that these rules read
(`channel_roles`, Task 5):
- PurpleAir's `channel_disagreement` (in the PurpleAir adapter in `app/sources.py`, commented "a laser is failing;
  rule on this later"). It is a direct instrument-failure signal and this pack is the "later" — but node #1 has no
  PurpleAir hardware, so nothing is lost today. A future version should declare it in `channels.yml` and add a
  rule.
- Meshtastic's `altitude_m` (`app/sources.py:441-442`), written by the position handler outside `MESH_METRICS`
  entirely, so it never gets a role and this pack never sees it.

**Where the numbers came from, and what was wrong with the first set.** Node #1, Ungasan, Kuta Selatan. On
7 September 2026 at 21:17 WITA this pack sent that household three warnings on Telegram and all three were wrong.
They are the reason for every number above.

- **A day was the fault under all three.** The first version of each rule asked 24 hours and treated the answer as
  an alert. Every kit it named was two days old. `coverage_low` wants 60% of 168 hours, which no node younger than
  about four days can reach, so a new node would have said "missing most of the week" on its first day — Lucas's
  and Vivanco's, when they come up. Hence `seasoned`, and hence seven-day windows.
- **`channel_dead` fired at dusk.** Its first form was six flat buckets out of the last 24 with the latest bucket
  flat too. Ungasan Kit's light channel reads 0 from dusk to dawn — eleven flat hours ending in the latest bucket
  — so the rule matched every evening, on every kit with a light channel, as often as its 12-hour cooldown
  allowed. Any channel with a legitimate floor (light, uv, rain, noise) or a steady indoor value trips that form.
  A full day of flat buckets is longer than any night in Kuta Selatan, so it needs no metric-specific exception,
  and a channel that genuinely dies still matches after a day.
- **A ratio says nothing in clean air.** `peer_disagreement`'s 0.85–1.15 band came from a week where node #1's one
  collocated pair agreed to within 4.5%, and had never met a disagreement. Its first outing produced two alerts
  for one fact: Ungasan Kit at 7.4 µg/m³ against BAYU NEW ENCLOSURE at 5.4, 30 m apart, a ratio of 1.37 and a
  difference of 2 µg/m³. At 7 µg/m³ that band is ±1 µg/m³ — the integer resolution of a Plantower-class sensor,
  and ten times inside its stated accuracy at low concentration. Two identical units in clean air disagree by more
  than that most days. The absolute floors come from the instruments, not from statistics: 5 µg/m³ is Plantower's
  own ±10 µg/m³ (or ±10%) below 100 µg/m³, halved; 2 °C and 5 points of humidity are what two boxes a few metres
  apart differ by on a still afternoon, with the SHT31's ±0.3 °C and ±2% on top of siting; 0.3 kPa is 3 hPa, in
  the unit this node stores pressure in.

**What has and has not been exercised.** The rules are tested against node #1's own series, replayed through the
SQL as it ships (`tests/data/node1-*.tsv`, `tests/trustdb.py`): the light channel at dusk, the 16-against-7 pair
and the 7.4-against-5.4 pair, the 59-hours-of-168 coverage, and a synthetic channel stuck on 412 lux for 26 hours
for the one case node #1 has never produced — a genuinely frozen channel. None of these thresholds has met a burn
season, when PM2.5 swings far wider and disagreement between units may widen with it. Node #1's own kits reach a
week between 9 and 12 September 2026; until then this pack says nothing at all about them, which is correct and is
also why the first week after this release proves less than it looks.
