# Networking — three problems, three layers

Three technologies keep coming up for a node's networking. They solve three different problems and should not be
confused with each other, or with the tree of nodes described in `ARCHITECTURE.md`.

| problem | layer | status |
|---|---|---|
| reaching a node behind someone's router, from anywhere | **Tailscale** (WireGuard overlay) | shipped: `planetai mesh` |
| sensors and alert delivery where there is no WiFi, no power, or no internet | **Meshtastic** (LoRa mesh) | next: Mosquitto + adapter |
| encrypted node-to-node data transport with no internet in between | **Reticulum** | parked with a trigger |

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
MQTT module uplinks the mesh to a broker. That broker is Mosquitto running on the node. A `meshtastic` adapter subscribes
to `msh/#`, maps `environment_metrics` and `air_quality_metrics` to readings (`kind='sensor'`, `local=true`), and takes
position from the radios' GPS. Mosquitto is a retired piece in `SPEC.md §6` whose trigger was *the first sensor that
publishes instead of being polled*; it has fired.

The nRF52 boards (Wio Tracker L1) have no WiFi and cannot be the gateway alone. They are the field sensors, or a
gateway by USB serial to the node's host with a small bridge.

**Outbound.** The node publishes alert text to a Meshtastic channel through MQTT downlink. A radio on a shelf relays
it to a phone over Bluetooth via the Meshtastic app. That is an alert path that works during an internet outage.

**Three things not to get wrong.**
- **Region.** Bali is **AS923**; Barcelona EU868; Boston US915. The SX1262 is wideband, so the board works anywhere, but firmware region and antenna must match local law.
- **Broker.** The firmware's default MQTT server is `mqtt.meshtastic.org`, a public broker. Point the gateway at the node's own Mosquitto or every reading leaves the building.
- **What LoRa is not.** It is not node-to-node transport. A district cannot pull a household's hourly means over LoRa; the bandwidth is two orders of magnitude short. The FAB26 plan says this correctly: "LoRa is local; the pipe that makes it a global dataset is MQTT."

**Relation to FAB26.** The six-month program hands 35 radios to lab reps. The plan's critical-path item was that the
"MQTT broker → ingest → FCI Observations pipe does not exist yet." planetai-node with Mosquitto and the `meshtastic`
adapter is that pipe, and it removes the need for a shared central broker: each lab's gateway talks to that lab's own
node, and nodes push cells up. The shared broker survives only as a fallback for a lab with a radio and no computer.

## 3. Reticulum — parked, with a trigger

**What it is.** A networking stack that runs over anything (LoRa via RNode, serial, TCP, I2P) with encryption,
authentication and source anonymity built in, and store-and-forward through propagation nodes. Architecturally it
is the most sovereign option on this page and the only one that could carry node-to-node data with no internet.

**Why not now.** A small ecosystem; no consumer phone experience comparable to Meshtastic's app; RNode hardware you
flash yourself; no sensor-telemetry conventions to inherit; a Python stack that is research-grade where the FAB26
program needs product-grade. Tailscale and Meshtastic cover every current need more simply, and someone else
maintains both.

**Trigger.** A district node and a community node with no internet between them that need encrypted data transport,
not just telemetry. When that deployment exists, Reticulum over RNode is the right tool. Recorded in `SPEC.md §6`.

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
