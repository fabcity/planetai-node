# Ask the node

The dashboard can be asked about what it shows. A pane opens beside the page and talks to the model on this
machine: the one `planetai agent local` set up for Telegram, asked through the same tools. It reads the page and
the node, it explains, and it changes nothing. When a question needs a change, it puts the change on a card and
the person presses it. Nothing asked or answered is kept.

This is the part of the node that answers in sentences. It needs a model on the machine; without one the pane
still searches this documentation.

## Opening it

1. Press **ask the node**, right of the modes in the header. On a phone the button is in the foot, and the pane
   opens as a sheet from the bottom. Learn mode opens it by itself.
2. The pane's header names the model, says `runs on this machine`, and says what it may do: `reads the page ·
   records what you did · changes nothing`. When it says `no model on this node yet`, see the last section.
3. Press one of the three questions under the thread, or type one. The questions are written by the node from
   tonight's figures: why the lead leads, the oldest open alert, what the lead's line means.

An answer arrives word by word. Under it a ledger line names every read the model made, how many milliseconds
each took, and `on this machine`.

`UI_ASK` under Set up turns the pane off for everybody: no toggle, no pane. It is `on` by default. The wall never
shows it.

## What it may do

| class | tools | in the pane |
|---|---|---|
| `read` | `status`, `health_check`, `sensors`, `context`, `readings`, `report_latest`, `history`, `alerts`, `packs`, `cells`, `issues`, `series` | run, through `/mcp` as `dashboard-chat` |
| `act` | `act` | not run: a card with the page's own **I did this** form |
| `admin` | `settings_set`, `run_pack_script`, `maintenance`, `report_now` | not run: a card, or a sentence naming where it is done |

`settings_get`, `report_bundle` and `export_day` are read tools the pane is not given. The pane can be open on a
wall at `SHARE_LEVEL=open`, and the person typing is not always the person who set the node up.

A setting card says what the setting is now, what it would become, what leaves the house (the setting's own help
text) and how to set it back. **turn it on** writes it with the admin token the page holds for Set up; with none
held, the card asks for it and says `needs your token`. **open Set up** goes to the setting's group instead. A
value the setting would refuse is not proposed; the card offers the values it takes.

An act card carries the alert's number and nothing the model wrote. What the person did is theirs to say, in
their own words, because ρ is built out of those sentences.

## What it never sends

The node builds the model's context itself, from the `/issues` bundle the page already has: the lead and its
sentence, the digest, every watched issue's state and values, the open alerts, and the documentation for the part
in focus. The browser sends only the thread.

That context, and every tool result the model reads, has no coordinate, no sensor or station name, no sensor id
and no `meta`. They are removed or replaced before the model sees them; `tests/test_ask.py` checks the context
built on node #1's own capture for each of them.

Nothing is stored. The thread is in the browser tab and goes when the tab closes. The node writes no transcript,
no database row and no log line with a word in it: the log says which tool ran and for how long. `GET
/ask/status` answers `stored: false`.

The pane asks the local rung only, never a tailnet model and never an online one, whatever `AGENT_PREFER` says
for Telegram. That is what `runs on this machine` means.

## Two ways to give it a voice

With no model set up, the pane says so, offers the documentation search, and shows two cards with a copy button.

- **A model on this machine.** The card names the tag `planetai agent local` suggests for this machine's memory
  and its size, with the line to run on the node: `planetai agent local pull <tag>`. `planetai agent local` sets up
  Ollama and the loop first; neither downloads anything until you pull.
- **Your own agent, over MCP.** The card prints the `claude mcp add` line with this node's address. `planetai
  agent` on the node prints the token. A remote agent gets the whole MCP surface, which rounds positions,
  refuses what it must and records every write; see [Bring your own agent](agents.md).

When the model is installed and not answering, the pane says so and names `planetai doctor`.

The next part to add is a pack: [packs](packs.md).
