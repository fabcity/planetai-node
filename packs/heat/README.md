# heat

Turns the temperature and humidity the node already stores into three sentences about heat, and one Index cell.

**What it adds**
- `heat_stress_now` — apparent temperature ≥ 32 °C at any local sensor (Steadman, no-wind form, the Australian
  BoM's "caution" line). Act-level: what to do, and who to check on.
- `heat_danger` — ≥ 40 °C apparent. Heatstroke territory.
- `night_no_relief` — overnight indoor minimum above 28 °C, the WHO ceiling for restorative sleep. Once a day,
  ending in the only thing that helps long-term: shade or airflow, not a bigger fan.
- `Social|Community` — hours per sensor in the last 30 days with indoor apparent temperature ≥ 32 °C. The Social
  column of the Index is empty across the whole registry; this is one honest number for it.

**Where the numbers come from.** Steadman's apparent temperature as published by the Australian Bureau of
Meteorology (AT = T + 0.33·e − 4.0, e in hPa). The no-wind form fits indoors. Thresholds are BoM's and WHO's, not
ours. Tune in a fork: a Balinese kitchen and a Barcelona flat do not share a comfort line.

**What it assumes.** A local sensor reporting both `temp` and `humidity` (Smart Citizen, AirGradient, and a BME680
on a Tracker all do). Indoor for the night rule and the cell; the stress rules fire on any local sensor.

**What it does not know.** Radiant heat (a tin roof at 14:00) and airflow (a fan on you). Apparent temperature
underestimates the first and ignores the second. It is a floor, not a full comfort model.
