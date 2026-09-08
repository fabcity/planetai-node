# Platforms

One installer, four platforms. It detects which. What it cannot do is make a machine newer than it is, so this
page states the floor for each, where the floor comes from, and what a machine below it should do instead.

```bash
curl -fsSL planetai.fab.city/install | bash
```

## The matrix

Every floor below is the vendor's own current statement, linked. The container runtime is the only hard
requirement the node adds; everything else it installs itself.

| Machine | Minimum OS | Container runtime that installs there | RAM | Free disk |
|---|---|---|---|---|
| **macOS, Intel (x86_64)** | **13.5** (Ventura) | ≥14.0: OrbStack, Docker Desktop or Colima · 13.5–13.7: **Colima only** (`--vm-type vz`) · 13.0–13.4: Colima on QEMU, which needs a package manager · **≤12.x: none** | 4 GB | 3 GB |
| **macOS, Apple Silicon (arm64)** | **13.5** (Ventura) | same three, same floors. The database image is amd64-only and runs emulated. | 4 GB | 3 GB |
| **Ubuntu / Debian (amd64)** | Ubuntu 22.04 · Debian 11 | Docker Engine, installed by this script from `get.docker.com` | 2 GB | 3 GB |
| **Raspberry Pi OS 64-bit (arm64)** | — | **none. The node does not run here.** See below. | — | — |
| **Windows via WSL2 (amd64)** | Win 10 22H2 (19045) · Win 11 23H2 (22631) | Docker Desktop, WSL2 backend | 8 GB | 3 GB |

RAM and disk are the runtime vendor's floors, not the node's own. The node itself is much smaller than they
are — see the next section — so the runtime is what decides whether a machine qualifies.

## Where each floor comes from

**OrbStack: macOS 14.0.** "macOS 14.0 and newer" — [OrbStack FAQ](https://docs.orbstack.dev/faq). The FAQ names the
reason: macOS 12.0–12.2 shipped "critical virtualization bugs". There is an Intel build; the floor is the same.

**Docker Desktop: a moving window.** "Docker Desktop is supported on the current and two previous major macOS
releases" — [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/). That is 26,
15 and 14 today (September 2026) and it drops the oldest each autumn, so **the floor moves without anyone editing this
file.** Same page: "at least 4 GB of RAM".

**Colima: macOS 13.0, and 13.5 in practice.** "Colima requires macOS 13 or newer" —
[Colima FAQ](https://github.com/abiosoft/colima/blob/main/docs/FAQ.md#are-older-macos-versions-supported). Below 14 it
is the only runtime left, and on Intel it needs the `vz` backend to avoid a QEMU dependency: `vz` is "Lima >= 0.14,
macOS >= 13.0", but "Intel Macs with macOS prior to 13.5 cannot boot Linux kernel v6.2" —
[Lima, vmType vz](https://lima-vm.io/docs/config/vmtype/vz/). Hence 13.5 as the real floor. Colima installs as one
binary, no package manager: [INSTALL.md](https://github.com/abiosoft/colima/blob/main/docs/INSTALL.md).

**A Mac below 13.5 has no runtime at all.** OrbStack wants 14, Docker Desktop wants 14, Colima wants 13. This is not
a gap the installer can close; it is an OS upgrade or a different machine. The installer now says so in one sentence
and stops, instead of naming software the machine cannot run.

A machine that offers **Xcode Command Line Tools 14.2** is macOS 12.5–13.x — "macOS Monterey 12.5 – macOS Ventura
13.x" on [Apple's Xcode support page](https://developer.apple.com/support/xcode/). If that dialog appears, the machine
is at or below the floor. (The installer no longer triggers it: it fetches a signed tarball instead of using `git`.)

**Linux: Docker Engine's own list.** "Ubuntu Resolute 26.04 (LTS), Ubuntu Noble 24.04 (LTS), Ubuntu Jammy 22.04 (LTS)"
— [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/); "Debian Trixie 13, Debian Bookworm
12, Debian Bullseye 11" — [on Debian](https://docs.docker.com/engine/install/debian/). Both list `x86_64 (or amd64)`
first. Fedora and Arch work; they are not on Docker's tested list, so they are not in the table.

**Windows: Docker Desktop's own list.** "Windows 10 64-bit: Enterprise, Pro, or Education version 22H2 (build 19045).
Windows 11 64-bit: Enterprise, Pro, or Education version 23H2 (build 22631) or higher", "WSL version 2.1.5 or later",
"8GB system RAM", "64-bit processor with Second Level Address Translation (SLAT)", "Enable hardware virtualization in
BIOS/UEFI" — [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
Run the installer inside the Ubuntu shell. Sensors on the LAN are reached from WSL2 normally.

## Raspberry Pi 4 / 5 — not yet, and here is the proof

The database image the node uses publishes **one manifest, for `linux/amd64`, and nothing else**:

```
$ docker buildx imagetools inspect postgis/postgis:16-3.4-alpine
Name:      docker.io/postgis/postgis:16-3.4-alpine
MediaType: application/vnd.docker.distribution.manifest.v2+json
Digest:    sha256:681931a625df344215e9b8998bf34daf146b6a395ceacee4439eb9c85869239f
```

A single `manifest.v2` and no `Manifests:` list means no other architecture exists; the image config confirms
`architecture: amd64, os: linux` (built 2024-10-14). On a Pi, or any arm64 Linux, the database container stops with
`exec format error` — measured on a clean Ubuntu 24.04 arm64 VM, 6 September 2026. An Apple Silicon Mac is fine: its
Docker runs the amd64 image emulated.

The other three images the node can pull are multi-arch and all carry `linux/amd64`: `python:3.12-slim` (the app's
base), `eclipse-mosquitto:2` (the `mqtt` profile), `ipfs/kubo:latest` (the `ipfs` profile).

When an arm64 database image is chosen: 64-bit Raspberry Pi OS, 4 GB, boot from an SSD; SD cards die under Postgres
writes within a year.

## What the node actually costs, measured on amd64

The tester tarball, unpacked, both containers built and run for `linux/amd64`, no sensor configured — the
`sensor: none, models only` case, which is how everyone starts:

| | mean | peak |
|---|---|---|
| app container, memory | 150.0 MiB | 150.9 MiB |
| database container, memory | 79.2 MiB | 80.4 MiB |
| **both, memory** | **229 MiB** | **231 MiB** |
| app container, CPU | 2.8 % | 23 % (during a poll) |
| database container, CPU | 4.8 % | 47 % (during a poll) |

Twelve samples over two poll cycles and one generated report, on an amd64 build running emulated on Apple
Silicon — so the memory figures are honest and the CPU figures are an over-estimate for real amd64 hardware.
A report generates in 1.5 s. On disk: 192 MB for the app image, 453 MB for the database image, and 114 MB for
the database volume after the 4,476-row bootstrap (92 days of CAMS plus NASA POWER normals).

**There is no `PROFILE=lite`, because there is nothing to take out.** A quarter of a gigabyte and under 5 % of
a core is already the lean configuration, and the one heavy thing a node can run — a local language model — is
opt-in behind `planetai agent local`, lives on the host rather than in a container, and is simply not installed
until someone asks for it. Containers on macOS get CPU only, on Intel and on Apple Silicon alike; that matters
for `planetai agent local` and for nothing else here.

## Any of them

The node needs about 2 GB of disk for itself; the images add 208 MB of download (162 MB database, 46 MB Python base,
both compressed, amd64). Node #1, with four local sensors and the public references, adds about 1 MB of readings a
day: a few hundred MB a year, not 50. Ethernet over WiFi where you can. The machine must boot and log in on its own
after a power cut, or the node is down until someone types a password. For an always-on mini, read `MAC_MINI.md`.

macOS 26 quirk: dragging firmware onto a Meshtastic radio's drive fails (FSKit). Serial DFU works; see `MESHTASTIC.md`.

## Check before you install

```bash
curl -fsSL planetai.fab.city/preflight | bash        # nothing installed yet
planetai preflight                                    # on a node
planetai preflight --json                             # to paste into an issue
```

It prints one table: OS, architecture, memory, free disk, container runtime, egress and ports. Every failing row
carries the one command that fixes it *on that machine*, and it never asks a question.
