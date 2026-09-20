# SPEC — a node is a key, not a string

**Status: Phase 1. Nothing here is built.** This is the document Tomas approves or strikes before any
code is written, per prompt 3 of the 18 September design review. The section at the end lists the four
places where this spec decides something the review's own wording did not, so that a strike is cheap.

## §1 · What is wrong today, with the lines

A child pushes hourly means and ρ events to a parent. Both handlers authenticate the same way:

```python
# app/main.py:1757 (receive_events) and :1800 (receive_aggregates), identical
if not AGG_TOKEN():   raise HTTPException(403, "this node accepts no children: set AGGREGATE_TOKEN…")
if not _bearer_ok(authorization, AGG_TOKEN()):  raise HTTPException(401, "bad or missing Authorization…")
rows, child = body.get("rows", []), body.get("node", "?")
```

`child` is `body["node"]` — **a string the child declares about itself.** One `AGGREGATE_TOKEN` is shared
by every child of a parent, because `AGG_TOKEN()` is one settings key and `_bearer_ok` compares against
it alone. So any child holding the district's token can:

- push readings as any sibling — `receive_aggregates:1807` writes `sensors.sensor_id = f"{child}/…"`,
  so the row lands under the sibling's namespace and the parent's `Environmental|Community` cell averages it;
- rewrite a sibling's ρ — `receive_events:1767` upserts on `PRIMARY KEY (child, alert_id)`, so a forged
  `acted_at` on a sibling's alert id replaces the real one;
- invent a tenth household — a `node` nobody has ever heard of creates sensor rows and events on first
  contact, and nothing anywhere says which names a parent expects.

None of this needs a bug. It is the contract working as specified.

**Scale is the whole argument.** `registry.json` lists one node while four run. `SPEC.md §6` defers
"Node registry service + signed handshake" to "roughly 30 nodes or a second operator org". At four nodes
this is an afternoon, one additive table and one additive column. At thirty it is a migration every
operator runs on a machine in a cupboard, coordinated across people who have never met. Do it before
node #5. The registry *service* in §6 is a different thing and still deferred: this spec adds identity to
the nodes, not a server to hand it out.

## §2 · The decisions

### 1. Ed25519, generated in the app container at first boot

The host CLI is Bash 3.2 and Apple's stdlib-only Python 3.9 (`tools/check_cli_python.py` enforces both) and
has no Ed25519. The app container is `python:3.12` and may add a dependency. So the key is generated,
held and used **only inside the container**, and `bin/planetai` never touches crypto — it calls the API,
which is what `api()` at `bin/planetai:153` already does for everything else.

`cryptography` goes in `app/requirements.txt`, pinned. It is the only new dependency.

### 2. The node id **is** the public key

```
node id = base32(raw 32-byte Ed25519 public key), lowercase, unpadded  →  52 characters
```

No hash. An Ed25519 public key is already 32 bytes; `base32(sha256(key))` is also 52 characters, so hashing
buys nothing and costs a lookup step, a second format to specify, and a `X-Node-Key` header carrying
something the id is not. The id is the key, the parent's `children` table is keyed on it, and "the parent
has this child's key" and "the parent knows this child's id" are one sentence.

Base32 and not base64 because it is case-insensitive and survives being read down a phone line, which is how
a fab lab in Menorca will actually enrol. It is deliberately not the format `planetai version` prints for the
release signer — that one is `ssh-keygen -lf`'s `SHA256:…`, ssh's format, not ours.

`NODE` stays exactly what it is: the human label, on the page, in the report, in `registry.json`. It is
never again an identity claim.

### 3. The key lives in its own volume, and **`backup.sh` decides that**

`backup.sh:44` runs `pg_dump --exclude-table-data=settings`, and the dump travels — `BACKUP_DIR` may be a
NAS mount, `BACKUP_REMOTE` is an rclone destination with forty backends. That fact rules out the obvious
options:

| where | what happens |
|---|---|
| a table in the dump | the node's **private key is copied to a NAS every night**, and to Backblaze if the operator set one. No. |
| a table excluded from the dump, like `settings` | the dump is honest, but a restore onto a new machine silently generates a *new* identity, the parent rejects it, and the operator sees "the child stopped pushing" with nothing naming why. |
| **a separate `identity` volume** | not in `pg_dump` at all, so the question never arises. |

Recommended: the third. The repo already ships this exact pattern one service over, and the operators
already understand its sentence — `docker-compose.yml:104`:

```yaml
- reticulum:/data     # identity + LXMF storage. Deleting it gives the node a new address.
```

The same sentence applies word for word. `./config` cannot hold it: that mount is `:ro` (`docker-compose.yml:33`).

**The honest cost, which goes in the docs and in `planetai doctor`:** rebuilding the machine loses the
identity and the node must be re-enrolled at its parent — one command, on the parent. That is the price of
a private key that is never written to a backup that leaves the house, and it is the right price.

### 4. Sign the bytes on the wire, not a canonical re-serialisation

```
X-Node-Key        the child's node id (§2)
X-Node-Ts         RFC 3339, the moment of signing
X-Node-Signature  base64( Ed25519_sign( ts + "\n" + sha256(raw request body bytes) ) )
```

**This is the first place this spec departs from the review's wording**, which said "canonical JSON body".
Canonical JSON means the parent re-serialises what it parsed and hopes it matches what the child serialised.
The two will disagree the first time a float round-trips differently, or a non-ASCII place name is escaped
on one side and not the other, or a key order changes — and the failure is a signature mismatch on a node in
a cupboard, which reads exactly like a wrong key.

Hashing the raw body removes the entire class: the child hashes the bytes it is about to send, the parent
hashes `await request.body()`. There is no serializer to agree on. The cost is that both handlers take
`Request` and parse the body themselves instead of letting FastAPI do it — about four lines each.

### 5. Skew is the replay defence, and there is no nonce table

The parent refuses `X-Node-Ts` more than **10 minutes** from its own clock, in either direction.

**No seen-signature table.** Both signed endpoints are idempotent upserts — `receive_aggregates` is
`ON CONFLICT DO NOTHING` on `readings`' `UNIQUE (sensor_id, metric, ts)`, `receive_events` is
`ON CONFLICT (child, alert_id) DO UPDATE`. So a replay inside the window writes either the same rows or rows
at most ten minutes staler, and the child pushes again on the hour regardless. A nonce table would be a
second table, a cleanup loop and a new way for a node in a cupboard to fail, bought to prevent ten minutes
of staleness on a number nobody reads faster than hourly.

**The condition that changes this:** the first signed endpoint that is not an idempotent upsert. A PR that
adds one names this paragraph and adds the table.

Both nodes must have a clock. They do — `docs/PLATFORMS.md` has no platform without NTP — and a node whose
clock is ten minutes out has worse problems than this, which `planetai doctor` should say in the same row.

### 6. Trust is a table on the parent, and enrolment is one command

```sql
CREATE TABLE IF NOT EXISTS children (
  fingerprint  TEXT PRIMARY KEY,        -- the node id of §2: base32 of the child's public key
  name         TEXT NOT NULL,           -- what the parent calls it. THIS is what lands in sensors/events.
  added_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  added_by     TEXT                     -- X-Agent, or 'cli'
);

ALTER TABLE events ADD COLUMN IF NOT EXISTS child_key TEXT;   -- which key pushed it, beside the name
INSERT INTO schema_version (version) VALUES ('0.63') ON CONFLICT DO NOTHING;
```

Both additive, both `IF NOT EXISTS`, per `AGENTS.md`. `events.child_key` is not the primary key and does not
replace `child`: `PRIMARY KEY (child, alert_id)` stays, so nothing about ρ's roll-up changes. It is there so
that a parent re-reading a year of events can tell which key wrote a row after a child has been re-enrolled
with a new one — the question `planetai children` cannot answer from the present tense.

**`/health` publishes one field, not two.** Because the id *is* the key (§2), `node_key` and `fingerprint`
are the same 52 characters; publishing both would be publishing the same string twice under two names and
inviting somebody to compare them. `/health` gains `node_key`, and `planetai status` and `planetai version`
print it. It is a public key: it is safe at every `SHARE_LEVEL`, and `/health` is the read that answers at
all of them.

A parent accepts a child **iff** its key is a row here. Enrolment:

```
on the child:   planetai status            # prints the node id
on the parent:  planetai children add <id> <name>
                planetai children list | remove <id>
```

Bash calls `POST /children` behind the admin token; no crypto on the host (§1). The registry PR remains the
later, larger path and is not this change.

**`child` is stamped from the row's `name`, never from the body.** That single line is most of the fix: after
it, `body["node"]` is decoration, and a forged one reaches nothing.

### 7. `AGGREGATE_TOKEN` is accepted for exactly one release

- **v0.63** — signatures accepted and preferred. A request with a valid `AGGREGATE_TOKEN` and no signature is
  still accepted, logged once per child per hour as `legacy push from <name>: no signature`, and `planetai doctor`
  on the parent carries a row naming each child still on the token.
- **v0.64** — the token path is removed from both handlers. `AGGREGATE_TOKEN` stays a settings key for one
  more release so nobody's `.env` sprouts an "unknown key" warning, then goes.

A parent one release behind must keep accepting a child one release ahead: v0.63's handlers accept both, so a
signed child reaching a v0.62 parent falls back to the token it still holds, and neither operator has to
update on a schedule. Nobody's node stops working on a Tuesday because somebody else updated.

### 8. The registry gains a `key`

`registry.json` gets `"key": "<node id>"` per node. `bayu-2`'s is read from node #1's `/health` over the
tailnet — **a read, nothing else**; node #1 is evidence, not a test bench. Nodes #2–#4 get rows with
`"key": "pending"` until their operators run an update and report theirs.

## §3 · What does not change

Named explicitly, because these are the things a reader will assume this touches:

- **The wire shapes of `/aggregates` and `/events` bodies.** Same JSON, same fields, same `rows`. Identity
  moved entirely into headers. A child that signs and a child that does not send byte-identical bodies.
- **`sensors.custody`** and the `local OR kind='child'` predicate (`docs/SPEC_custody.md §1–2`). Untouched.
- **`child` rows in `sensors`**, their `kind='child'`, `cadence='PT1H'` and `<child>/<sensor_id>` namespacing.
  Only the source of `<child>` changes — from the body to the `children` row.
- **What is not sent.** `docs/SPEC_custody.md §4`'s refusal stands: no `text`, no `note`, no `actor`, no
  `sensor_id` in an event. This spec adds no field to either body.
- **`PARENT_TOKEN`.** The child keeps presenting it; §7 is what retires it.

## §4 · The tests, named

`tests/test_identity.py` — new suite, so `tests/all` and its count move by one (NEXT_RELEASE rule 1: no other
open PR may move it in the same hour).

1. sign → verify round trip, and the id round-trips to the same 32 bytes
2. a body with one byte flipped is rejected
3. `X-Node-Ts` 11 minutes old is rejected; 9 minutes old is accepted; 11 minutes *ahead* is also rejected
4. a well-formed signature from a key that is not in `children` is rejected
5. a legacy `AGGREGATE_TOKEN` push is accepted **and logged**, and the log line names no secret
6. **`events.child` equals the registered `name` whatever `body["node"]` says** — the row is written with
   `body["node"] = "some-sibling"` and comes back as the enrolled name
7. the same, for `sensors.sensor_id`'s `<child>/` prefix in `receive_aggregates`

`tests/test_custody.py` is not modified and must stay green — it builds the same node twice and compares every
number, so it is the thing that catches this change altering a count it should not.

Each of 2, 3, 4 and 6 is written **failing first** against the unsigned handlers, the way `tests/test_custody.py`
records at its head. A gate that has never been seen to fail is asserting nothing.

## §5 · What Tomas is being asked

Four decisions in this document are ones the review left open or worded differently. Striking any of them is
cheap now and expensive after Phase 2:

| § | the call | the alternative, if struck |
|---|---|---|
| 2 | the id **is** the public key, not a hash of it | `base32(sha256(key))`, same length, one more lookup and one more format |
| 3 | a separate `identity` volume; a machine rebuild means re-enrolment | a table excluded from the dump — restore then silently re-identifies the node |
| 4 | sign the raw body bytes | canonical JSON, as the review wrote it, and a serializer to keep in step on both sides |
| 5 | no nonce table; the 10-minute window is the whole replay defence | a `seen` table and a cleanup loop, for ten minutes of staleness on an idempotent upsert |

And one thing this spec does **not** decide, because it is not this change: nothing here enrols node #2 as a
child of anything. There is no parent yet.

**Phase 2 begins on "go", not before.**
