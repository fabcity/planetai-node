# Channels

Four ways a message leaves the node and reaches a person or a house. All four are functions inside
`notify()`; a separate notifier service returns when a second channel with its own auth lifecycle (WhatsApp
Business) arrives, not before. Raw readings travel none of them.

| channel | receives | needs internet | configured by |
|---|---|---|---|
| Telegram | every alert that reaches the floor; every report; the bot's answers | yes | `planetai telegram` |
| Meshtastic (LoRa mesh) | `act` alerts, first line only | no | `planetai meshtastic`, `MESH_ALERTS=1` |
| Reticulum (LXMF) | `act` alerts, full text; takes `act <id>` back | no | `planetai reticulum` |
| Home Assistant | every alert, sent or not, and every report, as entity state | no (LAN) | `planetai homeassistant` |

## Telegram

The default channel and the one the report uses. `planetai telegram` makes the setup: a bot from
@BotFather, its token, your first message to it, and both `TELEGRAM_BOT_TOKEN` (secret) and
`TELEGRAM_CHAT_IDS` (comma list; several people can receive) written to `.env` and the running node. Alerts
arrive prefixed with the level's icon; the report arrives as plain text. With the token blank the node logs
alerts and sends nothing. The node never logs the Telegram URL, because the token is in it; `planetai logs`
containing `api.telegram.org/bot` would be a leak.

Answering questions on Telegram is the [bot](bot.md), a separate container.

## Meshtastic — the LoRa mesh

For sensors and alerts where there is no WiFi. One gateway radio with WiFi uplinks the mesh to an MQTT
broker on the node (`planetai meshtastic` starts it as the compose profile `mqtt` and prints the radio
settings for your region); field radios carry a sensor on a battery; a shelf radio paired to a phone receives
alerts when the internet is down.

Downlink: with `MESH_ALERTS=1` and `MESH_GATEWAY_NODE_NUM` set, an `act` alert's first line is published to
the mesh through the gateway. A LoRa frame is about 200 bytes, a few a minute: telemetry and one-line alerts,
never data between nodes. Uplink: radio telemetry arrives on `msh/#` and becomes readings; a radio's own
temperature and pressure are its enclosure, not the street. Everything about the boards, the firmware and
the channel key is on [Radios](radios.md).

## Reticulum — LXMF

The bridge container (`planetai reticulum`, compose profile `reticulum`) gives the node an LXMF address.
Outbox: `act` alerts, full text, delivered directly to every hash in `RETICULUM_ALERT_DESTINATIONS` — a phone
running Sideband, typically. Inbox: a message `act <alert id> [note]` records an action with the actor
`lxmf:<hash>` and replies "recorded: you acted on #N". TCP transport today; an RNode LoRa interface is a
commented block in `config/reticulum/config.tpl`.

Presence is separate and off by default: with `RETICULUM_PRESENCE=1` the bridge announces the node's name
and a coarse H3 cell every half hour — the cell rounded *up* to `RETICULUM_PRESENCE_RES` (3) with a floor of
resolution 6 that no setting can go under, so an exact place never leaves. `GET /presence` is what the bridge
reads to do it, and answers at every sharing level for that reason.

Node-to-node data over Reticulum — a district and a community node with no internet between them — is a
retired piece with its trigger written in [`SPEC.md`](spec.md) §6.

## Home Assistant

`HA_DISCOVERY=1` with a broker (`planetai homeassistant` ensures both) publishes MQTT discovery entities: one
sensor per local sensor and metric, grouped as a device per physical kit with a suggested area of Indoor or
Outdoor, states retained at `planetai/<node>/<sensor>/<metric>` and expiring after an hour of silence.
Reference stations are not published. One text sensor, `planetai_<node>_alert`, carries the first line of
the latest alert with `level`, `alert_id` and `ts` as attributes — every alert, whatever its level and
whatever quiet hours say, and every report.

The node switches nothing on or off. Build the automations there: purifier on above 35 for ten minutes; a
window reminder at the cleanest hour; a phone notification when the alert level is `act`.

## What a house with no internet still gets

A shelf radio paired to a phone receives the first line of every `act` alert over LoRa. Sideband receives the
whole alert over LXMF and can answer `act <id>`. Home Assistant on the LAN keeps every entity current. The
dashboard on a wall screen keeps drawing. The node keeps polling its LAN sensors, running its rules and
writing its reports; only Telegram waits for the internet to come back.
