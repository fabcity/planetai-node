# Nodes finding each other on a tailnet

*Proposed, 22 September 2026, from Tomas: "it is interesting for nodes to choose to be discoverable,
which does not mean accessible or sharing data, just sharing I am in X cell, and can say hi to other
nodes, and also see them. So someone can choose for their node to be visible in the network or not."*

Not built. This is the specification; nothing in it ships until it is read and argued with.

## 1 · The three things this is not

Discovery is a small idea that attracts large ones. It is worth writing down what it refuses before
what it does.

- **Discoverable is not accessible.** A node that says it exists has not opened its API. `SHARE_LEVEL`
  is untouched by this and stays the only thing that decides who may read what. A node can be
  discoverable at `SHARE_LEVEL=off`, and that combination is the expected one.
- **Discoverable is not sharing data.** Nothing here carries a reading, an alert, a sensor, a
  household's sentence, or a position. Nothing here rolls up into a cell or a count.
- **Discoverable is not being listed by somebody else.** There is no registry, no rendezvous server,
  no bootstrap host, nothing to sign up to and nothing to be removed from. A node answers for itself
  or it does not answer.

## 2 · What a node says

Exactly what `GET /presence` already returns, and nothing added for this. Node #1 today:

```json
{"enabled": true, "node": "bayu-ungasan", "cell": "8395a4fffffffff", "res": 3,
 "version": "v0.71", "kind": "home"}
```

A name the keeper chose, a **coarse H3 cell**, the resolution it was coarsened to, the version, and
what kind of place it is. The cell is the node's own res-8 cell rounded **up** to res 3 — about sixty
kilometres across, which names an island rather than an address. Resolution 6 — about three kilometres — is the
finest anything may ever be announced at, and it is a constant in `app/main.py` rather than a
setting, because "which neighbourhood am I in" is not a thing a person should be able to publish by
typing a number into a box.

Off, it answers `{"enabled": false}` and stops. Not a 403, not silence: the honest answer to "are you
there" is "yes, and I am not saying".

**Distance between two nodes is the distance between two cell centres,** and neither of them ever
published a position. Two nodes in the same res-3 cell know they are within about sixty kilometres of
each other and nothing more precise than that, ever, by construction.

## 3 · The switch, and why it is a new one

`/presence` is gated today on `RETICULUM_PRESENCE`, which is a **radio** setting: it turns on a
broadcast over LoRa and Reticulum to anyone within reach. Being visible to the four machines on your
own tailnet is a different decision from broadcasting to an open radio network, and one should not
imply the other.

So: **`DISCOVERY`**, default `0`, its own key under Set up → Node.

| setting | what it turns on |
|---|---|
| `DISCOVERY=1` | this node answers `/presence` to other nodes on the tailnet, and looks for them |
| `RETICULUM_PRESENCE=1` | this node announces over the radio, as now |
| either | `/presence` answers with the body above; they share the same words and the same floor |

`DISCOVERY=0` is the default and the shipped state. A node that is never touched is never visible.

**One switch, both directions.** A node that is not discoverable does not look for others either. The
alternative — seeing without being seen — is the shape of a thing that watches, and it is not what
this is. If you want to know who is out there, be someone they can know about.

## 4 · How a node finds the others

Tailscale already knows every machine on the tailnet; the node does not need a directory because the
tailnet is one.

**The host reads the peer list. The node never talks to `tailscaled`.** `planetai mesh` already
installs and joins Tailscale on the host, and `bin/planetai` already runs there. A new
`planetai mesh peers` runs `tailscale status --json`, takes each peer's name and tailnet address, and
writes that list into the node.

The obvious alternative is mounting `/var/run/tailscale/tailscaled.sock` into the container so the
node refreshes itself. **Refused.** That socket is the Tailscale LocalAPI, and it can bring the
tailnet up and down, read the whole network map and rewrite routes. A container serving a page to a
household LAN should not hold it. A list of names and addresses is the whole of what discovery needs,
and it is the whole of what it gets.

Then the node, on a slow loop — hourly, not every poll, because a neighbour appearing is not urgent —
does `GET http://<peer>:8080/presence` on each. That is the entire protocol. There is no write, no
handshake, no registration, no heartbeat.

**Saying hi is answering.** Both nodes probe, so both see each other, and neither had to tell anyone
anything. A node that has not answered is simply not listed.

**A tailnet is not all nodes.** It has laptops and phones, and probing port 8080 on each is a scan of
your own network — one request per machine per hour, but still worth being exact about. A reply only
counts when it is JSON carrying `enabled`, and when true a `cell` and a `node`. Anything else is a
machine that is not a node, and the node records nothing about it at all: not that it was probed, not
that it refused, not that it exists.

## 5 · What a keeper sees

On **Network**, beside the map of what this node hears by radio, a row per node that answered:

> `mahon` · home · v0.67 · **340 km away** · answered 4 minutes ago

and, when this node is not discoverable, one line instead of a list: this node is not looking, here is
the setting, and here is what turning it on would say about you — the name, the cell, the version, the
kind, and the sixty kilometres.

The list is drawn from what came back and is never cached into a claim: a node that stops answering
leaves the list, it does not become a node that "was" there. Nothing here enters `sensors`, `cells`,
`custody` or any count. It is not a source and it is not a peer in the `kind='peer'` sense — those are
readings, and this is not readings.

## 6 · What it refuses, at every stage

- No position, ever, at any resolution finer than the floor in the code.
- No reading, no alert, no sensor, no household sentence.
- No record of who probed this node. A node answers; it does not keep a visitors' book.
- No write endpoint. Discovery adds no way for another machine to change anything here.
- No central list, no bootstrap node, no service that has to be up for this to work.
- Nothing is enabled by an update. `DISCOVERY` defaults to `0` on a node that already exists and on
  one installed tomorrow.

## 7 · Open, and needing Tomas

- **Is the tailnet the right boundary?** Everything above assumes the people on one tailnet already
  trust each other enough to be seen. Discovery *between* tailnets is a different problem with a
  different answer, and Reticulum presence is already that answer over the radio.
- **Should `kind` and `version` be there at all?** They are useful — "a `community` node three cells
  away is on v0.66" is how help gets offered — and they are also a fingerprint. The cell is the thing
  Tomas asked for; the other two are an argument.
- **What a node does with the knowledge.** Seeing each other is where this stops. Asking a neighbour
  for anything is `PARENT_API_URL` today and `PEERS` when somebody builds it, and both are decisions
  a keeper makes by hand, about one named node.

---

*Grounded in `app/main.py::presence` and `PRESENCE_RES_FLOOR`, `docs/site/federation.md` ("listening
to other nodes as peers is proposed and not built in this version"), `docs/site/cli.md` on
`planetai mesh`, and `docs/site/concepts.md` on the tailnet.*
