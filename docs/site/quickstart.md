# Quick start
<!-- checked: v0.91.0 -->

This page puts a node on a computer your lab or home already owns, in six steps and one sitting. Once it runs, the
node reads its place every five minutes, keeps the raw readings on that machine, tells the people there when
something needs doing and counts whether anyone did. [Introduction](introduction.md) says why. Each step ends with
something you can check and a link to the page that goes deeper.

You need a computer that stays on. Linux on x86 is the first choice, then a Mac on macOS 13 or newer, then Windows
through WSL2. It needs 4 GB of memory (8 GB under WSL2, 16 GB if you want the model in step 4) and 3 GB of disk, and
you need Telegram on a phone.

The commands run on the node's machine. Where the dashboard can do the same, the step says where in **Set up**, the
page behind the gear that the admin token from `planetai ui` unlocks. A setting saved there is live within 20 seconds
and wins over `.env`.

## 1. Install

```bash
curl -fsSL https://planetai.fab.city/preflight | bash   # checks the machine and installs nothing; exit 2 means below the floor
curl -fsSL https://planetai.fab.city/install | bash     # four questions
planetai status                                         # open a new terminal if planetai is not found
```

The installer asks for a name, the place, what the node is for and whether you have a Smart Citizen kit. Type the
town and pick the right match, because the place fixes the cell the node stands in and the 500 m inside which a
sensor counts as yours. Near the end it offers to fetch the map of your place: say `y`.

It worked when `planetai status` shows `polls` going up every five minutes, `errors none`, and the public stations
and models it reads under `reference`. If a line is wrong, `planetai doctor` prints every check with its fix.

Deeper: [Install](install.md), [Platforms](platforms.md), [Revive a laptop](revive-a-laptop.md).

## 2. Your sensor and the first alert

```bash
planetai config set SC_DEVICES 19880    # your Smart Citizen kit, if you skipped it at install
planetai sensors                        # after the next poll
planetai telegram                       # make a bot with @BotFather, paste its token, message it once
planetai test-alert                     # one real alert, through the whole path to your phone
planetai act 12 read it on my phone     # the alert's number, as test-alert printed it
```

`planetai sensors` marks each sensor `yours`, inside the 500 m, or `reference`. An AirGradient or a PurpleAir on
your WiFi goes in `AIRGRADIENT_HOSTS` or `PURPLEAIR_HOSTS` the same way; a Bayu or a Meshtastic radio comes in through
`planetai broker` or `planetai radio`. Without a sensor the node still reads the public stations and models.

It worked when the test alert is on your phone and `planetai act` answers `1/1 alerts answered`. That share of
alerts somebody acted on is ρ, and it is what the Index measures. On the dashboard, sensors go in Set up › Sources, and
Data › Workbench flashes and tests a board you built.

Deeper: [First ten minutes](first-ten-minutes.md), [Sensors and sources](sensors.md), [Radios](radios.md).

## 3. Let the packs run

Every pack in the node's folder is on from the start, and the sensor packs run on their own switches. The rest of
the packs that ship code, `place`, `forecast` and `terrain` among them, run Python with the node's privileges, so they
wait for one setting you give once you have read what they do:

```bash
planetai config set PACKS_ALLOW_CODE 1   # on the dashboard: Allow code packs, under Set up › Packs
planetai packs install                   # builds the packs' libraries into the image, once
planetai restart
planetai packs                           # what is loaded now
```

Then switch off on Set up › Packs what does not fit your place: `coast` is for a node near the sea,
`open-data-health` for a city with a CKAN portal. `fire` stays off until `FIRE_ENABLED=1`, for the bandwidth. Below
the packs is the wild list, written by other nodes, where **Install** shows who wrote a pack and what it reads before
anything is fetched.

It worked when no line on Set up › Packs says it is waiting for Allow code packs, and `planetai packs` lists them
under `loaded now`.

Deeper: [Packs that ship](packs-reference.md), [Packs](packs.md) for a wild pack or one of your own.

## 4. A model on the machine

```bash
planetai agent local                    # installs Ollama and starts the loop; downloads no model
planetai agent local pull qwen3.5:9b    # 6.6 GB, for 16 GB of memory; qwen3.5:4b (3.4 GB) for 8 GB
```

`planetai agent local` prints the tag that fits this machine's memory, and on Linux how to make Ollama listen on
`0.0.0.0` so the node's container reaches it. The model talks through the bot from step 2.

It worked when your bot answers "is the node healthy?" from the node's own readings, and `/act 23 closed the windows`
records an action as `planetai act` does. The same model answers the ask pane on the dashboard. A bigger model on
another computer of yours goes in Set up › Model; at the default `AGENT_PREFER=private` nothing is sent online.

Deeper: [The bot](bot.md), [Ask the node](ask.md), [the model tags](../MODELS.md).

## 5. Your own agent

```bash
planetai agent    # the MCP address, the token, and a block for Claude Desktop, Claude Code or Cursor
planetai mesh     # only if the agent runs on another computer: joins your tailnet and opens no port
```

The node is an MCP server at `/mcp`. Paste the block into your agent's MCP settings and change its `X-Agent` name
to one you will recognise, because every write the agent makes is logged under it. After `planetai mesh`, the block
carries the node's tailnet address.

It worked when the agent calls `health_check` and `status` and tells you the node's name and its last poll. An agent
you drive gets twenty-one tools, and its `act` tool records what a person did, in their own words.

Deeper: [Bring your own agent](agents.md), [MCP server and tools](mcp.md).

## 6. The map of your place

```bash
planetai run place basemap    # if you said no at install: streets, buildings and drone imagery, kept on the node
planetai run place gaps       # what is unmapped within the kilometre, for a mapping afternoon
```

The `place` pack runs once step 3 allows code, and its first poll fetches the kilometre around the node from
OpenStreetMap. Open the Place door on the dashboard. The rings and every distance from the house need the admin token,
because together they place the house; nothing finer than the node's cell leaves the machine.

It worked when the Place door draws your streets and Set up no longer lists **The map of this place** under what is
left to finish. A zero in the place's figures means unmapped, and `place gaps` says what to map.

Deeper: [The Place door](place.md), [the place pack](packs-reference.md#place).

## Every day

```
planetai status    is it alive, what has it read, what fired, ρ
planetai doctor    every check, with the fix next to any failure
planetai update    backup, fetch the latest version, check its signature, migrate, rebuild, verify
```

When something breaks, write to **info@fab.city** with `planetai status`, `planetai doctor` and the last twenty
lines of `planetai logs`, and never your `.env`. The next part is joining the network: with a parent set,
[Federation and the Index](federation.md) sends up hourly means and the times of alerts, and the readings stay in
the house.
