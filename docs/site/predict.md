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
- the metric's channel role is `ambient`, so a forecast the node fetched (an `fc_` metric) is never forecast again;
- it has hourly means for at least 7 days before the day forecast, with 90% of the hours measured over the last 14
  days, or over all of them while it is younger than that.

Indoor series are forecast too, and only a screen with the token sees them.

On its first night the node also forecasts each of the previous 28 days, from what it knew before each one, so the
score starts with up to 28 days behind it. A day in those 28 that has no forecast yet is filled the same way on any
later night. The model reads up to 4,096 hours of a series before the day it forecasts, with a short gap filled by a
straight line between the hours either side, and it gets only those numbers, without the sensor's name, its room,
the place or the time.

For each hour the model gives a middle value and an 80% band around it. The page uses the middle value and the node
keeps the band. Forecasts are kept for 35 days. If the container does not answer or the run fails, the node tries again
at most once an hour until today's forecast is stored.

## Turn it on

```bash
planetai models
```

lists the models the node knows, from `packs/predict/models.json`, with their size, licence, whether the weights are
on this machine and which one runs. There are two:

| model | size | licence |
|---|---|---|
| `amazon/chronos-2` | 456 MB | Apache-2.0 |
| `amazon/chronos-bolt-tiny` | 33 MB | Apache-2.0 |

```bash
planetai models pull amazon/chronos-2
```

says the model's size and licence and asks before it does anything (`--yes` skips the question). Then it builds the
models image, which carries PyTorch for the CPU and takes a few minutes the first time, downloads the weights once from
huggingface.co at the revision the catalogue pins, and checks them against the catalogue's sha256. Only after that it
sets `PREDICT_MODEL` in `.env`, adds `models` to `COMPOSE_PROFILES` and, if `PACKS_ENABLED` lists packs, `predict` to
it, starts the container and restarts the node. If the build or the download fails, `.env` is left as it was. It ends
with "amazon/chronos-2 is on this machine. predict forecasts this node's own series from tonight (00:10)."

Nothing is downloaded before you run that command, and it is the only time a node reaches huggingface.co for a model.
After it the container runs with `HF_HUB_OFFLINE=1` and asks nothing of the internet. `planetai update` rebuilds the
models image only on a node that has the `models` profile.

Set up › Model shows the model as a read-only row, Forecast model. The command is the way to change it, because the
container follows `.env`. While the profile is on, `planetai doctor` has a line for it, "forecast
model amazon/chronos-2 running".

```bash
planetai models rm amazon/chronos-2
```

deletes the weights. If that was the model running, `PREDICT_MODEL` is blanked, the container stops and the node
restarts with `predict` off. The forecasts already written stay.

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
| off by, last N days | the model's mean absolute error over the N days scored, today's and then tomorrow's, in the series' unit |
| yesterday repeated | the same error for the last measured day repeated. A narrow screen hides it |

A day is shown only when at least 7 days are scored and the model's error is strictly below that of yesterday
repeated. Otherwise the cell says "yesterday is closer", or, while the series is young, how far it has got, "too
young: 9 of 14 days". Today and tomorrow are judged apart, so a row can show one and not the other. Yesterday repeated
is the 24 hours before local midnight, hour by hour, used for both days, and an hour counts only when the forecast,
the measurement and yesterday's value are all there. The scores are worked out each time the page asks, from the
stored forecasts and the hourly means, and never stored.

What the node expects of its own rooms is the household's, so the section needs a node token. Without one it says so
and where to unlock it. With no model pulled it says "This node does not forecast its own readings." and gives the
command.

Next days on Now gets one line from it, Modelled here, for tomorrow's PM2.5 outside, such as "PM2.5 outside: 12–18
µg/m³ (modelled here)". It names no sensor. It reads the outdoor PM2.5 series with the most hours, and it is there
only while tomorrow is shown for that series in the section above.

`GET /predict` answers what the section draws, and [the API](api.md) has the route.

## What it never does

A forecast is kept in its own table, `predictions`, and is never written as a reading. It sends no alert and fills no
Index cell, and ρ never moves with it. It is not in the daily export, in what a parent node gets or in the report
bundle, no agent tool reads it, and pack rules and Grafana cannot read it, because the table is closed to
`planetai_ro`.

The one line in Next days is the exception. It is served with Next days, to whoever can see Now on this node, and it
carries tomorrow's range for PM2.5 outside and nothing else.

## What we measured

On 21 November 2026 we ran both models on node #1's own hourly series, four of them, PM2.5 and temperature from an
outdoor kit and one indoor room, about 1,900 hours each. Each was forecast 24 hours ahead from 28 different days.

- Chronos-2 with no training was 16 to 29% closer than the same hour yesterday, in mean absolute error, and closer on
  22 to 25 of the 28 days. Chronos-Bolt tiny was 9 to 27% closer.
- On the second day ahead Chronos-2 was 16 to 31% closer than the last measured day repeated.
- Its 80% band held the measurement 68 to 86% of the time, so on some series it is a little narrow.
- One night's forecasts for 45 series took 1.0 second and 1.5 GB of memory with Chronos-2, and 0.1 second and 0.7 GB
  with Bolt tiny, on a laptop's CPU.

We also tried adapting Chronos-2 to node #1, on its own 37 series, and tested the result on 28 days it had not seen.
Against the same model with no training it came out at −0.4% with one method and +0.6% with another. That is no gain,
and one of the runs needed 6.9 GB of memory. So the node runs the general model as it is published, and adapting is left out.
More seasons of data, or the data of several nodes together at a community or city node, may change that, and we have
not shown it.

We have not measured an old computer, more than one season or more than one node.

The commands are on [the CLI](cli.md) page, and the rest of Data is on [the dashboard](dashboard.md) page.
