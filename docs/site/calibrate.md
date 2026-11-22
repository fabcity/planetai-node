# Corrections
<!-- checked: v0.92.0 -->

Many nodes have a cheap particle sensor and a better one a few metres away, and the node already shows both numbers.
The `calibrate` pack lets you use the better one to correct the cheap one. You tell the node which two sensors sit
together, it fits a straight line from one to the other, and the Data page shows the corrected number beside the
measured one for as long as the line has been closer on days it never saw.

The pack is off on every node until you name a pair. Nothing is stored but that setting, and the corrected number
lives on the page only.

## Naming a pair

A pair is one entry in Set up, under Calibrate, in the setting `CALIBRATE_PAIRS`. It has four or five parts,
separated by spaces: the sensor to correct, the better sensor beside it, the metric, the day you put them together
and, if one of them has gone, the day it left. Dates are the node's own days (`NODE_TZ`). Separate pairs with `;`.

Our garden in Ungasan is the worked example. An HM-3301 (`sc-19874`) sits 30 m from a kit with a SEN5X
(`sc-19236`), both outdoors, together since 30 August:

```
CALIBRATE_PAIRS=sc-19874 sc-19236 pm25 2026-08-30
```

The one to correct always comes first. Use the row ids the node shows, since a kit that is both forwarded and polled
is two rows, and you choose which one you mean. When two of your sensors are within 50 m of each other, both indoors
or both outdoors, and share a metric, the Corrections section suggests them with the text to paste: "You could name:
… Write the one to correct first".

`since` is required because the node keeps no history of where a sensor stood. Two sensors that both reported for
months from different rooms would otherwise be fitted on hours when they were apart. If you move a sensor and tell the
node nothing, it goes on fitting hours that are no longer side by side. The 50 m test below catches it when the pin
moves; otherwise the node has only your word, so give it an `until` when the two are separated.

## What the node checks

Set up takes whatever you type. The Corrections section then says, in words on the row, what is wrong with a pair it
will not use:

| the row says | when |
|---|---|
| `cannot read "…"` | the entry does not have four or five parts, a date does not parse, the last day is before the first, the first day is in the future, both ids are the same, or this sensor and metric are already in an earlier pair |
| `not known to this node: <id>` | the node has no sensor with that id |
| `<id> is not a sensor` | the id is something other than a sensor row, such as a peer, a child, a model or a portal |
| `a public station cannot be the one corrected` | the sensor side is a station the node reads from a public network |
| `<source> declares no <metric> channel` | one side's source does not declare that metric as an ambient, comparable channel |
| `one is indoors and the other outdoors` | as it says |
| `<n> m apart` | both have coordinates and they are more than 50 m apart |

50 m is what the node already means by "the same place" (the trust rule `peer_disagreement`). When either side has no
coordinates the pair is accepted on your word, and the row says the distance is not known.

The better sensor can be any of your own sensors or a public station the node reads. It is always read as measured,
even when it is itself the sensor of another pair.

## The line and the check

The node reads the hourly means of both sensors from the day you named. A paired hour is an hour in which both have
a mean. The line is `better = a + b × sensor`, fitted by least squares on the paired hours of the 14 days that end at
the last paired hour, and it needs 168 paired hours. The corrected number is that line applied to the sensor's
latest hourly mean. It never goes below zero when the better sensor never read below zero in those 14 days.

Every finished day with at least 12 paired hours is scored, if the 14 days before it hold 168 paired hours: a line is
fitted on those 14 days alone and applied to that day, and the day gets two numbers, how far the measured hours were
from the better sensor on average and how far the corrected hours were.

The corrected number is shown when the newest 14 scored days that are no older than 28 days number at least 7, and
over them the corrected distance is at most nine tenths of the measured one, so the line has been at least a tenth
closer. Otherwise the row shows the measured number alone and says why: too young (how many hours or checked days it
has), measured is closer, not a tenth closer, or the sensor read one value for two weeks.

Each row shows the two distances as "off by 2.6 → 1.4", measured first. Each call reads 42 days of hourly means.

## When the better sensor leaves

The clock runs from the last paired hour. For 7 days after it the row keeps the corrected number from the last line,
as long as the check on the days already scored still passes. After 7 days the correction is withdrawn, and the row
says "withdrawn: nothing beside it since" and the date. A better sensor that drops out for two days and comes back is
covered by the same rule.

In the garden a line left alone was clearly closer in its first week, barely in the second, and worse than the
measured number from the fourth, which is why 7 days and no more (the table is below).

## What the corrected number never does

It is worked out when the page asks and stored nowhere. The node stores, alerts on and shares the measured number. No
rule, alert, ρ, Index cell, `/export`, report, digest, bot answer or aggregate sent to a parent ever sees a corrected
number, and no line is sent to another sensor or another node.

`GET /calibrate` answers only this machine or a screen holding a node token, because which sensor sits beside which
is the household's. A locked screen shows the Corrections section with a line asking you to unlock it. On an unlocked
screen, the row of a sensor whose correction is shown also carries a small mark in Readings, "corrected 13.6 against
Ungasan Kit", linking to the section. The measured value stays the row's number.

## A public station beside your sensor

A station can be the better side of a pair, if the node reads it. With the `bali-air-dispatch` pack the ring drops any
station within 150 m of the node, taking it for your own hardware, and any beyond `BAD_RADIUS_KM`. A station your
sensor sits beside is either very close or far outside the ring, so put its id in `BAD_INCLUDE` and the ring keeps it
at any distance. Stale and malfunctioning stations still drop, and so does a device the node already polls or one you
listed in `BAD_EXCLUDE`.

If you carry a sensor to a station, move its pin on the network it reports to, or the node sees the two as
kilometres apart and refuses the pair. Give the pair the day you put it there as `since`. While the
sensor is there the row shows how far off it reads, and for 7 days after it comes home the corrected number stays.
That does not make the sensor corrected from then on.

The row names the station's network and, for Bali Air Dispatch, whether it is official and whether its numbers are an
index converted back: "corrected against Kabupaten Badung Sempidi (AQICN), official station, its numbers are an index
converted back". Other station packs give the network only.

> **Not run yet.** No pair with a public station has run anywhere. This half of the pack is tested on fixtures only.
> The archive holds two official stations in Bali, Lumintang has been silent since August 2025, Sempidi's PM2.5 is an
> index converted back, and no sensor of ours sits beside either.

## Boxes with more than one particle sensor

Pair only boxes with one particle sensor, on either side. Today the node stores every PM2.5 channel of a Smart Citizen
box under one `pm25` and keeps whichever the API lists first, so a line fitted against such a box may be a line
against the wrong sensor, and the stored row cannot say so. The node cannot tell these boxes apart yet, so it does not
refuse them. The garden pair is safe: `sc-19236` has a SEN5X only and `sc-19874` an HM-3301 only.

## Kits on the node's broker

A kit that publishes straight to the node's broker (`sck-…`, source `smartcitizen-direct`) cannot be paired yet. That
source declares no channels and carries no coordinates, so the row says it declares no channel for the metric. Pair
the kit's Smart Citizen row instead, if the node polls it too.

## What was measured

All of this comes from Smart Citizen's open API, hourly means of PM2.5, read on 22 November 2026 for our own sensors
in Bali. The better sensor in every set is a Sensirion SEN5X, and none of them is a reference instrument. No node
was used. Two sets, the living room and the study's PMS5003, have both sensors in one box: Smart Citizen's own
history keeps their channels apart, which the node cannot do yet.

In the first table each set stands alone, and a day is scored with a line fitted on the 14 days before it. Distances
are in µg/m³.

| set | where | paired hours | r | line, SEN5X = | measured off by | corrected off by | days closer |
|---|---|---|---|---|---|---|---|
| Ungasan garden, HM-3301 | outdoor, 30 m | 1,892 | 0.97 | −4.27 + 1.51 x | 2.40 | 1.33 | 50 of 72 |
| Ungasan study, HM-3301 | indoor, side by side | 573 | 0.98 | −1.08 + 0.97 x | 1.01 | 0.95 | 10 of 16 |
| Living room box, HM-3301 | indoor, one box | 834 | 0.94 | −9.17 + 3.87 x | 5.80 | 4.64 | 19 of 28 |
| Serangan kiosk, HM-3301 | outdoor, 13 m | 1,256 | 0.90 | −11.75 + 2.03 x | 3.77 | 5.81 | 7 of 37 |
| Ungasan study, PMS5003 | indoor, one box | 573 | 0.96 | +2.64 + 0.61 x | 3.06 | 0.94 | 16 of 16 |
| Jimbaran office, HM-3301 | indoor/outdoor, 40 m | 166 | 0.97 | −1.58 + 1.31 x | 1.62 | too short | |

Each HM-3301 has its own slope, between 0.97 and 3.87. A line borrowed from another place made the sensor worse than
measured every time, and so did one line pooled from all the others, which is why nothing here corrects a sensor that
has nothing beside it. At Serangan the line made the sensor worse, and the check below keeps it off the page.

A line left alone, in the garden, fitted on 14 days and then the better sensor treated as gone:

| weeks after | measured off by | line off by | starts the line won |
|---|---|---|---|
| 1 | 2.55 | 1.47 | 8 of 9 |
| 2 | 2.54 | 2.06 | 5 of 9 |
| 3 | 2.41 | 2.40 | 4 of 8 |
| 4 | 2.07 | 2.42 | 3 of 7 |

Weeks 5 to 8 were worse than measured. At Serangan the line was worse every week, and in the living room it won the
first week and lost after. Only the garden pair has enough history for this table.

The check, replayed day by day on Bali days, with the distances on the days in each column:

| set | wait to first shown | days shown: measured → corrected, closer | days not shown: measured → corrected, closer |
|---|---|---|---|
| Garden | 21 days | 63: 2.55 → 1.39, 49 | 7: 1.20 → 0.72, 6 |
| Study HM-3301 | 15 days | 4: 0.39 → 1.51, 0 | 12: 1.25 → 0.75, 10 |
| Living room | 17 days | 20: 5.65 → 3.78, 15 | 7: 6.51 → 3.87, 7 |
| Serangan | never | 0 | 38: 4.21 → 5.41, 5 |
| Study PMS5003 | 15 days | 9: 3.59 → 1.03, 9 | 7: 2.46 → 0.85, 7 |

The days not shown include the first seven scored days of each pair, when there is no verdict yet. Without the tenth,
Serangan would have been shown for 3 days at 1.44 → 2.01 and the study HM-3301 for 6 days at 0.46 → 1.25. With it,
the study HM-3301 is still shown for 4 days on which it was worse by about 1 µg/m³: there the two sensors agree so
closely that the check follows noise. We picked the tenth after seeing these five sets in four places, so this table
does not test it independently.

In the garden, adding humidity or the hour of day moved the distance between 1.36 and 1.40 against 1.37 for the
straight line, and in the study a humidity correction took the HM-3301 from 1.0 to 1.9, so the pack fits a straight
line only.

Not measured: a reference instrument; any pair with a public station; two units of one model side by side; a full
wet season; any sensor that is not an HM-3301 or a PMS5003; any metric but PM2.5; node #1 or any other node; the
decay of a line left alone on more than one pair. The pack lets you name any ambient, comparable metric, and the
check runs on each pair by itself, so an untested metric still has to earn its place on your node.

## How long it takes

Expect two to three weeks from the first paired hour to a first corrected number: 7 days to fit, then 7 scored days,
and hours go missing. In the replay it took 15, 17 and 21 days. A node holds only what it polled, with no backfill,
so a node that started reading a sensor last week has one week of it whatever the sensor's own network holds.

The route and its answer are in [the API](api.md), the setting in [Configuration](configuration.md), and the rest of
the Data page on [the dashboard](dashboard.md) page. Next, [the packs reference](packs-reference.md) lists every pack
that ships.
