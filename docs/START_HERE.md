# Start here

PLANETAI node is a small program that runs on a computer in your home, lab or office and tells you about the air,
the heat and the weather around it, in plain sentences, on Telegram. It reads the sensors you already have, compares them
with the public sensors nearby and with satellite models, and speaks only when something should change. Your readings
stay on your machine.

## What you get

**Alerts you can act on.** Not "PM2.5 is 42." Instead: what is happening, what it means for the people in the house, and
what to do. "Inside is worse than outside. Something is cooking or burning. Open a window." In English or Bahasa Indonesia.

**A dashboard that reads like a sentence.** "Falling to 9 micrograms, under the street, under the model, under the line."
Then the day as a chart, every sensor with a note on what it is doing, the sea, the land, the weather. Open it on your
phone or leave it on a screen on the wall.

**A bot you can talk to.** Ask it how the air is, how big the swell is, what the kitchen did overnight, or tell it you
closed the windows. It runs on a small model on your own machine, and uses a bigger one when it can reach it.

**A house that learns its own rhythm.** After a week the node knows when your street is worst, when it is cleanest, and
how much of the outside air your building keeps out. It tells you the hour to air the house.

**Your data, kept.** The database never leaves the machine. Backups run nightly and can be pulled by a NAS or copied to
any storage you choose. What the node shares upward is a daily summary, and only if you point it somewhere.

**Nothing to buy.** It runs on a Mac, a Linux box, a Raspberry Pi or a Windows PC with WSL2, and works with the sensors
people already own: Smart Citizen, AirGradient, PurpleAir, Meshtastic radios. Without a sensor it still knows your
weather, the satellite air model for your district and forty years of climate for your coordinates.

## Install

```bash
curl -fsSL planetai.fab.city/node0/install | bash
```

It asks four things: a name for the node, the place (type a town; it finds the coordinates), what the node is for (a
home, a business, a lab, a district), and your sensor if you have one. Two minutes later it is running.

The install ends with a checklist. A cross next to *telegram connected* is expected; that comes next. A cross next to
*database* or *node answers* means something is wrong; see [When it breaks](#when-it-breaks).

## Your first ten minutes

```bash
planetai telegram      # connects a bot: make one with @BotFather, paste the token, message it once
planetai test-alert    # a real alert arrives on your phone within a minute
planetai ui            # the dashboard's address, and the token for its settings pages
```

Open the dashboard. Set up → Sources is where you add or change sensors. Set up → Model is where the bot's brain lives.

When an alert arrives that you act on, tell the node, in Telegram (`/act 12 closed the windows`) or with the button on the
dashboard. The node keeps one score for itself: how many of its alerts led to someone doing something. That number is
called ρ, and it is the only one on the page that comes from a person.

## Talk to it

```bash
planetai agent local   # installs Ollama and a small model on this machine; the bot answers from now on
```

Then message your bot: "how is the air?", "how big is the swell?", "is the node healthy?". With a laptop or workstation
on your network running a bigger model, set its address under Set up → Model and the bot uses that when it can reach it.

## Everyday

```
planetai status      is it alive, what has it read, what fired
planetai doctor      every check, with the fix written next to any failure
planetai logs        what it is doing right now
planetai update      backup, fetch the latest version, migrate, rebuild, verify
planetai storage     where the data is, where the copies go
```

`planetai` on its own lists the rest: mesh radios, Home Assistant, packs, IPFS, restore.

A good week looks like this: a short note from the bot each morning, a handful of alerts rather than dozens, one or two
that changed what you did, and a fresh file in `backups/`. Dozens of alerts a day means the thresholds are wrong for
your place; tell us which ones.

## What it will not do

It does not send your readings anywhere. It does not switch anything on or off; connect it to Home Assistant if you want
that. It does not replace a reference instrument; low-cost sensors drift and disagree, and the node says so where it
matters. It does not need the internet to keep working, only to send you messages.

## When it breaks

`planetai doctor` first. Everything below has happened to a real node.

| what you see | what to do |
|---|---|
| Nothing installs | Docker is not running. Open OrbStack or Docker Desktop, then run the line again. |
| `command not found: planetai` | Open a new terminal window. |
| `port is already in use` | `planetai config`, set `APP_PORT=8081`, `planetai restart`. |
| No alerts at all | Normal when the air is fine. `planetai test-alert` proves the path works. |
| Alerts every few minutes | Thresholds wrong for your place. Tell us. |
| A sensor shows nothing | `planetai sensors`. A Smart Citizen kit must be publishing; an AirGradient must be on the same network. |
| Telegram says nothing | Message the bot first; a bot cannot start a conversation. Then `planetai telegram` again. |
| The bot does not answer | `planetai logs agent`. The first lines say whether Telegram is set and which model it found. |
| Stopped after a power cut | The computer must boot and log in on its own. On a Mac: Login Items, and Energy → start after power failure. |
| A setting changed nothing | Settings made in the dashboard win over `.env`; the page says so next to them. |
| `planetai update` fails on `.DS_Store` | `find . -name .DS_Store -delete`, then update again. |

When you ask for help, send `planetai status`, `planetai doctor` and the last twenty lines of `planetai logs`. Not `.env`:
it holds your tokens.

## Remove it

`planetai stop` keeps the data. `docker compose down -v` in the node folder removes everything; then delete the folder.
