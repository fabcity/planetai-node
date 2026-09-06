# Handoff: beta-readiness review, 6 September 2026

For a fresh session that continues this work. The full findings, scores and evidence are in
`docs/reviews/BETA_READINESS_2026-09.md`; the tester-facing path is `docs/BETA_TESTER_GUIDE.md`; what changed is the
`v0.31` section of `CHANGELOG.md`.

## State

- `fabcity/planetai-node` is **public** on GitHub (the brief said private); `fabcity/planetai` (the site) is **private**.
- Review commits: `git log a5a67bb..v0.31 --oneline`, one fix per commit, gates green (`make lint && make test`), pushed
  to `main` and tagged `v0.31`. Branch `beta-review-2026-09` carries the same commits (delete it when convenient).
- The site was **not** changed. Its tarball at `/node0/get/` is still v0.12; `tools/bundle.sh` writes a fresh one into
  `../planetai/node0/get/` (run by `tools/release.sh`), but deploying the site (`make deploy` there) is a publish and
  was left to Tomas.
- Node #1: ssh `fablabbali@bayu-2` (tailnet name; the machine calls itself `fabalabbali.local`, tailscale IP
  100.90.223.47), node folder `~/planetai/planetai-node`, **APP_PORT 8081** (caddy has 8080), Docker via Colima,
  v0.30, schema 0.20, ρ 0.519 (14/27), 8 cell rows = 6 distinct cells, **no backup crontab**. Read-only throughout the
  review; it has not been updated to v0.31. Dashboard from the laptop: `http://100.90.223.47:8081/`.
- Test VMs (Lima, `limactl list`): `pai-clean` (Santiago node on v0.31, laptop `127.0.0.1:8080`), `pai-clean2`
  (Barcelona node, restore target, laptop `127.0.0.1:8082` via an ssh tunnel), `pai-clean3` and `pai-clean4` (release
  rehearsals). All arm64 Ubuntu 24.04 with `qemu-user-static` added so the amd64-only PostGIS image runs. Wizard driver:
  `~/drive_install.py` on each VM; transcripts under `~/logs/`. `limactl delete <name>` removes them.
- Session scratchpad on the laptop (may be gone in a new session):
  `/private/tmp/claude-501/-Users-tomasdiez-claudecode/7373c723-0c14-47f9-bb7c-ca7631f5cfa2/scratchpad/` with
  `site_inventory.md`, `security_audit.md`, `pip-audit.json`, every install transcript and sweep log. The facts that
  matter were copied into the review.

## Decisions made during the review, and why

- Fixed only what the rehearsal broke or what misled a tester; no features, no new files beyond the fix (the three docs
  the brief asked for excepted). Gates added only where a bug had shipped (import check, tool-count words).
- Two security fixes were made although they touch secrets, because they close an exposure of the stated invariant
  rather than change how secrets are handled: `/settings/raw` now needs the admin token (b94e2e8) and the agent loop no
  longer logs `settings_set` values (b8e98d1). Everything else about secrets (dump contents, LAN writes) is proposed,
  not done.
- `POST /actions` stays open on the LAN (the household's button) but now rejects unknown alerts and foreign stages.
- The install rehearsal used Lima instead of Multipass/OrbStack (both need administrator rights on this laptop), and no
  fresh macOS account was possible for the same reason.
- The Phase 3 rehearsal ran the site's `/install` stub with `PLANETAI_REF=beta-review-2026-09` so the exact stub was
  exercised before anything touched `main`.
- Node #1 was never written to. Its missing backup cron is reported, not fixed there.

## Open findings (not fixed)

Blocking a class of tester
- arm64 Linux / Raspberry Pi: no arm64 PostGIS image (decision 2 in the review).

Decisions for Tomas (review §"three decisions" and the smaller calls)
- Release channel (`main` vs a tag; the v0.12 tarball; the private-repo footer link on the site).
- `POST /readings` without a token; dump contents (`settings` table); `/actions` openness.
- Cell count to state (6 distinct / 8 rows / "seven" / "4 of 20"); `daily_pulse` still in `config/rules.yml`; the heat
  pack's Social cell reporting 0.0 hours with no indoor sensor.
- Every site narrative change (legacy agents/hardware block, ρ 0.67, alpha/beta, version, meta, served internal files).

Serious, code, not done
- Pack SQL runs as the DB owner (needs a read-only role in `init.sql`: schema change).
- Log rotation missing on the `db`, `agent`, `ipfs` containers.
- `planetai packs` rebuilds the image when asked only to list.
- Briefings and the dashboard test alert are English-only even for `ALERT_LOCALE=id`; no Spanish anywhere (inventory in
  review §3).
- `GET /settings` unauthenticated shows chat ids and LAN hosts; token compares not constant-time; containers run as root.

Polish, not done
- Geocoder shows duplicate choices ("Sant Martí" twice); `planetai run` descriptions; `planetai config` without a tty;
  doctor has no disk-space check; `.planetai-setup.log` grows without bound; commands missing from `--help`
  (`start restart sensors cells version geocode`).

## Do not touch

- Node #1: no `update`, `restore`, migrations, `docker compose down`, no writes, until Tomas decides to move it to v0.31.
- The FCI formula, ρ's definition, cell weights, provenance rules, the schema, the data model, dependencies (the arm64
  image is a dependency change).
- Secrets: never print `.env` values; the VMs' tokens are throwaway but were not pasted anywhere.
- Deletions: `daily_pulse`, unreferenced site screenshots, the v0.12 tarball. All flagged, none removed.

## If you continue

1. Ask Tomas the three decisions; each has a proposed change in the review.
2. If node #1 moves to v0.31: `planetai update` there (its `.env` has `NODE_KIND=home`, so the v0.30 `update.sh` is
   safe), then `planetai doctor` will show the missing cron line to add.
3. Site: apply the mechanical diffs in review §9 (footer link, alpha wording, "four questions"), run `tools/bundle.sh`,
   deploy, and re-check `/node0/get/VERSION`.
4. Spanish: the 23 alert templates in `packs/*/rules.yml` + `config/rules.yml`, six briefing sentences in
   `app/main.py`, the dashboard test alert, and the CLI's `say/warn/fail` lines are the inventory; `ALERT_LOCALE`
   validation in `app/settings.py:46` would need `es`.
