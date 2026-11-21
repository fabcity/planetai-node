# predict

A general forecasting model, not adapted here, reads this node's own hourly series, outdoors and in, and forecasts the
next 48 hours. Each night, a little after local midnight, it writes day one and day two, and later scores them against
what the sensors measured. A day's forecast is shown in Data › Models and satellite only once at least 7 days are scored
and the model's mean absolute error is strictly below the repeated last day's. Next days on Now gets one line from it,
tomorrow's PM2.5 outside with its error, while that day is shown.

**What it never does.** It writes nothing to `readings` or `observations`, sends no alert, moves no rule, fills no
Index cell and sends nothing off the node apart from that one line. Both tables are revoked from `planetai_ro` and are
in no export. Only own sensors count (not peers, not `fc_%` forecast channels), and only their ambient metrics. There is
no training and no adaptation: the weights are the published ones.

**What it needs.** The models container and weights fetched once with `planetai models pull`, the only step that
reaches huggingface.co. `models.json` pins each model's revision and the sha256 of its weights.

**The 21 November figures.** `amazon/chronos-2` is 456 MB, `amazon/chronos-bolt-tiny` 33 MB, both Apache-2.0. A series
needs 7 days of history to get a context, 14 days with 90% of the hours measured, and its first forecast can be shown
once 7 days are scored, so about two weeks after switching on.

**Off by default.** On once `PREDICT_MODEL` names a model, which `planetai models pull <name>` sets in `.env` after the
weights are here. Set up shows it and does not edit it.
