# Updating a node

One command, and it refuses to proceed if it can't back up first.

```bash
cd ~/planetai/planetai-node
./update.sh
```

That's the whole thing. What it does, in order, and why each step exists:

1. **Backs up the database.** If the backup fails, nothing else happens. Every bad update story starts with someone skipping this.
2. **Copies your `config/rules.yml` and `.env`** to `*.before-update`, so local edits are recoverable even if the new version replaces them.
3. **Pulls the new code** (`git pull --ff-only`). If you have uncommitted changes it stops and tells you, rather than merging something surprising.
4. **Applies the schema to your existing database.** This is the step people get wrong: Postgres runs `init.sql` *only* when the data volume is first created, so a running node never sees new tables, columns or views unless something applies them. `update.sh` pipes the same `init.sql` into the live database. Every statement in that file is idempotent — `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`, `DROP VIEW` then `CREATE VIEW` — so running it twice changes nothing.
5. **Adds new settings** from `.env.example` that your `.env` doesn't have yet, with their defaults, and lists them. It never overwrites a value you set.
6. **Rebuilds and restarts** the containers.
7. **Checks**: database healthy, app answering, readings still there, views rebuilt, packs loaded — and prints the row counts so you can see nothing was lost.

If step 4 fails the script stops and tells you where the backup is. Your data is untouched; the old containers are still running.

## Updating from a tarball instead of git

```bash
cd ~/planetai/planetai-node
tar xzf ~/Downloads/planetai-node-vX.Y.tar.gz --strip-components=1 --exclude='.env' --exclude='registry.json'
./update.sh --no-pull
```

`--exclude='.env'` matters. That file holds your Telegram token and your database password.

## Rolling back

```bash
git checkout v0.3          # or whatever tag you were on
docker compose up -d --build
```

Schema changes are additive only — new columns and views, never dropped or renamed — so an older app runs fine
against a newer database. That is a deliberate constraint, written into `SPEC.md §5`, and it's what makes rollback a
one-liner instead of a restore.

If you do need the data back:

```bash
gunzip -c backups/<node>-<date>.sql.gz | docker compose exec -T db psql -U planetai planetai
```

## What changes between versions, and what never does

**Never**: your readings, your alerts, your actions ledger. Every schema change is additive. If a release ever needs
to break that, it gets a major version and a paragraph in `CHANGELOG.md` explaining why, with the migration written out.

**Sometimes**: `config/rules.yml`. Rules move into packs as domains get factored out — the v0.2 update moved the three
PM2.5 rules into `packs/air-quality/`. Behaviour is preserved, but rule **ids** change (`indoor_pm25_high` became
`air-quality/indoor_pm25_high`), which resets that rule's cooldown once. You may get one duplicate alert. That's the
whole cost.

**Lesson worth taking from that**: if you tune a threshold, don't edit `config/rules.yml` — copy the pack folder,
rename it, and edit yours. Then updates never touch your numbers. See [`PACKS.md`](PACKS.md).

## Backfilling history on an existing node

The first-run bootstrap (92 days of CAMS air quality, NASA POWER climatology — [`PREFILL.md`](PREFILL.md)) only runs
when a node's `readings` table is empty, so a node installed before v0.4 never got it. To pull it in after the fact:

```bash
make bootstrap
```

Safe to run more than once — readings are deduplicated on `(sensor_id, metric, ts)`, so a repeat inserts nothing.

## Checking where you are

```bash
make health
```

`version` is the code, `schema` is the database. If `schema` says `pre-0.4 (run ./update.sh)`, the code moved but the
database didn't — that's exactly the failure this page exists to prevent, and the fix is `./update.sh`.
