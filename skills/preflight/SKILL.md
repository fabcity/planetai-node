---
name: preflight
description: The first ten minutes of any working session on this repository — where main is, what is open, what is red, what the neighbours are on — before a line is changed.
---

# Preflight: before you touch anything

You are about to work on `planetai-node`. Somebody else — a person or another session — has almost
certainly worked on it since the last time this checkout was current. Everything that went wrong in
the week of 12–19 September 2026 went wrong at that seam, not inside a feature. This is the ten
minutes that finds the seam first.

## Run it

```bash
tools/session.sh preflight
```

Read-only, under a minute. It says: which worktree holds `main` and whether you are standing in it;
how far your branch is from `origin/main`; whether `tests/all` lists as many suites as it asserts; every
open PR with its age and whether it merges; how many branches on origin are ahead of main with no PR;
whether CI is green on main's head; whether the site is behind main; and what branch each sibling
checkout (`planetai-design`, `awesome-fabcity-data`) is on and how far behind *its* main.

A red `x` is a stop. Do not start on top of it.

## Then, before writing

1. **Work in your own worktree, on a branch, never in the checkout that holds `main`.** Several
   sessions share this repository. `git worktree add ../planetai-node-<task> -b <task> origin/main`.
   The worktree holding `main` is for shipping, and `tools/ship.sh` needs it clean.
2. **Read `docs/NEXT_RELEASE.md`.** It is what is owed and how the two large changes are staged. If
   your task is on it, it says what it touches and what not to touch. If your task moves the suite
   count in `tests/all`, check no open PR does too — one at a time, that is the rule.
3. **Read the gates before you read the code.** `make lint` is the list, and `docs/DEVELOPING.md`
   says what each one has caught. If you are about to add a pack, `tools/check_sources.py` and the
   locale gate in `tests/test_packs.py` are the ones that will fail you; if you are about to touch
   `app/static/`, `check_ui.py` and `check_theme.py` are.
4. **The sibling checkouts are not the registry.** `check_sources.py` and `wired.py` read the other
   repo's `origin/main` on purpose. If preflight says `awesome-fabcity-data` is on a harvest branch
   thirty files dirty, believe the gate and not the directory.

## What preflight does not do

It does not fix anything, merge anything or delete anything. Thirty-five stray branches is a number
to know, not a task to start on unasked. `tools/sweep.py` lists them; `docs/NEXT_RELEASE.md` says
what is actually owed.

When you are done: `skills/land/SKILL.md`.
