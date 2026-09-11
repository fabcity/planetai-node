# Fixtures

The fixtures a design round renders against live in **`app/issues/fixtures/`**, not here.

They have to be inside `app/`, because `docker-compose.yml` builds the app image with `build: ./app`
— the build context is that directory, so a `COPY` cannot reach up into `docs/`, and `docs/` is not
one of the five paths the compose file mounts either (`config`, `packs`, `out`, `backups`,
`exports`). A fixture under `docs/` would be readable on a dev laptop and absent on every node,
which is the opposite of what a fixture is for.

They are served by the issues router at `/issues/fixtures/<name>`, and the dashboard reads that
route with `?fixture=<name>`. Deliberately not from `/static/`: that prefix is on the
`SHARE_LEVEL=off` allowlist, and a snapshot carries alert texts and sensor names.

Today: `node1-2026-09-06.json` — node #1 as it stood on 6 September 2026 at 14:08 UTC. Its own
`provenance` block says which parts were read from the API verbatim, which were transcribed off the
capture's screenshot, and which had to be reconstructed.

To make another one, on the node: `planetai snapshot --out <file>`.
