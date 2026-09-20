# Install

One line, four questions, two minutes. Before it, if the machine is old or you are not sure it qualifies,
the preflight reads it in four seconds and installs nothing:

```bash
curl -fsSL planetai.fab.city/preflight | bash
```

It prints one table — OS, architecture, memory, free disk, container runtime, egress and ports — and every
failing row carries the one command that fixes it on that machine. Exit `0` means install; `1` means fix the
named thing and run it again; `2` means the machine is below the floor and Linux on the same hardware is the
route ([Platforms](platforms.md), [Revive a laptop](revive-a-laptop.md)). Never continue past `2`.

## The one line

```bash
curl -fsSL planetai.fab.city/install | bash
```

`/install` is a stub that reads the published version at `planetai.fab.city/node0/get/VERSION`, takes the
commit it names, and fetches the installer from exactly that commit, so the bootstrap, the preflight and the
node in the tarball come from one version. The node lands in `~/planetai` and the command in
`~/.local/bin/planetai`. To put a second node somewhere else on the same machine:

```bash
PLANETAI_HOME=~/somewhere bash -c "$(curl -fsSL planetai.fab.city/node0/install)"
```

## The four questions

| | question | what it writes |
|---|---|---|
| 1 | A short name for the node (lowercase, dashes; default: the hostname) | `NODE_NAME` |
| 2 | The place. Type a neighbourhood, town or city; it geocodes (Nominatim, then Open-Meteo), shows the hits, and asks you to confirm even when there is one. `lat,lon` is accepted. | `NODE_LAT`, `NODE_LON`, `NODE_TZ`, `NODE_CITY`; a pilot preset when the place falls inside Bali, Barcelona, Boston or Santiago; `BAD_ENABLED=0` outside Bali |
| 3 | What the node is for: a home · a business · a community or lab · a district or region | `NODE_KIND`; `district` also sets `NODE_SCALE=city` |
| 4 | Your sensor, if you have one: none · a Smart Citizen kit number · an AirGradient host (and whether it is indoors) · a PurpleAir IP (and whether it is indoors) | `SC_DEVICES` · `AIRGRADIENT_HOSTS` · `PURPLEAIR_HOSTS`, plus `SENSOR_INDOOR` |

Without a sensor the node still knows your weather, the satellite air model for your district and forty
years of climate for your coordinates — see [Before a sensor](before-a-sensor.md).

> **Gap in v0.57.** The AirGradient and PurpleAir adapters exist in `app/sources.py` and are tested, but this
> version does not register them for polling; the hosts you enter are used to keep your own kit out of the
> Bali Air Dispatch ring and for nothing else. A Smart Citizen kit is read. Details on the [sensors](sensors.md)
> page.

## Without a terminal

An agent, CI or a provisioning script installs from a file:

```bash
planetai setup --answers node.json
```

```json
{"name": "bayu-2", "place": "Kuta Selatan", "kind": "home", "sensor": {"sc": "19880"}}
```

`place` is geocoded (Open-Meteo, first hit) or replaced by `"lat"` and `"lon"`; `kind` defaults to `home`;
`sensor` is one of `{"sc": "19880"}`, `{"sc_user": "name"}`, `{"airgradient": "host"}`, `{"purpleair": "ip"}`
or absent. The answers become `install.sh` flags and the installer runs with `--yes`. It needs `python3` on
the machine, standard library only.

## What the installer does

Seven named steps, each printing its elapsed time and a heartbeat at least every ten seconds:

1. **Container runtime.** Detects OrbStack, Docker Desktop, Colima or a systemd Docker and starts it. On
   Linux without Docker it installs it: `pacman` on Arch, Docker's own Ubuntu repository on Ubuntu and its
   derivatives (Mint, Pop), `get.docker.com` elsewhere; then adds you to the `docker` group. It tells apart a
   daemon that is down, a socket you are not allowed to use, and a daemon that is crash-looping.
2. **`.env`.** Copies `.env.example` (mode 600), applies the preset for your pilot city if any, writes the
   answers, stamps `NODE_VERSION`, generates `POSTGRES_PASSWORD` and `ADMIN_TOKEN`. It refuses to start
   without coordinates, and refuses to generate a new database password over an existing database volume.
3. **Port and folders.** Checks `APP_PORT` (8080) is free; creates `backups`, `exports`, `out`.
4. **The database image.** Pulls `imresamu/postgis:16-3.4-alpine` (about 162 MB) with visible progress. It is published for amd64 and arm64, which is why a Raspberry Pi gets this far.
5. **Build and start.** `docker compose up -d --build`: the `app` image on `python:3.12-slim`, then both
   containers.
6. **Schema.** Waits for Postgres and applies `init.sql` — the whole schema, idempotent, the same file a
   fresh volume and an update both run.
7. **Doctor.** Modules in the image, database healthy, app answering, Telegram set, `backup.sh` executable.

Then it installs the nightly backup in your crontab (`17 3 * * *`), and, unless `--no-bootstrap`, the first
start pulls about 2,200 rows of history for your coordinates — 92 days of the Copernicus air model and NASA
POWER's monthly normals — so `planetai status` has something to say within minutes.

The install ends with a checklist. A cross next to *telegram connected* is expected; that comes next. A cross
next to *database* or *node answers* means something is wrong; see [Troubleshooting](troubleshooting.md).

## Re-running it

`~/planetai` with a `VERSION` file or a git checkout is an existing node, and the installer treats a re-run
as an update that keeps your `.env`. `planetai setup` on an existing node offers to update, reconfigure, do
nothing or remove. To start over, remove first:

```bash
planetai remove              # containers, database, folder, cron entry, the command itself; asks twice
planetai remove --keep-data  # the same, but the readings stay in their volume
```

The Docker volume outlives the folder, and every node's compose project is `planetai`, so a fresh install in
the same folder re-attaches the old database unless the volumes were deleted. `planetai remove` deletes them
by name and then checks. If the node will not start at all, `curl -fsSL planetai.fab.city/remove | bash -s --
--purge` finds the containers, the four volumes, the folder, the symlink and the crontab line without running
any of the node's own code.

## Where things are

```
~/planetai/
  .env                 every setting; mode 600; never committed, never pasted
  backups/             nightly pg_dump, kept BACKUP_KEEP days
  exports/<node>/      the daily CC BY 4.0 export, one JSON a day
  out/                 what pack scripts write: land-change maps, timelapses, mapping briefs
  packs/               the rules; add a folder to add a domain
  config/rules.yml     the two domain-blind core rules
  .planetai-setup.log  what setup and the CLI did
~/.local/bin/planetai  the command
```

## Machines that stay on

A node wants a computer that boots and logs in on its own after a power cut. An x86 Linux box first — a mini
PC, or an old laptop with Linux on it; the ten-year-old laptop is faster than the mini PC you would otherwise
buy. A Mac works ([Mac mini](mac-mini.md) has the settings that stop it sleeping). Windows through WSL2.
Raspberry Pi is untested: the database image has no arm64 build. The floors, with where each number comes
from, are on [Platforms](platforms.md).
