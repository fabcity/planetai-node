# Alerts

An alert is what a rule produced: one row in `alerts`, three paragraphs of text, and a level that decides
whether it interrupts anyone. Between reports the node speaks only when something needs doing.

## From a rule to a message

Every 60 seconds the rules loop runs each loaded rule — the two domain-blind ones in `config/rules.yml`
and every pack's `rules.yml` — as the read-only database role `planetai_ro`, which can read every table but
`settings` and can write nothing. Every row a rule's SQL returns is a candidate alert for the `sensor_id` in
that row (or for `node` if the row has none). For each candidate:

1. **Cooldown.** If an `alerts` row for the same rule and sensor is newer than `cooldown_minutes` (default 60),
   nothing happens.
2. **Message.** The template for `ALERT_LOCALE` (falling back to English) is filled with the row's columns by
   Python's `str.format`; a `None` renders as `—`; a template that does not fit its row falls back to the raw
   text rather than failing.
3. **Record.** The alert is inserted into `alerts` and published to Home Assistant whatever its level. It is
   on the dashboard from here on.
4. **Send.** It goes out through `notify()` only if its level reaches `ALERT_LEVEL` and it is not held by
   quiet hours.

The rule contract — the fields, the variables the SQL may read, the lint — is on the [Packs](packs.md) page.

## Levels

| level | meaning | default behaviour |
|---|---|---|
| `act` | something needs doing | always sent, even in quiet hours; also goes to the LoRa mesh and Reticulum |
| `warn` | something changed | sent only if `ALERT_LEVEL` is `warn` or `info` |
| `info` | everything else | sent only if `ALERT_LEVEL` is `info`; otherwise waits for the next report |

`ALERT_LEVEL` (default `act`) is the floor for interrupting a person. `planetai report level warn` lowers it
without a restart. Below the floor an alert is still recorded, still drawn, and still in the next
[report](report.md).

## Quiet hours

`QUIET_HOURS=1` (default) holds everything but `act` between `QUIET_FROM` (22) and `QUIET_TO` (6), local
time from `NODE_TZ`, wrapping midnight when the start is after the end. A report due inside quiet hours is
written and stored with `held_quiet` and not sent; the next one to go out covers every hour that was held.

## What an alert says

Three paragraphs separated by blank lines: what is happening, what it means for the people in the house,
what to do — the third opening with 👉. From the air pack:

```
🏠😷 The air inside at Kitchen is unhealthy right now.

Fine particles are high enough to bother people with asthma, children and older people, and to tire
anyone over a few hours.

👉 Run the purifier if you have one. Before opening a window, check whether outside is any better;
often it is not.
```

An act alert says what to do in one sentence and asks for nothing back: since v0.39 no id is appended,
because a number a household is expected to quote back was a chore. The API's test alert (`POST /test-alert`) is
the exception: it ends with `👉 Reply /act N to show me how you close the loop.` when the bot runs, or
`👉 In the terminal, planetai act N records that you closed the loop.` when it does not; `planetai
test-alert` prints the id in the terminal instead. The rules name the threshold's
source in their README, and the sentences carry the numbers the SQL returned — a rule may not print a number
its SQL did not compute.

## Languages

`ALERT_LOCALE` is `en`, `id` or `es`. The shipped rules carry English and Bahasa Indonesia; `nearby`'s two
alerts and the `posidonia` pack also carry Spanish; the report carries all three; the issue sentences on the
dashboard carry all three. A language a rule does not have falls back to English. The presets set `id` for
Bali and `es` for Menorca.

## Where alerts go

`notify(level, text)` fans out. Telegram receives every alert that reaches it, prefixed with the level's
icon (ℹ️ ⚠️ 🔴). An `act` alert also goes to the LoRa mesh (first line only — a LoRa frame is about 200
bytes) and to the Reticulum bridge for LXMF delivery. Home Assistant receives every alert, sent or not, as
the state of one text entity. The configuration of each is on [Channels](channels.md).

## The two rules the core knows

The core names no metric. Its two rules in `config/rules.yml` are about the instruments:

| rule | level | cooldown | fires when |
|---|---|---|---|
| `sensor_silent` | warn | 720 min | a local sensor has produced no new value for more than 90 minutes |
| `daily_pulse` | info | 100000 min | once, on an old node; superseded by the report and kept so existing nodes lose nothing until they update |

Everything else — `air-quality/indoor_pm25_high`, `heat/heat_danger`, `nearby/only_here` — is a pack's, and
is listed with its condition and cooldown on [Packs that ship](packs-reference.md).

## Closing the loop

An alert's `acted_at` is null until someone acts. The person records it — the dashboard's button, `planetai
act <id> [note]`, `/act <id> note` to the bot, `act <id>` from Sideband over LXMF, or an agent's `act` tool —
and that writes a row in `actions` with the stage `acted` (or `acknowledged`), the actor and the note. This
is the one measurement the node cannot make itself, and it is how [ρ](rho.md) exists. An agent never invents
one: it asks the person and records their words.

## Conditions that are not events

A heat alert is a condition that holds for hours; the ratio test between inside and outside cannot tell a
stopped stove from an opened door. In this version every rule is an event with a cooldown; there is no
`recovery` block and the schema has no notion of an alert clearing, only of cooldowns. The dashboard marks
an open act-level ask as *current* only while its condition still holds — the room over the line, or the
alert under two hours old — and otherwise says the reading came back on its own and the ask is still open.
Turning conditions into their own kind of rule, with a reminder at 30 minutes and at two hours and then
silence until the next report, is proposed in `docs/HANDOFF_reports.md` and not built.

## Reading them

`GET /alerts?limit=50` lists the most recent with `id, ts, rule_id, sensor_id, level, text, acted_at`.
`planetai status` shows the last few; the dashboard's *What this node has asked* section draws them with
their state; the report's fourth part says what happened after this window's act alerts.
