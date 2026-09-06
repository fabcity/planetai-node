# Handoff: beta-readiness review, 6 September 2026 (interim; rewritten at the end of the review)

For a fresh session continuing this work. Read `docs/reviews/BETA_READINESS_2026-09.md` when it exists; until then this
file is the state.

## Where things are

- Repo `fabcity/planetai-node` is **public** on GitHub (the brief assumed private). Site repo `fabcity/planetai` is **private**.
- Local checkouts: `/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node` and `.../planetai`. `main` was v0.30
  (a5a67bb) when the review started; review commits sit on top of it locally and are pushed to branch
  `beta-review-2026-09` for VM testing. `main` on GitHub is untouched until the release.
- Node #1: ssh `fablabbali@bayu-2` (tailnet), node folder `~/planetai/planetai-node`, APP_PORT **8081** (caddy holds 8080),
  Docker via Colima, v0.30, schema 0.20. Read-only during the review. Dashboard from the laptop: `http://100.90.223.47:8081/`.
- Clean test VMs (Lima, Ubuntu 24.04 arm64): `pai-clean` (Santiago node, laptop `127.0.0.1:8080`) and `pai-clean2`
  (Barcelona node, laptop `127.0.0.1:8082` through an ssh tunnel). Both needed `qemu-user-static` to run the amd64-only
  PostGIS image. Driver for the interactive wizard: `~/drive_install.py` on each VM; logs under `~/logs/`.
- Scratchpad on the laptop: `/private/tmp/claude-501/-Users-tomasdiez-claudecode/7373c723-0c14-47f9-bb7c-ca7631f5cfa2/scratchpad`
  (site_inventory.md, security_audit.md, install transcripts, sweep logs).

## Decisions only Tomas can make (not fixed, proposed in the report)

1. Release channel: `/install` clones `main` HEAD; the tester tarball at `/node0/get/` is v0.12; site footer links the
   private repo. Pin a tag, refresh the tarball, or accept `main`.
2. arm64 Linux (Raspberry Pi): no arm64 build of `postgis/postgis` exists. Pick an image (community multi-arch image, or
   `postgres:16` + apt postgis) or drop the Pi promise. Docs now say "not yet".
3. Backups contain the `settings` table with the Telegram token; `POST /actions` is open on the LAN (household act button);
   `POST /readings` is open (a stranger on the WiFi can inject "live" readings and fire alerts). Auth decisions.
4. Cell count to state publicly: node #1 reports 8 rows, 6 distinct cells; COVERAGE.md says seven; site says seven and
   "4 of 20"; the dashboard says 8/20.
5. Every site narrative change (legacy "four action agents" block, ρ 0.67 claim, alpha/beta wording, version).
6. `config/rules.yml` still carries `daily_pulse` although v0.30 says the reports superseded it (deletion = your call).
7. The heat pack's Social|Community cell reports 0.0 hours on a node with no indoor sensor (cell SQL = your call).

## Do not touch

- Node #1: no `update`, `restore`, migrations, `docker compose down`, no writes. Evidence only.
- FCI formula, ρ definition, cell weights, provenance rules, schema, data model, dependencies.
- Secrets: never print `.env` values. Tokens for the VMs live only in the VMs and in the scratchpad.

## What was fixed (each its own commit on the review branch)

See `git log a5a67bb..HEAD --oneline`. Blockers: NODE_NAME=Ubuntu on Linux; NODE_KIND sentence from the wizard; update.sh
executing and then deleting `.env`; four 500s (/export, /history, /readings, negative limits); /settings/raw accepting the
backup token; fresh install ending in the red box; docker-group death on first Linux run; root-owned backups/; bootstrap
skipped; Makefile import gate never running. Plus doctor cron check, presets in the wizard, docs corrections, gates.

## Still to do when this file was written

Phase 1 evidence gathering on the VMs (update path, restore into a second node, MCP calls, dashboard at three widths),
Phase 3 re-run of the clean install from the site path, CHANGELOG v0.31 and tag, the four deliverables.
