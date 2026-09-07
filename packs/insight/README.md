# insight

Three rules that turn the node's own history into sentences. No Python: Postgres has `corr()` built in.

**`digest`**, every three hours — inside, outside, model, 24h mean and peak, trend. Copy the folder and change
`cooldown_minutes` to change the cadence; that is the whole configuration.

**`agreement`**, daily — Pearson r between indoor and outdoor, outdoor and the CAMS model, indoor and the model;
how much of the street the house holds back; the model's bias. Needs 48 overlapping hours.

**`rhythm`**, daily — the street's worst and cleanest hours this week, local time, checked against the one thing
that can say why: the street's own noise. It needs a local outdoor noise sensor and stays silent without one — see
below.

**Where the numbers came from.** Written against seven days at Kuta Selatan, 5 September 2026, from six Smart Citizen
kits in one account plus CAMS: indoor tracks outdoor at r = 0.55 with the house filtering ~30%; two indoor kits agree
at r = 0.73; the model tracks the street at r = 0.51 and reads 2–3 µg/m³ high, overstating peaks by ~60%; the model
tracks indoor air at r = −0.18. The street peaked at 18:00 and 06:00 WITA; the model was flat all day.

**These pooled figures are dated 5 September 2026 and are kept for the record, not as current guidance.** They
average kits of mixed hardware together before correlating, and one kit in that pool reads about 1.5x the others
in the same room — enough to move a correlation on its own. Measured pairwise instead, for the same seven-day
window, `sc-19880` against `sc-19874` gives r = 0.20 over 134 overlapping hours, not 0.55. Two kits that actually
sit in the same room agree far less than the pooled number suggested. Prefer the pairwise figure; the paragraph
above stays as the record of what the pack originally shipped with and why it changed.

**Why `rhythm` no longer blames traffic.** The rule used to end "that is the burning and the traffic, not the
weather" — an evening PM2.5 peak, so traffic felt like the obvious other half. `sc-19236`, the one kit in the fleet
with a noise sensor, said otherwise once anyone read it: it sits 250 m from the node, local under both the 500 m
default and the 1500 m radius node #1's operator has chosen. Over the same seven days its hour-of-day means show
the street loudest across the late morning and afternoon and at its quietest overnight, while PM2.5 peaks in the
evening with a second peak near dawn — the loud hours are the clean hours. Pearson r between PM2.5 and noise
across 169 hourly buckets is negative. An evening pollution peak arriving as the street quiets down is not what
traffic looks like; it fits a source that starts after dark, which is what `docs/sensors.md` already documents for
this season. `rhythm` now says that and stops naming a cause its own data argued against.

**A node with no local outdoor noise sensor gets no `rhythm` alert.** The SQL cross-joins a `loud` CTE built from
local outdoor noise readings; with none, that CTE is empty and the whole rule returns nothing. That is deliberate.
The old rule asserted a cause with no evidence for it in either direction — no message is better than a wrong one.
