# Alerts

An alert is the node asking a person to do something. This is the Act stage, which the architecture describes
as the one that "turns an observation into a human decision", and it is "the only place ρ can be measured".
With rules running, the node can interrupt a household with one plain message when a reading crosses a line,
then record what somebody did about it. Every answer is a row in `actions`, and [ρ](rho.md) is counted from those
rows, pooled with the answers a node's children report as timestamps.

## From a rule to a message

Every 60 seconds the rules loop runs each loaded rule (the two domain-blind ones in `config/rules.yml` and every
pack's `rules.yml`) as the read-only database role `planetai_ro`, which can read every table but `settings` and
can write nothing. Every row a rule's SQL returns is a candidate alert for the `sensor_id` in that row, or for
`node` if the row has none. For each candidate:

1. **Cooldown.** If an `alerts` row for the same rule and sensor is newer than `cooldown_minutes` (default 60),
   nothing happens.
2. **Message.** The template for `ALERT_LOCALE` (falling back to English) is filled with the row's columns by
   Python's `str.format`. A `None` renders as `—`. A template that does not fit its row falls back to the raw
   text rather than failing.
3. **Record.** The alert is inserted into `alerts` and published to Home Assistant whatever its level. It is on
   the dashboard from here on.
4. **Send.** It goes out through `notify()` only if its level reaches `ALERT_LEVEL` and it is not held by quiet
   hours.

## The rule contract

A rule is a few keys in a `rules.yml`. `app/packs.py` loads them, namespaces a pack's ids as `<pack>/<id>`, and
`run_rules` in `app/main.py` runs them. `tools/check_rules.py` checks every one against the schema in
`init.sql` without a database.

| key | what it does |
|---|---|
| `id` | the rule's name; a pack's becomes `<pack>/<id>` |
| `level` | `act`, `warn` or `info` (default `info`) |
| `cooldown_minutes` | how long the same rule stays quiet on the same sensor (default 60). Over a fortnight is refused unless `long_cooldown_ok: true` |
| `sql` | the condition. Every row it returns is a candidate alert; its columns are what the message may print |
| `message` | `{en, id, es}`, three paragraphs each. Every placeholder must be a column the SQL returns |
| `contributes: report` | instead of a message: the rule is never sent, and its first row lands in the report's bundle |
| `watch: {metric, over}` | since v0.72: the indicator and the line this rule is about, so `GET /effect` can say how long an act took to work. `over` must be a number the SQL uses |

Every shipped rule with a message carries all three languages. The full contract, with the variables a rule's
SQL may read, is on the [Packs](packs.md) page.

## Levels

| level | meaning | default behaviour |
|---|---|---|
| `act` | something needs doing | always sent, even in quiet hours; also goes to the LoRa mesh and Reticulum |
| `warn` | something changed | sent only if `ALERT_LEVEL` is `warn` or `info` |
| `info` | everything else | sent only if `ALERT_LEVEL` is `info`; otherwise waits for the next report |

`ALERT_LEVEL` (default `act`) is the floor for interrupting a person. `planetai report level warn` lowers it
without a restart. Below the floor an alert is still recorded, still drawn on the dashboard, and still in the
bundle the next [report](report.md) is written from.

## Quiet hours

`QUIET_HOURS=1` (default) holds everything but `act` between `QUIET_FROM` (22) and `QUIET_TO` (6), local
time from `NODE_TZ`, wrapping midnight when the start is after the end. A report due inside quiet hours is
written and stored with `held_quiet` and not sent; the next one to go out covers every hour that was held.

## What an alert says

Three paragraphs separated by blank lines: what is happening, what it means for the people in the house, and
what to do, the third opening with 👉. From the air pack:

```
🏠😷 The air inside at Kitchen is unhealthy right now.

Fine particles are high enough to bother people with asthma, children and older people, and to tire
anyone over a few hours.

👉 Run the purifier if you have one. Before opening a window, check whether outside is any better;
often it is not.
```

The 👉 paragraph is the rule author's recommendation. Since v0.72 the dashboard also draws it on its own under
Decide, in *What to do about it*, as "what this node suggests". A rule without one gets a line saying so, and the
page does not invent advice.

An act alert says what to do and asks for nothing back: since v0.39 no id is appended, because a number a
household is expected to quote back was a chore. The API's test alert (`POST /test-alert`) is the exception. It
ends with `👉 Reply /act N to show me how you close the loop.` when the bot runs, or `👉 In the terminal, planetai
act N records that you closed the loop.` when it does not; `planetai test-alert` prints the id in the terminal
instead. The rules name the threshold's source in their README, and the sentences carry the numbers the SQL
returned. A rule may not print a number its SQL did not compute.

## Languages

`ALERT_LOCALE` is `en`, `id` or `es`. Since v0.63 every rule with a message carries all three, the two core rules
and all 29 messaged pack rules. The report, the test alert and the Telegram bot's own replies follow the same
setting; the bot's few fixed lines fall back to English for `id`. A language a template lacks falls back to
English. The presets set `id` for Bali, `es` for Menorca, Barcelona and Santiago, and `en` for Boston and Delhi.

## Where alerts go

`notify(level, text)` sends to Telegram every alert that reaches it, prefixed with the level's icon (ℹ️ ⚠️ 🔴).
An `act` alert also goes to the LoRa mesh (first line only; a LoRa frame is about 200 bytes) and to the Reticulum
bridge for LXMF delivery. Home Assistant is a separate call, `ha_alert()`, made for every alert whether it was
sent or not; it becomes the state of one text entity. The set-up of each is on [Channels](channels.md).

## The two rules the core knows

The core names no metric. Its two rules in `config/rules.yml` are about the instruments:

| rule | level | cooldown | fires when |
|---|---|---|---|
| `sensor_silent` | warn | 720 min | a local sensor's newest reading is more than 90 minutes old (`silent_minutes > 90`, a timestamp; the `trust` pack's `channel_dead` checks values) |
| `daily_pulse` | info | 100000 min | once, on an old node; superseded by the report and kept so existing nodes lose nothing until they update |

Everything else (`air-quality/indoor_pm25_high`, `heat/heat_danger`, `nearby/only_here`) is a pack's, and is
listed with its condition and cooldown on [Packs that ship](packs-reference.md).

## Answering an alert

An alert's `acted_at` is null until somebody answers it. An answer is a row in `actions` with a stage, an actor
(at most 80 characters) and a note (at most 500). There are five stages:

| stage | what it records | written by | counts toward |
|---|---|---|---|
| `acknowledged` | somebody saw it | `POST /actions` | ρ, and the funnel |
| `decided` | what somebody said would be done | the dashboard's Decide form, `POST /actions` | nothing |
| `acted` | somebody did the thing | the dashboard's *I did this*, `planetai act`, Telegram `/act`, the MCP `act` tool, `act <id>` over LXMF, `POST /actions` | ρ, the funnel, and closes the ask |
| `measured` | the condition stopped | derived by the node, never posted: an `acted` ask followed by 48 hours (`MEASURED_WINDOW_MIN`, 2880) with no new alert from the same live rule on the same sensor | the funnel; the ask was already closed by its `acted` row |
| `settings` | a setting was changed; an audit row with no alert | the node, on `PUT /settings` | nothing |

`POST /actions` accepts `acknowledged`, `acted` and `decided` and refuses the rest with a 400.

**A decision moves nothing.** It is not in ρ, not a stage of the funnel, and closes no ask; the node keeps
watching. What it changes is the record: a household that looked, decided and did not manage it no longer leaves
the same trace as one that never looked. With `DECISION_REQUIRED=1` (Set up → Node, off by default), `POST
/actions` answers an `acted` with no earlier `decided` row for the same alert with a 409, whichever way the act
came in. Turn it on only where everybody answering has a screen to decide on: the radio, the terminal and the
bot have none.

## Who has to use their own words

ρ is built out of these rows, so the note is supposed to be what the person said. Not every way in enforces it:

| way in | without a note |
|---|---|
| the dashboard's *I did this* and Decide forms | will not post; needs `ACT_TOKEN` or `ADMIN_TOKEN` from Set up |
| Telegram `/act <id> <words>` | `/act 23` alone is answered with "What did you do about #23?" and nothing is written |
| the MCP `act` tool | refuses an empty note and placeholders such as `acted`, `done` or `ok` |
| `planetai act <id> [note]` | records the note `acted` |
| `act <id>` over LXMF | records the note `acted (via reticulum)` |
| `POST /actions` directly | records whatever it is given |

An agent is expected to ask the person and record their answer, and the MCP tool's refusal is what holds an
agent to it.

## Conditions that are not events

A heat alert is a condition that holds for hours; the ratio test between inside and outside cannot tell a
stopped stove from an opened door. In this version every rule is an event with a cooldown; there is no
`recovery` block and the schema has no notion of an alert clearing, only of cooldowns. The dashboard marks
an open act-level ask as *current* only while its condition still holds (the room over the line, or the
alert under two hours old), and otherwise says the reading came back on its own and the ask is still open.
Turning conditions into their own kind of rule, with a reminder at 30 minutes and at two hours and then
silence until the next report, is proposed in `docs/HANDOFF_reports.md` and not built. What the node does
have is the derived `measured` stage above and `GET /effect`, which counts per rule how many acts were
followed by the condition stopping; neither is a `recovery` block.

## Reading them

`GET /alerts?limit=50` lists the most recent with `id, ts, rule_id, sensor_id, level, text, acted_at`, and is
where an alert's id comes from. `GET /actions` lists every answer with its stage, actor and note, and answers
only a token or the machine itself, because a note is a household's own words about its own house. `planetai
status` shows the last three alerts and ρ. On the dashboard, *What this node has asked* draws the asks with
their state and *What was decided, and by whom* is the ledger of answers. The report's fourth part says what
happened after the window's act alerts.

## Where this leads

The node can now ask. Next, choose where the asking reaches people: [Channels](channels.md) sets up Telegram,
the LoRa mesh, Reticulum and Home Assistant. Then [ρ](rho.md) is how the node measures whether the asking
worked.
