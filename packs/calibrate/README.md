# calibrate

A node often has a cheap particle sensor and a better one a few metres away. This pack uses the better one to
correct the cheap one, once you tell it which two sensors sit together. You name the pair in one setting,
`CALIBRATE_PAIRS`, and while that is blank the pack does nothing at all.

Each pair is four or five parts separated by spaces: the sensor, the better sensor beside it, the metric, the day
they were put together and, if you took one away, the day it left. Pairs are separated by `;`, as in
`sc-19874 sc-19236 pm25 2026-08-30`. The better sensor can be one of yours or a public station, and the page says
which, and names the network when it is a station.

It fits a straight line on the 14 days before a day, scores the line on that day, which the line has never seen,
and keeps score. A line needs 168 paired hours, and a day is scored when it has 12.

The verdict reads the newest 14 scored days that are no older than 28 days, and needs 7 of them. The corrected
number is shown only while it has been at least a tenth closer to the better sensor than the measured one, so the
corrected distance is at most 0.9 of the measured. When it is not shown the page says what is missing, and the
measured number stays as it was.

Seven days after the last paired hour the correction is withdrawn, since the line was fitted only while the two were
together. Beside means at most 50 m, and each call reads 42 days of hours.

Nothing is stored except that one setting. `GET /calibrate` works everything out again each time, so there is
nothing to clean up, and the route only reads. It is on no share list, so it answers this machine or a node token
only, and a household that opens its node to its own WiFi does not open this.

It writes no rules, alerts, cells or export rows, and it passes no corrected number to a parent node. Wherever a
corrected number appears it says "corrected against" and the name of the sensor, next to the measured one.

## What was tested and what was not

The line was tried on five sets in four places in Bali: a garden, a study (two sensors there), a living room and a
kiosk. The sensors were HM-3301 and PMS5003 against a SEN5X, PM2.5 only, from Smart Citizen's own history, and the
garden had the most hours. The check was replayed day by day on those five sets. We picked the tenth after looking at
them, so those days do not prove the tenth. A line left alone stopped helping within a month.

We have not tried a reference instrument, or a pair with a public station. We have not tried two units of one model
side by side, a full wet season, another sensor or another metric, and it has not run on any node, ours included.

The first link we want is one sensor beside the Sempidi station, and until that exists nothing in Bali is corrected
against an instrument. The numbers are on the docs page, [docs/site/calibrate.md](../../docs/site/calibrate.md).
