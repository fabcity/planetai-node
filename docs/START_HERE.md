# Start here

Setting up a node, for someone who is comfortable with a computer but has never run a server.

A node works anywhere. It needs coordinates, a computer that stays on, and about forty-five minutes,
most of it waiting. A sensor is optional on day one. Nothing here can damage your machine; the worst
case is that it does not start and you send someone the log.

Wherever you see **Bali** below it is a worked example, not a requirement. Node #1 happens to run in
Kuta Selatan on a Smart Citizen kit, so its real values make the commands concrete. Yours will differ,
and section 2 is how you find yours.

On Linux, a Raspberry Pi, or Windows, read [`PLATFORMS.md`](PLATFORMS.md) first. It is short and lists
only what differs.

---

## The short version

```bash
curl -fsSL planetai.fab.city/install | bash
```

It asks a name, a place and whether you have a sensor, and installs. Then `planetai telegram` connects your
phone and `planetai test-alert` fires one so you see it work. If that went fine, you can stop reading.

The rest of this page is for when you want to understand what it did, when something goes wrong, or when you
would rather do it by hand.

---

## 1. What you are about to set up

A small program that runs quietly on a computer you own. Every five minutes it reads whatever sensors you
have given it, reads a global air-quality model at your coordinates, saves both, and checks a short list
of rules. When a rule is true it sends one message to Telegram. Once a day it sends a pulse so you know
it is alive.

It also publishes what it knows in the Fab City Index format and records whether anyone acted on an
alert, which is the ρ measurement. Both happen on their own; you do not need to think about them on day one.

Everything runs in two containers: one holds the database, one holds the program. They touch nothing else
on the machine. Deleting the folder removes it all.

## 2. Your five inputs

Before installing, write these down. They are the only things about your place the node needs to know.

### a. Coordinates

Open Google Maps or OpenStreetMap, right-click the spot where the node will physically sit, copy the two
numbers. Decimal degrees, south and west negative. Four decimal places is plenty.

    Kuta Selatan, Bali   -8.8271, 115.15709
    Santiago             -33.4489, -70.6693
    Delhi                 28.6139, 77.2090

Coordinates decide which public sensors count as nearby and where the global models are sampled. Get them
roughly right rather than exactly; a few hundred metres does not matter.

### b. Time zone

An IANA name, not an offset: `Asia/Makassar`, `America/Santiago`, `Asia/Kolkata`, `Europe/Madrid`. If you
are unsure, `timedatectl` on Linux or `sudo systemsetup -gettimezone` on macOS prints the one your machine
is using. Daily buckets and the daily pulse use this. An offset like UTC+7 will not work.

### c. A city key

One lowercase word, used to label the Index cells this node publishes: `NODE_CITY`. If you are at one of
the four Fab City Index pilots, use its key so your cells join the existing rows:

    bali · barcelona · boston · santiago

Anywhere else, invent one that reads as a place: `delhi`, `medellin`, `taipei`. It is a label, not a
registration, and nothing breaks if the Index has never heard of it. When you want the site on the map,
open a pull request against `registry.json`.

### d. Sensors, or none

Pick whichever you have. You can mix them, and you can start with none.

| you have | flag | how it is read |
|---|---|---|
| a Smart Citizen kit | `--sc 19880` | its cloud API, by the number in the kit's URL |
| an AirGradient | `--airgradient ag-roof.local` | directly over your WiFi, no cloud, no account |
| a PurpleAir | `--purpleair 192.168.1.60` | directly over your WiFi, use the IP |
| nothing yet | omit all three | the node still runs, on models alone |

Add `--indoor` if the AirGradient or PurpleAir sits inside. Smart Citizen kits carry that setting themselves.

**With no sensor**, the node pulls three months of Copernicus CAMS history and forty years of NASA POWER
normals for your coordinates on first start, and sends you a daily line about your own location. That is
the cheapest way to see whether this is worth putting hardware behind.
[`PREFILL.md`](PREFILL.md) covers what arrives and where it comes from.

### e. A reference for "outside"

The useful rules compare the air where you are against the air around you. That reference comes from one of
three places, and the node picks the best one available:

1. **Public sensors near you**, if this node reads a network that has any in range. Today that means Bali, through the Bali Air Dispatch adapter. Elsewhere the equivalent is OpenAQ, which now needs a free API key and is therefore not switched on by default.
2. **Copernicus CAMS**, a global model sampled at your coordinates. Free, no key, on by default, works in Delhi and Santiago exactly as it does in Bali. Roughly 11 km resolution, so it knows your district rather than your street.
3. **Your own outdoor sensor**, if you have one, which is better than either.

You do not configure this. The node uses public sensors when it has them and CAMS when it does not, and
every alert says which. Outside Bali, add `--no-bad` so it does not poll an island archive that cannot
help you.

### Optional: your city's open-data portal

If your city runs a CKAN portal, the node can watch how well it is maintained and publish that as a
`Governance|City` cell. Test any candidate URL in a browser:

    https://<portal-domain>/api/3/action/package_search?rows=0

JSON with a `count` means it is CKAN and the node can read it. A 404 means it is something else, likely
Socrata or ArcGIS, for which adapters are not written yet. Known-good ones:

    barcelona  https://opendata-ajuntament.barcelona.cat/data
    boston     https://data.boston.gov
    santiago   https://datos.gob.cl
    bali       https://balisatudata.baliprov.go.id

## 3. Before you start, four checks

Each one either passes or tells you exactly what to fix.

**Check 1. Is your sensor alive?** Skip if you have none.

*Smart Citizen:* open `https://smartcitizen.me/kits/<your kit number>` in a browser. You want readings with a
timestamp from the last hour. In Terminal, replacing the number with yours:

```bash
curl -s https://api.smartcitizen.me/v0/devices/19880 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['name'], '| last reading:', d['last_reading_at'])"
```

*AirGradient:* on the same WiFi, open `http://airgradient_<serial>.local/measures/current`. You want JSON with
`pm02`, `rhum`, `atmp`. If the `.local` name does not resolve, find the device's IP in your router and use that.

*PurpleAir:* open `http://<its IP>/json?live=true`. JSON with `pm2_5_cf_1` means it is alive.

**Check 2. Can you reach the global sources?** These work everywhere and need no account.

```bash
curl -s "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=28.6139&longitude=77.2090&current=pm2_5" | head -c 200
```

Use your own coordinates. A JSON block with a `pm2_5` number means the node will have something to say from
its first minute, sensor or not. *In Bali only,* also check the island archive:

```bash
curl -s "https://baliairdispatch.com/api/v1/latest" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['count'], 'stations, generated', d['generated_at'])"
```

**Check 3. Command line tools** (macOS).

```bash
xcode-select -p
```

A path means you are fine. An error means run `xcode-select --install`, accept the dialog, wait, re-check.

**Check 4. Docker.** Install [OrbStack](https://orbstack.dev) (free for personal use; Docker Desktop also works),
open it once, then:

```bash
docker info >/dev/null && echo "docker ok"
```

"Cannot connect to the Docker daemon" means OrbStack is not running.

Four passes? Continue.

## 4. Install

The one-liner at the top does everything in this section, including asking you the inputs from section 2 in a
form and looking up coordinates and time zone from a place name. What follows is the manual route, useful if you
want flags you can script or you are installing several nodes.

```bash
mkdir -p ~/planetai && cd ~/planetai
git clone https://github.com/fabcity/planetai-node && cd planetai-node
chmod +x install.sh backup.sh update.sh bin/planetai
```

Then one command, built from your five inputs. Four sites ship as presets, which fill in coordinates,
time zone, language and the city's portal:

```bash
./install.sh --preset bali      --name bayu-2   --sc 19880
./install.sh --preset santiago  --name lab-roof --airgradient ag-roof.local
./install.sh --preset barcelona --name poblenou --purpleair 192.168.1.60 --indoor
./install.sh --preset boston    --name cba-lab
```

Nowhere on that list? Pass your own values. This is the Delhi form, with no sensor yet:

```bash
./install.sh --name mayur-vihar --lat 28.6139 --lon 77.2090 --no-bad
```

and with one:

```bash
./install.sh --name mayur-vihar --lat 28.6139 --lon 77.2090 --no-bad --airgradient ag-balcony.local --indoor
```

Then open `.env` and set the two things a flag does not cover:

```
NODE_CITY=delhi
NODE_TZ=Asia/Kolkata
```

Run `make restart` after editing. Adding your city as a preset is one small file in `presets/` and a pull
request, which spares the next person this step.

**What the flags mean**

- `--name` a short lowercase name for this node. It appears in every alert; pick something the household recognises.
- `--preset` a shipped site: coordinates, time zone, language, portal. Anything it sets can be overridden.
- `--lat --lon` required if you are not using a preset.
- `--sc` / `--airgradient` / `--purpleair` your sensors. Comma-separate several of a kind, and mix kinds freely.
- `--indoor` the LAN sensor is inside.
- `--no-bad` you are not in Bali. Turns off the island archive.

**What you will see:** a line about your platform, then a slow first build of one to three minutes, then a
`doctor:` block, then `done.` A cross next to *telegram set* is expected; that is step 7. A cross next to
*db healthy* or *app answering* means stop and go to troubleshooting.

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
- a row for each of your own sensors, with `"local": true` and `indoor` set the way you expect. Ids look like `sc-19880`, `ag-84fce612a5b4`, `pa-84f3eb…`. AirGradient and PurpleAir also produce `pm25_raw`, the uncorrected number kept beside the humidity-corrected `pm25`.
- a row `cam-point` or `cams-point` with `"kind": "model"`. That is the global model at your coordinates, and it appears everywhere on earth.
- in Bali only, rows starting `bad-`, which are public reference stations within `BAD_RADIUS_KM`.

Outside Bali there will be no `bad-` rows and that is correct. Your reference for "outside" is the CAMS model
row, and the comparison rules use it automatically. In Bali, no `bad-` rows means the radius is too tight:
open `.env`, change `BAD_RADIUS_KM=15` to `25`, `make restart`, wait five minutes, check again.

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

## 7. Turn on Telegram

The guided way, two minutes: `planetai telegram`. It checks the token with Telegram, waits for you to send the bot a
message, finds your chat id itself, writes both to `.env`, sends you a hello and restarts the node. The manual
steps below are what it does, for when you want to see them.

### 7b. By hand (10 minutes)

1. In Telegram, message **@BotFather**. Send `/newbot`. Give it a name (whatever you like, for example "Mayur Vihar air") and a username ending in `bot`. It replies with a **token** — a long string like `7123456789:AAF…`. Copy it. Treat it like a password.
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

## 8. Test an alert without waiting for bad air

`planetai test-alert` adds a temporary rule that fires once, waits for it, removes itself, and tells you the alert
id to close the loop with `planetai act <id>`. Your own rules are never touched. Or by hand:

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

**`make health` shows `last_error` mentioning a source** — that source failed on the *last* poll; it clears by itself when the next poll succeeds. `smartcitizen`: the kit or their API is down, check the kit page. `airgradient`/`purpleair`: the device is off, on a different WiFi, or its `.local` name stopped resolving — try its IP in `.env`. `open-meteo`: their server or your connection; it clears itself. `baliairdispatch`: only relevant in Bali, and only their server can fix it. Several sources are separated by `|`. The node keeps running on whatever is answering.

**No `bad-` rows in `make stats`** — expected everywhere except Bali; the CAMS model row is your reference instead. In Bali, widen `BAD_RADIUS_KM` (step 5), or wait if `last_error` says their API is down.

**Telegram silent** — Is the bot an admin of the group? Is the chat id negative and complete? Is there a stray space in `.env`? After any change to `.env`: `make restart`. Then force a test alert (step 8).

**`/cells` or `/rho` returns an error** — This is the newest code and hasn't been run against a live database by its author. Copy the output of `docker compose logs app | tail -30` and send it. It's a five-minute fix on the other end and we want to know.

**It worked yesterday and the pulse didn't come today** — Is the Mac awake? Is OrbStack running (menu bar icon)? `docker compose ps` — both should say "running". If not, `docker compose up -d`.

**Everything is confusing and you want to start over** — `docker compose down -v` (this *does* delete the data — only do it if you mean to), delete the folder, unpack again, go to step 4.

## 11b. A word about the bot token

The token from @BotFather is a password for your bot. Keep it in `.env`, which is never committed. Before pasting a
log anywhere — an issue, a chat, a screenshot — check it for `api.telegram.org/bot…`. Nodes from v0.4.3 on don't log
it; older ones did. If it ever escapes, revoke it in @BotFather with `/revoke`, put the new one in `.env`, and
`make restart`. Nothing else is lost.

## 12. When you ask for help, send this

```bash
cd ~/planetai/planetai-node
make health; docker compose ps; docker compose logs app | tail -50
```
Paste all of it. Not your `.env`, and scan the log for `api.telegram.org/bot…` before you send it.

---

## What "working" looks like after a week

- The daily pulse arrives every morning. `ours` matches the number of sensors you installed, which may be zero. `refs` counts public reference sensors in range, which will be zero outside Bali and is fine.
- `make alerts` shows a handful of alerts, not dozens. Dozens means the thresholds are wrong for your place. Copy `packs/air-quality/` to `packs/air-<yourplace>/`, change the numbers there, and updates will never overwrite them.
- You changed something, a window or a purifier or a habit, because of a message, and you told the node with `POST /actions`.
- `make cells` shows `Environmental|Community` as `live`, labelled with your `NODE_CITY`.
- There is a fresh file in `backups/` from last night.

## When you are not the first

Node #1 is in Bali because that is where the first sensor happened to be. Nothing in this page is about Bali,
and the parts that are say so. If you are setting up in Santiago or Delhi or anywhere else, the sequence is
the same: five inputs, four checks, one command.

Two things are worth sending back when you are done. Add your node to `registry.json` with a pull request so
the site knows where it is. And if you had to work anything out that this page did not tell you, say so in an
issue. The page was written against one install; it gets accurate by surviving others.
