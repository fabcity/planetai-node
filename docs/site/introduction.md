# Introduction

A PLANETAI node is a small program for a computer in your home, lab or community centre. It connects
everything that measures where you stand — a particle sensor on the wall, a radio in a field, the public
station down the road, the city's open-data portal, the satellite overhead — into one picture of the place,
sharp enough to act on: what to do about the air, the heat, the sea and the land, today, here. It tells the
people there in plain sentences on Telegram, keeps every raw reading on the machine it was recorded on, and
passes upward only what a city, a bioregion or a planetary model needs from the ground.

```bash
curl -fsSL planetai.fab.city/install | bash
```

Four questions, two minutes, running. Then `planetai telegram` for the alerts and `planetai ui` for the
dashboard. The walk-through is [Install](install.md); the ten minutes after it are
[First ten minutes](first-ten-minutes.md).

> **Note.** The node is alpha. Installing one makes you part of an experiment: things will break, some will
> surprise you, and what you report decides what gets fixed first. Write to **info@fab.city** with what broke,
> what helped and what did not. Node #1 has run in Kuta Selatan, Bali, since 2 September 2026; node #2 runs in
> Menorca.

## What these pages are

This is the reference for the node as it is in the version named in the footer, read from the code of that
version. The pages under *Get started* and *Operate* are for the person running one. *Alerts, reports and ρ*,
*Packs*, *Dashboard* and *Agents* explain what the node does and how to change it. *Reference* is the
[HTTP API](api.md), the [database](schema.md) and the [federation contracts](federation.md). *Project* holds
the architecture and the spec, which are the canon the rest of this is measured against.

Where a page and the code disagree, the code wins and the page has a bug: the link at the foot of every page
opens its source on GitHub.

## What a node is not

It does not send your readings anywhere. It does not switch anything on or off; connect it to Home Assistant
if you want that. It does not replace a reference instrument: low-cost sensors drift and disagree, and the
node says so where it matters. It does not need the internet to keep working, only to send you messages. And
it is not a cloud service: two containers on a machine you own, a database on a local disk, nothing that
requires a provider to function.

## Who it is for

A household with a sensor in the living room that still does not know whether to open the window. A fab lab
that wants its own address on the [Fab City Index](https://index.fab.city). A school or clinic with a duty of
care and a budget line for health and safety. A banjar or a desa that wants its own number on the island's map.
And the people who keep sensors alive for all of them, which is the part of this that is a service rather than
a program — the argument is in [`PRODUCT.md`](../../PRODUCT.md).

## Where to go next

| you want to | read |
|---|---|
| know whether your machine can run it | [Platforms](platforms.md) |
| install it | [Install](install.md) |
| understand the words the rest of the pages use | [Concepts](concepts.md) |
| see what it does with a reading | [How it works](how-it-works.md) |
| add a sensor | [Sensors and sources](sensors.md) |
| write a rule for your place | [Packs](packs.md) |
| connect Claude, Codex or a local model | [Agents](agents.md) |
| read its API | [HTTP API](api.md) |
