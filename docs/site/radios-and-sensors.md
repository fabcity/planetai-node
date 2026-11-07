# Radios and sensors: the essential guide
<!-- checked: v0.91.0 -->

This page is for the person with hardware on the table: a kit from the FAB26 sensors workshop, a Bayu built at a
lab, a bag of Meshtastic radios, or a plan to put a sensor on a roof with no WiFi. It takes each one from parts to a
row in `planetai sensors` marked `yours`, which is the moment the node's rules can fire on it and its hourly means
can count toward this place's cell. It assumes a node that is already running; [The essential guide](essential-guide.md)
gets you there.

Three kinds of hardware reach a node, and the first decision is which path each piece takes.

| hardware | path | what the node gets |
|---|---|---|
| A Bayu, the Making Sense Bali DIY node: XIAO ESP32-S3, BME680, and an HM3301 on the Plus kit | WiFi, straight to the node's own broker (`planetai broker`) | temperature, humidity, pressure, gas resistance, and PM1, PM2.5, PM10 on a Plus, every 60 s, with the device's own timestamp |
| A Meshtastic radio with a sensor on its Grove port, in a field or on a roof with no WiFi | LoRa, to a gateway radio on the node's USB (`planetai radio`) | the sensor's channels every 15 min, filed under the radio that measured it, plus the radio's own battery and air time |
| A Smart Citizen kit | the public API, nothing to install (`SC_DEVICES`) | covered in [the essential guide](essential-guide.md); the one sensor the installer asks about |

A FAB26 kit (XIAO ESP32-S3 with the Wio-SX1262 LoRa module, a Grove shield, a BME680 and an HM3301) is the same
board as a Bayu with a radio on it, so it can take either path. Over WiFi it is a Bayu and both sensors are read.
Over LoRa it is a Meshtastic sensor radio, and whether the HM3301 is read that way is unsettled: `FAB26_EXPERIMENT.md`
says stock Meshtastic reads the BME680 and not the HM3301, while `MESHTASTIC.md` lists the HM3301 among what the
node files from a radio with air-quality telemetry on. Try one before you fit a batch, and tell info@fab.city which
it was. Within WiFi reach, take the WiFi path.

Two rules come before anything with a radio. Put the antenna on before power, always. And give every radio the same
region, the same frequency slot and the same channels, region first, or it never transmits and nothing tells you.

## 1. The workbench

Everything that flashes, tests and finds a board is one page on the node: **Data › Workbench** on the dashboard,
`http://<node>:8080/#data/workbench`. It needs no internet, because the node keeps its own copy of every firmware in
`out/firmware/`, refreshed every six hours while it is online and checked against each release's `SHA256SUMS`. The
full workbench, with a demo and the long explanations, is at planetai.fab.city/sensors, and the tab links to it.

Use Chrome or Edge on a laptop. Phones, Safari and Firefox open the page but have no Web Serial, so they cannot reach
a board. Chrome opens a USB port only on `localhost` or https, so:

- On the node's own machine, `http://localhost:8080/#data/workbench` works as it is.
- From another laptop on the LAN, do this once: open `chrome://flags/#unsafely-treat-insecure-origin-as-secure`,
  paste the node's address exactly as the Flash view shows it in its dashed box (`http://192.168.1.20:8080`), choose
  Enabled and press Relaunch. The flag covers that one address, so give the node a DHCP reservation on the router.
  Why a flag and not https on the node is in `docs/decisions/2026-10-27-serial-on-the-lan.md`.

Three views. **Flash** installs firmware: the Bayu card for a XIAO ESP32-S3 or an ESP32-C3 SuperMini, and a card per
Meshtastic board (the XIAO and the Heltec flash over USB; the nRF52840 Trackers take a `.uf2` by drag and drop).
**Test** opens a board over USB and shows what it reads, each sensor animated, with a checklist for sensors found,
WiFi, clock and publishing, and saves readings as CSV. **Network** draws every device the node knows: sensors that
publish to it, radios its gateway hears, the stations and platforms it reads, and the boards on this laptop's USB. A
browser cannot scan a network, so a board the node has never heard from is not on the map yet.

Plug a board in with a data cable; a charge-only cable shows no port. If a XIAO shows no port, hold BOOT while you
plug it in.

## 2. A Bayu over WiFi

The Bayu is the workshop sensor from Making Sense Bali, built at Fab Lab Bali, in two variants that run the same
firmware. Full hardware documentation, schematics, the enclosure and the use cases are in the
[makingsensebali repository](https://github.com/Meaningful-Design-Group/makingsensebali/tree/main/hardware/diy-node).

| | Basic | Plus |
|---|---|---|
| parts | Seeed XIAO ESP32-S3, GY-BME680 breakout (check the IC reads BME680, not BME280), 4×6 cm perfboard, four short jumpers, a USB-C phone charger | Basic, plus a Seeed Grove HM3301 and a 5 V / 2 A supply, because the fan and laser brown out a 1 A one |
| reads | temperature, humidity, pressure, gas resistance (a VOC indicator) and an open IAQ index | the same, plus PM1, PM2.5, PM10 |
| for | a room: mould, heat, cooking and mosquito-coil smoke, a classroom | a roof or a banjar office: burning, traffic, construction dust |
| build time | about two hours | about three |
| price band | the lowest; for the price of one Smart Citizen kit a lab builds six to ten | three to four times a Basic; the HM3301 is the cost driver, and ordering five or more direct from Seeed beats retail |

**Wire it.** Both sensors share one I²C bus. From the XIAO: `3V3` to the BME680's VCC, `5V` to the HM3301's VCC,
`GND` to both, `D4` (GPIO5) to both SDA pins, `D5` (GPIO6) to both SCL pins. The BME680 answers at `0x76`, the HM3301
at `0x40`. Leave the BME680's SDO floating and ignore its SPI pins. If only one sensor shows up, check power first,
then the pull-ups: the HM3301's Grove cable assumes someone else on the bus provides them, and the BME680 breakout
usually does.

**Test it before it has a network.** The repository's test sketch (`firmware/diy_node_test/`) scans the bus, probes
both sensors and prints readings to the serial monitor every five seconds with no WiFi and no account. Flash it first
after soldering: sensible numbers mean the hardware works. The Test view of the workbench does the same from the
browser once the production firmware is on.

**Flash it from the node.** Data › Workbench › Flash, the Bayu card, Connect and flash, pick the port, about a
minute. Reflashing keeps a sensor's saved WiFi, token and name.

**Tell it where to publish.** On the node's machine:

```bash
planetai broker
```

It starts the node's MQTT broker (the same one the radios use), prints what to type into the Bayu's setup portal,
and waits up to three minutes for the first message. Power the Bayu; on first boot it opens a captive portal. Join
it from a phone, enter the WiFi, the node's broker as printed, a name for the sensor and whether it is indoors. The
firmware publishes the Smart Citizen platform's own topics to the node instead of the cloud,
`device/sck/<token>/readings` plus a retained `meta` with the name, the site, the mounting height and `indoor`. The
node stores every reading with the device's own timestamp, which the cloud API never gives. Its id is `sck-` and
eight hex characters of the token's hash; the token itself is a credential and is never shown.

A Bayu arrives with no coordinates, so it stays `local` without a distance check: it is yours because it reached the
node through your own broker. Without a `meta` message it is outdoor and named by its id, so give it a name and say
which side of the wall it is on.

**If you also want it on smartcitizen.me.** Register the device there as "Other devices" with the sensors it
publishes, put its token in the portal, and list the token in `SC_FORWARD` on the node. The node passes every message
on unchanged through a queue that outlives an internet outage, so the device keeps its page on the platform. Then
add the device's platform id to `SC_EXCLUDE`, or the node reads it twice, once direct and once from the cloud.

**Check it.** After one poll (`POLL_SECONDS`, 300 s):

```bash
planetai sensors            # sck-3f9a1c2e   sensor   yours   outdoor   Warung roof
planetai sensors --json     # "custody": true on the same row
```

A FAB26 kit left the workshop flashed with the Bayu firmware and needs no reflash: power it within reach of the
node's WiFi and go through the portal. If you ever reflash it with stock Meshtastic, read the next part first.

## 3. Radios over LoRa

A sensor that stands where there is no WiFi reaches the node over LoRa with Meshtastic: one gateway radio on the
node's own USB carries the mesh to the node's broker, field radios carry sensors on batteries, and a shelf radio
paired to a phone receives alerts when the internet is down. A LoRa frame is about 200 bytes and a radio sends a
few a minute, enough for telemetry and one-line alerts; hourly means between nodes go over Tailscale.

**Which board does what.** The firmware is the same on every board; the job is in the settings, and
`planetai radio provision` writes them.

| board | chip | WiFi | GPS | job |
|---|---|---|---|---|
| XIAO ESP32-S3 + Wio-SX1262 (the FAB26 kit) | ESP32-S3 | yes | no | the gateway, one per node; or a sensor radio with an I²C sensor, pinned with `--fixed LAT,LON` because it has no GPS |
| Wio Tracker L1 (L1, Lite, e-ink) | nRF52840 | no | yes | a field sensor: a 3.3 V sensor on the Grove port, on a battery |
| Wio Tracker L1 Pro, SenseCAP T1000-E | nRF52840 | no | yes | a shelf radio, paired to a phone |

The Tracker's Grove port is 3.3 V. Seeed rates the Grove HM3301 for 3.3 V or 5 V, and the Grove SEN54 and SEN55
carry a regulator for 3.3 V, so a PM sensor can go on a Tracker; a SEN54 once did not appear at all and the reason
was never found, so try one before a batch. A PM sensor's fan runs whenever it measures, which a battery feels. Do
not fit an MLX90632: it sends the temperature of whatever it points at as the radio's `temp`, and nothing in the
packet says so.

**Firmware.** Every radio in a mesh on the same Meshtastic version (2.7.26 on v0.91.0), from the workbench's Flash
view: the XIAO and the Heltec over USB, the Trackers by double-clicking RST and copying the `.uf2` onto the drive
that appears. On macOS 26 that copy fails with error -36 whatever you do; use serial DFU instead
(`adafruit-nrfutil dfu serial --package firmware-seeed_wio_tracker_L1-<ver>-ota.zip -p /dev/cu.usbmodem1101 -b 115200 --singlebank`).
Never use the phone app's over-the-air update on these boards; Seeed says it can brick them. The workbench leaves
region and channel empty on purpose: those come from the node.

**Your first radios.** Everything runs on the node's machine with the radios plugged into it. `planetai radio` at
any point ticks what is done, lists the radios on USB now, and ends with the next command, port filled in.

```bash
python3 -m pip install --user meshtastic paho-mqtt        # once; planetai radio prints the exact line for your Python
planetai meshtastic                                       # the broker and its user
planetai radio init                                       # the fleet: region from NODE_CITY, the slot, two channel keys
planetai radio provision gateway-host "lab gateway" GATE --port /dev/cu.usbmodem1101
planetai radio gateway --port /dev/cu.usbmodem1101 --install     # the gateway as a service; leave this radio plugged in
planetai radio provision sensor "Subak edge" SBK --port /dev/cu.usbmodem1101            # a Tracker: it has GPS
planetai radio provision sensor "Warung roof" WRG --port … --fixed -8.80045,115.17664   # a XIAO: pin it, south as written
planetai radio provision shelf "kitchen shelf" SHF --port /dev/cu.usbmodem1101
planetai radio url                                        # the link and a QR for anyone joining by phone
planetai radio doctor --port /dev/cu.usbmodem1101
```

`init` writes `config/radio/fleet.yaml`, mode 600 and gitignored, because it holds the keys: a primary `planetai`
channel for the household's telemetry and full position, and a secondary `fabcity` channel that crosses to other
nodes with position capped at about 2.9 km. Regions: Bali `SG_923` with the slot pinned inside Indonesia's 920 to
923 MHz (slot 19, 921.625 MHz), Barcelona and Menorca `EU_868`, Boston `US`, Santiago `ANZ`. A city with no known
region stops and asks for `--region`; it never guesses, because a radio on another country's band is illegal there.

`provision` writes one settings section at a time, 25 s apart, reboots the radio and reads everything back over a new
connection, about seven minutes. It ends `>> ok. !abcd1234 booted on it … channels planetai 0xfe and fabcity 0xe7`
(your hashes differ); anything else is a list of what the radio holds that it should not, and the answer is to run
it again. Name a sensor for the place where it stands, because that name becomes its name in the node. Provision
each radio, unplug it, and take it where it goes.

Indoor radios go in `MESH_INDOOR_NODES=!id,!id`, because a radio does not know which side of a wall it is on. A
relay (`relay`) is for a roof or a mast. A sensor's first reading arrives within its 15-minute interval, and the
Network view draws every radio the node hears.

**What the node files from a radio.** Every reading is filed under the radio that measured it; the gateway only
passes it on.

| on the radio | metrics |
|---|---|
| the radio itself | `battery_v`, `battery_pct`, `lora_util_pct`, `lora_channel_pct` |
| BME280, BME680, SHT4x, AHT10 | `temp`, `humidity`, `pressure`, a BME680's `gas_resistance` in kΩ |
| SEN5x | `pm1`, `pm25`, `pm4`, `pm10`, `tvoc_index`, `nox_index` |
| Plantower, HM3301 | `pm1`, `pm25`, `pm10` |
| SCD4x | `co2` |
| SFA30 | `hcho` |
| others | `light`, `uv_lux`, `wind_speed`, `wind_direction`, `rainfall_1h`, `soil_moisture`, `soil_temp`, `distance` (a water level), `weight`, `radiation` |

A radio's own temperature, humidity and pressure are its box, not the street: the node files them as `enclosure`
and never averages them as ambient. The sensor profile turns on environment and air-quality telemetry; a radio
provisioned by hand without air quality sends nothing from a PM, CO₂ or formaldehyde sensor.

**Two nodes talking.** `RADIO_PEERS=menorca=<tailnet host>:1883:<their MQTT_PASS>` in `.env`, then
`planetai radio federate --write`, bridges this node's broker to theirs over the tailnet. Text and alerts on the
`fabcity` channel cross, at most six lines a minute; readings and positions never do. A line typed on a Bali shelf
radio shows up on Menorca's radios as `[bayu-ungasan] …`. No public broker, no shared keys between nodes.

## 4. Siting, naming, and what counts

**Where.** Three to six metres up, away from a kitchen exhaust, a chimney or a parking spot, in outdoor air
sheltered from horizontal rain, within reach of 2.4 GHz WiFi for a Bayu. Print the enclosure in PETG, not PLA, which
softens on a Bali rooftop; the five-part snap-fit case for the Bayu is `hardware/diy-node/enclosure/node-v3.2` in the
makingsensebali repository and fits the FAB26 assembly, and Fab Lab Bali prints the outdoor sensor enclosure.

**What it is called.** Name it after the place. The name becomes the sensor's name on the page and in every
message, and the household's own word for the room comes from Set up › Rooms. A screen without the token reads
"Room A" and "Sensor 1" instead, and no room name ever reaches the Wall.

**Whether it is yours.** `local` is two facts at once: the adapter says the sensor is yours, and the node checks it
is here, within `LOCAL_RADIUS_M` (500 m). A Bayu or a radio with no coordinates stays local because it came through
your own broker or gateway. A kit on your account 1.2 km away is `reference`.

**Whether it counts.** `custody` is a generated column, `kind = 'child' OR (local AND kind <> 'peer')`, and no
adapter writes it. A cell says `live` only from sensors in custody, and only once the node holds 12 hourly buckets
from them in the last 24 hours. A model, a public station, a peer's sensor and a fab lab can never make a cell say
`live`.

**Indoors or out.** Every air rule depends on it. A Bayu says so in its `meta`; a radio is listed in
`MESH_INDOOR_NODES`; AirGradient and PurpleAir units take `SENSOR_INDOOR=1`. Indoor sensors measure a room and are
never in an ambient average.

**The rules the node inherits**, several from Bali Air Dispatch's methodology: silence is a value that stops
changing, not a timestamp, which is what the core rule `trust/channel_dead` reads; a daily mean can be one reading,
so check `n`; instants are UTC and days are local, or Bali's 9 am burning peak vanishes on a UTC day; corrected and
raw are both stored and raw is never overwritten; gaps are real, with no fill and no interpolation; these are not
reference instruments, and the node labels them that way; sensors in the same place disagree, and three kits at
one address once read the same air with one running 1.5 times the other two. Collocation is the cheapest
calibration a node can run, and `trust/peer_disagreement` reads it.

The EPA 2021 humidity correction applies to Plantower lasers (PurpleAir, AirGradient, a DIY PMS5003) and not to the
HM3301 in a Bayu or a Smart Citizen kit, because it was not derived for that sensor. Thresholds written for Kuta
Selatan are not thresholds for Barcelona, and a pack's README says which place it was written for.

## 5. When nothing arrives

`planetai radio doctor --port …` first for a radio, `planetai logs mosquitto` for the broker, `planetai doctor` for
everything else. Everything below has happened on a real node.

| what you see | what to do |
|---|---|
| `planetai radio` lists no port | a charge-only cable, a Tracker with its power switch off (lift it, charge from a normal charger), a XIAO that needs BOOT held while you plug it in, or a USB hub in between |
| the Flash and USB buttons are grey on a laptop | Chrome needs the flag for the node's address (part 1), or the page is open on a phone or in Safari |
| a radio transmits nothing | region `0` (unset). `meshtastic --get lora.region` prints `0`; `18` is SG_923. Provision it again, region first |
| two radios do not hear each other | different firmware versions, different regions or slots, antennas off, or distance. Prove two radios a few metres apart on the default channel before anything else |
| a sensor radio sends temperature and no PM | air-quality telemetry is off; provision it again with the `sensor` role |
| a Bayu publishes and `planetai sensors` shows nothing | the broker refuses anonymous clients; type exactly what `planetai broker` printed into the portal. `planetai logs mosquitto` shows the refusal |
| a Bayu is read twice | it is on `SC_FORWARD` and on the cloud; add its platform id to `SC_EXCLUDE` |
| a sensor shows `outdoor` for a room | a Bayu's `meta` or the radio's `MESH_INDOOR_NODES`; a Smart Citizen kit's `exposure` on the platform |
| `error -36` copying a `.uf2` on a Mac | the drive vanished on reboot; if it fails every time it is macOS 26, use serial DFU |
| the gateway service stopped | the radio was unplugged; the service restarts it when the radio is back on the same port. The log is `out/radio.log` on a Mac |
| a channel that reads the same number for days | not silence by timestamp but by value: `trust/channel_dead` says so; the channel is dying |

To read a XIAO over USB, turn on its serial console (`device.serial_enabled`) and the debug log
(`security.debug_log_api_enabled`), then `stty -f /dev/cu.usbmodemXXX 115200 raw -echo; cat /dev/cu.usbmodemXXX`.

## Where this leads

With a sensor of yours reporting, the [air-quality pack](packs-reference.md#air-quality) has a room to fire on,
`insight/agreement` can say each day how far the house follows the street, and `Environmental|Community` turns
`live` after twelve hours. Everything in [the essential guide](essential-guide.md) from part 3 on now has your
own readings under it. A sensor the node does not read yet is an adapter in a wild pack, `packs.md#code-packs-adapters`,
and a source filed in `awesome-fabcity-data`. The FAB26 experiment runs until January 2027; what you report to
@planetai_exp_bot decides what gets fixed first.
