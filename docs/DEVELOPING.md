# Development machine

One machine develops; nodes only consume. Mixing the two is how a node breaks at 9pm and how history quietly forks.

| | development | node |
|---|---|---|
| where | a laptop — for this project, `~/Documents/Claude/Projects/FAB CITY/planetai-node` | wherever it runs, e.g. `~/planetai/planetai-node` on `fablabbali` |
| does | edit, lint, test, commit, tag, push, cut releases | `./update.sh`, and nothing else |
| git | full remote | `git remote set-url --push origin no-push` so an accidental push fails loudly |
| holds | no `.env`, no database | its own `.env`, its own data, neither ever in git |

## Setting one up

```bash
git clone https://github.com/fabcity/planetai-node
cd planetai-node
make dev-setup      # installs the pre-commit hook
make lint && make test
```

Needs `git`, `make`, `python3`, and `gh` (or any git credential helper). Docker only if you want to run a node
locally for testing — everything in `make lint` and `make test` is offline and needs neither Docker nor network.

## The pre-commit hook

`make dev-setup` symlinks `tools/hooks/pre-commit`. It refuses a commit that contains:

- `.env`, `backups/`, `*.before-update`, or `.git` contents;
- anything matching a live credential — a Telegram token (which appears in URLs, so a pasted log leaks it), a long `*_TOKEN=` or `*_API_KEY=` value, or a real `POSTGRES_PASSWORD`;
- a change that fails `make lint` (SQL parens and idempotency, the Dockerfile module glob, YAML, shell syntax).

Every one of those corresponds to something that already went wrong here. If a check can't run it **fails the
commit** rather than passing quietly — the first version of this hook used a PCRE lookahead that `grep -E` rejects,
so it errored, swallowed the error, and let a fake token through on its own test. A security check that no-ops
silently is worse than no check.

## Running a node locally to test a change

Use a second folder and a different port so you never touch a real node's data:

```bash
git clone https://github.com/fabcity/planetai-node ~/tmp/test-node && cd ~/tmp/test-node
chmod +x install.sh backup.sh update.sh
echo "APP_PORT=8082" >> .env 2>/dev/null || true
./install.sh --preset barcelona --name test-bcn
curl -s localhost:8082/health | python3 -m json.tool
```

No sensor needed — it bootstraps from CAMS and NASA POWER for the preset's coordinates. Throw the folder away
afterwards; `docker compose down -v` removes its data volume.

## Cutting a release

```bash
make release V=0.4.5
```

Refuses to run on a dirty tree, refuses if `CHANGELOG.md` has no `## v0.4.5` section (say what changed and why),
refuses if the tag exists. Then lints, tests, tags, pushes, and builds a tarball into `~/Downloads` with `.git`,
`.env` and `backups/` excluded — a tarball carrying `.git` overwrites the repository of anyone who unpacks it over
a clone, which happened to both a laptop and a node on 3 September 2026.

Nodes then take it with `./update.sh`.

## Where the pieces live

| repo | what | where it deploys |
|---|---|---|
| `fabcity/planetai-node` | this — the node runtime, packs, docs | every node |
| `fabcity/planetai` (site) | planetai.fab.city, including `/node0/` | Cloudflare |
| `fabcity/awesome-fabcity-data` | the Index's source registry; the Airtable `Data Sources` table syncs one-way from it | — |

Local siblings worth reconciling rather than duplicating: `FAB CITY/home-sensor`, `FAB CITY/fci-ingestion-tool`,
`MDG/PLANETAI-local-ingest`. If any has working code it should become a pack or be marked superseded.
