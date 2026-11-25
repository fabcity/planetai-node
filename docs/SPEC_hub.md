# SPEC: nodes hear each other through a hub

*Asked, 24 November 2026, by Tomas: the hello workflow "is not allowing users to easily allow their node to be
discoverable within the network". Is Tailscale a limitation, should we consider Headscale, "or, can we do it with
reticulum (it would be ideal), as it also creates a distributed infrastructure". Read the same day against main and
node #1; Tomas: "Yes, write the spec".*

**Status: ruled; step 0 merged, the Funnel on, step 1 built (25 November).** The act allowlist is
fabcity/planetai-reticulum#1 (a65ad0f), pinned by planetai-node #422 (f1fcfa7), and node #1 runs it. Step 1 is this
pull request and its bridge commit. Steps 2 to 4 are not built. Tomas, 24 November: "Lets do the mac mini as the hub. On for the bend. Not yet as you
propose. hello as a reticulum message". Then "Use a relay server", and, once Tailscale Funnel turned out to carry
it with no server, "Yes, switch it". So node #1 is the first hub, reached through Funnel with a relay as the fallback
(§3), the bend in §10 stands, the hub does not dial the public Reticulum testnet yet, and hello travels as a
Reticulum message (§9). Steps 0 to 4 are each a pull request, in the repository the table in §12 names, and each runs
on node #1 before it merges.

## 1 · What a node can do today

A node is **listed** or **heard** (SPEC_hello §2). Read on 24 November:

- **Listing needs GitHub, and two nodes have made it.** `planetai hello` needs `gh` logged in, forks this repository,
  opens a pull request, and a person merges it. Without `gh` it prints JSON to paste on GitHub by hand. Since the
  command shipped in October, `registry.json` holds two nodes, `bayu-ungasan` and `barcelona`. Lars's first try
  (#365) failed on an old fork. `mahon1` and node #3 are not listed.
- **Hearing is built, but nothing carries it.** The bridge announces `planetai.presence` and its LXMF address every
  half hour. The config it ships, `config.tpl` in fabcity/planetai-reticulum, opens one TCP server on port 4242 and
  dials nowhere, with transport off. A node hears only a machine that dials into it, and none do. Node #1 on 24
  November: `announcing: true`, `peers: []`.
- **The tailnet path was never built.** SPEC_discovery §2–5 ("Tailscale first", 22 September) gave way to
  SPEC_hello in October. A tailnet belongs to one account. Node #1 and `mahon1` are on Fab City's,
  node #3 is on Tomas's own, and the two meet only where a machine is shared, in one direction. SPEC_discovery §9
  already says there is no way across two tailnets.
- **SPEC_hello §4 is not built.** The Node door says heard nodes are "not on this map yet". The addition it asked
  for, `GET /geo/cell` taking a cell id, is already there.

## 2 · Why not Headscale

Headscale is a Tailscale control server you run yourself, and it runs one tailnet. A programme tailnet means Fab City
keeps a server up for every join, every household's API sits on one network with people it does not know, someone
writes and keeps the access rules, and an operator leaves their own tailnet to join ours, since a machine is logged
into one at a time. It does nothing for the GitHub step. It stays parked in SPEC.md §6, with its trigger.

## 3 · The hub

A hub is a node whose bridge has transport on and that the internet can reach, directly or through a tunnel. Other
nodes dial out to it, so nothing opens on their routers. It passes each announce on to every node connected to it,
so a node on the hub hears every other one within half an hour, without a pull request or a tailnet.

The first hub is node #1, `bayu-ungasan`, on the Mac mini. Its bridge already listens on 4242 and the machine already
publishes that port, so being the hub is one line in its `config/reticulum/config`:

```
[reticulum]
  enable_transport = Yes
```

The mini cannot take a connection from the internet, so Tailscale Funnel takes it instead. Tailscale's servers take
connections on port 443 of the mini's tailnet name and carry them to the mini, where Tailscale ends the TLS and hands
plain TCP to the bridge on 4242:

```
sudo tailscale funnel --bg --tls-terminated-tcp=443 tcp://localhost:4242
```

Funnel takes only TLS, and Reticulum's TCP client sends plain TCP. So a node dials through `openssl s_client` in a
`PipeInterface`, which frames packets the same way the TCP interface does (both HDLC, read in rns 1.5.4). The bridge
image already carries `openssl`, so this needs no code:

```
[[Fab City hub]]
  type = PipeInterface
  enabled = yes
  command = openssl s_client -quiet -verify_return_error -connect fabalabbali.tail71245c.ts.net:443 -servername fabalabbali.tail71245c.ts.net
  respawn_delay = 15
```

The mini's own address is never published, and its tailnet name goes with it when it moves to the lab. Funnel serves
only ts.net names, so the hub has no `planetai.fab.city` name. Funnel is in beta, with bandwidth limits Tailscale does
not publish, and announces are small. Sideband on a phone cannot dial a Funnel hub, since it has no way to wrap its
connection in TLS; a phone reaches its node over the LAN or the tailnet as today, or through a relay if one is added.

If Funnel fails the test in §6, or stops serving, a relay takes its place: a small server with a fixed public address
on Fab City's tailnet, running `socat TCP-LISTEN:4242,fork,reuseaddr TCP:<node #1's tailnet name>:4242` and nothing
else, with the tailnet's policy letting it reach only that port. Nodes then dial the relay with a plain
`TCPClientInterface`, and nothing else in this spec changes.

Relaying for others is a service a community node offers its territory (the node types of 22 and 23 November). A
base node keeps `enable_transport = No` and never carries another node's traffic. A lab can run a second hub the same
way, through Funnel, a relay, or neither when its node takes connections itself, and a node can dial one or two.

One presence announce and one LXMF announce per node per half hour is about seven a minute at a hundred nodes. The
hub keeps what Reticulum keeps to route (paths and known identities) and nothing PLANETAI adds. It stays its own
network and does not dial the public Reticulum testnet (Tomas: not yet).

## 4 · Two choices for the household

On a hub, the bridge's LXMF announce reaches everyone connected: the name `planetai <NODE>` and an address. That
happens with presence off. So dialling a hub is a choice about being seen, and the spec treats it as one:

| choice | where it is made | what others on the hub see |
|---|---|---|
| dial a hub | `planetai reticulum` asks, and writes a `[[Fab City hub]]` block into `config/reticulum/config` | the node's name and LXMF address |
| `RETICULUM_PRESENCE=1` | Set up › Sharing, as now | also its cell at res 3 (about 60 km), version, kind and id |

Neither is turned on by an update. A node already running the bridge keeps its config as it is until someone runs
`planetai reticulum` again and says yes. Saying no on a later run takes the block out.

## 5 · Step 0: `act` only from the node's own people

`on_message` in the bridge records `act <id>` from any sender. On a LAN or a tailnet the only senders are the
household's people. On a hub, anyone who heard the address can close the node's alerts, and ρ in the open export
counts those rows. Node #1, as the hub, is the most exposed node of all.

So before node #1 opens its Funnel, the bridge records an act only from an address the node sends alerts to:
`RETICULUM_ALERT_DESTINATIONS` and, once #414 lands, every address `/send` has been given in a `to` list. The bridge
keeps them in its `/data` beside the heard peers. Any other sender gets one reply, "this node takes act only from the
addresses it sends alerts to", and nothing is written.

## 6 · Step 1: the mini becomes the hub, and nodes dial it

- **Reaching the mini:** on 24 November it had no public IPv6 and sat behind two routers, neither with a forward
  for it, so Funnel carries every connection (§3).
- **The mini's tailnet, done 24 November:** no TCP crossed the tailnet to or from the mini, while `tailscale ping`
  answered. Two Tailscale clients ran on it as two machines in Fab City's tailnet, the system daemon and the app with
  its network extension, and both claimed the tailnet's addresses. `planetai mesh` says a headless Mac runs the
  daemon, so the app was disconnected, quit and kept from starting at login. Ports 22, 8081 and 4242 then answered
  over the tailnet.
- **Funnel, on Tomas's side (on since 25 November):** the tailnet policy grants the mini the `funnel` attribute, and
  Tomas ran the `tailscale funnel` line of §3 on the mini. `tag:planetai-node` is also on mahon, Lucas's MacBook Air
  and dieznode, so the grant belongs on a tag only the mini carries, `tag:planetai-host`, never on
  `tag:planetai-node`.
- **The test, before any node dials it (passed 25 November):** a throwaway Reticulum instance with the §3 block,
  pointed at a relay address from public DNS (103.84.155.153) and not at the tailnet address MagicDNS gives, sent
  `act 1` to node #1's LXMF address. The bridge logged it, refused it, and its reply came back through the Funnel.
  The certificate is Let's Encrypt for the mini's name. The first connection to a relay waits while Tailscale fetches
  it, and IPv6 did not connect from behind the Deco. A presence announce heard through the Funnel is still to see; it
  comes every 30 minutes, and step 2 needs it.
- **On the mini:** `enable_transport = Yes` in node #1's own config. It has said so since 14 September, so node #1
  has passed announces on all along, with nobody dialling it. A new hub needs the line and then
  `docker compose restart reticulum`, since the bridge reads the file when it starts and `planetai restart` recreates
  only the app.
- **fabcity/planetai-reticulum:** `config.tpl` gains the `[[Fab City hub]]` block of §3, commented. The bridge's
  `/health` says whether the hub interface is up, so a node that hears
  nobody can tell whether the hub is down. Heard rows keep the `id` a presence body carries (§7).
- **planetai-node:** `cmd_reticulum` asks whether to dial the hub, says what others will see (§4), and writes the
  block when the answer is yes and the file has none, or takes it out on no. Last time's answer is the default, so a
  run with no terminal changes nothing. It then recreates the bridge, which reads its config only at start.
  `planetai doctor` checks the hub when the block is there. `/health` › reticulum carries `hub` (on it, or not
  answering) and `relaying` (on a hub, the nodes connected), and the Node door's Radio row says both. Heard rows
  keep `id`. `RETICULUM_REF` moves to the new commit, as every bridge change does.

## 7 · Step 2: draw what was heard

SPEC_hello §4 as written, with one change: the presence body gains `id`, the node ID `/health` already carries
(SPEC_identity §2). A heard node is matched to a listed one by `id`, and by name only when either side has none.

The Node door outlines each heard node's res-3 cell (through `GET /geo/cell`) and adds a row: "heard on the hub,
20 min ago, about 340 km away", with "listed" beside it when the registry has it too. A heard node that is not
listed has an outline and no point. Nothing about a peer reaches custody, cells, aggregates, alerts or the export.

Hearing a node proves nothing about who sent the announce. Any machine can announce any name or id, because the
announce is signed by its Reticulum identity and the node key plays no part in it.

> ponytail: matched by id and never verified. Sign the presence body with the node key when the first forged row shows up.

## 8 · Step 3: one question in setup

At the end of `planetai setup`:

```
Let other PLANETAI nodes see this node?
  They would see its name, its LXMF address, and an area about 60 km across.
  Never a reading, a sensor or where the house is. Reticulum's licence is not an open licence:
  https://planetai.fab.city/docs/channels/
Turn it on? [y/N]
```

Yes runs `planetai reticulum` with the hub answered yes and sets `RETICULUM_PRESENCE=1`. No is the default and asks
nothing more. A node set up before this release gets the same question from `planetai reticulum`.

## 9 · Step 4: hello as a Reticulum message

Being heard does not put a node on the programme's list, and the list stays the approved one. What needs GitHub
today is sending the entry, and Tomas chose to send it over Reticulum. That also settles the question the 23 October
licence ruling left open: a registry entry is discovery, so it may travel over Reticulum.

- **The programme's inbox** is an LXMF address, kept in `registry.json` as `inbox` beside `nodes`, so it moves by
  pull request like everything else on the list. The first inbox is node #1's bridge.
- **Sending:** `planetai hello` builds and shows the entry as it does today and asks before sending. With the bridge
  running it sends `hello <the entry as JSON>` to the inbox through the bridge's `/send` and prints whether the inbox
  took it. Without the bridge it uses `gh` as today, and without either it prints the edit link.
- **Receiving:** the inbox's bridge takes a message that starts with `hello`, keeps it when it parses as an entry with
  the fields `planetai hello` writes and nothing else, and replies "received: a person reads it before it is listed".
  It writes nothing on the node and takes no allowlist, since anyone may ask to be listed. Messages wait in its
  `/data`, and the bridge answers them on `GET /inbox`.
- **Listing:** on node #1, `planetai hello --inbox` shows what arrived and, for the one the keeper picks, opens the
  pull request with the keeper's own `gh`. The merge stays the approval. Within the hour of it, every node lists the
  new one, as today.

> ponytail: one stored entry per sender, the newest, and at most 200 in all. A queue with history when a busy week
> shows it is needed.

## 10 · What it keeps, and the one bend

Kept from SPEC_discovery §8 and SPEC_hello §6: no position finer than res 6, since presence does not change; no
reading, alert, sensor or household sentence; no write endpoint on the node; nothing on by an update; no base node
relays for another. Reticulum carries discovery and messages to people, which the 23 October ruling allows, and
parent links stay on HTTPS.

The bend is §8's "no bootstrap node, no service that has to be up". A hub is one, and Tomas accepted it on 24
November. While the first hub runs on Funnel, Tailscale's servers are part of that service. A node that cannot reach
a hub works as it does today and hears nobody. A second hub can run on any community node, and the hubs a node dials
are written in its own Reticulum config, where the household can change them.

## 11 · Ruled, and still open

Ruled by Tomas, 24 November:

1. The first hub is the Mac mini, node #1.
2. The bend in §10 stands.
3. The hub does not dial the public Reticulum testnet yet.
4. Hello travels as a Reticulum message (§9).
5. Tailscale Funnel carries connections to the mini, with a relay server as the fallback (§3), and no forward on
   any router.

Done 25 November: the Funnel is on and a message went both ways through it (§6). Still open: the `funnel` grant
narrowed to `tag:planetai-host` once the mini carries that tag (Tomas's), then the rest of step 1, starting with
`enable_transport = Yes` on node #1.

## 12 · Files

| Step | Repository | Files |
|---|---|---|
| 0 | planetai-reticulum | `reticulum_bridge.py` (`on_message`, the remembered addresses), `tests/test_peers.py` |
| 1 | planetai-reticulum | `config.tpl`, `reticulum_bridge.py` (`/health`, `id` in heard rows), `README.md` (running a hub through Funnel, or a relay) |
| 1b | planetai-node | `bin/planetai` (`RETICULUM_REF`, `cmd_reticulum`), `docs/NETWORKING.md`, `docs/site/channels.md`, `CHANGELOG.md` |
| 2 | planetai-node | `app/presence.py`, `app/static/doors-node.js`, `app/static/doors-nodegeo.js`, `tests/test_nodes_registry.py` |
| 3 | planetai-node | `bin/planetai` (`cmd_setup`), `tests/test_hello.sh`, `docs/site/cli.md` |
| 4 | planetai-reticulum | `reticulum_bridge.py` (`hello` messages, `GET /inbox`), `tests/test_peers.py` |
| 4b | planetai-node | `bin/planetai` (`cmd_hello`), `registry.json` (`inbox`), `tests/test_hello.sh`, `docs/site/cli.md`, `docs/SPEC_hello.md` |
