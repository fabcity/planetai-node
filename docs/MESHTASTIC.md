# Radios
<!-- checked: v0.82.1 -->

Three boards. The board suggests the job; the settings decide it, and `planetai radio provision` sets them.

| board | chip | WiFi | GPS | job |
|---|---|---|---|---|
| XIAO ESP32-S3 + Wio-SX1262 | ESP32-S3 | yes | no | **gateway** (uplinks the mesh to the node over WiFi, one per node) or **sensor node** with an I2C sensor, like the Bayu sensor by Fab Lab Bali. Same image either way. No GPS: a sensor node gets `--fixed LAT,LON`. |
| Wio Tracker L1 (L1, Lite, e-ink) | nRF52840 | no | yes | **field sensor**: a 3.3 V sensor on the Grove port, on a battery, where there is no WiFi. |
| Wio Tracker L1 Pro, SenseCAP T1000-E | nRF52840 | no | yes | **shelf radio**: paired to a phone, receives alerts when the internet is down. |

The L1 variants are one board with different displays. nRF52 radios have no WiFi, so they reach the node through a
gateway: the XIAO on WiFi, or any radio on the node's own USB (`planetai radio gateway`).

Two rules that cost hardware if ignored: **antenna on before power**, always. **Same region, same frequency slot and
same channels on every radio**, region first, or the radio never transmits.

## Firmware: the browser

**`makingsense.fablabbali.com/flash`** flashes the XIAO from Chrome or Edge over USB and hands out the trackers' UF2
and DFU files, all from the pinned stable release (not what Meshtastic's own flasher offers first: it offered a 2.8.1
alpha that is not a release). All radios on one version. The page sets no region and no channel on purpose; that is the
next step, and it belongs to the node.

Trackers by hand: drag-to-drive fails on macOS 26 (error -36 / Input/output error, whatever the bootloader version:
FSKit). Use serial DFU. Double-click RST, then:

```bash
pip3 install --user adafruit-nrfutil
adafruit-nrfutil dfu serial --package firmware-seeed_wio_tracker_L1-<ver>-ota.zip -p /dev/cu.usbmodem1101 -b 115200 --singlebank
```

XIAO: hold BOOT while plugging in if no port appears. Never use the phone OTA app on these boards; Seeed says it can
brick them.

## Your first radios, step by step

Run **`planetai radio`** at any point. It ticks what is done, lists the radios plugged in by USB right now, and ends
with the one command that comes next, port filled in. Everything below happens on the node's machine (node #1: the
mini), with the radios plugged into it.

0. **The packages, once.** `planetai radio` says what to install for its own Python. On a Mac with Apple's Python 3.9:
   `python3 -m pip install --user "pyobjc-core<12" "pyobjc-framework-Cocoa<12" "pyobjc-framework-CoreBluetooth<12"
   "pyobjc-framework-libdispatch<12" meshtastic paho-mqtt`.
1. **The broker.** `planetai meshtastic`. The node gets an MQTT broker and a user for it; this is where the gateway
   delivers what the radios hear. *You see:* the broker's address and password, and `planetai radio` ticks step 1.
2. **The fleet.** `planetai radio init`. One set of channel keys, region and frequency for every radio of this node,
   in `config/radio/fleet.yaml`. *You see:* `region SG_923, slot 19 (921.625 MHz)` on a Bali node. If the city has no
   known region it stops and asks for `--region`: it never guesses, because a radio on another country's band is illegal there.
3. **The gateway radio.** Antenna on, then plug a radio into the node's USB and run the command `planetai radio`
   prints, e.g. `planetai radio provision gateway-host "bayu gateway" GATE --port /dev/cu.usbmodem1101`. It writes every
   setting in one go and the radio reboots once. *You see:* `>> ok. !abcd1234 is on the fleet's channels`.
4. **The gateway, always on.** `planetai radio gateway --port /dev/cu.usbmodem1101 --install`. The gateway becomes a
   service that starts again after every restart. *You see:* `the gateway runs as a service now`. Leave this radio
   plugged in.
5. **Each other radio.** Plug it in by USB, provision it, unplug it, take it where it goes:
   a field sensor `planetai radio provision sensor "Subak edge" SBK --port …` (a Tracker has GPS; a XIAO sensor node gets
   `--fixed LAT,LON`), a relay `relay`, a shelf radio for alerts when the internet is down `shelf`. Name a sensor for the
   **place**: that name becomes the sensor's name in the node.
6. **Phones.** `planetai radio url` prints the three steps and the link (a QR too, with `qrencode` installed): the
   Meshtastic app, Bluetooth pairing, then open the link and accept replacing the channels.
7. **Is it working?** `planetai radio doctor --port …` checks the usual reasons nothing arrives, one by one; the bench at
   `http://<this node>:8080/tester` draws every radio the node hears. A sensor's first reading arrives within its
   15-minute interval.

### All the commands

```bash
planetai radio                                           # where you are, and the next command
planetai meshtastic                                      # the broker and its user
planetai radio init                                      # the fleet: region from NODE_CITY, slot, two channel keys
planetai radio provision gateway-host "bayu radio" NODE --port /dev/cu.usbmodem1101
planetai radio gateway --port /dev/cu.usbmodem1101 --install
planetai radio provision sensor "Subak edge" SBK --port /dev/cu.usbmodem1101             # a Tracker: it has GPS
planetai radio provision sensor "Warung roof" WRG --port … --fixed -8.80045,115.17664    # a XIAO sensor node: pin it
planetai radio provision shelf "kitchen shelf" SHF --port /dev/cu.usbmodem1101
planetai radio url                                       # for phones: the link, the QR, the three steps
planetai radio doctor --port /dev/cu.usbmodem1101
```

One settings transaction per radio, one reboot. `render` instead of `provision` prints the profile without touching a
radio. A WiFi gateway is `provision gateway-wifi … --wifi SSID:PSK`; it fills the broker address and password itself.

**The fleet** lives in `config/radio/fleet.yaml` (mode 600, gitignored: it holds the keys). Two channels, each with its
own 256-bit key: `planetai` is **primary**, the household's, and carries telemetry and position; radios send those on
channel 0 only, which is why a private channel added as secondary never carried sensor data (our gateway sat a day
publishing nothing). `fabcity` is secondary and is what crosses to other nodes, with position capped at 13 bits
(2.9 km). **Bali's slot is pinned** inside Indonesia's 920–923 MHz; SG_923 spans 917–925 and a slot hashed from the
channel name can land outside it. Regions: Bali `SG_923`, Barcelona and Menorca `EU_868`, Boston `US`.

Radios provisioned before `planetai radio` (the old mesh-provision.sh script and `~/planetai-mesh.url`) are on the old
key and the hashed slot: provision each once more, the gateway last.

Name field sensors for the **place**: the name becomes the sensor's name in the node. Indoor radios go in
`MESH_INDOOR_NODES=!id,!id` in `.env`; a radio does not know which side of a wall it is on.

**Other nodes.** `RADIO_PEERS=menorca=<tailnet host>:1883:<their MQTT_PASS>` and `planetai radio federate --write`
bridge this node's broker to theirs over the tailnet. Text and alerts on the `fabcity` channel cross, six lines a minute
at most; readings and positions never do. `docs/SPEC_radio.md` has the whole design.

## Is it working? The bench

**`http://<this node>:8080/tester`** draws every device this node reads, in layers you switch on and off: mesh
radios through the gateway, WiFi pods on the broker, LAN devices, Smart Citizen kits, stations and models, other
nodes. On this machine (`http://localhost:8080/tester`) it also reads a board on USB: each sensor animated, and a
check list for sensors found, WiFi, clock and publishing. From any other laptop, USB is at
`makingsense.fablabbali.com/test`, which works offline after one visit.

## The phone app

If you would rather tap. Bluetooth first, then the radio appears as `Meshtastic_xxxx`.

**PIN.** Radios with a screen show it. Radios without (L1 Lite, XIAO) use `123456`.

**The quick way by phone:** `planetai radio url` prints the link, the QR and the three steps. Region, slot and keys arrive together. The steps below are for a radio with no node in reach.

**Region.** *Radio configuration → LoRa → Region.* Do it before anything else. A radio with region unset does not transmit
and nothing tells you.

**Prove two radios see each other** on the default `LongFast` channel before creating a private one: a few metres apart,
the other appears under Nodes within a minute. If not: region on both, same firmware, antennas, distance.

**Then the channel.** Edit the **primary** channel (`LongFast`, index 0): rename it, generate a 256-bit key. Share by
QR to every other radio.

**Field sensor:** role `SENSOR`, GPS on, position every 30 min, *Telemetry → Environment* on at 15 min. Plug the Grove
sensor before power-up; I²C is scanned at boot.

**Gateway, in this order:** region, channel, name; then WiFi, last. On ESP32 turning WiFi on turns Bluetooth off; from
then on use the web client at the radio's IP, or USB. *Module → MQTT*: address from `planetai meshtastic`, JSON output
**on**, encryption **off**. *Channels → primary → uplink on, downlink on.*

## Sensors on radios

The Tracker's Grove port is **3.3 V**. A SEN54/SEN55 or any fan-driven PM sensor needs 5 V and simply does not appear.
Use BME280/BME680, SHT4x or AHT10 on Trackers. PM belongs on a mains-powered kit. The gateway can carry a sensor too
(same rules; keep its role `CLIENT`; mark it indoor).

## What went wrong, so you skip it

- Region `0` (unset) on both radios: they never saw each other for a week.
- The Tracker has a **physical power switch**. Lift it. Charge from a normal charger.
- `error -36` when a copy *works* is the drive vanishing on reboot; when it fails every time, it is FSKit. Serial DFU.
- The XIAO's serial console is off (`device.serial_enabled`), and newer firmware gates the debug log
  (`security.debug_log_api_enabled`). Turn both on to read the radio over USB:
  `stty -f /dev/cu.usbmodemXXX 115200 raw -echo; cat /dev/cu.usbmodemXXX`.
- `meshtastic --get lora.region` prints numbers: `0` unset, `18` SG_923. `device.role` `6` is SENSOR.

## Limits

A LoRa frame is about 200 bytes, a few a minute. Telemetry and one-line alerts. Hourly means between nodes go over
Tailscale (`NETWORKING.md`).
