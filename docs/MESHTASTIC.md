# Setting up the radios

Three kinds of radio, three jobs. Which board you hold decides the job, not the other way round.

This page is the *why*. For *what to press*, in the app, one screen at a time, including the two things that stop most
first attempts (a power switch and a six-digit code): [`MESHTASTIC_APP.md`](MESHTASTIC_APP.md).

| board | chip | WiFi | GPS | job |
|---|---|---|---|---|
| **XIAO ESP32-S3 + Wio-SX1262** | ESP32-S3 | yes | no | **the gateway**: uplinks the mesh to the node over WiFi. One per node. |
| **Wio Tracker L1** (L1, L1 Lite, L1 e-ink) | nRF52840 | no | yes | **field sensors**: a BME680 or HM3301 on the Grove port, on a battery, somewhere with no WiFi. |
| **Wio Tracker L1 Pro** (cased, with battery) | nRF52840 | no | yes | **the handheld / the shelf radio**: a person's, paired to their phone, receives alerts. Or a field sensor that already has a case. |

The whole L1 series is the same board with different displays; anything below about "the Tracker" applies to all four.
nRF52 radios have no WiFi, so they cannot talk to the node directly. They talk to the gateway over LoRa, and the gateway
talks to the node. That is the whole topology.

**Before anything else, two rules that cost hardware if ignored.**
1. **Never power on a radio without its antenna attached.** An SX1262 transmitting into nothing can destroy itself.
2. **Every radio on your mesh must have the same LoRa region and the same channel.** Region is set first, before anything else works.

## 0. Region and channel: the same on every radio

**Region.** Bali is `SG_923` — the AS923 band Indonesia allocates (920–923 MHz); Meshtastic has no Indonesia-specific
code. Barcelona `EU_868`. Boston `US`. Set it in the app under *Radio configuration → LoRa → Region*. A radio with the
region unset does not transmit at all. A radio with the wrong region transmits illegally.

**Channel.** Create one private channel on the first radio and copy it to every other: *Radio configuration → Channels
→ add*, name it after the node (`bayu-2`), let the app generate a PSK, and share it to the other radios with the QR code
the app produces. Everything on that channel is encrypted between radios; the gateway decrypts it for the node.
Leave the default `LongFast` in place as well; it costs nothing and lets your radios see other Meshtastic users nearby.

**Preset.** *LoRa → Modem preset*: `LONG_FAST` is the right default. `MEDIUM_FAST` gives more bandwidth for
telemetry-heavy meshes at the cost of range; try it only if packets are being dropped.

## 1. The gateway — XIAO ESP32-S3 + Wio-SX1262

**Firmware.** If it is not pre-flashed: connect by USB-C, open https://flasher.meshtastic.org in Chrome, choose
*Seeed XIAO ESP32S3 & Wio-SX1262 kit*, latest stable, flash.

**First configuration, over Bluetooth from the phone app:** region (§0), then the channel (§0), then a name:
*Radio configuration → User → Long name* `bayu-2 gateway`, short name `GW`. Device role stays `CLIENT`.

**WiFi.** *Radio configuration → Network → WiFi enabled*, SSID and password of the network the node's computer is on.
The radio reboots. **From now on Bluetooth is off** — on ESP32 boards Meshtastic runs WiFi or Bluetooth, not both.
To change anything further, open `http://<the radio's IP>` in a browser (the app shows the IP under the device, or
find it in your router), or plug it into a computer with `pip install meshtastic` and use the CLI over USB.

**MQTT.** Run `planetai meshtastic` on the node first: it creates the broker credentials and prints this block filled
in with your values. Then in the web client, *Module configuration → MQTT*:

    Enabled              on
    Address              <the node computer's LAN IP>:1883      planetai meshtastic prints it
    Username / Password  planetai / <printed>
    Encryption enabled   OFF      — the broker is yours. Encrypted uplink hides readings from your own node.
    JSON output enabled  ON       — without this the node cannot read a single packet
    Root topic           msh
    TLS                  off

Then *Channels → your channel → Uplink enabled ON, Downlink enabled ON*. Uplink sends the mesh to the node;
downlink lets the node send alerts back.

**Placement.** Near the router, antenna vertical, not on a metal shelf, ideally high with a window. It is the one radio
that must have both good WiFi and good LoRa reach.

**Its node number**, for alerts back over the mesh: the app shows it as `!a1b2c3d4`. The node wants decimal:
`printf '%d\n' 0xa1b2c3d4`. Put that in `.env` as `MESH_GATEWAY_NODE_NUM`, set `MESH_ALERTS=1`, `planetai restart`.

## 2. Field sensors — Wio Tracker L1 / L1 Lite / L1 e-ink

**Firmware.** Pre-flashed. To update: hold the reset button pattern from Seeed's wiki to get a USB drive named
`WIO_L1…`, drag the `.uf2` from https://flasher.meshtastic.org onto it.

**Sensor.** Plug a Grove I²C sensor into the Grove port before powering on. Meshtastic detects I²C sensors at boot.
Seeed's verified list for this board is BME280, SHT31/SHTC3/SHT4x, AHT10, BMP085, MCP9808, PCT2075. The BME680 is
supported by Meshtastic's telemetry module in general but is *not* on Seeed's verified list for the L1; test one before
trusting a batch of twenty-five. SEN5x (PM + VOC + NOx) is supported by the module; likewise unverified on this board. The HM3301 needs its driver present in the firmware you flash; check the release notes, and
if it is not there yet the BME680 alone is still a useful outdoor unit.

**Configuration, over Bluetooth:** region, channel (§0), then
- *User → Long name* the place, not the device: `Subak edge`, `Temple spring`. It becomes the sensor's name in the node.
- *Device → Role* **`SENSOR`**: broadcasts telemetry and position, sleeps between, does not relay other traffic.
- *Position → Broadcast interval* 30 min; *GPS* on. The Tracker has GPS, so the node learns where the sensor is without you typing coordinates.
- *Module configuration → Telemetry → Environment measurement enabled* on, *update interval* 15 min (900 s). *Air quality enabled* on if a PM sensor is attached.
- *Power → Sleep*: leave the defaults; the `SENSOR` role already sleeps aggressively.

**Power.** USB-C for the bench. In the field: a 2000–3000 mAh LiPo on the JST connector runs a `SENSOR`-role Tracker
with 15-minute telemetry for days to weeks; a 5–6 V solar panel on the two-pin solar input keeps it running
indefinitely. The board manages charging.

**Placement.** Antenna vertical, as high as practical, line of sight to the gateway if you can. The sensor itself needs
to breathe and stay dry: a radiation shield or a printed vented enclosure (the outdoor-sensor-enclosure work), never a
sealed box and never direct sun on the sensor. 3–6 m up, away from a kitchen exhaust.

**Indoor units.** Same setup. Then tell the node: `MESH_INDOOR_NODES=!<its id>,…` in `.env`, `planetai restart`.
Indoor readings never enter an ambient average; the rules depend on the flag being right.

## 3. The shelf radio and the handheld — Wio Tracker L1 Pro

Same board in a case with a battery, so the same configuration as §2 minus the sensor. Two uses:

**On a shelf in the house, paired to the household's phone.** Role `CLIENT`. This is how an alert reaches someone
when the internet is down: the node publishes it on the mesh, the gateway transmits it, the shelf radio hears it and
hands it to the phone over Bluetooth, the Meshtastic app shows it. Nothing in that path needs an ISP.

**In a pocket, for whoever walks the deployment.** Same, plus GPS on so the mesh map shows where they are. Useful for
finding a good spot for a field sensor: watch the signal report in the app as you move.

If instead you have a **SenseCAP T1000-E** (the card-shaped tracker), it fills the same role: nRF52840, no Grove
port, pre-flashed, pairs to a phone. It cannot carry a sensor, but it can carry an alert.

## 4. Roles, in one line each

`CLIENT` — the default; talks and relays normally. Gateway, shelf radio, handheld.
`SENSOR` — telemetry and position, sleeps, no relaying. Every field unit.
`ROUTER` — a dedicated relay on a hill or roof, mains-powered. Only if you have a coverage gap; too many routers make a mesh worse.
Never `ROUTER` on a battery unit, and never on the gateway.

## 5. Checking it works

On the node: `planetai meshtastic` waits for the first packet and lists sensors as they appear; afterwards
`planetai sensors` shows every `msh-…` unit with its name and whether it is indoor or outdoor, and `planetai status`
shows the mesh packet count under `mesh`. `planetai logs` shows any telemetry field the adapter did not recognise, by
name — send those along and they get added.

In the app: the gateway's node page shows *Uplink/Downlink* counters climbing; each field unit's page shows its last
telemetry and position; the map shows where everything is.

Nothing arriving is nearly always one of: JSON output off on the gateway; wrong IP for the broker (`planetai
meshtastic` prints the right one); the gateway on a different WiFi from the node; a region mismatch between radios;
or the field unit not on the private channel. In that order.

## 6. What a mesh cannot do

A LoRa frame is about 200 bytes and a channel carries a handful of them a minute. It moves telemetry and one-line
alerts. It does not move hourly means between nodes, images, or anything a district would aggregate — that goes over
Tailscale. `docs/NETWORKING.md` has the full split.
