# Maintainers

Who is answerable for what in this repository. `GOVERNANCE.md` says how this list changes and what
needs how many of the people on it.

**Draft, 20 September 2026.** Only the first row is confirmed. Every other row is `proposed` and is
not in force: a name here is a person agreeing to be answerable for a thing running in somebody's
house, and nobody but Tomas has agreed to that in writing yet.

## Active

| name | GitHub | scope | since |
|---|---|---|---|
| Tomas Diez | `@tomasdiez` | everything | 2026-09-02 |

"Everything" is the accurate word and not a compliment. On 20 September one person holds merge,
`make ship`, the Cloudflare zone, the Airtable base and the release signing key, and wrote 431 of the
441 commits under five author identities. `GOVERNANCE.md` opens with that table because this row is
the reason the file exists.

## Proposed

| name | GitHub | proposed scope | note |
|---|---|---|---|
| Lucas Marangoni | `@lucfabcity` | the installer and the Linux platforms — `install`, `install.sh`, `update.sh`, `tools/preflight.sh`, `data/platform_floors.yml` | **already holds admin on this repository.** Runs node #2 in Menorca and has pushed to `main`. This row grants nothing; it records a scope and asks him to agree to it. |

**Lucas's admin is not a proposal, it is a fact** — checked against the GitHub API on 20 September
2026. The repository's permissions have had two admins for some time while every file in it implied
one. What is missing is not access; it is a person having said "yes, that is mine to answer for", and
a scope narrow enough that saying yes is reasonable. The installer is the obvious one: one leg of
`install-smoke.yml` is named "Linux Mint 22.3 (Lucas's machine)", and the whole Ubuntu-derivative
branch in `install.sh` exists because Docker's own installer mis-read his machine as Debian and left
apt broken. That code has a reader already.

## Not a maintainer, on purpose

**The methodology owner.** The Fab City Index's methodology — what a cell means, what `live` is allowed
to claim, which pillars and scales exist — is owned outside this repository and is not a maintainer's
to change. `SPEC.md §1` carries the contract and `docs/SPEC_rho.md` will carry ρ's; neither is settled
by a merge here.

That person holds **read access and no merge rights**, and that is the correct arrangement rather than
an oversight: the methodology constrains this code, so the person who owns it should not also be the
person who can quietly change what the code does to fit.

> **For Tomas:** the repository has a third collaborator, `@pipezulu`, with pull-only access. If that
> is the methodology owner, put the name in this section. If it is somebody else, this section still
> stands and the row is owed a name. An agent should not map a GitHub handle to a person it has not
> been told about, so it did not.

## Inactive

Nobody. A maintainer unreachable for three months moves here, which is a fact and not a judgement, and
moves back by asking (`GOVERNANCE.md`).

## Security

Reports go through the repository's private advisory form — `SECURITY.md`. Every maintainer in the
**Active** table above can read them, which is one more reason for that table to have a second row.
