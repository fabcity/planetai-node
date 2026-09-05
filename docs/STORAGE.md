# Where the data lives, and where copies go

Four things, four places, and a rule for each. `planetai storage` shows all of it on one screen.

| what | where | can it be on a NAS? | who else can have it |
|---|---|---|---|
| **the live database** | a local disk on the node | **no** | nobody |
| **backups** | `BACKUP_DIR`: local folder, NAS, USB drive | yes — that is what it is for | an rclone remote (`BACKUP_REMOTE`) |
| **daily exports** (open data) | `exports/<node>/YYYY-MM-DD.json` | yes, via the remote | IPFS, a parent node, the Index, anyone |
| **artifacts** (images, briefs) | `out/` | yes, via the remote | whoever you send them to |

## The live database stays on a local disk. Here is why.

Postgres writes assuming the filesystem honours `fsync` and file locking. SMB and NFS — what a NAS speaks — do not
honour them reliably, and Docker bind mounts over them on macOS are slow on top. The failure is not "a bit slower":
it is a database that corrupts silently on a power cut or a WiFi drop, and you find out at the worst moment. Every
Postgres and Docker guide says the same thing, and the node does not make an exception for you.

There is also the trap this project has now hit three times: a bind mount to a path that is not mounted becomes an
empty local folder with the NAS's name. The node would run fine, on its own disk, believing its data was elsewhere.

**So the answer to "can I move the database to the NAS" is: don't. Move the backups there, nightly, and the NAS
holds a copy of everything the node has ever known, refreshed every night.** That is the right relationship
between a small always-on machine and a big careful one. If the node dies, `planetai restore` on a new machine
brings it back from the NAS in a minute.

If you have a second **internal** disk or a partition on the node itself, `DATA_DIR=/path/on/that/disk` in `.env`
moves the database there: back up, stop, edit, start, restore. A USB drive that sleeps or gets unplugged is not that.

## Backups

Every night at 03:10 `backup.sh` dumps the database with `pg_dump`, checks the file is a valid gzip that contains a
readings table, keeps `BACKUP_KEEP` days (30), writes `LAST_OK`, and refuses outright if `BACKUP_DIR` is under
`/Volumes`, `/mnt` or `/media` and that drive is not mounted — it will not create a local folder with the drive's
name and back up into the wrong place.

```bash
planetai storage set backups /Volumes/NAS/planetai/bayu-2    # checks the drive is really mounted first
planetai backup                                               # run it now
planetai restore backups/bayu-2-2026-09-05.sql.gz             # replace the live database (safety backup first)
```

For node #1: the Mac mini keeps its database; `BACKUP_DIR` points at the Fab Lab NAS. That is the setup to have.

## A NAS that pulls (the setup node #1 uses)

Better than mounting the NAS on the node: the NAS fetches the dumps from the node over HTTP. The node serves
`/backups` (a list) and `/backups/<file>` behind a read-only `BACKUP_TOKEN`, separate from the admin token, and
`/exports` openly. A 60-line stdlib script in one small container on the NAS asks every hour and fetches what it lacks,
opening each dump to check it is a database before keeping it. The schedule and the copies live on the machine meant
to survive; the node never holds NAS credentials or a mount; nothing can silently turn out to be local.

`tools/nas/` has the script and its compose file. On the NAS: put them in a folder, write the node's token into
`.env`, `docker compose -p planetai-backup up -d`. `planetai storage` on the node prints the token.

## Off the machine

`BACKUP_REMOTE` is an [rclone](https://rclone.org) destination — one binary, forty-plus backends: S3, Backblaze B2,
Cloudflare R2, Google Drive, Dropbox, SFTP, WebDAV, Nextcloud, a second NAS. After each backup the last three days of
dumps and every export are copied there. `rclone config` once, then:

```bash
brew install rclone            # macOS;  apt install rclone  on Linux
rclone config                  # name a remote: b2, r2, drive, nas…
planetai storage set remote r2:planetai/bayu-2
```

Cheapest honest choice for a node: Backblaze B2 or Cloudflare R2 — object storage, cents per month for a node's
lifetime of dumps, and they hold up. Google Drive works and is free but is a person's account, not infrastructure.
Whatever you pick, the dump is not encrypted by us: it holds readings, alert texts and sensor names, not tokens, but
treat the remote as private. rclone's `crypt` backend encrypts a remote transparently if you want that.

## The export: what the node gives away

`/export?day=YYYY-MM-DD`, written nightly to `exports/<node>/`. Hourly means, minimums and maximums per sensor and
metric; the Index cells; the alerts (first line only); ρ. Your own sensors are named by role — `indoor-1`,
`outdoor-2` — not by device id; coordinates are the node's, rounded to three decimals; there are no raw readings, no
tokens, no chat ids, no exact position of anything. It is what a parent node, the Index at index.fab.city, a
researcher or the commons should receive, and it is licensed CC BY 4.0 in the file itself.

This is the *data in, data out* part of the project made literal: the node keeps the raw and gives away the
aggregate, every day, in a form anyone can use.

## IPFS: the commons layer

IPFS stores content by its hash. Two consequences decide how the node uses it. **Everything on it is public** — so
only the export goes, never the database or a dump. **Nothing persists unless someone pins it** — the node pins its
own exports, which means they live while the node does; durability beyond one machine comes from a second node pinning
yours, or a pinning service.

```bash
planetai ipfs        # starts the ipfs container (Kubo, low-power profile), turns publishing on
planetai backup      # publishes yesterday now; otherwise tonight
cat exports/bayu-2/CIDS.txt
```

Each line is a day and its CID. Anyone can fetch `ipfs://<cid>` or `https://ipfs.io/ipfs/<cid>`; the hash proves
the content is what the node produced. This is the honest version of "open data": not a portal someone maintains,
but files whose address is their content.

What IPFS is **not** for here: backups (public, and unpinned data vanishes), raw readings (public), or anything
you would not print on the wall of the lab.

## What to do this week, for node #1

1. `planetai update` (brings `/backups`, the token, and the endpoints), then `planetai storage` to read the token.
2. On TX-NAS-BALI the puller is already in place (`planetai-backup` project); write the token into its `.env` and start it.
3. Within an hour `backups/planetai/bayu-2/` on the NAS holds every dump the node has, and keeps collecting nightly.
4. Later, when there is a second node or a partner who wants the data: `planetai ipfs`. Not before; a commons with one
   contributor is a folder.
