# Changelog

## v0.1.1 — 2026-09-02 (same night as v0.1)

Fixes from the first live install at Fab Lab Bali, and the first two asks from the field.

**Fixed**
- `last_error` in `/health` now clears when every source succeeds on a poll. It used to show the last failure forever. Several failing sources are joined with ` | `.
- Installer: scripts shipped without exec bits; `COPY` syntax failed on Docker's legacy builder; `index.py` wasn't copied into the image; a port clash with another container failed ten seconds in instead of before building. All fixed; `APP_PORT` in `.env` moves the host port.
- `.env`: inline comments after empty values confused the parser (phantom `PARENT_API_URL`). Comments now sit on their own lines; values are stripped in code; a parent URL without `http(s)://` is ignored with a warning.
- Rules are mounted as a directory (`config/`) so editors that save-by-replace (TextEdit) don't break the mount.
- `make restart` applies `.env` changes; `daily_pulse` prints integers and says "no public sensors in range" instead of a dash.

**Added**
- **AirGradient** and **PurpleAir** adapters — both read directly over the LAN, no cloud. EPA 2021 correction applied; raw stored beside corrected. PurpleAir path reproduces Bali Air Dispatch's published Klungkung example.
- Installer flags `--airgradient`, `--purpleair`, `--indoor`, `--no-bad`; env `AIRGRADIENT_HOSTS`, `PURPLEAIR_HOSTS`, `SENSOR_INDOOR`.
- Linux: installer installs `make`/`curl` if missing. Windows: WSL2 detected; uses Docker Desktop's engine instead of trying to install one.
- `docs/PLATFORMS.md` — Linux, Raspberry Pi, Windows (WSL2), Intel Mac: only what differs.
- `docs/START_HERE.md` — choose-your-sensor, pre-flight checks for each, multi-sensor install examples.

**Not changed**
- Rules, schema, Index contract, ρ ledger. A v0.1 node updates in place: `git pull && docker compose up -d --build`.

## v0.1 — 2026-09-02

First running node. Smart Citizen 19880 + Bali Air Dispatch → Postgres → five SQL rules → Telegram. `GET /cells` (fci-cells-v0), `POST /actions` (ρ). Node #1: "Bayu 2 – Indoor", Kuta Selatan.
