# Deciding, and being able to tell whether it worked

*Proposed, 22 September 2026, from Tomas: "it is not specifying which decisions are made, or by whom.
I think we need to be able to provide insights on the behaviour of the data in the observation layer,
at different scales and dimensions, and then have the option for the node owner to decide something…
creates an action or options of actions that then can be measured depending on when and where they
executed and how impact the readings again."*

**Status: nothing here is built.** This is the document to argue with before any code is written.

The honest headline: about two-thirds of this already exists and is unreachable from the page.

## 1 · What this is not

- **Not a second ρ.** ρ has a specification of its own (`docs/SPEC_rho.md`) and one meaning. Nothing
  here changes what it counts.
- **Not advice.** The node does not tell a household what to do about its air. It can say what
  changed, and it can hold you to what you said you would do.
- **Not a workflow.** No assignees, no due dates, no statuses beyond the three the ledger already
  has. A decision is one sentence and one thing to watch.
- **Not dependent on a model.** The agent container is optional (`profiles: ["agent"]`). Every word
  below works on a node that has never run one.

## 2 · What is already built

Worth being exact about, because it is most of the loop:

| | where | what it does |
|---|---|---|
| the ask | `alerts` | a rule fires and a row exists: `rule_id`, `sensor_id`, `level`, `text` |
| the decision | `POST /actions` | `stage` · `actor` (80 chars) · **`note`, 500 characters in the keeper's own words** |
| the measurement | `app/index.py::_funnel` | **derived, never posted** |
| the hand | MCP `act(alert_id, note, agent)` | what the local model already uses |

`POST /actions` is guarded by `ACT_TOKEN`, deliberately weaker than the admin token, so somebody in
the house can close a loop without being handed the key to `/settings/raw`.

**The measurement is the part worth admiring, and it is already right.** Nothing writes a `measured`
row. `run_rules` re-fires an alert the moment its cooldown expires and the condition still holds, so
an act followed by `MEASURED_WINDOW_MIN` (2,880 minutes — 48 hours) of silence *from the same rule on
the same sensor* is the condition having stopped being true. It is evidence of whether, never of
when, and `latency_minutes.measured` is `null` on purpose. It works retroactively, on every node,
with nobody asked to learn a new habit. **This is already "how it impacts the readings again."**

## 3 · What is missing

Three things, smallest first.

**The page cannot act.** In seven thousand lines of `dashboard.js` the only write is `/settings`. The
page draws a funnel counting acted and measured and offers no way to make either. Every act on node #1
was made over Telegram, MCP or curl. This costs nothing to close: a note field and two buttons on each
open ask in Act, posting to an endpoint that already exists and already takes a note.

**A decision must be a reply to a rule that already fired.** `POST /actions` 404s without a valid
`alert_id`. Somebody who reads Observe, sees something, and decides to do something has no row to
write.

**Nothing proposes options.**

And the framing problem underneath: Observe has fourteen sections. Decide has three — claims, grain,
trust — and all three answer *at what grain may this be said*, not *what is the data doing and what
should I do about it*. The loop is named as four stages and built as one.

## 4 · An insight

An insight is not a number. It is **a number that changed, at a stated grain, against a stated
comparison** — and this page already refuses to draw a number without a comparison (T4 counts the
ones that try). So an insight carries four things or it is not one:

- **the claim** — what moved
- **the grain** — which stop of the dial, or which of the four distances. An insight at resolution 4
  and the same insight at resolution 10 are different claims, and this page is the one thing on the
  network that already knows how to say so.
- **the window** — over what stretch of time
- **what it is measured against** — its own history, the line, or the same variable at another
  distance

Three kinds the node can derive today, from views it already has:

- **against itself.** `stats` carries `mean_15m`, `mean_1h`, `mean_24h` per sensor and metric. The
  short mean pulling away from the long one is the whole of "something is happening now".
- **against the other distances.** The room against the wall outside against the street against the
  model — the stack the lead already draws. A room worse than its own street is a different problem
  from a street worse than its model, and only the comparison says which you have.
- **against the grain.** The flat run `grain` already finds: past some resolution, finer stops stop
  telling you anything new. An insight drawn finer than the flat run begins is precision with no
  information in it, and the page should refuse to offer a decision at a grain it has already proved
  is empty.

The catalogue is open. The four things an insight must carry are not.

## 5 · A decision is a prediction

*Decided 22 September: a decision names what it expects to stop being true.*

This is the only shape in which the node can tell you whether you were right, and the reason is the
measurement in §2: `measured` is derived from **a named rule going quiet on a named sensor**. A
free-text decision about nothing in particular can be recorded and can never be closed, because the
mechanism has nothing to watch.

So a decision is two sentences from a person and one thing for the node to watch:

> *I closed the windows on the north side.*
> *I expect PM2.5 at the wall outside to be under 25 within two days.*

The second sentence is a **watch**, and a watch is an ordinary rule: metric, sensor, comparator,
threshold, window. Note which way round it is written — the watch is the condition the keeper expects
to **stop** being true, because silence is what the funnel reads. "Under 25" and "the watch *at or
above 25* goes quiet" are the same statement, and only one of them is measurable.

**From a template, never from a keeper's SQL.** A rule is SQL over the `stats` view. Nobody is going
to type that, and a form that accepts SQL is a hole even read-only. The node composes the statement
from five values; the keeper picks a metric, a station, a direction and a number.

**The evaluator does not change by one line.** `run_rules` iterates whatever `packs.load_rules()`
returns, and runs each statement through `index.run_ro` **as `planetai_ro`** — SELECT on every table
but settings, no writes. A watch that joins that list is already sandboxed by machinery that exists.

**The cooldown is the window.** Set it to the decision's own window and the watch fires at most once
per window: one message per two days, not noise, and the funnel reads it exactly as it reads every
other act-level alert. It has to be act level, because `_funnel` counts `level='act'` and nothing
else.

### Where a watch lives, and why not in `config/`

`docker-compose.yml` mounts `./config:/app/config:ro`. Read-only, on purpose. A container serving a
page to a household LAN must not be able to rewrite its own rule set on disk, and the only writable
path in the whole service is `./out`, which is for artefacts a pack makes.

So **a watch is a row in Postgres**, and `load_rules()` gains a third source beside core and packs.
The node already has a database; a watch is a record, not a config file.

### A watch is retired, never deleted

`_live_rule_ids()` exists for a reason that bites here. A rule that has been renamed or deleted can
never fire again, so its silence is not evidence of anything — and counting it would turn every
retired rule into a success. The node found three of those on a live database and the funnel's real
number was 5, not 8.

A keeper deleting a watch would therefore **retroactively convert every decision made against it into
a success.** So: `retired_at`, and the derivation keeps ignoring anything not currently live. This is
the single sharpest constraint in this document and it is not negotiable.

## 6 · The decision is the record, and the action may never come

*From Tomas, 22 September: "it is important to record the decision… If there is no act, then it
should be taken as no action, so the process is recorded but does not affect further down, it is as
an action that never happens. But an action coming from a decision and it never happened, it should
show that the decision was made."*

This splits something the ledger currently runs together. `actions` has three stages —
`acknowledged`, `acted`, `measured` — and the *decision* is not among them. Today a decision only
exists as the note attached to an act, so a decision that was made and never carried out leaves no
trace at all: the ask simply stays open, as though nobody had thought about it.

So a decision is its own record, and an act is a separate thing that may or may not follow it:

| | what it means | what it does downstream |
|---|---|---|
| **decided** | somebody thought about this and said what they would do | **nothing** |
| **acted** | it was done | the funnel's `acted`, and the watch starts earning its answer |
| **measured** | the condition stopped being true | derived, as now |

**A decision alone moves nothing.** It does not close an ask, it does not enter ρ, it does not count
as `acted`, and it does not make a cell or a count say anything different. In Tomas's words it is
*an action that never happens* — and the point of recording it is precisely that the node can tell
the difference between a household that never looked and a household that looked, decided, and did
not manage it. Those are opposite facts and today they are the same blank.

**And it stays visible.** A decision with no act is not a failure to be tidied away. Where an ask
shows as open, it shows *what was decided about it and when*, and the page says plainly that the
thing was not done. That is the one place this spec asks the page to be blunt: the honest sentence
is "decided on the 14th, not done", not a quiet omission.

Two consequences worth writing down now:

- **A decision needs no watch.** §5's prediction is what makes an *act* measurable. A decision that
  never becomes an act has nothing to measure and needs nothing, so nothing in §5 gates §6. The
  watch is created when the act is recorded, not when the decision is.
- **The stage goes in the same table, and there is already a precedent for adding one.**
  `actions.stage` is a CHECK constraint that `init.sql:135` drops and re-adds with **four** values —
  `acknowledged`, `acted`, `measured` and `settings`. That fourth one is the node recording its own
  configuration changes: `alert_id` NULL, no ask, counted by nothing. `_funnel` selects the three it
  names and ignores it, which is exactly the treatment `decided` needs. So this is a fifth value by
  the same two lines of migration, and every existing consumer ignores it without being told. What
  must **not** happen is `decided` counting anywhere `acted` counts, which is the whole of §6.

## 7 · At this scale, one person. At the next, consensus

*From Tomas: "at this scale is individual, but as we keep developing the node, it will be collective,
depending on the scale of the decision. If I decide to do something about my street, maybe need to
build consensus with other neighbors."*

Not built, and not designed here — but the shape of §6 has to leave room for it, so:

**A decision carries the scale it is about.** This node already has the vocabulary and uses it for
everything else it says: the four distances (room · wall outside · street · model) and the eleven
grains of the rail. A decision about the room is one person's and needs nobody. A decision about the
street is about ground this node shares with nodes it can already see — §4 of `SPEC_discovery.md`
gives it the list — and one household recording it does not make it true for the street.

So the field exists from the first version and the consensus does not. A decision at room scale is
complete when one person makes it. A decision at street scale is **recorded by whoever made it and
marked as one household's**, and what turns several of those into a decision the street has taken is
the question the collective version answers. It is a real question — who is asked, what counts as
agreement, what a node does when its neighbours disagree, and whether a decision can bind anyone who
did not answer — and none of it should be guessed at while there are two nodes on the network.

What matters now is only that a decision recorded today at street scale is still legible when that
arrives, rather than being an individual decision with a bigger word on it.

## 8 · Options of actions

The agent has the readings, the alerts, the issues and a model, and could offer two or three things a
household might do. It must not be load-bearing:

- the agent container is optional, and a node without one has to be able to decide;
- alerts deliberately do not pass through the model — *"the node sends them; the model answers
  questions about them"* (`app/agent_loop.py`);
- a proposal is a suggestion with a name on it, and the name is the model's, not the node's.

So: the form works with nothing proposed. Where an agent is running it may offer options, each one
pre-filling the same two sentences, each one editable, and each one marked as the model's suggestion
and not the node's finding. A decision recorded from a proposal records which rung answered — the
agent already stamps `X-Agent=<name>/<rung>` on every write.

## 9 · By whom

`actions.actor` is eighty characters of free text. Today the honest answer to "who decided" is
"whoever typed their name", and there is no identity behind it. That question belongs to
`docs/SPEC_identity.md` and should not be answered twice. What this spec adds is only that the field
must be *asked for* and not defaulted: an unattributed decision in a house with four people in it is
a record nobody can check.

## 10 · What it refuses

- No decision without something to watch, or it is a diary entry the funnel cannot count — and the
  page must say which of the two it is taking.
- No keeper SQL. A watch is five values and a template.
- No deletion of a watch. Retirement only.
- No watch finer than the grain the node has already proved is flat.
- No proposal presented as a finding.
- Nothing here writes a `measured` row. The derivation stays the only way that stage is reached.
- **A decision never counts as an act.** Not in the funnel, not in ρ, not in a cell, not in a count.
- **A decision that was never acted on is never hidden.** It shows, with its date, beside the ask it
  was about.
- No decision speaks for more people than the one who made it, whatever scale it names.

## 11 · Still open

- **What happens to a decision whose watch never fires.** If the condition is not true when you
  decide, there is no alert to act on and nothing to measure. Probably correct — you decide about
  what is happening — but it means the form has to refuse gracefully, and the words for that refusal
  are not written.
- **A decision about something the node cannot see.** "We moved the burning to the far field" is
  real, useful, and has no metric. §8 forbids counting it; it does not say whether to record it.
- **What a decision at a scale bigger than this house means before consensus exists.** §7 says it is
  recorded as one household's and that is all. Whether the page should say so every time, or only
  where a neighbour is visible to disagree, is not settled.
- **Whether an insight can be wrong.** The three kinds in §4 are arithmetic, not judgement. A sensor
  in the sun reads high and the arithmetic will call it an insight.

---

*Grounded in `init.sql` (`alerts`, `actions`), `app/main.py::run_rules` and `POST /actions`,
`app/index.py::_funnel`, `_live_rule_ids` and `run_ro`, `app/packs.py::load_rules`,
`docker-compose.yml`'s read-only `config` mount, `config/rules.yml`'s own format, and
`app/agent_loop.py`.*
