# Predict
<!-- checked: v0.92.0 -->

The `predict` pack forecasts today and tomorrow, hour by hour, for the node's own sensors, with a general time-series
model that runs in a container on the same machine. Every night it also checks what it forecast against what the
sensors then measured, and against a plain guess, the last measured day repeated. A day's forecast is shown only while
the model is closer than that guess.

The model is a published one and the node uses it as it comes, with the weights it was released with. The section on
the page says so on its first line, "general model, not adapted here". The pack is off until you pull a model, and a
node without one loses nothing.

## What it forecasts

Each night, at the first poll after 00:10 in the node's time zone (`NODE_TZ`), the node asks the model for the next 48
hours of each of its own series. Day one is today, from local midnight, and day two is tomorrow. A series is one metric
of one sensor, the PM2.5 of an outdoor kit for example, and it is forecast when:

- the sensor is the household's own (`local`) and not a peer's;
- the metric's channel role is `ambient` and it is not an `fc_` metric, so a forecast the node fetched is never
  forecast again;
- it has hourly means for at least 7 days before the day forecast, with 90% of the hours measured over the last 14
  days, or over all of them while it is younger than that;
- at least one of the 6 hours before local midnight is measured, so a sensor that has gone quiet is not forecast from
  its last value held flat.

Indoor series are forecast too, and only a screen with the token sees them.

The first run is at the node's next poll after `planetai models pull`, whatever the hour. In it the node also
forecasts each of the previous 28 days, from what it knew before each one, oldest first, so the score starts with up
to 28 days behind it. The poll that does this also reads the household's sensors, so the pack works for at most a
minute at a time and the next poll carries on where it stopped. Each day is stored whole or not at all. A day in
those 28 that has no forecast yet is filled the same way later. The model reads up to 4,096 hours of a series before
the day it forecasts, with every gap filled by a straight line between the hours either side, and it gets only those
numbers, without the sensor's name, its room, the place or the time.

For each hour the model gives a middle value and an 80% band around it. The page uses the middle value and the node
keeps the band. Forecasts are kept for 35 days. If the container does not answer or the run fails, the node tries again
at most once an hour until today's forecast is stored.

## Turn it on

```bash
planetai models
```

lists the models the node knows, from `packs/predict/models.json`, with their size, licence and which one runs. While
the models container is on it also says whether each one's weights are on this machine, and while it is off the list
says so. There are two:

| model | size | licence |
|---|---|---|
| `amazon/chronos-2` | 456 MB | Apache-2.0 |
| `amazon/chronos-bolt-tiny` | 33 MB | Apache-2.0 |

```bash
planetai models pull amazon/chronos-2
```

says the model's size and licence, says that the models image is built first, carries PyTorch and is several times
larger than the weights, and asks before it does anything (`--yes` skips the question). Then it builds the models
image, which took 5 minutes and came to 1.76 GB on node #1, downloads the weights once from
huggingface.co at the revision the catalogue pins, and checks them against the catalogue's sha256. Only after that it
sets `PREDICT_MODEL` in `.env`, adds `models` to `COMPOSE_PROFILES` and, if `PACKS_ENABLED` lists packs, `predict` to
it, starts the container and restarts the node. If the build or the download fails, `.env` is left as it was. It ends
with "amazon/chronos-2 is on this machine. predict starts at the node's next poll, and after that runs each night
after 00:10."

Nothing is downloaded before you run that command, and it is the only time a node reaches huggingface.co for a model.
After it the container runs with `HF_HUB_OFFLINE=1` and asks nothing of the internet. `planetai update` rebuilds the
models image only on a node that has the `models` profile.

Set up › Model shows the model as a read-only row, Forecast model. The command is the way to change it, because the
container follows `.env`. While the profile is on, `planetai doctor` has a line for it, "forecast
model amazon/chronos-2 running".

```bash
planetai models rm amazon/chronos-2
```

deletes the weights, from the shared folder the download keeps them in too. If that was the model running, `PREDICT_MODEL` is blanked, `models` leaves `COMPOSE_PROFILES`,
the container stops and the node restarts with `predict` off, so `planetai doctor` no longer has a line for it and an
update no longer builds the image. The forecasts already written stay.

On a machine short of memory, take `amazon/chronos-bolt-tiny`. In our measurements below it was a little less close
and needed under half the memory.

## Reading it

Data › Models and satellite has a second section, "Its own readings, forecast", under the table of models. Its first
line names the model, then "general model, not adapted here". Under it, one row per series:

| column | what it says |
|---|---|
| series | the sensor and the metric, with ", inside" for an indoor one |
| today | the lowest and highest hourly value the model expects today, or a dash and why it is not shown |
| tomorrow | the same for tomorrow |
| off by, last N days | the model's mean absolute error over the N days scored (the last 28 at most), today's and then tomorrow's, in the series' unit, or a dash while no day is scored |
| yesterday repeated | the same error for the last measured day repeated. A narrow screen hides it |

A day is shown only when today's forecast is stored, at least 7 days are scored and the model's error is strictly
below that of yesterday repeated. Otherwise the cell says "yesterday is closer" when the model lost, "too young:
4 of 7 days" while that day has fewer than 7 scored, "too many hours missing" for a series old enough to forecast that
has too many gaps or has stopped, and "not made yet today" before today's run has stored it. Today and tomorrow are
judged apart, so a row can show one and not the other. Yesterday repeated is the 24 hours before local midnight, hour
by hour, used for both days, and an hour counts only when the forecast, the measurement and yesterday's value are all
there. A day counts as scored with at least 12 such hours. The scores are worked out each time the page asks, from the
stored forecasts and the hourly means, and never stored.

What the node expects of its own rooms is the household's, so the section needs a node token. Without one it says so
and where to unlock it. While no model is set, as on every node until `planetai models pull`, it says "This node
does not forecast its own readings." and gives the command, and with a model set and none ready in the container it
says "No model is pulled."

Next days on Now gets one line from it, Modelled here, for tomorrow's PM2.5 outside, such as "PM2.5 outside: 12–18
µg/m³ (modelled here, off by 3 on average over 28 days)". The error is tomorrow's mean absolute error over the days
scored. It names no sensor. It reads the outdoor PM2.5 series with the most hours, and it is there
only while tomorrow is shown for that series in the section above.

`GET /predict` answers what the section draws, and [the API](api.md) has the route.

## What it never does

A forecast is kept in its own table, `predictions`, and is never written as a reading. It sends no alert and fills no
Index cell, and ρ never moves with it. The daily export and the report bundle leave it out, and a parent node gets
nothing of it. No agent tool reads it, and pack rules and Grafana cannot, because the table is closed to
`planetai_ro`.

The line on Now is served to whoever can see Next days on this node, and it carries only tomorrow's range for PM2.5
outside and its error.

## What we measured

On 21 November 2026 we ran both models on node #1's own hourly series, four of them, PM2.5 and temperature from an
outdoor kit and one indoor room, about 1,900 hours each. Each was forecast 24 hours ahead from 28 different days.

- Chronos-2 with no training was 16 to 29% closer than the same hour yesterday, in mean absolute error, and closer on
  22 to 25 of the 28 days. Chronos-Bolt tiny was 9 to 27% closer.
- On the second day ahead Chronos-2 was 16 to 31% closer than the last measured day repeated.
- Its 80% band held the measurement 68 to 86% of the time, so on some series it is a little narrow.
- One night's forecasts for 45 series took 1.0 second and 1.5 GB of memory with Chronos-2, and 0.1 second and 0.7 GB
  with Bolt tiny, on a laptop's CPU.

On 23 November we ran it on node #1 itself, a Mac mini, with Chronos-2. It forecast 34 series and filled the 28 days
before in about 40 minutes, a minute at each poll, and the container never used more than 583 MiB of memory. Over
those 28 days its error on the outdoor kit's PM2.5 for today was 2.8 µg/m³, where yesterday repeated was off by 3.6.

We also tried adapting Chronos-2 to node #1, on its own 37 series, and tested the result on 28 days it had not seen.
Against the same model with no training it came out at −0.4% with one method and +0.6% with another. That is no gain,
and one of the runs needed 6.9 GB of memory. So the node runs the general model as it is published, and adapting is left out.

We have not measured an old computer, more than one season or more than one node.

The commands are on [the CLI](cli.md) page, and the rest of Data is on [the dashboard](dashboard.md) page.
