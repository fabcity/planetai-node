# Platforms

**Linux first, macOS second, Windows third.** Not a preference — a consequence. A node's home is a box
that stays on, and a laptop under macOS is designed to go to sleep. More to the point: on macOS the floor
rises every year, and on Linux it does not. Docker Desktop supports "the current and two previous major
macOS releases" *by policy*, so a Mac falls off that list on its own, with nobody deciding anything.
Docker Engine still supports Ubuntu 22.04 and Debian 11, four and five years old.

One installer, five platforms. It detects which. What it cannot do is make a machine newer than it is, so
this page states the floor for each, where the floor comes from, and what a machine below it should do
instead — which is usually Linux, on the same hardware.

```bash
curl -fsSL planetai.fab.city/install | bash
```

## The matrix

The container runtime is the only hard requirement the node adds; everything else it installs itself.
This table and the sources under it are generated from `data/platform_floors.yml`, so the page cannot
drift from what the installer asserts.

<!-- BEGIN GENERATED: tools/render_platforms.py from data/platform_floors.yml -->
| Machine | Minimum OS | Container runtime that installs there | RAM | Free disk |
|---|---|---|---|---|
| **Ubuntu / Debian (amd64)** — *the first choice* | Ubuntu 22.04 · Debian 11 | Docker Engine, installed by the script | 4 GB | 3 GB |
| **Arch, and Omarchy on top of it (amd64)** | rolling | Docker from Arch's own repository, installed by the script | 4 GB | 3 GB |
| **macOS, Apple Silicon (arm64)** | **13.0** | OrbStack, Docker Desktop or Colima. Colima reaches 13.0 here; the database image is amd64-only and runs emulated. | 4 GB | 3 GB |
| **macOS, Intel (x86_64)** | **13.5** | ≥14.0: all three · 13.5–13.7: **Colima only** (`--vm-type vz`) · **below 13.5: none, and Linux is the route** | 4 GB | 3 GB |
| **Windows via WSL2 (amd64)** | 10 22H2 (build 19045) | Docker Desktop, WSL2 backend | 8 GB | 3 GB |
| **Raspberry Pi OS 64-bit (arm64)** | — | **none. Untested, and the database image has no arm64 build.** | — | — |

### Where each number comes from

Every floor below is the vendor's own current sentence, with the date it was read. `make check-floors` fails when any of them is more than 180 days old.

| | Floor | The vendor's words | Read |
|---|---|---|---|
| [OrbStack](https://docs.orbstack.dev/faq) | 14.0 | macOS 14.0 and newer | 2026-09-08 |
| [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) | 14.0 | Docker Desktop is supported on the current and two previous major macOS releases | 2026-09-08 |
| [Colima](https://github.com/abiosoft/colima/blob/main/docs/FAQ.md#are-older-macos-versions-supported) | 13.5 | Colima requires macOS 13 or newer | 2026-09-08 |
| [UTM](https://github.com/utmapp/UTM/releases/tag/v5.0.5) | 11.3 | "Reverted minimum version requirement imposed by v5.0.4: once again we support versions down to macOS 11.3 and iOS 14.0." | 2026-09-08 |
| [VMware Fusion 13.0](https://techdocs.broadcom.com/us/en/vmware-cis/desktop-hypervisors/fusion-pro/13-0/using-vmware-fusion/getting-started-with-vmware-fusion/system-requirements-for-vmware-fusion.html) | 12.0 | Any Mac that officially supports macOS 12 Monterey or later. | 2026-09-08 |
| [VMware Fusion (current line)](https://techdocs.broadcom.com/us/en/vmware-cis/desktop-hypervisors/fusion-pro/25H2/using-vmware-fusion/getting-started-with-vmware-fusion/system-requirements-for-vmware-fusion.html) | 15.0 | Any Mac that officially supports macOS 15 Sequoia or later. | 2026-09-08 |
| [VirtualBox](https://www.virtualbox.org/manual/topics/installation.html) | 13.0 | Supported macOS hosts are listed as "26 (Tahoe)", "15 (Sequoia)", "14 (Sonoma)" and "13 (Ventura)", each "with Intel x86_64 processors" and again with… | 2026-09-08 |
| [Multipass](https://canonical.com/multipass/docs/latest/how-to-guides/install-multipass/) | 14.0 | You can use any Mac (M-series or Intel based) with macOS 14 Sonoma or later installed. | 2026-09-08 |
| [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) | 22.04 | "Ubuntu Resolute 26.04 (LTS), Ubuntu Noble 24.04 (LTS), Ubuntu Jammy 22.04 (LTS)" and "compatible with x86_64 (or amd64), armhf, arm64, s390x, and ppc… | 2026-09-08 |
| [Docker Engine on Debian](https://docs.docker.com/engine/install/debian/) | 11 | "Debian Trixie 13 (stable), Debian Bookworm 12 (oldstable), Debian Bullseye 11 (oldoldstable)" and "compatible with x86_64 (or amd64), armhf (arm/v7),… | 2026-09-08 |
| [Docker Engine on Fedora](https://docs.docker.com/engine/install/fedora/) | 43 | you need a maintained version of one of the following Fedora versions: Fedora 44, Fedora 43 | 2026-09-08 |
| [Docker on Arch](https://wiki.archlinux.org/title/Docker) | rolling | Arch has no Docker Engine page at docs.docker.com; docker is packaged in Arch's own extra repository and the installer uses pacman. Rolling release, s… | 2026-09-08 |
| [Docker Desktop with the WSL2 backend](https://docs.docker.com/desktop/setup/install/windows-install/) | 10 22H2 (build 19045) | "Windows 10 64-bit: Enterprise, Pro, or Education version 22H2 (build 19045). Windows 11 64-bit: Enterprise, Pro, or Education version 23H2 (build 226… | 2026-09-08 |

*Docker Desktop's floor moves on its own: Docker Desktop is supported on the current and two previous major macOS releases — so it drops the oldest macOS each autumn whether or not anyone edits this page.*
<!-- END GENERATED -->

RAM and disk are the runtime vendors' floors, not the node's own. The node itself is much smaller — see
*What the node actually costs* below — so the runtime is what decides whether a machine qualifies.

## Two ways to put Linux on a machine

The choice is not really which distribution. It is whether anybody still uses the machine.

**Ubuntu Server** — nobody uses it, it just runs. No desktop, ssh in, the lowest upkeep of anything here,
and the longest support window: 22.04 is four years old and Docker still supports it. This is the right
answer for a mini PC in a hallway, or a laptop with the lid shut on a shelf.

**Omarchy** — a machine somebody uses *and* a node. Arch underneath, Hyprland on top, installed from an
ISO by answering five questions. Its own page says a 2011 ThinkPad X220 with 2 GB of RAM runs it, which
is smaller than any node in this network. Arch is a rolling release, so there is no version floor to
outlive — and the installer takes its pacman branch, which CI simulates on every push.

Either way the install line is the same one, and `docs/REVIVE_A_LAPTOP.md` walks the whole thing.

## A Mac below the floor is not finished

Below the floor no container runtime installs, and for some models upgrading is not a route: a MacBook
Pro (Retina, 15-inch, Mid 2015) tops out at macOS 12.7.6, while a 2017 model reaches Ventura and clears
the floor. `data/mac_ceilings.yml` holds what Apple's own compatibility pages establish, and
`planetai preflight` says which case a machine is in rather than sending anyone to check a list.

Two routes work on a Mac that cannot upgrade, and both are printed as commands:

- **Linux in a VM on that Mac.** UTM is free, needs no account, supports macOS 11.3, and on Intel wraps
  Apple's Hypervisor framework so the guest CPU is near-native. Old UTM builds stay on GitHub Releases,
  so a Mac below a current build's floor can fetch an earlier one. VMware Fusion **13.0** is the
  alternative when the VM will outlive a few weeks — bridged networking, open-vm-tools, and
  `vmrun start <vmx> nogui` for headless autostart; note the *current* Fusion line needs macOS 15.
- **Linux on the metal**, and the laptop becomes the node: `REVIVE_A_LAPTOP.md`.

Not Multipass, whatever anything else in this repository says: its floor is macOS 14. Not VirtualBox
either — its oldest supported host is Ventura.

## Raspberry Pi 4 / 5 — untested, and here is what blocks it

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

## Two machines to aim at, and which one to reach for first

**Reference A — a repurposed x86_64 laptop.** The machine this section exists because of: a MacBook Pro
(Retina, 15-inch, Mid 2015), Core i7-4870HQ, 4 cores / 8 threads, 16 GB, 428 GB free. Its Geekbench 6
multi-core score is **3,664**
([cpu-monkey](https://www.cpu-monkey.com/en/benchmark-intel_core_i7_4870hq-geekbench_6_multi_core),
read 9 September 2026). Under macOS it cannot run a node at all; with Linux on the metal it is a good
one. Any x86_64 laptop from about 2015 with 8 GB is in the same class.

**Reference B — a small always-on x86 mini PC.** A Beelink MINI S12 Pro or equivalent: Intel N100,
4 cores / 4 threads, 16 GB, 500 GB SSD, roughly 6 W idle, no fan noise to speak of. Its Geekbench 6
multi-core score is **2,595** across 677 samples
([cpu-monkey](https://www.cpu-monkey.com/en/benchmark-intel_processor_n100-geekbench_6_multi_core),
read 9 September 2026).

**So the ten-year-old laptop is about 40 % faster on multicore than the mini PC we would otherwise tell
someone to buy.** That is the whole argument for reviving what a building already has: revive first, buy
second. The mini PC wins on idle power, silence and the fact that it has no battery to age — reasons to
choose it, but not performance ones.

*The mini PC's street price is the one number here that is not verified. It moves weekly and by region,
so price the named model where you are, on the day, and write the figure and the date in next to it.*

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
