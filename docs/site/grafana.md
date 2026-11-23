# Grafana
<!-- checked: v0.92.0 -->

The dashboard draws the node the way this project decided to draw it. Grafana is for the person who keeps the node
and wants to look at their own data their own way: a month of one room, every sensor on one chart, the hours a sensor
went quiet, panels nobody here thought of. It runs beside the dashboard and never replaces it.

Grafana reads the database directly, raw readings included, and carries none of the dashboard's rules. It will not
mark a number `live`, `partial` or `stale`, and it draws a model's estimate the same way as a measurement unless you
tell it apart. The starter dashboard's title says so ("keeper's view · no provenance"), and the
[traps](#what-grafana-will-not-tell-you) further down are yours to keep in mind.

## Turn it on

```bash
planetai grafana
```

It adds `grafana` to `COMPOSE_PROFILES`, makes Grafana's database login, starts Grafana and prints its address,
`http://127.0.0.1:3000` unless you changed it. Sign in as `admin` with `GRAFANA_ADMIN_PASSWORD`, or `admin` until you
set one. The starter dashboard is in the PLANETAI folder.

Grafana listens on the node's own machine only. From a laptop, tunnel to it:

```bash
ssh -L 3000:localhost:3000 <the node's machine>
```

and open `http://localhost:3000` on the laptop. To open it to the house network instead, set `GRAFANA_ADMIN_PASSWORD`
first, then `GRAFANA_BIND=0.0.0.0`, and run `planetai grafana` again. Whoever signs in sees everything the next
section lists.

```bash
planetai grafana off
```

stops it, takes it out of `COMPOSE_PROFILES` and drops the database login. Your own dashboards stay in the `grafana`
volume, and come back the next time you turn it on.

| key | default | what it does |
|---|---|---|
| `GRAFANA_PORT` | `3000` | the port Grafana answers on |
| `GRAFANA_BIND` | `127.0.0.1` | the address it listens on; `0.0.0.0` is every interface |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | the password of Grafana's `admin` login |

The three keys are read at start, so they are changed in `.env`, then `planetai grafana` again. Set up › System says
whether Grafana is running, at which address, whether its password is set (never the password) and how to open it
from a laptop.

## What it can read

Grafana signs in to the database as `planetai_grafana`, a login made by `config/grafana/role.sh` each time Grafana
starts. It belongs to `planetai_ro`, the role pack rules already run as, which can read every table except
`settings` and the household's own (`captures`, `things`, `learnings`, `digests`, `household`, `place_photo_asks`,
`place_photo_asks_in`), and write none. On top of that:

- every session it opens is read-only;
- a query stops after 30 seconds, so a wide panel cannot slow the node down;
- it holds four connections at most;
- its session timezone is the node's `NODE_TZ`, as the app's own connections are;
- its password is generated into the `grafana-secret` volume. Nothing goes in `.env`.

What it can read is far more than the API gives a screen without a token. The rooms have their real names, the
household's sensors stand at their real points, and private channels (a home's counts of what it keeps) are there in
full. That is why Grafana listens on loopback by default, and why `GRAFANA_BIND` comes after a password.

The tables a panel usually wants are `readings` (`ts, sensor_id, metric, value`), `sensors` (who each sensor is, in
which room, and whether it is the household's) and `alert_events` (what the node said and when).

## The starter dashboard

It fills itself from this node's sensors: three pickers choose a metric, a room and an outside sensor, out of the ones
that reported in the last week.

| panel | what it shows |
|---|---|
| in every room and yard, hourly | the household's own sensors, the hourly mean of the raw readings, mean, max and 95th percentile beside each |
| a room by hour of day, one column per day | each cell is one hour's mean. A habit shows as a row, a bad day as a column |
| a room against outside | one dot per hour. Above the diagonal the room is worse than outside, so the source is indoors |
| when each sensor was heard | every one of the household's sensors, every three hours, red where it sent nothing. A sensor that never spoke is a red row |
| outside | every outdoor sensor the node reads, the neighbours' too, and the model, dashed |
| radios | how busy each Meshtastic radio's channel is. Empty on a node with no radio |

The node's alert events are drawn on the time charts, from when each opened to when it cleared, marked `sent` or
`held`.

The starter ships with the node and is replaced on every update, so Grafana will not save changes over it. Save as
makes a copy that is yours; edit that one.

## The weekly report

There is a second dashboard in the PLANETAI folder, "Weekly sensor report", and the same one in Bahasa Indonesia,
"Laporan mingguan sensor". A reader of the Bali air sensors asked how many days of a week were bad, how often the
sensor went over a high value on those days, and whether the place is stable or getting better. The report answers
that for any metric and any sensors the node holds.

There are four pickers at the top: the metric, one or more sensors, and two lines.

| picker | starts at | what it sets |
|---|---|---|
| Bad day over (24 h mean) | 15 | A day is bad when its 24-hour mean is over this. 15 µg/m³ is the WHO guideline for PM2.5. |
| High over (1 h mean) | 55 | The sensor went over the high each time an hourly mean rose past this. 55 µg/m³ is where Indonesia's air index (ISPU) turns unhealthy. |

Both lines start where they do for PM2.5. For any other metric, type your own.

| panel | what it shows |
|---|---|
| Week by week | one row per sensor and week: the bad days, the week against the one before, the times and the hours over the high, the highest hour, the weekly median, all sensors' median and the days counted |
| Bad days in each week | the count week after week, one line per sensor |
| Daily median, beside all sensors' median | each picked sensor's median for the day, and the median of every outdoor sensor the node reads, dashed |
| The bad days | every day over the line, with its 24-hour mean, its median, the times and hours over the high, the highest hour and when it was |
| Hour by hour | the hourly means, with the high line across them |

How it counts:

- Everything is counted from the node's hourly means (`readings_1h`). A sensor that sends every minute and one that
  sends every quarter of an hour are counted the same way.
- A day counts when the sensor was heard for 18 of its 24 hours. A thinner day whose mean is over the line is still
  listed among the bad days, with its hours in red, and the week does not count it.
- Going over the high counts once for each episode, on the day it began. Three hours in a row over the line is one
  time and three hours.
- "All sensors" takes each outdoor sensor's own median first and then the median across them, so a sensor that
  sends more often does not weigh more. Rooms and models are left out.
- A week is `improving` when it had fewer bad days than the week before and `worse` when it had more. When the bad
  days are equal the weekly median decides, if it moved by more than a tenth, and otherwise the week is `stable`. Both
  weeks need five counted days, or the row says `too few days`.

The report does not say why. A week can be better because less was burned, or because wind and rain carried the smoke
away, and these numbers cannot tell the two apart. The readings are as each sensor sent them and none is calibrated
against a reference station, so compare a sensor with its own earlier weeks before you compare it with its neighbours.

The address carries the pickers and the dates, so a copied link opens the same report, and `&kiosk` at the end of it
hides Grafana's menus. The link at the top switches language and keeps what you picked.

Like the starter, the two reports are replaced on every update, so Save as before you change one. Both files are
written by `tools/gen_grafana_report.py`, and another language is one more column of words there.

### The same report on the node's page

Data › Report on the node's own page draws this report for anyone who can open the node, with no Grafana and nothing
to sign in to ([Data](dashboard.md#data)). It runs the same queries, written once in `app/weekly.py`, so the two
always count alike. A screen other than the node's own machine reads it once `SHARE_LEVEL` is `open` (Set up ›
Sharing). Without the token the page offers the outdoor sensors only, and the rooms stay out of it.

The page draws more than Grafana does: the days in Indonesia's air index colours, a PDF of the week and images to
post. [Data](dashboard.md#data) says what each part shows. The colours and counts come from the node, so the page and
this dashboard still agree on every number.

## What Grafana will not tell you

### The forecast is stored in the future

The forecast pack writes each value at the hour it is for, days ahead, as
`fc_*` metrics with `fc_lead_hours` beside them. A query with no upper bound, or a time picker set past now, draws
tomorrow's forecast as if it had been measured. End every query on `readings` or `readings_1h` with `ts <= now()`
(`bucket <= now()` on `readings_1h`). The starter does.

### A silence is drawn as a line

Grafana joins the points it has. When a sensor sends nothing for seven hours there
are no rows for those hours, so the line runs straight across them. In a time series panel, set *Connect null values*
to *Never* and *Insert nulls* to a gap you care about (the starter uses three hours). The heatmap and the
when-heard panel show silence without being told.

### Hour of day is the session's

Grafana's own axis follows `NODE_TZ`. Inside SQL, use
`ts AT TIME ZONE current_setting('TimeZone')`, which is `NODE_TZ` for `planetai_grafana`. The same query pasted into
`psql` runs in UTC, eight hours off in Bali, unless you `SET TIME ZONE` first.

### Some rows are models

`sensors.kind` says what a row is: `sensor` measured it, `model` estimated it (the CAMS
point, Open-Meteo, the forecast), `map` counted it from OpenStreetMap or satellite. `sensors.local` is true for the
household's own; the rest are other people's stations the node reads.

### `$__timeGroup` is a number

For PostgreSQL it gives epoch seconds, not a timestamp, so it will not join a
`generate_series` of times. Wrap it in `to_timestamp(...)`, or build the bucket yourself as the when-heard panel does.

### Names change

A room renamed in Set up is renamed in `sensors`. An alert written before that keeps the old name
in its text.

Next, [Schema](schema.md): every table and view a panel can be built from.
