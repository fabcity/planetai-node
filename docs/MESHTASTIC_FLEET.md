# Provisioning a fleet of radios from a laptop

The phone app is fine for one radio. For eight, or the thirty-five going out with the FAB26 program, use a USB cable
and the command line: no Bluetooth pairing, no PIN, one command per radio, and every radio ends up on the same
firmware, the same region and the same encrypted channel. This page is the procedure, then the field notes from the
first radios: what actually went wrong and why, so nobody repeats it.

## 1. The laptop, once

```bash
pip3 install --user meshtastic adafruit-nrfutil
export PATH="$HOME/.local/bin:$PATH"          # add to ~/.zshrc so it sticks
```

`meshtastic` configures a running radio over USB. `adafruit-nrfutil` flashes nRF52 boards over the bootloader's
serial port, which is the method that works on current macOS (see the field notes).

**Firmware.** Use the current **stable** release, not what the web flasher happens to offer first (it offered a 2.8.1
alpha that is not a GitHub release at all). Check and fetch:

```bash
gh release list -R meshtastic/firmware --limit 5            # the one marked "Latest" is stable
gh release download v2.7.26.54e0d8d -R meshtastic/firmware -p 'firmware-nrf52840-*.zip'
unzip -q firmware-nrf52840-2.7.26.54e0d8d.zip -d ~/Downloads/mesh-2.7.26
```

Each board has three files inside. For the Tracker L1 / L1 Lite / L1 Pro: `firmware-seeed_wio_tracker_L1-<ver>.uf2`
(drag-to-drive), `…-ota.zip` (serial DFU, and phone OTA), `…mt.json`. The e-ink variant has its own set. A fleet
should run one version; mixed versions is a common reason radios do not see each other.

## 2. Each radio: plug, flash, provision, label

One radio at a time. Its port is whatever `ls /dev/cu.usbmodem*` shows, and it can change between radios.

**Flash** (skip if it already runs the version you want: `meshtastic --port <port> --info | grep firmwareVersion`):

```bash
# double-click RST: yellow LED solid, a TRACKER L1 drive appears. Ignore the drive; use the serial port.
adafruit-nrfutil dfu serial --package ~/Downloads/mesh-2.7.26/firmware-seeed_wio_tracker_L1-2.7.26.54e0d8d-ota.zip \
  -p /dev/cu.usbmodem1101 -b 115200 --singlebank
```

A progress bar, a minute or two, the board reboots into Meshtastic. Do not unplug during it.

**Provision** with `tools/mesh-provision.sh`:

```bash
tools/mesh-provision.sh <port> "<long name>" <SHORT> <SENSOR|CLIENT> <REGION> <channel file>

tools/mesh-provision.sh /dev/cu.usbmodem1101 "Subak edge"    SBK SENSOR SG_923 ~/planetai-mesh.url
tools/mesh-provision.sh /dev/cu.usbmodem1101 "kitchen shelf"  SHF CLIENT SG_923 ~/planetai-mesh.url
```

It sets region and the `LONG_FAST` preset, long and short name, role, and for `SENSOR` environment telemetry every
15 minutes and position every 30 with GPS on. The **first** radio you run it on turns its **primary** channel into a
private channel named `planetai` with a random key and saves the channel URL to the file; every later radio imports it
with `--seturl`, which replaces all its channels. Primary, not secondary: see the field notes. The script ends by
printing what it set, so you read the result before unplugging.

**Label the radio** with its long name. Eight identical boards on a bench are indistinguishable, and the label is the
name that appears in the node and in the app.

**Rename** if a radio moves: `meshtastic --port <port> --set-owner "Temple spring" --set-owner-short TMP`.

## 3. Naming and roles

| radio | long name | role |
|---|---|---|
| field sensor | the **place**: `Subak edge`, `Temple spring`, `School roof` | `SENSOR` |
| shelf radio paired to a household phone | whose or where: `Wayan`, `kitchen shelf` | `CLIENT` |
| the gateway (ESP32) | `<node> gateway`, e.g. `bayu-2 gateway` | `CLIENT` |
| a mains-powered relay on a roof, only for a coverage gap | `Relay <place>` | `ROUTER` |

The long name becomes `sensors.name` in the node, so a place name makes an alert read *Indoor PM2.5 at Temple spring*
rather than *at Meshtastic b768*. Short name: two to four characters, for screens and the app's node list.

## 4. The channel file is a key

`~/planetai-mesh.url` holds the channel's pre-shared key inside the URL. Anyone with the file can read the mesh. Keep
it with the node's `.env`; never in a repo or a chat. Bring a radio into the fleet by handing it the file, or the QR
from `meshtastic --port <port> --qr-all`. To rotate: on one radio `--ch-add` a new channel and `--ch-set psk random`,
save the new URL, re-run the script on every radio.

The gateway joins the same channel this way, and in its web client that channel needs *Uplink enabled* and *Downlink
enabled* (`MESHTASTIC_APP.md` D1). The channel name appears in the MQTT topic the node reads:
`msh/SG_923/2/json/planetai/!<gateway>`.

## 5. Reading what the CLI prints

`--get` returns enum numbers. The ones that matter:

| setting | value | meaning |
|---|---|---|
| `lora.region` | `0` | **UNSET: the radio never transmits.** The silent failure. |
| | `18` | `SG_923`, the AS923 band (Bali) |
| | `3` · `1` | `EU_868` · `US` |
| `device.role` | `0` · `6` · `2` | `CLIENT` · `SENSOR` · `ROUTER` |
| `lora.modem_preset` | `0` | `LONG_FAST` |

`meshtastic --port <port> --info` shows `firmwareVersion`, `hwModel`, `role`, and the radio's default name `Meshtastic xxxx`.

## 6. Field notes from the first radios, 4 September 2026

In the order they were found. Each cost time; none is in the official guides.

**Two radios never saw each other (the week before).** `lora.region` was `0`. A radio with region unset does not transmit,
and nothing in the app says so. Check region on both radios before touching channels.

**Copying the `.uf2` onto the `TRACKER L1` drive fails on this Mac, every time.** Finder: *error code -36*. `cp`:
*fcopyfile failed: Input/output error*. `dd` in 512-byte blocks: stalls after 356,864 bytes. The drive's `INFO_UF2.TXT`
reported bootloader **0.9.2**, newer than the version Adafruit's "macOS copy fix" landed in, so this is *not* the
old-bootloader case Seeed's FAQ describes. The mount showed `fskit`: macOS 26 mounts FAT volumes through FSKit, Apple's
new user-space filesystem layer, and the UF2 bootloader stops accepting its writes part way. **Serial DFU works**; it
never touches the drive. On macOS before Sequoia, or on Linux or Windows, the drag works as documented.

**"Error -36" can also mean success.** When a copy does work, the bootloader reboots the board and unmounts the drive
mid-copy, and Finder reports the vanished disk as an error. Same message, opposite meaning. Tell them apart: after
success the drive is gone and the board boots; after the FSKit failure the drive is still there with a partial
`firmware.uf2` on it and nothing rebooted.

**The web flasher offered a build that is not a release.** `2.8.1.d5873ea` is not under GitHub releases; stable is
`2.7.26.54e0d8d`, the 2.8.0 builds are alphas, one revoked. Take firmware from the releases page.

**Seeed warns against phone OTA on these boards** ("may cause the device to be completely dead"). Serial DFU over the
cable is a different mechanism and is fine.

**Seeed's verified Grove sensors for the L1** are BME280, SHT31/SHTC3/SHT4x, AHT10, BMP085, MCP9808, PCT2075. The
BME680 is not on the list, though Meshtastic's telemetry module supports the chip. Test one before trusting a batch.

**The Tracker has a physical power switch.** Lift it. A Tracker showing nothing is usually off or flat; charge from a
normal charger, not a fast one.

**Screenless boards pair with PIN `123456`** (L1 Lite, XIAO). The app asks and shows nothing.

**Telemetry travels on the primary channel.** The first fleet channel was created as a *secondary* (`--ch-add`), with
uplink enabled on it, and the gateway sat connected to the broker for a day publishing nothing. Radios send telemetry,
position and node info on channel 0, the primary, where uplink was off. Proven by forcing a text on channel 0, which hit
the broker within a second. Fix: the fleet channel *is* the primary. `mesh-provision.sh` now renames channel 0 rather
than adding a channel; on radios already provisioned the old way, `--seturl` with the new fleet URL replaces the set.

**The XIAO's serial console is off by default** (`device.serial_enabled: false`), and newer firmware also gates the debug
log behind `security.debug_log_api_enabled`. With both on, the radio's own log streams over USB and answers questions
the app cannot: `stty -f /dev/cu.usbmodemXXXX 115200 raw -echo; cat /dev/cu.usbmodemXXXX`.

**Mosquitto was crash-looping for a day** because its config file was never committed and Docker mounted an empty
directory in its place. `make lint` now refuses a compose bind mount the repo does not ship.

## 7. The test that closes it

Two provisioned radios, on, a few metres apart. Connect the app to one; the other appears under Nodes within a minute.
Send *hello* on the `planetai` channel; it arrives on the other. Then, and only then, the gateway (`MESHTASTIC_APP.md`
D1) with `planetai meshtastic` on the node waiting for the first packet.
