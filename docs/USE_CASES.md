# Three things node #1 can tell you today

Written on 5 September 2026 against seven days of real data from the sensors in one Smart Citizen account in
Kuta Selatan, Bali: three indoor kits at one house, an outdoor kit a kilometre away, and the Copernicus CAMS model
sampled at the house. Every number below was computed, not invented. Each use case names the feature that
produces it and what it asks of you.

## 1. Is the air in my house my problem or the street's?

**The answer this week:** mostly the street's. Indoor PM2.5 tracked the outdoor kit at r = 0.55, and the house held
back about 30% of it (indoor mean 5.8 µg/m³ against outdoor 9.6). Zero hours in seven days had indoor more than
10 µg/m³ above outdoor, so nothing was burning or frying inside that the street didn't explain. Two indoor kits in
the same house agreed at r = 0.73 with a 0.2 µg/m³ bias, which is the sensors saying they can be trusted.

**What produces it:** the `insight` pack's daily `agreement` rule, in Postgres with `corr()`. And the moment it
changes, the air-quality pack's `inside_worse_ventilate` fires: *inside is worse than outside, something is burning
or cooking indoors, open a window*. Those two together are the household's answer, one sentence a day and one
sentence when it matters.

**What it needs from you:** an indoor kit and something outdoor to compare with. This week the outdoor comparison
was your own enclosure kit; with `SC_USER=tomasdiez` the node discovers it from your account and classes it as a
reference automatically because it sits a kilometre away.

## 2. When should I open the windows?

**The answer this week:** around 15:00. The street was worst at 18:00 (12.6 µg/m³) and 06:00 (11.0), the evening
and morning burning, and cleanest mid-afternoon (7.5). Indoors peaked at 18:00 (8.7) and again at 09:00 (7.7),
following the street with a lag. The CAMS model, meanwhile, read a flat 11–14 all day and missed the rhythm entirely.

**What produces it:** the `rhythm` rule, daily, in local time, ending in the one actionable line. And the `digest`,
every three hours: inside, outside, model, 24h mean, peak, and whether it's rising or falling. Copy the pack and
change one number to make it hourly.

**What it needs from you:** a week of data, and `NODE_TZ` set — which until this morning it wasn't reading, so the
"hours" would have been UTC. Fixed in v0.9.

## 3. Should I trust the satellite?

**The answer this week:** for your street, roughly; for your room, not at all. Outdoor kit vs CAMS: r = 0.51, the
model reading 2.2 µg/m³ high on average and overstating the peaks by about 60% (p95 23.1 against 13.7). Indoor vs
CAMS: r = −0.18. No relationship. The model is an 11 km grid cell; it can tell you what the atmosphere over the
district is doing and nothing about the air you breathe. Shifting the model an hour earlier improved the street
correlation slightly (r = 0.53), suggesting the street follows the regional signal by about an hour, which is
plausible and worth watching over more weeks.

**Why this matters beyond one house:** it is the argument for the whole project, in your own data. A node that
knows only the model knows the district. A node with a sensor knows the address. The gap between them is the local
signal, and the `agreement` rule states it in a sentence every day so nobody has to take it on faith.

**What it needs from you:** nothing. The model arrives on its own; the comparison runs on its own.

## Also learned from the same data

- **Ungasan Kit has published no PM2.5 in seven days.** Online radio, dead sensor. The `sensor_silent` rule only sees
  a kit that stops publishing entirely; a kit that publishes everything except the metric you care about is a gap
  worth a rule of its own.
- **Ulu Garden (Making Sense Bali) is indoor, seven kilometres away, and offline this week.** Discovery classifies
  it correctly: not local, not outdoor, so it enters neither the household rules nor the ambient average.
- **Your account is a six-sensor network already.** The node was reading one of them.

## Automations, when you want them

The node does not switch anything. It publishes. `planetai homeassistant` puts every local sensor and the latest
alert into Home Assistant as entities over MQTT discovery, and Home Assistant does what it is good at: *when
indoor PM2.5 > 35 for 10 minutes, turn on the purifier; when the alert level is act, flash the kitchen light*. Three
worth building first, all from the numbers above:

1. **Purifier on** when any indoor PM2.5 entity exceeds 35 µg/m³ for ten minutes; off when below 12 for thirty.
2. **A window reminder** at the street's cleanest hour, only on days the indoor 24h mean is above 10.
3. **A phone notification** from HA whenever the `latest alert` entity changes to level `act`, so a household that
   already lives in Home Assistant never needs Telegram.

None of these needs code in the node. That is the point of the split.
