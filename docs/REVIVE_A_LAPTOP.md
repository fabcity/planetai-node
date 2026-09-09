# Turn an old laptop into a node

> **Not yet rehearsed.** Every command here is written from the vendors' own documentation and from what
> `planetai preflight` already knows about the machine, but nobody has walked this end to end on real
> hardware. Until somebody has, treat it as a plan and not a recipe, and tell **info@fab.city** where it
> was wrong. The rest of this repository's instructions were rehearsed before they were published; this
> page is marked because it was not.

A node's home is a box that stays on. A laptop is designed to go to sleep, which makes it a poor node
under macOS or Windows and a good one under Linux, where you can simply tell it not to.

This is the route for a Mac that no container runtime supports any more — and for any x86_64 laptop from
about 2015 onwards. It is not a downgrade. A 2015 quad-core with 16 GB outruns the mini PC you would
otherwise buy (see `PLATFORMS.md`), and once Linux is on the metal the floor stops moving underneath you.

**What it costs you:** a USB stick of 4 GB or more, an hour, and everything currently on that laptop.

---

## 0. Before you wipe anything

The disk gets erased. Copy what you want off it first — this is the step people skip.

Check the machine is worth it:

```bash
curl -fsSL planetai.fab.city/preflight | bash
```

If it prints *"This hardware is a capable node"*, the hardware is fine and only the OS is in the way,
which is exactly what this page fixes.

## 1. Choose which Linux, then make the USB stick

One question decides it: **is anybody still going to use this machine?**

**No — it sits on a shelf and runs.** Ubuntu Server. No desktop, ssh in, the lowest upkeep of anything
here, and a support window measured in years.

```bash
curl -fL -o ~/Downloads/ubuntu-server.iso https://releases.ubuntu.com/24.04/ubuntu-24.04.4-live-server-amd64.iso
```

**Yes — somebody uses it, and it is also a node.** [Omarchy](https://omarchy.org): Arch underneath,
a finished desktop on top, five questions from stick to working machine. Its own page says a 2011
ThinkPad X220 with 2 GB runs it. Everything below applies, except that you get a desktop at the end and
the installer takes Arch's `pacman` branch instead of `apt`.

```bash
curl -fL -o ~/Downloads/omarchy.iso https://iso.omarchy.org/omarchy-4.0.3.iso
curl -fL -o ~/Downloads/omarchy.iso.sha256 https://iso.omarchy.org/omarchy-4.0.3.iso.sha256
shasum -a 256 -c ~/Downloads/omarchy.iso.sha256      # must say: OK
```

The rest of this page is written for Ubuntu Server, because that is the one a node usually wants. Where
Omarchy differs, it says so.

Write it to the stick with [balenaEtcher](https://etcher.balena.io) — it is the same on macOS, Windows and
Linux, it refuses to write to your system disk by accident, and it verifies afterwards. Open it, pick the
`.iso`, pick the stick, click Flash.

*If you would rather not install anything: on macOS, `diskutil list` to find the stick, then*
*`sudo dd if=~/Downloads/ubuntu-server.iso of=/dev/rdiskN bs=1m` — where N is the stick and getting it*
*wrong erases the wrong disk. Etcher exists because of that sentence.*

## 2. Boot from it

| Machine | Key, held from the moment you press power |
|---|---|
| Mac (Intel) | **⌥ Option**, then choose the orange "EFI Boot" |
| Dell, Lenovo | **F12** |
| HP | **F9** |
| Most others | **F12**, else **Esc** or **F2** into the firmware and set the boot order |

If the machine boots into its old system instead, you held the key too late. Power off fully, hold the
key, then press power.

## 3. Plug in an ethernet cable for the install

Wi-Fi during a server install is the single most common way this goes wrong, and on Macs it is worse than
usual — see the next section. A cable for twenty minutes saves an hour. If the laptop has no ethernet
port, a USB gigabit adapter is about the cheapest useful thing you can own.

## 4. Install it

**Omarchy:** answer its five questions and skip to step 6 — it hands back a finished desktop, and it
brings its own Wi-Fi handling. Then come back for the lid and the install line.

**Ubuntu Server:**

Take every default except these:

- **Erase disk** — the whole disk, not "install alongside". You are not keeping the old system.
- **Your name / server name / username** — the server name becomes the node's hostname; something like
  `node-kitchen` is easier to live with than `ubuntu`.
- **Install OpenSSH server** — tick it. This is how you reach the machine once the lid is shut. Skipping
  it means carrying a monitor to it later.
- Skip every "featured server snap".

It reboots. Pull the stick out when it asks.

## 5. The Wi-Fi chip, if you need Wi-Fi

Apple laptops of this era use Broadcom cards, and which one decides how much work this is. On the
installed machine:

```bash
lspci -nn | grep -i network
```

- **BCM43602** — works with the in-kernel driver. Nothing to do.
- **BCM4360** — needs Broadcom's proprietary driver, and it is not on the install media. With the
  ethernet cable still plugged in:
  ```bash
  sudo apt update && sudo apt install -y bcmwl-kernel-source
  sudo modprobe wl
  ```
  This is why step 3 says to use a cable: without one you cannot download the driver that gives you
  Wi-Fi. Wired is better for a node anyway.

## 6. Tell it not to sleep when the lid closes

The one thing that separates a laptop-shaped node from a laptop:

```bash
sudo sed -i 's/^#\?HandleLidSwitch=.*/HandleLidSwitch=ignore/' /etc/systemd/logind.conf
sudo sed -i 's/^#\?HandleLidSwitchExternalPower=.*/HandleLidSwitchExternalPower=ignore/' /etc/systemd/logind.conf
sudo systemctl restart systemd-logind
```

Close the lid. `ssh` in from another machine. If you get a prompt, it is done.

## 7. Install the node

Same line on either, and on Omarchy the installer uses `pacman` instead of `apt` without being told.

The same line as everywhere else, now on a machine that can run it:

```bash
curl -fsSL planetai.fab.city/install | bash
```

Preflight runs first, the installer adds Docker itself on Linux, and it asks four questions.

---

## Two things worth knowing

**A headless node does not care about the graphics card.** The MacBook Pro (Retina, 15-inch, Mid 2015)
has two GPUs — a Radeon R9 M370X and Intel Iris Pro, switched by Apple's gmux — and that pair is a
known source of trouble for a Linux *desktop* install. A node has no desktop: nothing renders, nothing
switches, and the problem does not arise. If you install a desktop environment on one of these, it can.

**The battery.** A laptop that has sat plugged in for years may have a swollen or dead battery. It will
still run as a node on mains power, but check it before you put it somewhere you cannot see it:

```bash
cat /sys/class/power_supply/BAT0/health /sys/class/power_supply/BAT0/cycle_count
```

## When you are done

`planetai status` on the machine, or from your laptop over SSH. The node is now a box that stays on,
which is what it always wanted to be.
