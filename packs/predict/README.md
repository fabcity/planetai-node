# predict

A general forecasting model, not adapted here, reads this node's own hourly outdoor series and forecasts the next
48 hours. Each night, a little after local midnight, it writes day one and day two, and later scores them against what
the sensors measured. A day's forecast is shown on Next days only once at least 7 origins are scored and the model's
mean absolute error is strictly below the repeated last day's.

**What it never does.** It writes nothing to `readings` or `observations`, sends no alert, moves no rule, fills no
Index cell and sends nothing off the node. Both tables are revoked from `planetai_ro` and are in no export. Only own
sensors count (not peers, not `fc_%` forecast channels), and only their ambient metric. There is no training and no
adaptation: the weights are the published ones.

**What it needs.** A model container (`MODELS_URL`) and weights fetched once with the planetai command's `models pull` step,
the only step that reaches huggingface.co. `models.json` pins each model's revision and the sha256 of its weights.

**The 21 November figures.** `amazon/chronos-2` is 456 MB, `amazon/chronos-bolt-tiny` 33 MB, both Apache-2.0. A series
needs 7 days of history to get a context, 14 days with 90% of the hours measured, and its first forecast can be shown
once 7 origins are scored, so about two weeks after switching on.

**Off by default.** On once `PREDICT_MODEL` is set: `PREDICT_MODEL=amazon/chronos-bolt-tiny`.
