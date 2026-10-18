# A NAS that collects the node's backups

Pull, not push. The node dumps its database every night at 03:17 and serves the list at `/backups`; the NAS asks
every hour what the node has and fetches anything missing. The schedule and the copies live on the machine meant to
survive; the node never holds NAS credentials or a mount; there is no folder that can silently turn out to be local.

Two files, both here: `pull.py` (about 120 lines, stdlib only) and `docker-compose.yml` (one container, 128 MB). Put them
on the NAS, write the node's address as `PLANETAI_URL` and its read-only `BACKUP_TOKEN` as `PLANETAI_TOKEN` into `.env` next
to them (`planetai storage` prints the token), and:

```bash
docker compose -p planetai-backup up -d
docker logs -f planetai-backup      # "bayu-2: 1 new, 1 dumps held"
```

Dumps land in `backups/planetai/<node>/`, exports in `backups/planetai/<node>/exports/`, and the earth pack's
change statistics and maps, if the node runs it, in `backups/planetai/<node>/earth/`. Every dump is opened and
checked for a `CREATE TABLE` before it is kept, so a truncated download fails now, not during a restore. Nothing is
ever deleted here: a node's dumps are a few hundred kilobytes a day.

Restore from the NAS onto any machine: copy a dump over and `planetai restore <file>`.

Node #1's copies live on TX-NAS-BALI (Synology), project `planetai-backup`, since 5 September 2026.
