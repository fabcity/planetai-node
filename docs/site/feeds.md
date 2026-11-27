# Feeds for subscribers
<!-- checked: v0.92.0 -->

This page is for the person who runs a community node and wants to know what the bot sends to people who are not the keeper. Once it is on, anyone can start the node's Telegram bot, pick what they want to hear about, and get a short message when it happens. A private node does none of this.

## What a subscriber gets

A person opens the bot and sends `/start`. The bot answers with a card: the node's name (`PLACE_NAME`), buttons for six feeds and a choice of English or Bahasa Indonesia. The weekly report is ticked to begin with. Tapping a button ticks or unticks it, and the card changes in place.

| Feed | What it sends | Where it comes from |
|---|---|---|
| Weekly report | Monday at 07:00 local, three to six lines about the week before | the node's own readings and the model points |
| Air | the air around here is unhealthy, or smoke has reached the node | the outdoor stations the node reads, and the fire rules |
| Heat | tomorrow feels hotter than usual | the forecast, compared with the last 30 days |
| Waves | a heavy, long-period swell is arriving | the marine model point |
| Fire | satellites saw fire near, and fire upwind | the fire pack |
| Rain and floods | heavy rain in the next 24 hours | the forecast, against `RAIN_HEAVY_MM` |

Each line has two parts: what is happening, then what to do. A feed sends at most one line a local day. The exception is a fire upwind of the node, which can send again.

The weekly message has a head line with the place and the dates, then only the lines the week's readings support: the worst air day, the hottest afternoon, the highest swell, the rain, the hour the air is usually worst. A week with none of them sends nothing. If `PUBLIC_URL` is set, the last line is a link to the report.

## What a feed never carries

A feed line is built from outdoor and public readings only. An indoor sensor, a room, or a metric on a private channel never reaches a subscriber, whatever a rule says. The check is made again when the line is queued, so a rule written wrongly still cannot send one.

## Commands

| Command | What it does |
|---|---|
| `/start` | adds the chat and shows the card |
| `/feeds` | shows the card again, to change feeds or language |
| `/now` | the newest line of each feed picked, from today |
| `/week` | the latest weekly message, or the day it first comes |
| `/stop` | deletes the chat from the node |

Anything else gets one line saying what the bot does. No model answers a subscriber. The keeper's chats (`TELEGRAM_CHAT_IDS`) keep everything they had, including asking the model, and can use these commands too.

## When messages go

The node checks for new lines every 2 minutes and sends one message per person per check, with everything that person picked. Quiet hours (`QUIET_FROM` to `QUIET_TO`, 22:00 to 06:00 by default) hold every line except a fire upwind. A held line goes out when quiet hours end, unless it is 12 hours old by then, and then it is dropped. If Telegram is down, the lines wait for the next check. The bot sends at most one message a second to a chat.

## What the node keeps

A chat number, the feeds picked, the language and the date they started. Nothing else: no name, no messages. `/stop` deletes the row. If someone blocks the bot, the node deletes the row on the next send. Backups leave the subscriber data out, and the chat number is not written to the log. Set up › Subscribers shows counts only, how many people and how many on each feed.

## Settings

| Setting | What it does |
|---|---|
| `PLACE_NAME` | the name on the card and at the top of the weekly message |
| `PUBLIC_URL` | the link that ends the weekly message |
| `RAIN_HEAVY_MM` | the forecast rain, in mm over 24 hours, that sends the rain feed; 50 by default |

## Adding a feed line to a rule

A rule in a pack can carry a `feed:` block. See [Alerts](alerts.md) for its keys.

Next, [Alerts](alerts.md) for the rules and levels the feeds come from.
