# Networking — three problems, three layers

Three technologies keep coming up for a node's networking. They solve three different problems and should not be
confused with each other, or with the tree of nodes described in `ARCHITECTURE.md`.

| problem | layer | status |
|---|---|---|
| reaching a node behind someone's router, from anywhere | **Tailscale** (WireGuard overlay) | shipped: `planetai mesh` |
| sensors and alert delivery where there is no WiFi, no power, or no internet | **Meshtastic** (LoRa mesh) | shipped: `planetai meshtastic` |
| encrypted messaging that works over TCP today and LoRa when a radio is plugged in | **Reticulum** (LXMF) | shipped as a bridge: `planetai reticulum` |

## 1. Tailscale — reachability

**The problem.** A node sits behind a home or lab router. You are somewhere else and want to run `planetai update`.
A household node needs to push hourly means to a district node in another building. Neither works without either
opening ports on a router (do not) or an overlay network.

**What it does.** One command per machine. Each gets a stable name and address on a private WireGuard network,
regardless of NAT, with no ports opened anywhere. `planetai mesh` installs the client, joins with the node's name,
and turns on Tailscale SSH so `ssh bayu-2` works from any of your devices with no keys to manage. Free for 100
devices.

**The trade-off.** Tailscale's coordination server is a third party, which sits against the principle that nothing
here should need one. The data path is peer-to-peer WireGuard; only key exchange and the address book go through
them. The exit is **Headscale**, a self-hosted coordinator that the same client talks to. It is parked in `SPEC.md §6`
with its trigger: a partner whose governance rules out a third-party coordinator, or exceeding the free tier.
Switching is one flag on each node (`--login-server`).

**Headless Macs.** Use the Homebrew daemon (`brew install tailscale`), not the App Store app. The daemon runs as a
system service with nobody logged in, which is what a node in a cupboard needs. `planetai mesh` does this.

**Unattended joins** for future nodes: create a pre-authorised key in the Tailscale admin console and run
`TS_AUTHKEY=tskey-auth-… planetai mesh`. No browser step.

## 2. Meshtastic — the ground layer

**The problem.** A sensor on a rice-field edge, a temple spring, a rooftop with no router. And: delivering an alert
when the internet is down, which in Bali is a routine condition rather than an edge case.

**What it does.** LoRa radios (in our case Seeed Wio Tracker L1 and Wio-SX1262) form a mesh that carries a few hundred
bytes a minute over kilometres, on a battery, for weeks. Meshtastic's telemetry module reads sensors natively: BME680
and SEN5x today, HM3301 when its driver lands. The HM3301 is the same Seeed particulate sensor as the Smart Citizen 2.3
kit, so its readings need no humidity correction.

**How it reaches the node.** One radio is the *gateway*: a WiFi-capable board (an ESP32 such as the Wio-SX1262) whose
MQTT module uplinks the mesh to a broker. That broker is Mosquitto on the node, behind the `mqtt` compose profile with a
password. `planetai meshtastic` creates the credentials, starts the broker, and prints every setting to type into the
gateway, then waits for the first packet. The adapter subscribes to `msh/#`, reads the JSON form of each packet
(`telemetry` → readings, `position` → the sensor's coordinates from the radio's GPS, `nodeinfo` → its name), and files
mesh sensors as `kind='sensor'`, `local=true`, outdoor unless listed in `MESH_INDOOR_NODES`. Unknown telemetry fields
are logged once rather than dropped, so a firmware rename shows up in the log instead of as silence.

**Outbound.** With `MESH_ALERTS=1` and the gateway's node number set, act-level alerts are published to the mesh
downlink topic and the gateway transmits them. Only the first line goes; a LoRa frame carries about 200 bytes.

**The same broker also takes DIY pods**: anything publishing `planetai/sensors/<id>/<metric>` with
`{"value": 12.3}` lands as `pod-<id>`. An ESP32 with a PMS5003 and ten lines of firmware is a sensor.

The nRF52 boards (Wio Tracker L1) have no WiFi and cannot be the gateway alone. They are the field sensors, or a
gateway by USB serial to the node's host with a small bridge.

**Three things not to get wrong.**
- **Region.** Bali is **AS923**; Barcelona EU868; Boston US915. The SX1262 is wideband, so the board works anywhere, but firmware region and antenna must match local law.
- **Broker.** The firmware's default MQTT server is `mqtt.meshtastic.org`, a public broker. Point the gateway at the node's own Mosquitto or every reading leaves the building.
- **What LoRa is not.** It is not node-to-node transport. A district cannot pull a household's hourly means over LoRa; the bandwidth is two orders of magnitude short. The FAB26 plan says this correctly: "LoRa is local; the pipe that makes it a global dataset is MQTT."

Setting up each radio, by board and by job: [`MESHTASTIC.md`](MESHTASTIC.md).

**Relation to FAB26.** The six-month program hands 35 radios to lab reps. The plan's critical-path item was that the
"MQTT broker → ingest → FCI Observations pipe does not exist yet." planetai-node with Mosquitto and the `meshtastic`
adapter is that pipe, and it removes the need for a shared central broker: each lab's gateway talks to that lab's own
node, and nodes push cells up. The shared broker survives only as a fallback for a lab with a radio and no computer.

## 3. Reticulum — the bridge is in, the radio is a config block

**What it is.** A networking stack that runs over anything (LoRa via RNode, serial, TCP, I2P) with encryption,
authentication and source anonymity built in, and store-and-forward through propagation nodes. Architecturally it
is the most sovereign option on this page and the only one that could carry node-to-node data with no internet.

**Why not now.** A small ecosystem; no consumer phone experience comparable to Meshtastic's app; RNode hardware you
flash yourself; no sensor-telemetry conventions to inherit; a Python stack that is research-grade where the FAB26
program needs product-grade. Tailscale and Meshtastic cover every current need more simply, and someone else
maintains both.

**What ships.** `planetai reticulum` starts a small bridge container (`app/reticulum_bridge.py`, behind the `reticulum`
profile) that gives the node an LXMF address, announces it, and does two things. Inbox: a message reading `act <id> [note]`
from Sideband or NomadNet becomes a recorded action on that alert — the loop closes over a medium that needs no
internet. Outbox: act-level alerts are delivered to every LXMF address in `RETICULUM_ALERT_DESTINATIONS`. The
transport is whatever `config/reticulum/config` enables: a TCP server on 4242 always (reachable over the LAN or the
tailnet, so Sideband on a phone connects to it today); an RNode LoRa radio when its block is uncommented and the
device is passed into the container, which is Linux-only because macOS Docker cannot see USB serial.

**Still parked.** Node-to-node *data* transport over Reticulum (a district pulling means from a child with no internet
between them). That is a Transport-enabled node plus a store-and-forward design, and the trigger stands: build it when
that deployment exists.

## What connects to what

```
  phone (Meshtastic app) ◀── BLE ── radio on the shelf ◀── LoRa ── field sensors (Tracker L1 + BME680/HM3301)
                                                              │
                                              gateway (ESP32, WiFi) ── MQTT ──▶ Mosquitto on the node
                                                                                      │
                                                            you, anywhere ── Tailscale ──▶ node ── Tailscale ──▶ district node
```

Three layers, none of them ours to maintain. What is ours is the adapter, the rules, and the record of whether
anyone acted.
