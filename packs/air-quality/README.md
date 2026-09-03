# air-quality

The first domain pack, and the one that proves the core is domain-blind: nothing about PM2.5 lives in `app/`.

**What it adds** — three rules built around the decision a household actually faces (is the room better or worse than
the street, should the windows be open or shut), and three Index cells for `Environmental|Community` and
`Environmental|City`.

**Where it was learned** — Kuta Selatan, Bali, September 2026, against Smart Citizen Kit 19880 and the public ambient
picture from Bali Air Dispatch. The burning pattern here peaks around 9am and climbs again after dark.

**What it assumes** — a low-cost PM sensor at the address, and at least two public outdoor sensors within range for the
comparison rules. Thresholds are US EPA / WHO 2021 (35.5 µg/m³ unhealthy for sensitive groups, 15 µg/m³ WHO 24h).

**Fork it.** The numbers that matter in Kerobokan are not the numbers that matter in Poblenou, and the sentence that
gets someone to close a window is different in every language and every building. Copy this folder, change the
thresholds and the wording, publish it as `planetai-pack-air-<yourplace>`.
