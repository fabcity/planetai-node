# Governance

**Draft, 20 September 2026. Nothing in this file is decided until Tomas says so.** It is written
because in a project whose whole purpose is that a community can run it without asking anyone, the bus
factor is the architecture — and the numbers below are what the repository actually says today.

## The number this file exists for

On 20 September 2026, day 19 of a project whose own `PRODUCT.md` says *"if it's Tomas past day 30, the
product is a hobby"*:

| | |
|---|---|
| commits (excluding merges) | **441** |
| by Tomas, under five different author identities | **431** |
| authored by an AI | **8** |
| by an external contributor (Lucas, under two identities) | **2** |
| carrying a `Co-Authored-By: Claude` trailer | **331** (75%) |

One person holds merge, `make ship`, the Cloudflare zone, the Airtable base and — since v0.60 — the
release signing key. `main` is the beta channel. Until this file there was no `GOVERNANCE.md` and no
`MAINTAINERS.md`.

## What is true today, and what is only written down

This distinction matters more than anything else here, so it is first.

**`main` has no branch protection.** Verified against the GitHub API on 20 September 2026: no required
reviews, no required checks, no restriction on who pushes. So every rule below — including
`.github/CODEOWNERS` — is **a promise between people, not a mechanism.** CODEOWNERS with no protected
branch requests a reviewer and enforces nothing.

`docs/decisions/2026-09-20-governance.md` lists the settings that would make these rules real. This
file does not flip them; that is Tomas's, and it should be done knowing that a two-review rule on a
one-maintainer project stops the project.

**Two people already hold admin.** `tomasdiez` and `lucfabcity` both have full admin on
`fabcity/planetai-node`. The bus factor in the repository's settings has been two for some time; it is
this *file* that has been at one. `MAINTAINERS.md` is catching up with reality, not granting anything.

## Maintainers

`MAINTAINERS.md` is the list and the scope of each. It is the file to change, not this one.

**Adding a maintainer:** two existing maintainers agree, in a pull request against `MAINTAINERS.md`.

**The bootstrap, because two-of-two cannot start from one:** while `MAINTAINERS.md` carries fewer than
two confirmed names, Tomas adds the second alone. From the moment there are two, the rule above
applies and Tomas is no longer an exception to it. Say so here rather than leaving a rule that cannot
be executed on the day it is written.

**Removing a maintainer:** they ask, or the other maintainers agree in a PR that says why. A
maintainer who has not been reachable for three months moves to `inactive` in `MAINTAINERS.md`, which
is a fact and not a judgement, and moves back by asking.

## What needs how many

| change | who has to agree |
|---|---|
| a pack, a doc, a rule, a test, a CI job | **one maintainer** |
| `init.sql`, `SPEC.md §1` contracts, `tests/data/wire/*`, anything under `install`, `install.sh`, `update.sh`, `bin/planetai` | **two maintainers** |
| the licence, the trademark, the release signing key, a new operator organisation | **the Fab City Foundation** |

The middle row is the one with teeth and the reason is the same for every path in it: **a household
updates by running `planetai update`, and cannot review what arrives.** `init.sql` runs against a
database that holds a year of somebody's readings. `install` and `update.sh` are executed by a stranger
straight off a URL. `bin/planetai` is what a keeper types when something is already wrong. A wrong
merge in any of them reaches every node without anyone choosing it.

`.github/CODEOWNERS` names the same paths so that GitHub requests the review, once there is a protected
branch for it to request against.

## How a decision is recorded

`docs/decisions/<date>-<topic>.md`, the pattern already in use — `2026-09-10-custody.md`,
`2026-09-10-make-pack.md`. A record says what was decided, what the alternatives were, and what it
costs if it is wrong. It is written when the decision is made, not when the code lands, and a record
that only argues for what was chosen has not been written yet.

A version bump on a wire format (`ARCHITECTURE.md §3`) is one of these. So is a licence change, a new
required dependency, and anything in the "two maintainers" row that a reviewer had to think about.

## Agents, and who is answerable

Three quarters of this repository's commits carry a `Co-Authored-By: Claude` trailer and eight were
authored by one outright. That is not a problem to be solved, and pretending otherwise would make this
file dishonest. But it puts the weight somewhere specific:

**A human maintainer is answerable for every merge, whatever wrote the diff.**
`.github/PULL_REQUEST_TEMPLATE.md` already asks it — *"A pull request opened by an agent with nobody
behind it is closed unread"* — and the reason is the one in this repository's own words: a node runs in
somebody's home, on their machine, next to their family, and somebody has to be answerable for what it
does there.

What follows from that, and what a maintainer may not delegate:

- **Reading the diff.** The template's "I read every line" box is the whole of the mechanism. An agent
  cannot tick it, and a maintainer ticking it without having read is the failure this file cannot
  prevent.
- **A merge.** No automation merges to `main`. No bot has write access, and none should be given it
  without a decision record.
- **Anything in the "two maintainers" row.** An agent may write it; two people agree to it.

## A second organisation running nodes under the name

**Not decided.** `docs/decisions/2026-09-18-licence.md` is where it is being decided, together with the
licence, and this section is a placeholder for its outcome. Until then: the name is the Foundation's,
and nobody has been given permission to ship a thing called PLANETAI. What a conformance test would
have to check is already written — `ARCHITECTURE.md §7`, the refusals.

## If the Fab City Foundation dissolves

The repository, the release signing key, and the Index observations repository pass to the maintainers
named in `MAINTAINERS.md` at that date, jointly, to be kept under the same licence and the same
refusals. They may pass them to another non-profit steward by agreement, and may not sell them, take
them private, or relicense them in a way that lets a household's raw readings leave the household's
machine.

This is a statement of intent in a file, not an instrument. `docs/decisions/2026-09-20-governance.md`
lists what would have to be true for it to bind — chiefly that the Foundation has to actually hold the
things it would be passing on, and today it holds none of them.

## What this file does not do

It does not decide the licence (`docs/decisions/2026-09-18-licence.md`), change branch protection,
change who has access to anything, or name anybody as a maintainer who has not agreed to be one. It
describes a shape, and the decision record beside it lists what a person has to do by hand before the
shape is real.
