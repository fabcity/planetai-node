# First ten minutes

The install ends with a running node that has read the models for your coordinates and is polling your
sensor. Nothing has reached your phone yet. Three commands change that.

## Connect Telegram

```bash
planetai telegram
```

Make a bot with **@BotFather** in Telegram, paste its token when asked, then send the bot one message — a bot
cannot start a conversation. The command waits up to two minutes for that message, records your chat id,
writes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` to `.env` and to the running node, sends a hello, and
recreates the app container. Several people can receive alerts: comma-separate chat ids in
`TELEGRAM_CHAT_IDS`.

## Prove the whole path

```bash
planetai test-alert
```

Writes a temporary pack with one always-firing act-level rule, waits up to ninety seconds for it to fire
through every channel the node has, prints the alert's id, and removes the pack. The message says: "Test
alert from your node. If you can read this, the whole path works: rule to message to you." It is the only
end-to-end proof there is; a quiet node is not a working node until this has happened once. (The API has a
second test alert, `POST /test-alert`, whose text ends by asking you to close the loop with `/act N` or
`planetai act N`.)

## Open the dashboard

```bash
planetai ui
```

Prints the dashboard's addresses — this machine, your LAN, the tailnet if you have joined one — and three
tokens. The **admin token** unlocks the Set up view: treat it like a password. The **backup token** is
read-only, for a NAS. The **act token** lets a phone close a loop and can read no secret. `planetai ui`
creates the admin and act tokens if they are missing.

Open `http://localhost:8080/`. At the default `SHARE_LEVEL=off` every browser — including the one on the
machine the node runs on, which Docker presents as a network client — sees the shell and the node's status
and no readings, until you paste the admin token into Set up or switch sharing to `open`; see
[Sharing](sharing.md). The Set up view is where sensors are added or changed (Sources), where the bot's
brain lives (Agent), and where every runtime setting can be changed without touching `.env`.

## Close a loop

When an alert arrives that you act on, tell the node. Three ways:

```bash
planetai act 12 "closed the windows"     # in a terminal on the node
```

or the button on the dashboard, or `/act 12 closed the windows` in Telegram once the bot runs (below). The
node keeps one score for itself: how many of its act-level alerts led to someone doing something within a
day. That number is [ρ](rho.md), and it is the only one on the page that comes from a person. The test alert
is a fine first one to close.

## Talk to it

```bash
planetai agent local
```

Installs Ollama on the machine, picks `qwen3:4b` (or `qwen3:8b` with 16 GB of RAM), pulls it, and starts the
`agent` container: a loop that answers your Telegram messages using the node's own tools. Then message your
bot: "how is the air?", "how big is the swell?", "is the node healthy?". A bigger model on a laptop or
workstation on your network, or an online one with a key, sits above it on the [model ladder](bot.md).

## Every day

```
planetai status      is it alive, what has it read, what fired, ρ
planetai doctor      every check, with the fix written next to any failure
planetai logs        what it is doing right now
planetai update      backup, fetch the latest version, migrate, rebuild, verify
planetai storage     where the data is, where the copies go
```

A good week looks like this: a short report from the node a few times a day, a handful of alerts rather
than dozens, one or two that changed what you did, and a fresh file in `backups/` every morning. Dozens of
alerts a day means the thresholds are wrong for your place; tell us which ones rather than raising them —
a node that is quiet because you raised its threshold is lying.

## When something is off

`planetai doctor` first. Then [Troubleshooting](troubleshooting.md), which is ordered by what is on your
screen. When you ask for help, write to **info@fab.city** with `planetai status`, `planetai doctor` and the
last twenty lines of `planetai logs`. Never `.env`: it holds your tokens.
