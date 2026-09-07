# trust

Whether the node's own sensors are telling it the truth. Three rules, no Index cell: this pack says something about
our instruments, not about the place.

**What it adds**
- `channel_dead` — a channel that has been flat (max − min = 0 within the hour) for 6 or more of the last 24
  hourly buckets, and whose most recent bucket is flat too. Requiring the latest hour to still be flat is what
  makes this "frozen right now": a channel that sat still for six hours overnight and then moved again — a stable
  pressure reading, say — does not match. Fires only under a kit that has reported at all in the last 2 hours,
  because a channel on a kit that has gone fully silent is `coverage_low`'s problem, not this one's.
- `coverage_low` — a local ambient channel that reported for under 60% of the last 7 days (under 60% of 168
  hours). A kit can be at 3% coverage and still show a reading from four minutes ago; this rule is what says so.
- `peer_disagreement` — two local ambient sensors within 50 m of each other whose 24-hour means differ by more
  than 15% (a ratio outside 0.85–1.15).

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
diagnosis itself, only point at it.

**Two things this pack does not see yet.** Found while building the channel registry that these rules read
(`channel_roles`, Task 5):
- PurpleAir's `channel_disagreement` (in the PurpleAir adapter in `app/sources.py`, commented "a laser is failing;
  rule on this later"). It is a direct instrument-failure signal and this pack is the "later" — but node #1 has no
  PurpleAir hardware, so nothing is lost today. A future version should declare it in `channels.yml` and add a
  rule.
- Meshtastic's `altitude_m` (`app/sources.py:441-442`), written by the position handler outside `MESH_METRICS`
  entirely, so it never gets a role and this pack never sees it.

**Where the numbers came from, and where they have not been tested.** Node #1, Ungasan, 1–7 September 2026, six
Smart Citizen kits, PM2.5 means of 6–10 µg/m³ across the week. All three thresholds were chosen against that one
low-PM week and have never met a burn season, when PM2.5 swings far wider and disagreement between units may
widen with it. `peer_disagreement`'s 0.85–1.15 band came from a week where the only local collocated pair — two
kits 31 m apart — agreed to within 4.5% (ratio 1.045), well inside the band. The 1.5x disagreement that motivated
this rule (§3 L0 of the spec) was between three kits at the same operator's other site, 1.2 km away; after Task 2
narrowed `local` to within `LOCAL_RADIUS_M` of this node, those three kits are no longer local to node #1, so
`peer_disagreement` is silent here until a second local unit is collocated with an existing one. Its band has not
yet been exercised against a real disagreement — only against one pair that agreed.
