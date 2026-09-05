# insight

Three rules that turn the node's own history into sentences. No Python: Postgres has `corr()` built in.

**`digest`**, every three hours — inside, outside, model, 24h mean and peak, trend. Copy the folder and change
`cooldown_minutes` to change the cadence; that is the whole configuration.

**`agreement`**, daily — Pearson r between indoor and outdoor, outdoor and the CAMS model, indoor and the model;
how much of the street the house holds back; the model's bias. Needs 48 overlapping hours.

**`rhythm`**, daily — the street's worst and cleanest hours this week, and when the house peaks, in local time.
Ends in the one actionable line: when to open the windows.

**Where the numbers came from.** Written against seven days at Kuta Selatan, 5 September 2026, from six Smart Citizen
kits in one account plus CAMS: indoor tracks outdoor at r = 0.55 with the house filtering ~30%; two indoor kits agree
at r = 0.73; the model tracks the street at r = 0.51 and reads 2–3 µg/m³ high, overstating peaks by ~60%; the model
tracks indoor air at r = −0.18. The street peaked at 18:00 and 06:00 WITA; the model was flat all day.
