# Meshtastic, screen by screen

Getting two radios talking, then making each one do its job, using only the Meshtastic phone app and
https://flasher.meshtastic.org. Written for someone who tried once and got nowhere, which is normal: the two
things that stop most first attempts are a power switch and a six-digit code, and neither is on the screen in front
of you. `MESHTASTIC.md` explains *why* each radio does what it does; this page is only *what to press*.

You need: the Meshtastic app (Android or iOS), Chrome or Edge on a computer (Firefox and Safari cannot flash), a
USB-C **data** cable (many are charge-only and the flasher will not see the board), and the radios with antennas on.

---

## Part A — get one radio alive

### A1. Power. Two things before you think anything is broken.

- **Antenna on.** Screw the antenna on before the first power-up, every time. Transmitting without one can kill the radio.
- **Wio Tracker L1 (all variants):** there is a **physical power switch** on the board. Lift it upward. A Tracker that shows nothing and pairs with nothing is almost always switched off, or flat. If it does not respond, charge it first over USB-C, from a normal charger, not a fast charger.
- **XIAO ESP32-S3:** no switch; it is on when plugged in.

### A2. Flash (only if it is not already running Meshtastic, or to update)

The Trackers and the XIAO kits ship pre-flashed. Skip this unless the app cannot find the radio at all, or you want
every radio on the same firmware version, which you do.

**Wio Tracker L1 / L1 Lite / L1 Pro (nRF52):**
1. Plug in by USB-C, switch on. Open https://flasher.meshtastic.org in Chrome.
2. *Select target device* → **Seeed Wio Tracker L1**. (L1 E-Ink has its own entry.) Pick the latest stable firmware.
3. Click **Flash**, then **Enter DFU Mode**. A serial port called *Tracker L1* appears; connect it. A USB drive called **TRACKER L1** mounts on your computer.
   If it does not: double-click the **RST** button on the board. The drive appears within 15 seconds.
4. **Drag the `.uf2` file onto the TRACKER L1 drive.** The drive vanishes, the board reboots. That is the flash.

**XIAO ESP32-S3 + Wio-SX1262 (the gateway):**
1. Plug in by USB-C. Open the flasher in Chrome.
2. *Select target device* → **Seeed Xiao ESP32-S3**. Latest stable.
3. First time: tick **Erase device** (a clean install). Click **Flash**, choose the serial port.
   If no port appears: unplug, **hold the BOOT button while plugging back in**, release, try again.
4. Wait for the progress bar to finish and the board to reboot. Do not unplug midway.

**"Error code -36" or "Input/output error" when copying the `.uf2` (macOS).** Two very different causes, same message.
Usually the copy *succeeded*: the bootloader flashed the file and rebooted, which unmounted the drive mid-copy, and
Finder is complaining about a disk that vanished on purpose. Check: drive gone, board rebooted, app finds it. Done.
If instead the board stays dead and the error repeats every time, it is macOS Sonoma-or-later writing to a drive whose
bootloader predates the fix. Update the bootloader once: Seeed's L1 page, *FAQ → Device bricked & Bootloader
installation*, download the bootloader file; double-click RST, copy the bootloader onto the `TRACKER L1` drive (it is
small and copies fine); double-click RST again and copy the firmware. Never use the Nordic OTA app on these boards —
Seeed warns it can brick them. Last resort: flash from a Windows or Linux machine, where the drag just works.

Flash all radios you own to the **same version** while you are at it. Mixed versions across a mesh is the third most
common reason two radios never see each other.

### A3. Connect the app

1. Open the app. Bottom bar → the connection screen (a Bluetooth / radio icon, or *Settings → Connect*).
2. Choose **Bluetooth**, tap **+** or *Scan*. The radio appears as `Meshtastic_xxxx`. Tap it.
3. **It asks for a PIN.**
   - Radio **with a screen** (L1, L1 Pro, L1 e-ink): read the six digits off the screen, type them.
   - Radio **without a screen** (L1 Lite, XIAO): type **`123456`**. That is Seeed's default. If it is refused, plug the radio into the computer, open the flasher, *Connect* → *Serial Monitor*, try pairing again, and read the code that scrolls past in the log.
4. Status turns to *Connected*. The app pulls the radio's config, which takes a few seconds.

### A4. Region: nothing works until this is set

The app may prompt for it on first connect. If it does not, or you dismissed it:

*Settings → Radio configuration → LoRa → Region* → pick yours → *Send*.

    Bali        SG_923    (the AS923 band Indonesia allocates; there is no "Indonesia" entry)
    Barcelona   EU_868
    Boston      US
    Santiago    check local allocation; commonly AU_915 / LORA_24 are not right — ask before choosing

The radio reboots. **Every radio on your mesh gets the same region.** An unset region means the radio never
transmits; a different region means the two radios are on different frequencies and will never hear each other.
This, not a channel problem, is what stops most "two nodes" attempts.

### A5. Name it

*Radio configuration → User → Long name* and *Short name*. Long name is what the node and the app show; make it the
**place** for a sensor (`Subak edge`), the **job** for infrastructure (`bayu-2 gateway`). Short name is four
characters (`SBK`, `GW`). *Send*.

Repeat A1–A5 on the second radio. Same region. You now have two radios alive.

---

## Part B — two radios see each other

1. Both radios on, region identical, **a few metres apart** (LoRa radios sitting on top of each other can fail to decode each other; two rooms apart is fine).
2. In the app, connected to radio 1, open the **Nodes** (or *Contacts*) tab. Within about a minute radio 2 appears in the list with a signal strength. If it does, you have a mesh.
3. Open **Messages**, pick the channel (the default is `LongFast`), type *hello*, send. Connect the app to radio 2 (or use a second phone) and see it arrive.

If radio 2 never appears:
- Region on both? (*LoRa → Region* on each). This is it nine times out of ten.
- Same firmware version on both? (Shown on the connect screen.)
- Antennas on? Radios a few metres apart, not touching?
- Both on the default `LongFast` channel, untouched? (Do not create private channels until this test passes.)
- Tracker switched on and charged?

**Only once two radios see each other on the default channel, continue.** Everything below assumes a working mesh.

---

## Part C — one private channel, on every radio

The default `LongFast` is public: anyone nearby running Meshtastic shares it. Your sensors want their own.

1. On radio 1: *Radio configuration → Channels* → tap the **+** (or *Add channel*). Name: your node's name, e.g. `bayu-2`. Tap the key/PSK field → *Generate 256-bit*. Role: *Secondary*. *Send*.
2. Tap the channel → **Share / QR code**. On the phone connected to radio 2, *Channels → Scan QR* (or paste the URL). *Send*. Repeat for every radio.
3. Keep `LongFast` as the primary. Your channel is secondary; the gateway will uplink it specifically.

---

## Part D — each radio, by job

### D1. The gateway (XIAO ESP32-S3)

Do these **in this order**, because after step 3 the phone can no longer talk to it.

1. Region, name (`bayu-2 gateway` / `GW`), private channel joined (A4, A5, C).
2. *Radio configuration → Device → Role*: `CLIENT` (the default). Leave it.
3. *Radio configuration → Network → WiFi*: **enabled**, SSID and password of the WiFi the node's computer is on. *Send*. The radio reboots.
   **From here Bluetooth is off.** On ESP32 boards Meshtastic runs WiFi or Bluetooth, never both. The phone app will lose it; that is expected.
4. Find its IP: your router's device list, or the flasher's *Serial Monitor* over USB. Open **`http://<that IP>`** in a browser on the same WiFi. This is the web client — the same settings as the app, on a computer.
5. On the node: run **`planetai meshtastic`**. It creates the broker login and prints a block of settings. In the web client, *Config → Module → MQTT*, copy them in:

        Enabled               on
        Address               <node computer's IP>:1883
        Username              planetai
        Password              <as printed>
        Encryption enabled    OFF   ← the broker is yours; encrypting hides the readings from your own node
        JSON output enabled   ON    ← without this the node reads nothing
        Root topic            msh
        TLS enabled           off

   *Save*.
6. Still in the web client: *Config → Radio → Channels* → your private channel → **Uplink enabled ON**, **Downlink enabled ON**. *Save*. (Uplink: mesh → node. Downlink: node → mesh, for alerts.)
7. Back on the node, `planetai meshtastic` is waiting for the first packet. Within a couple of minutes it lists what arrived.

Its node number, for alerts out to the mesh: the web client shows it as `!a1b2c3d4`. In a terminal,
`printf '%d\n' 0xa1b2c3d4` gives the decimal. `.env`: `MESH_GATEWAY_NODE_NUM=<that>`, `MESH_ALERTS=1`, then `planetai restart`.

### D2. A field sensor (Wio Tracker L1 / L1 Lite / L1 e-ink)

Plug the Grove sensor into the Grove port **before** switching on; Meshtastic detects I²C sensors at boot.
Seeed's *verified* list for the L1's Grove port is BME280, SHT31/SHTC3/SHT4x, AHT10, BMP085, MCP9808, PCT2075. The
**BME680 is not on it**, although Meshtastic's telemetry module supports the chip in general, so test one before
relying on a batch. A BME280 is the safe choice for temperature, humidity and pressure. Then, over Bluetooth:

1. Region, private channel joined (A4, C). Long name = the place: `Temple spring`. Short name three or four letters.
2. *Radio configuration → Device → Role*: **`SENSOR`**. Broadcasts readings and position, sleeps between, does not relay other people's traffic. *Send*.
3. *Radio configuration → Position*: *GPS enabled* on; *Position broadcast interval* 1800 s (30 min). *Send*. The Tracker has GPS; the node learns where the sensor is from this.
4. *Module configuration → Telemetry*: **Environment measurement enabled** on; *Environment update interval* 900 s (15 min). If a PM sensor is attached, **Air quality enabled** on, same interval. *Send*.
   To check the sensor is detected: the app's node page for this radio shows *Environment* values after the first interval, or the L1's screen cycles to a temperature page.
5. *Radio configuration → Power*: leave defaults. `SENSOR` already sleeps.
6. Unplug USB. Battery on the JST connector, solar (if any) on the two-pin input. Antenna vertical, sensor in a shield, 3–6 m up.

If the sensor is indoors, tell the node: `.env` → `MESH_INDOOR_NODES=!<its id>` (the id from its node page), `planetai restart`.

### D3. The shelf radio or handheld (Wio Tracker L1 Pro, or T1000-E)

1. Region, private channel joined (A4, C). Long name: whose it is or where it lives: `Wayan`, `kitchen shelf`.
2. Role **`CLIENT`**. Position on if it moves with a person, off if it sits on a shelf.
3. Nothing else. Leave the app on the phone it is paired to. When the node sends an alert over the mesh, it appears in the app's Messages on your private channel — with or without internet.

---

## Part E — when it does not work

| symptom | first thing to check |
|---|---|
| App cannot find the radio | Tracker: power switch up, charged. XIAO with WiFi on: Bluetooth is off by design, use the web client. |
| App asks for a PIN and there is no screen | `123456`. Failing that, read it from the flasher's Serial Monitor. |
| Radio connected, other radios never appear | Region set on *both*, identical. Then firmware version, antennas, distance. |
| Radios see each other, no readings reach the node | Gateway: JSON output on; MQTT address is the node computer's IP on the *same* WiFi; channel uplink on. `planetai logs mosquitto` shows connections; `planetai logs` shows packets. |
| Readings arrive, no sensor values | Grove sensor plugged in before power-on; Telemetry → Environment enabled; wait one interval. The app's node page shows what the radio itself sees. |
| Alerts do not go out on the mesh | Downlink enabled on the channel; `MESH_GATEWAY_NODE_NUM` set (decimal); `MESH_ALERTS=1`; `planetai restart`. |
| Flasher shows no serial port | Chrome or Edge only. A data cable, not a charge cable. XIAO: hold BOOT while plugging in. Tracker: double-click RST for the UF2 drive. |
| Everything worked, then a radio went silent | Battery. Then the power switch got knocked. Then someone moved the antenna. |

The node side reports plainly: `planetai meshtastic` waits for the first packet and names what it saw,
`planetai sensors` lists every `msh-…` unit, `planetai logs` names any telemetry field it did not recognise.
