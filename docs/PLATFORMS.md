# Platforms

One installer, four platforms. It detects which.

```bash
curl -fsSL planetai.fab.city/node0/install | bash
```

## macOS

Apple Silicon or Intel, macOS 13+. Install OrbStack or Docker Desktop first and open it once. For an always-on mini,
read `MAC_MINI.md`: automatic login and "start after power failure" are what keep it up.

macOS 26 quirk: dragging firmware onto a Meshtastic radio's drive fails (FSKit). Serial DFU works; see `MESHTASTIC.md`.

## Linux

Ubuntu, Debian, Fedora, Arch. The installer adds Docker if missing (`get.docker.com`) and puts you in the `docker`
group; log out and in once. Containers restart with the machine.

## Raspberry Pi 4 / 5

**Not yet.** The database image the node uses (`postgis/postgis:16-3.4-alpine`) has no arm64 build, so on a Pi or
any other arm64 Linux machine the database container stops with `exec format error` (measured on a clean Ubuntu 24.04
arm64 VM, 6 September 2026). An Apple Silicon Mac is fine: its Docker runs amd64 images. When an arm64 image is chosen:
64-bit Raspberry Pi OS, 4 GB, boot from an SSD; SD cards die under Postgres writes within a year.

## Windows

WSL2 with Ubuntu, Docker Desktop with the WSL2 backend. Run the installer inside the Ubuntu shell. Sensors on the LAN
are reached from WSL2 normally.

## Any of them

The node needs about 2 GB of disk. Node #1, with four local sensors and the public references, adds about 1 MB of
readings a day: a few hundred MB a year, not 50. Ethernet over WiFi where you can. The
machine must boot and log in on its own after a power cut, or the node is down until someone types a password.
