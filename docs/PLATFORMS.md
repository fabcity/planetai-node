# Not on an Apple Silicon Mac?

`START_HERE.md` is written against one real machine. The node itself doesn't care: it's two Docker containers, and
the installer detects the platform. This page is the list of *differences* — read the section for your machine, then
follow START_HERE with those substitutions.

| platform | works? | Docker comes from | auto-start after reboot | notes |
|---|---|---|---|---|
| **Mac, Apple Silicon** | yes (reference) | OrbStack or Docker Desktop | needs auto-login (see MAC_MINI.md) | fastest, quietest |
| **Mac, Intel** | yes | OrbStack or Docker Desktop | same | slower builds, otherwise identical |
| **Linux desktop/server** (Ubuntu, Debian, Fedora, Arch) | yes | installer installs Docker Engine | **yes, without login** — systemd starts Docker at boot | the best always-on target |
| **Raspberry Pi 4/5**, 64-bit OS | yes | installer installs Docker Engine | yes, without login | 2 GB RAM is enough; use a good SD card or USB SSD |
| **Windows 10/11** | yes, via WSL2 | Docker Desktop (Windows) with WSL integration | needs Docker Desktop set to start at login | run everything from the Ubuntu (WSL) terminal |
| Raspberry Pi Zero / 32-bit OS | no | — | — | 64-bit only |

## Linux (Ubuntu, Debian, Fedora, Arch)

The installer does more here than on a Mac: if Docker isn't present it installs Docker Engine (via `get.docker.com`,
or `pacman` on Arch), adds you to the `docker` group, and installs `make` and `curl` if missing.

**One difference to know:** after the installer adds you to the `docker` group, that only takes effect on your *next*
login. If the first run ends with a permissions error on `docker ps`, log out, log back in, run `./install.sh …` again
— it's idempotent.

**Text editing:** `nano` is there. Where START_HERE uses `sed -i '' …` (the Mac form), on Linux it's `sed -i …`
without the `''`. Or just use nano.

**Always-on is easier than on a Mac.** Docker Engine starts at boot as a system service and the containers are set to
restart, so a Linux box comes back from a power cut with nobody logged in. No auto-login, no FileVault trade-off.
Do still set the BIOS/firmware to power on after loss where the machine allows it.

**Firewall:** if `ufw` is on, `sudo ufw allow from 192.168.0.0/16 to any port 8080` (or your LAN range) so other
devices on the LAN can read the API. Nothing needs to be open to the internet.

## Raspberry Pi 4 / 5

Use **Raspberry Pi OS 64-bit** (Bookworm or newer) — the 32-bit image fails at the arch check on purpose. Then follow
the Linux section; the installer treats it as Debian. A Pi 4 with 2 GB runs the node comfortably (Postgres + the app
idle under 300 MB). A few Pi-specific things:

- **Storage:** SD cards die under Postgres write patterns within a year or two. A USB SSD, or at least a high-endurance card, is worth the €20. Point `BACKUP_DIR` at a NAS so a dead card costs you nothing but an afternoon.
- **Power:** use the official supply. Brownouts corrupt filesystems; a UPS or a powered USB-C hub with a battery is cheap insurance in Bali.
- **Ethernet** over WiFi, same reason as the Mac mini.
- **Headless setup:** enable SSH in Raspberry Pi Imager when you flash the card, then everything in START_HERE happens over `ssh pi@<name>.local` from your laptop.

A Pi with an AirGradient or PurpleAir on the same WiFi is the cheapest complete node: about €80 of computer, and the
sensor never touches a cloud. This is the same anywhere; nothing about it is specific to one country.

## Windows 10 / 11 (via WSL2)

Windows runs the node through WSL2, which is a real Ubuntu inside Windows. Docker Desktop provides the engine; the
installer runs inside Ubuntu exactly as on Linux. Setup, once:

1. **Install WSL2 with Ubuntu.** Open PowerShell as administrator: `wsl --install`. Reboot. On first launch Ubuntu asks you to create a username and password.
2. **Install Docker Desktop for Windows** from docker.com. In its Settings → General tick *Use the WSL 2 based engine*; in Settings → Resources → WSL integration, enable it for **Ubuntu**. Also tick *Start Docker Desktop when you sign in*.
3. **Open the Ubuntu terminal** (search "Ubuntu" in the Start menu). Check: `docker info >/dev/null && echo "docker ok"`.
4. From here, follow START_HERE inside that Ubuntu terminal. Keep the repo **in the Linux filesystem** (`~/planetai`), not on `/mnt/c/…` — Docker bind mounts from the Windows drive are slow and sometimes break the `config/` mount.

Differences you'll meet:
- The installer prints `Windows (WSL2) detected` and will *not* try to install Docker Engine (it uses Docker Desktop). If it says Docker isn't visible, step 2's WSL-integration checkbox is the fix.
- `localhost:8080` works from a Windows browser too — Docker Desktop forwards it.
- **Always-on:** the node runs only while Windows is logged in and Docker Desktop is running. Set Windows to never sleep (Settings → System → Power), and Docker Desktop to start at sign-in. For unattended use, a Linux box or Pi is more dependable than a Windows machine; use Windows to try it, not to leave it.
- `cron` inside WSL doesn't run unless WSL is running. The nightly backup will fire only if the Ubuntu terminal (or any WSL process) is alive. Alternative: Windows Task Scheduler running `wsl -d Ubuntu -- bash -lc 'cd ~/planetai/planetai-node && ./backup.sh'` nightly.

## Intel Mac

Identical to START_HERE. OrbStack and Docker Desktop both support Intel. Builds take a little longer the first time.
The `MAC_MINI.md` settings apply unchanged to a 2018 Intel mini.

## Any of them: picking your sensor

The node reads three kinds of sensor out of the box; pick at least one when you run the installer.

| sensor | how it's read | flag | best for |
|---|---|---|---|
| **Smart Citizen Kit** (2.1, 2.3) | its cloud API, by kit number | `--sc 19880` | kits you already have; indoor flag comes from the kit's own setting |
| **AirGradient** ONE / Open Air | **directly on your WiFi**, no cloud | `--airgradient airgradient_84fce6.local` | new deployments; €120–220; the outdoor unit BAD recommends for Bali |
| **PurpleAir** | **directly on your WiFi**, no cloud | `--purpleair 192.168.1.60` | if you already own one; use its IP |

Add `--indoor` if your AirGradient or PurpleAir is inside; Smart Citizen kits carry that themselves. Add `--no-bad`
anywhere outside Bali, since that reference layer is one island's archive. Mixed kinds on one node are fine:
`--sc 19880 --airgradient ag1.local,ag2.local`. With no sensor at all the node still runs on global models.

Details, siting, and what the humidity correction does to each: `docs/sensors.md`.
