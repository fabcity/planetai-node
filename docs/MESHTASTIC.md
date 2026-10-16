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

## Settings: `planetai radio`

```bash
python3 -m pip install --user meshtastic paho-mqtt       # on the machine the radios plug into; `planetai radio` prints
                                                         # the exact line for its python3 (Apple's 3.9 needs pyobjc<12)
planetai meshtastic                                      # the broker and its user, as before
planetai radio init                                      # the fleet: region from NODE_CITY, slot, two channel keys
planetai radio provision gateway-host "bayu radio" NODE --port /dev/cu.usbmodem1101
planetai radio gateway --port /dev/cu.usbmodem1101 --install
planetai radio provision sensor "Subak edge" SBK --port /dev/cu.usbmodem1101             # a Tracker: it has GPS
planetai radio provision sensor "Warung roof" WRG --port … --fixed -8.80045,115.17664    # a XIAO sensor node: pin it
planetai radio provision shelf "kitchen shelf" SHF --port /dev/cu.usbmodem1101
planetai radio url                                       # the QR, for anyone joining by phone
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

## The phone app

If you would rather tap. Bluetooth first, then the radio appears as `Meshtastic_xxxx`.

**PIN.** Radios with a screen show it. Radios without (L1 Lite, XIAO) use `123456`.

**The quick way by phone:** scan the QR from `planetai radio url` and accept replacing the channels. Region, slot and keys arrive together. The steps below are for a radio with no node in reach.

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
