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

## Conventions

- `make lint` must pass. That's `bash -n`, `py_compile`, and YAML parsing — deliberately cheap.
- Schema changes go in `init.sql` additively (`IF NOT EXISTS`, `CREATE OR REPLACE VIEW`). A v0.1 node must update in place.
- One dated line in `CHANGELOG.md` per change, saying why.
- Code Apache 2.0, docs CC-BY 4.0. By opening a PR you agree to those terms.

## Voice

Docs are written for the person installing at 9pm with a sensor that just went quiet. Plain words. Say what to do.
No emoji, no hype, no "simply".
