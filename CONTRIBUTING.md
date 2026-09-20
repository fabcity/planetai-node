# Contributing

Short version: run a node, tell us what broke, send the fix.

## The three ways to help

**Run a node and report.** The most useful contribution is `docs/START_HERE.md` failing on your machine. Open an issue
with the "Node problem" template — it asks for the exact three commands we need.

**Add a sensor or a source.** An adapter is one function in `app/sources.py` returning `(sensors, readings)`; the
contract is at the top of that file and in `docs/sensors.md §1`. Test it against a saved payload from the real device
(see how the existing ones are tested in the PR that added them) before opening a PR. Set `local` and `indoor`
honestly — every rule depends on them.

**Write a rule.** Rules are SQL in `config/rules.yml`. If your rule needs a column `stats` doesn't have, propose the
column in the same PR. A rule should end in something a person does.

## What we won't merge

- Anything that makes a node depend on a cloud service to *function*. Reference data (public APIs) is fine; control planes are not.
- A third container without a trigger written in `SPEC.md §6`. The list of retired pieces exists for a reason.
- Raw readings leaving the node. Hourly means, cells, model updates — yes. Raw — never.
- Rules that fire on indoor sensors as if they were ambient. `NOT s.indoor` is not decoration.

## Before your first commit

```bash
cp tools/hooks/pre-commit .git/hooks/
```

Installs the pre-commit hook: blocks `.env`, credentials and `.git` contents, and runs `make lint`. See
[`docs/DEVELOPING.md`](docs/DEVELOPING.md).

## Conventions

- `make lint` must pass. That's `bash -n`, `py_compile`, and YAML parsing — deliberately cheap.
- Schema changes go in `init.sql` additively (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`). A v0.1 node must update in place.
- One dated line in `CHANGELOG.md` per change, saying why.
- Code Apache 2.0, docs CC-BY 4.0. By opening a PR you agree to those terms.
- **Sign off your commits.** `git commit -s` adds one line:

  ```
  Signed-off-by: Your Name <your@email>
  ```

  That is the [Developer Certificate of Origin](https://developercertificate.org/) — you are saying you
  wrote the change or have the right to contribute it, under the licences above. Not a CLA: nothing is
  assigned to anybody, and there is no form. It exists because this repository already merges code
  three quarters of which carries a `Co-Authored-By` trailer for a model, and the line that says a
  *person* stands behind a commit is worth having written down rather than assumed.

## Who decides

`GOVERNANCE.md` says who merges what and how that list changes; `MAINTAINERS.md` is the list. Most
changes need one maintainer. `init.sql`, `SPEC.md`'s contracts, `install`, `install.sh`, `update.sh`
and `bin/planetai` need two, for one reason: a household updates by running `planetai update` and
cannot review what arrives.

## Voice

Docs are written for the person installing at 9pm with a sensor that just went quiet. Plain words. Say what to do.
No emoji, no hype, no "simply".
