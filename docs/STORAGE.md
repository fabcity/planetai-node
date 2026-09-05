# Where the data lives

`planetai storage` shows all of this on one screen.

| what | where | NAS? | who else gets it |
|---|---|---|---|
| live database | a local disk on the node | no | nobody |
| backups | `BACKUP_DIR`, or pulled by a NAS | yes | an rclone remote |
| daily exports (open data) | `exports/<node>/` | yes | IPFS, a parent node, the Index, anyone |
| artifacts (images, briefs) | `out/` | yes | whoever you send them to |

## The database stays on a local disk

Postgres needs `fsync` and file locking. SMB and NFS, what a NAS speaks, do not honour them reliably. The result is
not slowness: it is a database that corrupts on a power cut and you find out at a restore. There is also the trap this
project hit three times this week: a mount path that is not mounted becomes an empty local folder with the NAS's name.

So the mini keeps the database. The NAS keeps a copy of every dump. If the mini dies, `planetai restore` on any machine
brings it back to last night in a minute.

`DATA_DIR=/path` in `.env` moves the database to another **internal** disk or partition: backup, stop, edit, start,
restore. A USB drive that sleeps is not that.

## Backups

Nightly at 03:10, `backup.sh` dumps the database, checks the file is a valid gzip with a readings table, keeps
`BACKUP_KEEP` days (30), and writes `LAST_OK`. If `BACKUP_DIR` is under `/Volumes`, `/mnt` or `/media` and the drive
is not mounted, it refuses rather than write to a local folder with the drive's name.

```bash
planetai backup                                    # now
planetai restore backups/bayu-2-2026-09-05.sql.gz  # replaces the database; takes a safety backup first
```

## A NAS that pulls (node #1's setup)

Better than mounting the NAS on the node: the NAS fetches the dumps. The node serves `/backups` behind a read-only
`BACKUP_TOKEN` (separate from the admin token) and `/exports` openly. On the NAS, one 60-line script in a small
container asks every hour and fetches what it lacks. It opens each dump to check it is a database before keeping it.
Nothing is deleted there. The node holds no NAS credentials and mounts nothing.

`tools/nas/` has the script and compose file. On the NAS:

```bash
# put pull.py, docker-compose.yml and .env in one folder; write the node's token into .env
docker compose -p planetai-backup up -d
docker logs -f planetai-backup             # "bayu-2: 0 new, 3 dumps held"
```

`planetai storage` on the node prints the token. Node #1's dumps have been on TX-NAS-BALI at
`/volume2/docker_1/agentic-os/backups/planetai/bayu-2/` since 5 September 2026, collected hourly.

## Off the machine

`BACKUP_REMOTE` is an [rclone](https://rclone.org) destination: S3, Backblaze B2, Cloudflare R2, Google Drive,
Dropbox, SFTP, WebDAV, Nextcloud. After each backup the last three days of dumps and all exports are copied there.

```bash
brew install rclone && rclone config
planetai storage set remote r2:planetai/bayu-2
```

B2 or R2 cost cents a month for a node's lifetime of dumps. Drive works but is a person's account, not infrastructure.
Dumps hold readings and alert texts, not tokens; still, treat the remote as private. rclone's `crypt` backend
encrypts if you want that.

## The export

`/export?day=YYYY-MM-DD`, written nightly to `exports/<node>/`. Hourly mean, min and max per sensor and metric; the
Index cells; alerts (first line); ρ. Your sensors are named by role (`indoor-1`, `outdoor-2`), not device id.
Coordinates are the node's, to three decimals. No raw rows, no tokens, no chat ids. CC BY 4.0, stated in the file.

This is what a parent node, the Index, a researcher or the commons should receive. The node keeps the raw and gives
away the aggregate.

## IPFS

Content-addressed and public. So only the export goes, never the database or a dump. And nothing persists unless
pinned: the node pins its own exports, which live while the node does. Durability beyond one machine needs a second
node pinning yours, or a pinning service.

```bash
planetai ipfs            # starts Kubo (low-power profile), turns publishing on
planetai backup          # publishes yesterday now
cat exports/bayu-2/CIDS.txt
```

Anyone can fetch `ipfs://<cid>`. Do this when a second node or a partner wants the data. A commons with one
contributor is a folder.
