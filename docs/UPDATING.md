# Updating

```bash
planetai update
```

In order: back up the database (and refuse to go on if that fails); fetch tags and pull, or download the tarball if the
node has no repository access; apply `init.sql`, which is idempotent, to the live database; merge new keys from
`.env.example` into `.env` under a dated marker; rebuild the image; restart; run the doctor; report the schema before
and after.

`update.sh` runs from a copy of itself, because pulling rewrites the file bash is reading and it would otherwise continue
from a random offset in the new file.

## If it fails

**`git pull failed`**: usually `.DS_Store`. `find . -name .DS_Store -delete`, then update again. If you edited files in
the node folder, `git stash`.

**`backup failed — not updating`**: the update refused on purpose. `planetai backup` alone shows why; `planetai storage`
shows where it is trying to write.

**`app answering ✗`**: `docker compose logs app | tail -40`. Paste it.

## Rollback

```bash
git checkout v0.17        # or the tag before
planetai restart
planetai restore backups/<node>-<date>.sql.gz    # only if the schema went forward and you need the old shape
```

## Testers without repository access

`update` downloads `planetai.fab.city/node0/get/planetai-node.tar.gz`, verifies its checksum, and unpacks over the folder
keeping `.env`, backups, exports and packs. Publish a new one with `tools/bundle.sh` and `make deploy` in the site repo.
