# Beta tester guide

> **Alpha.** This is an experiment and you are joining it. Things will break. What you report decides what gets fixed
> first. Write to **info@fab.city** with what broke, what helped, and what did not.

This is the path two testers follow in September 2026, rehearsed on a clean Ubuntu machine on 6 September with the
Santiago (Providencia) and Barcelona (Poblenou) presets. It is written for someone who is not a developer.

**Language.** What the node sends you is in Spanish on a Santiago or Barcelona node: the alerts, the two daily
reports, the test alert, and the bot's own replies (`/act`). The Spanish was written by the team and reviewed by one
native speaker, not by many; tell us every sentence that reads wrong. The dashboard, the terminal and these documents
are still in English. To switch: Set up → Alerts → Alert language, or `ALERT_LOCALE=es` in `.env`.

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

Within a minute an alert arrives on your phone (and in the dashboard). It ends with a number, for example `#3`. Then:

```bash
planetai act 3 "read it"
```

The terminal answers with ρ ("rho"): the share of alerts that led to someone doing something. This one number is what
the node exists to measure. On the dashboard, the button **I did this** beside an alert does the same.

Replying `/act 3` in Telegram only works if the node's bot is running (`planetai agent local`, which installs a small
local model; optional, and heavy on an 8 GB machine).

## 6. Every day

- `planetai status` — is it alive, what it read, what fired.
- `planetai doctor` — every check, with the fix written next to any failure.
- Alerts arrive on Telegram: **act** when something needs doing, **warn** when something changed. Two short reports a
  day at 06:00 and 18:00 local time. Quiet hours 22:00–06:00 hold everything but *act*.
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
| Stopped after a power cut | The computer must boot and log in on its own (Mac: Login Items; Energy → start after power failure). |

Updating to a newer version: `planetai update`. It backs up first and refuses to continue if the backup fails.

Removing it: `planetai stop` keeps the data; `docker compose down -v` in `~/planetai` removes everything.
