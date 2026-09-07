# Beta tester guide

> **Alpha.** This is an experiment and you are joining it. Things will break. What you report decides what gets fixed
> first. Write to **info@fab.city** with what broke, what helped, and what did not.

This is the path two testers follow in September 2026, rehearsed on a clean Ubuntu machine on 6 September with the
Santiago (Providencia) and Barcelona (Poblenou) presets. It is written for someone who is not a developer.

**Language.** The alerts, the dashboard, the terminal and the Telegram bot are in English or Bahasa Indonesia
(`ALERT_LOCALE=en` or `id`). **The report is also in Spanish** (`ALERT_LOCALE=es`) — the first Spanish anything on the
node. The Spanish and the Bahasa Indonesia report templates were written by an assistant and no native reader has been
through them yet, so treat them as a draft and tell us which sentences are wrong or strange. Everything else is still
English only.

## 1. What you need

- A computer that stays on: a Mac (Apple Silicon or Intel, macOS 13 or later), a Linux machine (x86), or Windows 10/11
  with WSL2 (Ubuntu). **A Raspberry Pi does not work yet** (the database image has no arm64 build).
- On a Mac: install [OrbStack](https://orbstack.dev) or Docker Desktop first and open it once. On Linux the installer
  installs Docker for you. On Windows: Docker Desktop with the WSL2 engine, and run everything inside the Ubuntu shell.
- About 2 GB of disk, an internet connection, and 10 minutes.
- A Telegram account on your phone (for the alerts). No sensor is needed to start.

## 2. The one line

Open a terminal and paste:

```bash
curl -fsSL planetai.fab.city/install | bash
```

What happens, in order:

1. A logo, then on Linux `sudo` asks for your password once to install `git`, `make` and Docker. Nothing else is
   installed on your machine; the node itself runs in two containers.
2. **Four questions.**
   - *A short name for this node* — lowercase and dashes, for example `casa-providencia`. It appears in every alert.
   - *Where is it?* — type a neighbourhood or town, for example `Providencia, Santiago` or `Poblenou, Barcelona`.
     If several places match you pick one from a list. The node finds the coordinates and the time zone itself.
     (Two identical lines in the list is a known cosmetic bug; pick either.)
   - *What is this node for?* — pick `1` (a home) unless you are setting it up for a lab or a shop.
   - *Do you have a sensor?* — pick `1`, *None yet*. You can add one later.
3. *Here's the plan* — check the place and the time zone, press Enter.
4. *Installing* — one to three minutes the first time (it downloads the database image and builds the node's image).
5. A checklist. **Two crosses are normal now**: *telegram connected* and *a backup exists*. Telegram comes next; the
   first backup runs tonight at 03:17.
6. **The green screen: "Your node is running."** It shows the dashboard address (`http://localhost:8080`), the address
   for your phone on the same WiFi, and the settings token (write it down; `planetai ui` shows it again). Then
   *What now?* Press `o` to open the dashboard, `t` to connect Telegram, or Enter to stay in the terminal.

Measured on a clean Ubuntu machine on 6 September: about 100 seconds from the line to the green screen the first
time (Docker install and image build included), 23 seconds on a machine that already had the images.

If the terminal says `command not found: planetai` afterwards, open a new terminal window and try again.

## 3. Minute five: what you should see

Open `http://localhost:8080`. With no sensor the top card says **"No sensor yet. The model says N for this square of
the map."** N is the satellite model's PM2.5 estimate for your district (CAMS, an 11 km square). Below it: *Inside*
(empty until you add a sensor), *Outside the door* (the wind), *The day it just had* (an empty chart for now), *Region*
(the model, and the weather). The node polls every 5 minutes; "polled N min ago" sits next to the orange **ALPHA** pill.

Within the first hour the node fetches 92 days of modelled air history and the climate normals for your coordinates,
so the chart and the "compared with normal" sentences fill in.

## 4. Connect Telegram

```bash
planetai telegram
```

1. On your phone, open Telegram and message **@BotFather**. Send `/newbot`. Give the bot any name, then a username
   ending in `bot` (for example `casa_providencia_bot`). BotFather replies with a **token** that looks like
   `7123456789:AAF…`.
2. Paste the token in the terminal.
3. Open a chat with your new bot and send it any message ("hola"). The terminal finds your chat and says
   "found your chat", then sends you a hello.

The token is a password. Never paste it into an email or an issue.

## 5. Fire a test alert and act on it

```bash
planetai test-alert
```

Within a minute an alert arrives on your phone (and in the dashboard). The test alert tells you its number, for
example `#3` — real alerts do not, because they ask for nothing back. Then:

```bash
planetai act 3 "read it"
```

The terminal answers with ρ ("rho"): the share of alerts that led to someone doing something. This one number is what
the node exists to measure. On the dashboard, the button **I did this** beside an alert in the *Act here* band does the
same.

Replying `/act 3` in Telegram only works if the node's bot is running (`planetai agent local`, which installs a small
local model; optional, and heavy on an 8 GB machine).

## 6. Every day

**Your nights are quieter than they were, on purpose.** From this version the node interrupts you only when
something needs doing — `ALERT_LEVEL` is `act`, where it used to be `warn`. Everything below that line is still
recorded, still on the dashboard, and in the next report. If you want the old, chattier node back, one line brings it
back and takes effect in twenty seconds:

```bash
planetai report every 12 && planetai report at 6
```

...for the two-reports-a-day rhythm, and in the dashboard under **Set up → Alerts**, *Interrupt me for* → "also when
something changed" for the warns.

- **One report every six hours**, at 06:00, 12:00, 18:00 and 00:00 local. Six short parts: where the place stands, what
  changed, anything only the satellites know, what happened after the alerts, the one thing to do before the next
  report, and an invitation to ask. Under a hundred words.
- **The one due at midnight is written and held, not sent.** You read it at six, with the night folded into it, and it
  says so. It is on the dashboard the whole time under *Here — the last thing the node said*.
- **Between reports: act-level alerts only.** They say what to do in one sentence and ask for nothing back — no number
  to quote, no button on the hero. Quiet hours 22:00–06:00 hold everything but *act*.
- Change the rhythm: `planetai report every 3|4|6|8|12|24` and `planetai report at <hour>`. Want one right now?
  `planetai report`. The last one? `planetai report last`.
- `planetai status` — is it alive, what it read, what fired.
- `planetai doctor` — every check, with the fix written next to any failure.
- Adding a sensor later: dashboard → **Set up** (needs the token from `planetai ui`) → Sources.

## 7. What to report, and where

Write to **info@fab.city**. Include the output of `planetai status`, `planetai doctor`, and the last twenty lines of
`planetai logs`. **Never send `.env`**: it holds your tokens. Say what you expected as well as what happened. A
screenshot of the dashboard on your phone is worth a lot.

Especially useful: alerts that arrive too often or say something wrong for your place, a sentence you did not
understand, anything that took more than one try.

## 8. When it breaks

| what you see | what to do |
|---|---|
| Nothing installs, or "Docker isn't running" (Mac) | Open OrbStack or Docker Desktop, then run the line again. |
| Linux: "permission denied … docker.sock" | Log out and back in, then run the line again. |
| `command not found: planetai` | Open a new terminal window. |
| "port is already in use" | `planetai config`, set `APP_PORT=8081`, `planetai restart`. |
| Telegram says nothing | Message the bot first; a bot cannot start a conversation. Then `planetai telegram` again. |
| Alerts every few minutes | Thresholds wrong for your place. Tell us which ones. |
| Nothing at all for a day | Check the report hour: `planetai report at 6`. A report due while the node was asleep is not sent late; the next one covers it. `planetai report` writes one now. |
| Stopped after a power cut | The computer must boot and log in on its own (Mac: Login Items; Energy → start after power failure). |

Updating to a newer version: `planetai update`. It backs up first and refuses to continue if the backup fails.

Removing it: `planetai stop` keeps the data; `docker compose down -v` in `~/planetai` removes everything.
