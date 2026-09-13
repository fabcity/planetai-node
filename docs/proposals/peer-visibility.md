<!-- Recovered 13 September 2026. Everything below the rule is the document exactly as it was written on
     10 September; this note is the only addition. -->

> **Editor's note — recovered, and partly overtaken.**
>
> This was written on 10 September 2026 into a **session scratchpad**, not into the repository, so it
> lived at `/private/tmp/.../scratchpad/peer-visibility.md` and would have been reaped with that
> directory. `docs/SPEC_custody.md` cites it as `docs/proposals/peer-visibility.md`; it had never been
> there. It is committed here unchanged so the spec's citations resolve.
>
> Four of its claims have since changed. Checked against the tree and against node #1 on 13 September,
> not assumed:
>
> - **§2's two leaks are both fixed.** `/health` rounds `lat`/`lon` to 3 dp (`app/main.py:779`) — node #1
>   serves `-8.819 / 115.164`. `/place/geojson` is refused by the public allowlist (`app/main.py:674`).
> - **§4's `SHARE_LEVEL` exists**, in `app/settings.py`.
> - **§3 is superseded.** It argues that `s.local` is the boundary that keeps a peer out of a cell. That
>   was true and it was also why a community node aggregating ten homes could never say `live` — children
>   are `local=FALSE` too. `docs/SPEC_custody.md` split the two meanings: **custody** is
>   `kind='child' OR (local AND kind <> 'peer')`, a generated column in `init.sql`, and it is what cell
>   SQL reads now. The invariant this document asks for is stronger under it, not weaker: a peer is
>   excluded *even when written* `local=TRUE`, which §3's version would have admitted.
> - **§9.4's decision has been taken.** `kind='peer'` is in `init.sql`'s vocabulary, approved with the
>   custody spec on 12 September. §9.1 — may a peer ever drive an alert — was answered the same way this
>   document recommends, and is now an invariant in `AGENTS.md`.
>
> §5's `PEERS` list and the listening loop remain unbuilt, and §9.2 and §9.3 remain open.

---

# Listening to other nodes, at a disclosure the household chooses

**Status: proposal. Nothing built.** Written 2026-09-10 against `v0.41.2-76`.

The ask has two halves that want different answers:

- **Speaking**: *"decide if someone can just see your node without location, or choose what to share."*
- **Listening**: *"listen to other nodes"* — lateral, peer to peer.

The upward half — node → community node → the Index — is already built and is **not** what this
changes. `push_aggregates()` sends hourly means to `PARENT_API_URL`; `POST /aggregates` receives them
as `kind='child'`; `cells-ingest` pulls `GET /cells` from exactly one node per pilot. That chain works
and this proposal must not disturb it.

---

## 1. What already exists (so nothing gets rebuilt)

The node already has a graded disclosure model. Nobody named it, but it is there, and every rung below
is a thing the code already does:

| grain | who gets it today | where |
|---|---|---|
| raw `(ts, sensor_id, metric, value)` | nobody off-box, ever | refusal §7 |
| hourly means, child's sensor ids namespaced | the parent | `push_aggregates()` |
| a day, sensors aliased `indoor-1`/`outdoor-1`, coords rounded to 3 dp, CC BY 4.0 | parent, Index, researcher, IPFS | `GET /export` |
| 20 `Pillar\|Scale` cells, no coordinates at all | the spine | `GET /cells` |

Alongside it: `NODE_KIND` (`home\|business\|community\|district`), `NODE_SCALE`, a `PUBLIC` allowlist
of settings an anonymous LAN reader may see, `AGGREGATE_TOKEN` / `PARENT_TOKEN` / `BACKUP_TOKEN` /
`ADMIN_TOKEN`, and an H3 **res-8 cell** (`~460 m edge`) already computed for every node by
`ground.facts()`.

So the vocabulary for "levels of privacy" exists. What does not exist is a **choice** over it.

## 2. The honest starting point: today there are no levels

Privacy today is enforced by network reachability — the node is on your LAN, so only your LAN sees it.
Two endpoints make that a thin defence, and both are in scope before any new feature:

- **`GET /health` returns full-precision `lat`/`lon`.** Unauthenticated. That is the address of the
  house, to anyone who can reach the port.
- **`GET /place/geojson` returns the property's building footprints.** Unauthenticated.

Neither is a peer-visibility feature. Both are the existing philosophy not being enforced, and they
should be fixed as a bug regardless of whether anything below is ever built. `/export` already rounds
to 3 dp; `/health` disagreeing with it is an inconsistency, not a decision.

## 3. The finding that makes this cheap

`s.local` is already the boundary that matters.

```sql
-- app/index.py::_buckets — the honesty check a pack must pass to claim `live`
SELECT count(*) FROM readings_1h r JOIN sensors s USING (sensor_id)
WHERE s.local AND r.bucket > now() - interval '24 hours'
```

Every pack's cell SQL filters `s.local` too (`packs/air-quality/cells.yml`, `packs/heat/cells.yml`).
Children (`kind='child'`) are already `local = FALSE` and already excluded.

**A peer stored as `local = FALSE, kind = 'peer'` therefore cannot contribute to an Index cell, cannot
upgrade a cell's state, and cannot be aggregated upward — structurally, not by convention.** There is
precedent in the same shape: `/nearby` already stores other people's stations this way and they inform
the ring without ever becoming the node's own claim.

That is what keeps refusals §7 intact without inventing an enforcement mechanism.

## 4. Speaking: one setting, one filter

`SHARE_LEVEL`, four rungs, default `off`. Not four endpoints — one filter over what is already emitted.

| rung | a stranger sees | assembled from |
|---|---|---|
| `off` | 404. The node is not on the network as far as anyone else is concerned. | — |
| `cell` | H3 res-8 cell id, `NODE_KIND`, `NODE_SCALE`, which metrics exist, how fresh. **No coordinates, no node name.** | `ground.facts()` + `/health` minus lat/lon/name |
| `means` | the above + hourly means per metric, sensors as `indoor-1`/`outdoor-1` | `/export`'s `hourly` rows |
| `open` | the above + `/cells`, `/rho`, first-line alert text, 3 dp coords, CC BY 4.0 | today's `/export`, unchanged |

`open` is what a node already publishes. `cell` is the interesting new rung and it is the one the ask
describes: *seen, without location.*

Reciprocity is not modelled. A node's rung is what it offers everyone; a token can gate `means`/`open`
if a household wants a named audience, reusing `AGGREGATE_TOKEN`'s pattern rather than a new one.

## 5. Listening: a typed list of URLs

`PEERS` — a list of node URLs. A loop fetches each peer's public surface at the rung that peer offers,
stores rows as `sensors(kind='peer', local=FALSE, scale=<theirs>)`, and the dashboard shows them as
context beside the ring.

No discovery service, no registry, no PKI, no DIDs, no gossip. A peer is a URL somebody typed. If a
directory is ever wanted, the community node already knows its own children and can list them — that is
a read of existing state, not a new system.

## 6. What this must never become

Written down because each is a plausible next step that breaks something specific:

- **Peers must not roll up.** The moment peer rows influence a cell, "no scale is skipped" and
  "aggregation stops at Region" are both gone and the pilot has two chains of custody. `local = FALSE`
  is the guard; any change to it is a change to this.
- **Peers must not drive alerts or the report.** Display-only. An alert is a claim the household acts
  on; sourcing it from a stranger's node makes the node's own voice unreliable. *(Recommended default,
  and a decision for you — §9.)*
- **No new provenance state.** `live|partial|mock` travels end to end and is never upgraded. A peer's
  reading is not evidence about this address at any state.
- **`place` geometry never leaves at any rung.** Building footprints of a private property are not
  environmental data.

## 7. Risks this design does not solve

- **A coarse cell is not anonymity when you are alone in it.** H3 res 8 is ~0.74 km². For the only node
  in a village, "cell" *is* the address. Coarsening only hides you in a crowd, and Menorca and Ungasan
  do not have a crowd yet. Res is a setting, but that only trades away usefulness — worth saying to a
  household in plain words rather than implying `cell` means anonymous.
- **Alert text carries household specifics.** "Shut the bedroom windows" describes a home. `open`
  including alert text needs a rule about what a rule may say, or the text withheld at that rung.
- **CC BY 4.0 asserts ownership.** Publishing laterally under it is a claim that the household owns
  what its sensors recorded. Probably right, worth being deliberate about.
- **`means` is re-identifiable in combination.** Hourly indoor temperature is an occupancy signal.
  Nothing about aliasing sensor names changes that.

## 8. Staging

Each step ships and is useful alone.

1. **Fix the two leaks** (§2). Bug fix, no new concepts, no decisions needed.
2. **`SHARE_LEVEL` + the filter.** Answers "choose what to share" completely. No listening yet.
3. **`PEERS` + read loop**, `local = FALSE`, display-only.
4. Stop. Re-read this document before anything further.

## 9. Decisions I should not make alone

1. **May a peer's data ever influence what the node says** — an alert, a report line — or is it
   display-only forever? I recommend display-only.
2. **Default rung for a new node**: `off` or `cell`? I recommend `off` — a node should not begin
   sharing because somebody installed it.
3. **Does the community node act as the peer directory**, or does everyone type URLs?
4. **`SHARE_LEVEL` is a settings key, not a schema change** — but `kind='peer'` adds a value to an
   existing column's vocabulary. Under the standing rule that is a data-model change and needs your
   yes before step 3.
