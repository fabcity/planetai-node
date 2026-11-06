# Quick start
<!-- checked: v0.91.0 -->

A node in six steps, on a computer your lab or home already owns. One sitting. Each step ends with something you
can see, and each has a page in the docs that goes deeper.

| step | what you have at the end |
|---|---|
| 1. Install | the node reading your place every five minutes |
| 2. A sensor and the first alert | your own sensor counted, a message on your phone, the loop closed once |
| 3. Choose your packs | the packs that fit this place switched on |
| 4. A model on the machine | a bot that answers "how is the air?" from the node's own readings |
| 5. Your own agent | Claude or any MCP client holding the node's tools over your tailnet |
| 6. The map of your place | the Place door drawing your kilometre from maps kept on the node |

You need a computer that stays on, with 4 GB of memory (16 GB if you want the model in step 4) and 3 GB of disk: an
x86 Linux box first, a Mac on macOS 13 or newer, or Windows through WSL2. Raw readings never leave it. If you work
with an agent, paste it the two lines under [Bring your own agent](agents.md) first.

Four things need the terminal on the node's machine: the install line, connecting Telegram, installing the model
and fetching the map. Everything else can be done from the dashboard, under **Set up** behind the gear, once you
have unlocked it with the admin token that `planetai ui` prints; each step below says where. A setting saved there
is live within 20 seconds and wins over `.env`.

## 1. Install

```bash
curl -fsSL https://planetai.fab.city/preflight | bash     # checks the machine, installs nothing; stop at exit 2
curl -fsSL https://planetai.fab.city/install | bash       # four questions, two minutes
planetai doctor                                           # every check with its fix; new terminal if planetai is not found
```

The installer asks for a name, the place (type a town; it finds the coordinates), what the node is for (home,
business, community or lab, district) and whether you have a Smart Citizen kit. Near the end it offers the map of
your place: say `y`. The place is the answer that matters, because it fixes the cell the node stands in and the
500 m inside which a sensor counts as yours.

Deeper: [Install](install.md), [Platforms](platforms.md), [Revive a laptop](revive-a-laptop.md).

## 2. A sensor and the first alert

```bash
planetai config set SC_DEVICES 19880       # a Smart Citizen kit; AIRGRADIENT_HOSTS or PURPLEAIR_HOSTS for those
planetai sensors                           # after one poll: yours or reference, indoor or outdoor
planetai telegram                          # a bot from @BotFather; message it once
planetai test-alert                        # one real alert reaches your phone
planetai act 12 "read it on my phone"      # the id the test printed; ρ is now 1 of 1
planetai ui                                # the dashboard's address and the token for Set up
```

On the dashboard: Set up › Sources takes the same kit ids and hosts, and Set up › Rooms names the room each sensor
is in. A sensor you built, a Bayu or a Meshtastic radio in a field, reaches the node through `planetai broker` or
`planetai radio`; Data › Workbench flashes and tests the board. Without any sensor the node still knows your
weather, the satellite air model for your district and forty years of climate.

Deeper: [First ten minutes](first-ten-minutes.md), [Sensors and sources](sensors.md),
[Radios](../MESHTASTIC.md).

## 3. Choose your packs

Open Set up › Packs on the dashboard with the admin token. Every pack the node could run is there with its switch:
`coast` if you are near the sea, `fire` if your place burns or sits downwind of fields that do, `open-data-health`
if your city has a portal, `thingdata` if there is a repair café, `surface-heat`, `earth` and `terrain` for the
ground from orbit. Under them is the wild list, packs other nodes wrote, each with an Install button that shows
who wrote it and what it reads before fetching anything. A pack that runs code waits for **Allow code packs** on
the same page, which the node asks you to confirm once. This step is the dashboard's; the terminal equivalent is
`planetai packs add <id>`.

Deeper: [Packs that ship](packs-reference.md), [Packs](packs.md) for writing one.

## 4. A model on the machine

```bash
planetai agent local                    # Ollama and the bot; downloads no model
planetai agent local pull qwen3.5:9b    # 6.6 GB at 16 GB of memory; qwen3.5:4b (3.4 GB) at 8 GB
```

Then message your bot: "is the node healthy?", "how is the air?", `/act 23 closed the windows`. The same model
answers the ask pane on the dashboard. On the dashboard: with no model yet, the ask pane shows the pull line for
this machine's memory with a copy button; a bigger model on a laptop or workstation of yours goes under Set up ›
Model, and at the default `AGENT_PREFER=private` nothing is ever sent online.

Deeper: [The bot](bot.md), [Ask the node](ask.md), [Models](../../docs/MODELS.md).

## 5. Your own agent

```bash
planetai mesh      # joins your tailnet under the node's name; no port opened anywhere
planetai agent     # the MCP endpoint, the token, and a block to paste into Claude Desktop, Claude Code or Cursor
```

Tell the agent its name once ("pass it as `agent` on every write"), then ask it to call `health_check` and
`status`. A remote agent gets all twenty-one tools; what it records in your words counts in ρ. On the dashboard:
the ask pane's third card prints the same `claude mcp add` line with this node's address; the token still comes
from `planetai agent` on the node.

Deeper: [Bring your own agent](agents.md), [MCP server and tools](mcp.md).

## 6. The map of your place

```bash
planetai config set PACKS_ALLOW_CODE 1    # the place pack fetches, so it needs the flag
planetai packs install && planetai restart
planetai run place basemap                # if you skipped it at install: streets and buildings, kept on the node
planetai run place gaps                   # what is unmapped within the kilometre, for a mapping afternoon
```

Open the Place door. The cell, the streets, the buildings within a kilometre from OpenStreetMap, the rings and every
distance are the node's own, and need the token because together they place the house. Nothing finer than the
node's cell leaves the machine. On the dashboard: Allow code packs and the place pack's own settings are under Set
up › Packs; the map itself is fetched once from the terminal, and until it is, Set up lists **The map of this place**
under what is left to finish.

Deeper: [The Place door](place.md), [the place pack](packs-reference.md#place).

## Every day

```
planetai status      is it alive, what has it read, what fired, ρ
planetai doctor      every check, with the fix next to any failure
planetai update      backup, fetch the signed release, migrate, rebuild, verify
```

`main` is the beta channel. When something breaks, send `planetai status`, `planetai doctor` and twenty lines of
`planetai logs` to **info@fab.city**, never `.env`.
