# ρ — the loop closed

ρ (rho) is the share of the node's act-level alerts that led to someone doing something. It is the one
number on the page that comes from a person, the Fab City Index's `Governance` cell at the node's scale, and
the reason the `actions` table is the Index's instrument rather than an app feature. Two generations of the
Index measured a snapshot with ρ implicit at 1. A node measures it, because it is the thing sending the
alert and the thing receiving the acknowledgement.

## The definition in this version

Over the last 30 days:

```
ρ = act-level alerts whose first acknowledged-or-acted action came within 24 hours
    ─────────────────────────────────────────────────────────────────────────────
                          act-level alerts raised
```

together with `median_minutes`, the median time from the alert to that first action, among the ones that
were answered within 24 hours. Both are computed by `index.rho()` from `alerts` joined to `actions`, pooled
with the `events` rows the node's children pushed up (`level='act'`, their `responded_at` or `acted_at`
whichever is earlier). A node with no children reads an empty `events` table. `days_ago` shifts the whole
window back; the report uses 7 to say what ρ was a week ago.

`GET /rho`:

```json
{"window_days": 30, "days_ago": 0, "alerts_act": 12, "acted": 8, "rho": 0.667, "median_minutes": 41}
```

`rho` and `median_minutes` are `null` when there is nothing to divide. `planetai status` and `planetai act`
print it; the `status` MCP tool carries it; the dashboard's *Whether it worked* section draws it as
"{closed} of {total} asks answered · median {n} min".

## Stages

`actions.stage` is one of four:

| stage | meaning | written by |
|---|---|---|
| `acknowledged` | somebody saw it | `POST /actions` |
| `acted` | somebody did the thing | `POST /actions`, `planetai act`, `/act` on Telegram, `act <id>` over LXMF, the `act` MCP tool |
| `measured` | the outcome was checked | in the schema and pushed to a parent as `measured_at`; nothing writes it yet |
| `settings` | a setting was changed — an audit row with no alert | `PUT /settings` |

For ρ, `acknowledged` and `acted` both count as a response; for the dashboard's asks, only `acted` and
`measured` close one — "acknowledged means somebody saw it; only these two mean somebody did something."
There is no cap of one action per alert; the first response is what the clock measures.

## What ρ is not

It is not a score of the household. A household that ignores its node is a real result, and the standing
instruction to testers is not to act on alerts in order to improve it. An instrument whose headline number
goes *down* as it measures more honestly is the credibility the Index never had.

It is not yet measured against the room. A retroactive pass over node #1's dumps found that many act alerts
were a few events repeating under cooldowns, that the inside-versus-outside ratio cannot tell a stopped
stove from an opened door, and that recorded action times cluster at "when I next opened the dashboard"
rather than when anything happened. The response is a split — the reported ρ above beside an observed one
read from the room's own recovery — and a funnel of four latencies: reached, acknowledged, deployed,
measured. The dashboard already draws the 2×2 (answered or not × the reading came back or still over) when
a node computes it, and says plainly that no endpoint on this node computes it yet. The schema for it is
proposed in the repository's decisions and handoffs, not built.

## Where it goes

- **The Index.** `GET /cells` appends `Governance|<Scale>` with ρ as its value when there has been any
  act-level alert in 30 days: `partial` until five have been acted on, `live` from then.
- **A parent.** Every hour the node posts its alerts of the last 36 hours to the parent's `/events` as
  timestamps only — `raised_at`, `responded_at`, `acted_at`, `measured_at`, the rule, the level, the pack —
  never the text, the actor, the sensor or a ratio. The parent computes ρ under whatever definition it runs.
- **The export.** The daily CC BY 4.0 export carries `rho` for the day.
- **The report.** The bundle carries ρ now and a week ago.

## Recording an action

From off the machine, `POST /actions` needs `ACT_TOKEN` or `ADMIN_TOKEN`; from loopback — the node's own MCP
tools, a shell in the container — it needs none. The body is `{"alert_id": 12, "stage": "acted", "actor":
"tomas", "note": "closed the windows"}`; `actor` is at most 80 characters, `note` 500, and an unknown alert is
a 404. An agent records what the person said, in their words, and never invents one.

The Telegram bot answers `/act 12 closed the windows` with "Recorded: you acted on #12." and the actor
`<AGENT_NAME>/telegram`. Sideband answers `act 12` over LXMF with the actor `lxmf:<hash>`. The dashboard's
button carries the act or admin token the browser holds.

## Invariants

The invariants that keep ρ honest are on the [federation](federation.md) page with the rest: peers never
roll up and never drive an alert; the actor and note on an action, the alert text, chat ids, coordinates, room names and sensor ids never leave the node at any sharing level; state is never upgraded by aggregation; exactly one node per pilot writes to the
Index's spine.
