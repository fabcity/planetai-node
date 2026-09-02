# Start here — setting up node #1

Written for someone who is comfortable with a computer but has never run a server. The example throughout is
the real first node: Tomas's Mac in Bali, Smart Citizen Kit 19880 ("Bayu 2 – Indoor"), alerts to Telegram.
If that's you, follow it literally. If it isn't, swap the values in step 4 — and if you're on Linux, a Raspberry Pi,
or Windows, read `PLATFORMS.md` first; it's short and lists only what differs.

Time: about 45 minutes the first time, most of it waiting. Nothing here is dangerous to your computer; the
worst case is that it doesn't start and you send someone the log.

---

## The ten-minute version (if you've done this kind of thing before)

```bash
cd ~/Downloads && tar xzf planetai-node-v0.1.tar.gz && cd planetai-node
chmod +x install.sh backup.sh
./install.sh --name bayu-2 --sc 19880 --lat -8.8271 --lon 115.15709
make health && make stats
```

Then step 7 (Telegram) and step 8 (test an alert). Everyone else, read on.

---

## 1. What you're about to set up

A small program that runs quietly on your Mac. Every five minutes it asks your Smart Citizen kit what it's reading,
asks Bali Air Dispatch what the public sensors around you are reading, saves both, and checks a short list of rules.
When a rule is true — the room is getting bad, outside is worse than inside, the sensor has gone quiet — it sends one
message to a Telegram group. Once a day it sends a pulse so you know it's alive.

It also does two things that matter for the bigger project: it publishes what it knows in the Fab City Index format,
and it records whether anyone acted on an alert (that's the ρ measurement). You don't need to think about either on
day one; they happen on their own.

It runs inside two "containers" — think of them as two sealed boxes on your Mac: one holds the database, one holds
the program. They don't touch anything else on the machine. Deleting the folder removes everything.

## 2. What you need

**Hardware**
- A Mac. Apple Silicon (M1–M4) or Intel, macOS 13 or newer. It must stay on and connected — a Mac mini in a cupboard is ideal; a laptop that sleeps is not. **If it's a mini, read `MAC_MINI.md` first** (an hour, once): auto-login, OrbStack at login, restart after power failure, remote access, backups to the NAS. Those settings are what make it survive a brownout without you.
- About 2 GB of free disk. The database grows by roughly 50 MB a year at this sensor count.

**Sensor — one of these, or several**
- A **Smart Citizen Kit** that is online and reporting (node #1: kit **19880**). Read through its cloud API by kit number.
- An **AirGradient** ONE or Open Air on the same WiFi as the computer. Read directly over the LAN — no cloud, no account.
- A **PurpleAir** on the same WiFi. Also read directly over the LAN.
You'll check yours is alive in step 3. Mixed kinds on one node are fine. Details and what to buy: `sensors.md` and `PLATFORMS.md`.

**Accounts**
- Telegram on your phone (free). Needed for alerts, not for install — you can add it later.
- Nothing else. No cloud account, no API keys, no payment.

**Software you'll install**
- **OrbStack** (free for personal use) — this is what runs the two containers. Docker Desktop also works; OrbStack is lighter and quieter on a Mac.
- **Xcode Command Line Tools** — gives your Mac `git`, `make`, `python3`. You may already have them.

**Skills**
- Opening Terminal, pasting a line, pressing Enter. That's the whole skill. Terminal is in Applications → Utilities, or press ⌘-Space and type "Terminal".

## 3. Before you start — four checks (5 minutes)

Do these in order. Each one either passes or tells you exactly what to fix before you touch the installer.

**Check 1 — Is the sensor alive?**
*Smart Citizen:* open <https://smartcitizen.me/kits/19880> in a browser. The page should show readings with a "last reading" time in
the last hour. If it says the kit is offline or the last reading is days old, fix the kit first (power, WiFi) — the
node will install fine but have nothing to say.

Equivalent in Terminal, if you prefer:
```bash
curl -s https://api.smartcitizen.me/v0/devices/19880 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['name'], '| last reading:', d['last_reading_at'])"
```
You want a timestamp from today.

*AirGradient:* in a browser on the same WiFi, open `http://airgradient_<serial>.local/measures/current` (the serial is on
the device's sticker / in its display). You should see a block of JSON with `pm02`, `rhum`, `atmp`. If the `.local` name
doesn't resolve, find the device's IP in your router and use that instead.

*PurpleAir:* open `http://<its IP>/json?live=true`. JSON with `pm2_5_cf_1` and `current_humidity` means it's alive.

**Check 2 — Is Bali Air Dispatch answering?** (Bali only — skip elsewhere and add `--no-bad` in step 4.)
```bash
curl -s "https://baliairdispatch.com/api/v1/latest" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['count'], 'stations, generated', d['generated_at'])"
```
You want a number above 10 and a timestamp from today. If this fails, the node still works — it just won't have the
outdoor comparison until BAD is back.

**Check 3 — Command Line Tools.**
```bash
xcode-select -p
```
If it prints a path (like `/Library/Developer/CommandLineTools`), you're fine. If it complains, run
`xcode-select --install`, accept the dialog, wait for it to finish (a few minutes), then re-run the check.

**Check 4 — OrbStack.**
Download from <https://orbstack.dev>, open the .dmg, drag to Applications, open it once. It asks for permission to
install a helper; say yes. Then in Terminal:
```bash
docker info >/dev/null && echo "docker ok"
```
You want `docker ok`. If you see "Cannot connect to the Docker daemon", OrbStack isn't running — open it from
Applications and try again.

Four passes? Continue.

## 4. Install (10 minutes, mostly waiting)

Put the folder somewhere permanent — not Downloads. `~/planetai` is good.

```bash
mkdir -p ~/planetai && cd ~/planetai
tar xzf ~/Downloads/planetai-node-v0.1.tar.gz
cd planetai-node
chmod +x install.sh backup.sh
./install.sh --name bayu-2 --sc 19880 --lat -8.8271 --lon 115.15709
```

That's the Smart Citizen form. The same command with a different sensor:

```bash
./install.sh --name warung-3 --airgradient airgradient_84fce6.local --lat -8.65 --lon 115.22          # outdoor AirGradient, Bali
./install.sh --name clinic-1 --purpleair 192.168.1.60 --indoor --lat -8.79 --lon 115.16                # indoor PurpleAir
./install.sh --name bcn-lab  --sc 15423 --airgradient ag-roof.local --lat 41.39 --lon 2.19 --no-bad     # Barcelona: two sensors, no Bali reference
```

(`chmod +x` marks the two scripts as runnable. Archives sometimes drop that flag; if you skip this line you get
`zsh: permission denied: ./install.sh`.)

The values, and what to change if you aren't Tomas:
- `--name` — a short name for this node, lowercase, dashes. It appears in every alert. Pick something a household would recognise.
- `--sc` / `--airgradient` / `--purpleair` — your sensor(s). Kit number for Smart Citizen; hostname or IP for the LAN sensors. Comma-separate several of the same kind; combine kinds freely.
- `--indoor` — say so if your AirGradient/PurpleAir is inside. Smart Citizen kits carry this themselves.
- `--lat --lon` — where the node physically is. Google Maps → right-click the spot → the two numbers. Used to decide which public sensors count as "nearby".
- `--no-bad` — outside Bali. Turns off the Bali Air Dispatch reference layer.

What you'll see: a few lines about your platform, then `building and starting` — this is the slow part, one to
three minutes the first time as it downloads Postgres and builds the program. Then a `doctor:` block with three ticks
or crosses, and a `done.` line.

If `doctor` shows **✗ telegram set** and the other two are ✓ — that's expected on day one. Alerts go to the log until
step 7.

If `doctor` shows **✗ db healthy** or **✗ app answering** — go to Troubleshooting, don't continue.

## 5. Watch the first five minutes

```bash
make health
```
You'll see `"polls": 0` and `"last_poll": null` at first. Wait until the five-minute mark, run it again: `polls` should
be 1 and `ingested` a number in the tens. If `last_error` has text in it, read it — it usually names the source
that failed (kit offline, BAD unreachable).

```bash
make stats
```
This is what the rules see. One row per sensor per metric. Look for:
- a row for your sensor with `"metric": "pm25"` and `"local": true` — `sc-19880`, `ag-84fce612a5b4`, or `pa-…` — with `indoor` set the way you'd expect. For AirGradient and PurpleAir you'll also see `pm25_raw`: the uncorrected number, kept beside the humidity-corrected `pm25`.
- rows starting `bad-…` with `"local": false` — public reference stations within 15 km.

If there are **no `bad-` rows**, the radius is too tight for where you are. Open `.env`, change `BAD_RADIUS_KM=15`
to `25`, run `make restart`, wait five minutes, check again. Kuta Selatan's nearest public outdoor sensors are
in Jimbaran and south Denpasar.

```bash
make logs
```
Live log. `Ctrl-C` to stop watching (this does not stop the node). You'll see a line per poll and, when a rule fires,
a line starting `ALERT`.

## 6. The two things that need a full day

Rolling averages need time to exist. After 24 hours:

```bash
curl -s localhost:8080/cells | python3 -m json.tool
```
This is what your node reports to the Fab City Index. You should see an `Environmental|Community` row with `"state": "live"`
once it has twelve hourly buckets from your kit. Before that, `partial`. If this command errors, see Troubleshooting —
it's the newest part of the code and the first thing we'd want to know about.

```bash
curl -s localhost:8080/rho | python3 -m json.tool
```
`alerts_act: 0` and `rho: null` is correct until an alert has fired and someone has acted on it (step 9).

## 7. Turn on Telegram (10 minutes)

1. In Telegram, message **@BotFather**. Send `/newbot`. Give it a name (e.g. "Bayu 2 air") and a username ending in `bot`. It replies with a **token** — a long string like `7123456789:AAF…`. Copy it. Treat it like a password.
2. Create a Telegram **group** for the alerts (you, and later the household). Add your new bot to the group. Make the bot an **admin** of the group (group → members → tap the bot → promote) — otherwise it can't see messages and the next step won't work.
3. Send any message in the group, e.g. "hello". Then open this in a browser, with your token pasted in:
   `https://api.telegram.org/bot<YOUR TOKEN>/getUpdates`
   In the response find `"chat":{"id":-100…` — that negative number is your **chat id**. Copy it.
4. Open the settings file:
   ```bash
   nano .env
   ```
   Arrow down to `TELEGRAM_BOT_TOKEN=` and paste the token after the `=`. Same for `TELEGRAM_CHAT_IDS=` with the chat id.
   `Ctrl-O` Enter to save, `Ctrl-X` to leave. (Or open `.env` in TextEdit — it's just a text file. Don't let TextEdit rename it.)
5. Apply (settings changes need the program restarted; rules don't):
   ```bash
   make restart
   ```
The next alert — and tomorrow's daily pulse — arrives in the group.

## 8. Test an alert without waiting for bad air (3 minutes)

Rules live in `config/rules.yml` and reload by themselves within a minute. So:

1. Open `config/rules.yml` (nano or TextEdit). Find `indoor_pm25_high`. Change `mean_15m > 35.5` to `mean_15m > 1`.
2. Save. Wait up to 60 seconds. `make logs` shows an `ALERT` line; if Telegram is set up, the message lands in the group, ending with something like `#3` — that's the alert id.
3. **Change it back** to `35.5` and save. Cooldown (120 min) means it won't re-fire immediately.

You've now seen the whole path: sensor → database → rule → message.

## 9. Close the loop (this is the part that measures ρ)

When an alert says "close the windows" and you close the windows, tell the node. Take the `#id` from the message:

```bash
curl -X POST localhost:8080/actions -H 'content-type: application/json' \
  -d '{"alert_id": 3, "stage": "acted", "actor": "tomas", "note": "test alert — closed windows"}'
```

Stages: `acknowledged` (I saw it), `acted` (I did the thing), `measured` (I checked it helped). Then:

```bash
curl -s localhost:8080/rho | python3 -m json.tool
```
`rho` is now a number between 0 and 1 — the share of act-level alerts that got a human response within 24 hours — and
`median_minutes` is how long it took. That number, at hundreds of addresses, is the Fab City Index's action-latency term.
Today it's you and curl. A Telegram reply handler and a phone app do exactly the same call.

## 10. Living with it

**Where things are.** Everything is in the `planetai-node` folder. Your settings: `.env` (apply with `make restart`). Your rules: `config/rules.yml` (apply themselves within a minute).
Your data: inside Docker's `planetai_db` volume (not a file you can open, but `backup.sh` turns it into one).

**Daily.** Nothing. The pulse arrives once a day. If it stops arriving, the node or the Mac is down.

**Weekly.** `make alerts` to see what fired. Ask yourself: was it right, was it useful, was it too often. Adjust
thresholds or cooldowns in `config/rules.yml`; changes apply within a minute, no restart.

**Backups.** `install.sh` scheduled `backup.sh` nightly at 03:17. Files land in `./backups/` and are kept 14 days.
To keep them off the Mac, set `BACKUP_DIR` in `.env` to a folder on the NAS or an external drive. Run one by hand to
check: `make backup`.

**Stop / start.**
```bash
docker compose down      # stop (data is kept)
docker compose up -d     # start again
```
Restarting the Mac: OrbStack starts at login and the containers come back on their own (they're set to).

**Update** (when a new version is shared):
```bash
cd ~/planetai/planetai-node && git pull && docker compose up -d --build
```
(If you got the tarball rather than git: unpack the new one *over* the folder, keep your `.env` and `config/rules.yml`, run the same `docker compose` line.)

**Never** run `docker compose down -v` — the `-v` deletes the database. Never share your `.env`; it holds the bot token.

## 11. Troubleshooting

**`zsh: permission denied: ./install.sh`** — the script lost its "runnable" flag in the download. `chmod +x install.sh backup.sh`, then run it again.

**`WARN Docker Compose requires buildx plugin`** — harmless. Docker falls back to its older builder, which works. (OrbStack ships buildx; this appears with some Docker Desktop or Homebrew installs.)

**`doctor: ✗ db healthy`** — Usually the first start needs longer than the 8-second wait. Run `docker compose ps`; if `db` says "starting", wait 30 s and run `./install.sh …` again (it's safe to re-run). If it says "exited", `docker compose logs db` — the common cause is a port clash (something else on 5432). Fix: in `docker-compose.yml` change `"127.0.0.1:5432:5432"` to `"127.0.0.1:5433:5432"`.

**`Bind for 0.0.0.0:8080 failed: port is already allocated`** (or the installer stops with "port 8080 is already in use") — something else on this Mac, usually another Docker project, has 8080. Either stop it, or open `.env`, set `APP_PORT=8081`, and run `./install.sh …` again. All `make` commands follow `APP_PORT`; if you type `curl` by hand, use the new number.

**`doctor: ✗ app answering`** — `docker compose logs app`. Read the last ten lines. If it mentions `.env` or a missing variable, compare your `.env` with `.env.example`.

**`make health` shows `last_error` mentioning a source** — that source failed on the *last* poll; it clears by itself when the next poll succeeds. `smartcitizen`: the kit or their API is down, check the kit page. `airgradient`/`purpleair`: the device is off, on a different WiFi, or its `.local` name stopped resolving — try its IP in `.env`. `baliairdispatch`: their server; nothing to do. Several sources are separated by `|`. The node keeps running on whatever is answering.

**No `bad-` rows in `make stats`** — widen `BAD_RADIUS_KM` (step 5). If BAD's API is down, `last_error` says so; wait.

**Telegram silent** — Is the bot an admin of the group? Is the chat id negative and complete? Is there a stray space in `.env`? After any change to `.env`: `make restart`. Then force a test alert (step 8).

**`/cells` or `/rho` returns an error** — This is the newest code and hasn't been run against a live database by its author. Copy the output of `docker compose logs app | tail -30` and send it. It's a five-minute fix on the other end and we want to know.

**It worked yesterday and the pulse didn't come today** — Is the Mac awake? Is OrbStack running (menu bar icon)? `docker compose ps` — both should say "running". If not, `docker compose up -d`.

**Everything is confusing and you want to start over** — `docker compose down -v` (this *does* delete the data — only do it if you mean to), delete the folder, unpack again, go to step 4.

## 12. When you ask for help, send this

```bash
cd ~/planetai/planetai-node
make health; docker compose ps; docker compose logs app | tail -50
```
Paste all of it. Not your `.env`.

---

## What "working" looks like after a week

- The daily pulse arrives every morning with `ours: 1`, `refs` of at least 3, and two PM2.5 numbers.
- `make alerts` shows a handful of alerts, not dozens. If it's dozens, the thresholds are too low for an indoor kit; raise them.
- You changed something — a window, a purifier, a habit — because of at least one message, and you told the node with `POST /actions`.
- `/cells` shows `Environmental|Community` as `live`.
- There's a fresh file in `backups/` from last night.

That's node #1 done. Node #2 is someone else's Mac and someone else's kit, following this same page without you in the room. When that works, we've got a product.
