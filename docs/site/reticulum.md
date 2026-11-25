# Reticulum
<!-- checked: v0.92.0 -->

This page adds Reticulum to your node. Reticulum is a network that runs over whatever links you have, your WiFi, the
internet or a LoRa radio, with no company in the middle. With it on, your node has an address you can write to from a
phone, sends its alerts there as messages, takes your answer back and can hear the other PLANETAI nodes through the
Fab City hub. Over a LoRa radio it keeps working when the internet is down.

The Node door shows it in one place, under **Reticulum**: the node's address with a copy button, whether it dials the
hub, how many nodes it hears, where its alerts go and what it answers.

## What it does on a node today

- **An address.** The bridge gives the node an LXMF address, 32 hexadecimal characters. Sideband and NomadNet, the
  Reticulum messengers, can write to it.
- **Alerts as messages.** Every `act` alert goes, in full, to each address in Set up › Sharing › Reticulum alert
  addresses.
- **Answers.** `act 3`, or `act 3 opened the windows`, sent from one of those addresses closes alert #3, the same as a
  Telegram reply or `planetai act`. Anyone else who writes gets one reply saying the node takes `act` only from the
  addresses it sends alerts to, and nothing is recorded.
- **Presence.** With presence on, the node announces its name, version and kind, and an area about 60 km across,
  every half hour. The nodes on the hub list it under The nodes around it, and yours lists them.
- **Hello.** `planetai hello` sends this node's entry to the programme's inbox on node #1, so a person can add it to
  the list of nodes without you needing a GitHub account.

## What it does not do yet

Apart from `hello`, nodes do not write to each other over Reticulum, and no reading travels over it. When a
house sends its hourly means to a community node, they go over a network the two share, a LAN or a tailnet, and the
Node door of each says where they went and what came in. A message to a node that is not `act` or `hello` gets no
answer. Anyone can announce any name, so hearing a node does not prove who runs it.

## Turn it on

**Read the licence before you turn it on.** The bridge installs `rns` and `lxmf`, which are under the
[Reticulum License](https://github.com/markqvist/Reticulum/blob/1.5.4/LICENSE): MIT with two conditions, and not an
open-source licence. You may not use them in a system that can purposefully harm people, or directly or indirectly
in making a dataset to train an AI or machine-learning model. The node does neither. If you share the image you
built, include that licence with it. What it means for the node is in
[the decision record](https://github.com/fabcity/planetai-node/blob/main/docs/decisions/2026-10-23-reticulum-licence.md).

The bridge has its own repository, [`fabcity/planetai-reticulum`](https://github.com/fabcity/planetai-reticulum),
under Apache-2.0, so the node's own code never takes in `rns` or `lxmf`. It runs in its own container (compose profile
`reticulum`).

1. **Run `planetai reticulum`.** It downloads the bridge at the commit this release pins, builds it on this machine
   and starts it. When it is done it prints `● this node's LXMF address: <address>`. The same address is on the Node
   door, under Reticulum, with a copy button.
2. **Answer its question.** It asks `Let other PLANETAI nodes see this node?`. Yes lets your node hear the other
   nodes through the Fab City hub, with nothing to open on your router, and turns presence on. Everyone on the hub
   then sees your node's name, its LXMF address and its rough area, about 60 km across, and never a reading, a sensor
   or where the house is. No keeps the node off the hub and presence off. The answer you gave last time is the
   default, `planetai setup` asks the same at the end of an install with no as the default, and an update never
   changes it. When yes worked, the command says `dialling the Fab City hub` and the Node door says "dialling it" on
   the hub row.
3. **Put Sideband on your phone.** On the same network as the node, add a TCP Client interface in Sideband to this
   machine's LAN address, or its tailnet address, on port 4242. Then start a conversation with the node's address.
4. **Give the node your address.** Copy your own LXMF address from Sideband's settings into Set up › Sharing ›
   Reticulum alert addresses, or run `planetai config set RETICULUM_ALERT_DESTINATIONS <hash>[,<hash>]`. Nothing needs
   restarting: the node sends the list to the bridge with each alert. The Node door's "Its alerts" row now counts
   your address.
5. **Send yourself a test.** Run `planetai test-alert`. Sideband shows a message from the node titled
   `planetai <NODE_NAME>`, with the whole test alert, and the terminal says which alert number it was.
6. **Answer it.** Send `act <number> testing` from Sideband. The node replies `recorded: you acted on #<number>`, and
   Data shows the alert as acted. It counts in ρ like any other answer, and its note says it was a test.

## Check it end to end

Run these after you turn it on, and again after an update. Each row is one thing that has to work.

| check | where | what you should see |
|---|---|---|
| `planetai doctor` | the terminal | `✓ reticulum bridge up`, and `✓ dialling the Fab City hub` once you said yes |
| Node › Reticulum | the page | "The bridge is running.", the address, and the hub row saying "dialling it" |
| `planetai test-alert` | Sideband | a message titled `planetai <NODE_NAME>` |
| `act <number> testing` from your address | Sideband | `recorded: you acted on #<number>` |
| `act <number>` from an address the node does not send to | Sideband | one reply, `this node takes act only from the addresses it sends alerts to` |
| Node › The nodes around it | the page | the nodes on the hub, each "heard on the hub, 20 min ago, about 340 km away" |
| after `planetai update` | Node › The nodes around it, on another node | your node's new version within a minute |

`planetai hello` is a check too, but it asks for your node to be listed, so run it when you want that: it prints
`received: a person reads it before it is listed`.

## The hub

The hub is node #1, the Mac mini in Bali, reached through Tailscale Funnel at `fabalabbali.tail71245c.ts.net:443`.
Funnel takes only TLS, so your bridge dials it through `openssl s_client`, which checks that the certificate is the
hub's. A node whose bridge has `enable_transport = Yes` passes announces and messages on between the nodes that dial
it. Running one is in the bridge's [README](https://github.com/fabcity/planetai-reticulum#running-a-hub), and
[SPEC_hub](https://github.com/fabcity/planetai-node/blob/main/docs/SPEC_hub.md) says why it works this way. A node
that is a hub itself is dialled rather than dialling, so its yes only turns presence on, and its Node door says how
many nodes are connected.

A phone reaches a node over its LAN or tailnet address on port 4242, and only nodes dial the hub.

## Presence

Presence is separate and off by default: with `RETICULUM_PRESENCE=1` the bridge announces the node's name and a
coarse H3 cell, its version, kind and node id every half hour, at `RETICULUM_PRESENCE_RES` (3) and never finer than resolution 6, whatever the
setting says, so an exact place never leaves. `GET /presence` is what the bridge reads to do it, and it answers at
every sharing level for that reason.

A node you hear stays on the page, an outline of its rough area on the globe and a row under The nodes around it.
Nothing about it reaches your cells, your alerts or the export.

## What the bridge is given

The bridge does not read `.env`. It receives eight variables from `docker-compose.yml`: `LOG_LEVEL`, `NODE_NAME`,
`NODE_API_URL`, `RETICULUM_CONFIGDIR`, `RETICULUM_DATA`, `RETICULUM_ALERT_DESTINATIONS`, `RETICULUM_ANNOUNCE_S`
and `ACT_TOKEN`. The Telegram token, the admin token and the database password stay out of a process whose job is
to speak to a radio mesh. `planetai reticulum` hands it the node's token, and makes one if the node has none yet;
the bridge reads it when its container is created, so after you change the token in Set up, run
`planetai reticulum` again.

The transport is TCP. An RNode LoRa interface is a commented block in `config/reticulum/config`, copied from the
bridge's `config.tpl` the first time; uncomment it and pass the device into the container to run over a radio.

## When something does not arrive

- **No message in Sideband.** `planetai logs reticulum` says `no path to <hash> yet; is that client announced and
  reachable?` when the node has not heard your phone. Open Sideband on the same network as the node so it announces,
  and check the interface from step 3.
- **`act` recorded nothing.** Your address is not in Set up › Sharing › Reticulum alert addresses, or the node has
  not sent it an alert since you added it. The log says which.
- **The hub row says "not answering".** `planetai doctor` checks the hub again and `planetai logs reticulum` says why.
- **The bridge is not answering.** `planetai logs reticulum`, then `planetai reticulum` to rebuild and start it.

Next: join the network, in [Federation and the Index](federation.md).
