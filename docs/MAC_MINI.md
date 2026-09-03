# Mac mini — turning it into an always-on node

The laptop is for trying it. The mini is for leaving it. A mini in a cupboard is the reference deployment for
node #1, and everything below is about the difference between "runs on my Mac" and "still running in March
without anyone touching it." Do this once, then follow `START_HERE.md` on the mini itself.

Time: an hour, once. You'll need a monitor and keyboard plugged into the mini for the first session only — some of
the permission dialogs can't be clicked over SSH.

## Which mini

Any Apple Silicon mini (M1, M2, M4) is more than enough; an 8 GB base model idles at under 10% doing this. A 2018
Intel mini also works if it runs macOS 13 or newer. Storage is irrelevant — the database grows ~50 MB a year.
Don't buy anything for this; if there's a mini already in the house or the lab, that's the one.

## 1. Physical

- **Ethernet, not WiFi.** The mini has a port; use it. WiFi drops are the #1 cause of "silent sensor" alerts that are actually a silent node. If it must be WiFi, 2.4 GHz is more stable through walls than 5 GHz.
- **Power.** Where the grid flickers, that is what kills nodes, not dramatic outages. Put the mini *and the router* on a small UPS; a 600 VA unit of the kind sold for a home PC runs both for twenty minutes and, more usefully, smooths the dips. In Bali this is the single most important line in this document. In a city with a steady supply you can skip it, and you will know which you have.
- **Placement.** Indoors, off the floor, not in direct sun, some air around it. It doesn't need AC. Away from the kitchen — not for the mini's sake, for the sensor's: the kit is what tells you about smoke, and if it's above the wok it will tell you about dinner.
- **Monitor.** Only for setup. Afterwards you can unplug it. (If Screen Sharing later shows a black or tiny screen with no monitor attached, a $10 "HDMI dummy plug" fixes it. Not needed for the node itself.)

## 2. macOS settings (System Settings, with the monitor attached)

**General → About → Name:** your node's name, for example `bayu-2` or `mayur-vihar`. Whatever you choose, the mini becomes reachable as `<that-name>.local` from any device on the same network, which is how you will talk to it from now on. The examples below use `bayu-2`; substitute yours.

**General → Date & Time:** time zone Asia/Makassar (WITA), "Set time and date automatically" on. Daily buckets and alert times depend on this.

**Energy** (desktop Macs show this instead of Battery):
- Prevent automatic sleeping when the display is off: **on**
- Put hard disks to sleep when possible: **off**
- Wake for network access: **on**
- Start up automatically after a power failure: **on** ← the line that brings it back after the brownout

**Lock Screen:** "Start Screen Saver when inactive": Never. "Turn display off when inactive": 2 minutes is fine — display off is not sleep.

**Users & Groups → Automatic login:** set to your user. **This is required.** Docker containers only run inside a logged-in user session on macOS; if the mini restarts after a power cut and sits at the login screen, the node is down until someone types a password. Automatic login is greyed out while **FileVault** is on — turn FileVault off first (Privacy & Security → FileVault). The trade-off is real: the disk is no longer encrypted at rest. For a node holding air-quality readings and a Telegram bot token, in a locked house, that's the right call. If the mini also holds anything personal, give the node its own user account instead and auto-login that one.

**General → Sharing:**
- **Remote Login** (SSH): **on**, for your user. This is how you'll run `make health` from the sofa.
- **Screen Sharing**: **on**. For the once-a-year dialog that needs a click.
- Everything else off.

**General → Software Update → Automatic Updates:** download on, **install macOS updates off** (install them yourself, on a day you're around — an unattended reboot mid-update is how a node stays down for a week). Security responses and system files: on.

**Privacy & Security → Full Disk Access:** add **Terminal** and, later, **cron** (it appears in `/usr/sbin/cron`; press ⌘-Shift-G in the file picker and paste the path). Without this the nightly backup fails silently on newer macOS.

## 3. OrbStack

Install as in `START_HERE.md` step 3. Then OrbStack → Settings → General:
- **Start at login: on.** With auto-login, this means: power returns → mini boots → user logs in → OrbStack starts → containers (set to `restart: unless-stopped`) come back → the node is polling again within about two minutes of power. No human involved.
- Leave everything else default.

Docker Desktop works too, with the same "Start when you log in" setting. OrbStack uses less memory and doesn't nag.

## 4. Install the node

Now follow `START_HERE.md` from step 3 on the mini itself (monitor still attached — the first `docker` run and the
cron line can trigger permission prompts you need to see). Use `~/planetai` as the folder.

When `doctor` is green and the first poll has landed, test the one thing that matters on a mini:

**Pull the power cord.** Wait ten seconds. Plug it back in. Go make coffee. Come back in five minutes and, from your
laptop on the same network:

```bash
ssh <your-user>@bayu-2.local 'cd ~/planetai/planetai-node && make health'
```

If `polls` is counting again, the node survives a power cut unattended. If you are at a login screen, revisit auto-login and FileVault.
If OrbStack didn't start, revisit "Start at login." Do this test *now*, not after the first real outage.

## 5. Working from your laptop

Unplug the monitor. From here on the mini is a box you talk to.

Add this to `~/.ssh/config` on your laptop (create the file if it isn't there):
```
Host bayu
  HostName bayu-2.local
  User <your-user>
```
Then `ssh bayu` gets you a Terminal *on the mini*, and everything in `START_HERE.md` works there exactly as written:
```bash
ssh bayu
cd ~/planetai/planetai-node
make health
make alerts
nano config/rules.yml
```

The node's own web endpoints are reachable from the laptop too, no SSH needed, while you're on the same network:
`curl -s bayu-2.local:8080/stats | python3 -m json.tool`. Bookmark `http://bayu-2.local:8080/health` in a browser.

Off the home network — from Ubud, from Barcelona — you can't reach `bayu-2.local`. That's Stage 1's Tailscale
(`ARCHITECTURE.md` §6): one install on the mini, one on the laptop, and `bayu-2` becomes reachable from anywhere,
with no ports opened on the router. Not needed for node #1. Needed the day you want to check on it from a plane.

## 6. Backups to the NAS

The mini shouldn't be the only place the record lives. Mount the NAS share on the mini and point backups at it:

1. Finder → Go → Connect to Server → `smb://<nas-name-or-ip>/<share>`. Tick "remember in keychain."
2. Make it reconnect after reboot: System Settings → General → Login Items → **+** → pick the mounted share under Volumes.
3. Create a folder on it: `planetai/bayu-2`.
4. In `.env`: `BACKUP_DIR=/Volumes/<share>/planetai/bayu-2`, then `make backup` to confirm a file appears there.

The 03:17 cron that `install.sh` scheduled now writes there. If the NAS is asleep at 03:17, the dump fails for that
night and the next one succeeds; you lose nothing because the database is still on the mini. Check once a month
that the newest file in that folder is recent.

## 7. What can still take it down, honestly

- **A macOS update you didn't install** eventually nags into a forced restart. With auto-login and OrbStack at login it comes back; without them it doesn't. That's why sections 2–3 matter more than anything in the code.
- **The router's DHCP lease changes** the mini's IP. `bayu-2.local` still works on the LAN. `PARENT_API_URL` on a future child node should use the `.local` name or, better, the Tailscale name — never a bare IP. Or reserve the IP in the router.
- **The ISP goes down.** A Smart Citizen kit publishes to its cloud, so with no internet its data is unreachable; the same is true of the global models. An AirGradient or PurpleAir on your LAN keeps reporting throughout. Alerts queue nowhere; they're just not evaluated for the duration. When the line returns, polling resumes and readings backfill only from that moment — the gap is real and stays in the record. This is the argument for a LAN-local sensor (AirGradient, `docs/sensors.md`) as the second piece of hardware: it keeps reporting to the mini when the internet doesn't.
- **Someone unplugs it to charge a phone.** Label the cable. Seriously.

## 8. Moving from the laptop to the mini

If you already ran node #1 on the laptop for a few days: don't migrate the database, just start fresh on the mini
and copy two files across — `.env` (then edit `NODE_NAME` if it changed) and `config/rules.yml`. A few days of
readings aren't worth a restore procedure. Stop the laptop's copy (`docker compose down`) so two nodes don't send
the same alerts to the same group.

If it's been running for months, `make backup` on the laptop, copy the `.sql.gz` to the mini, and restore it before
the first poll: `gunzip -c file.sql.gz | docker compose exec -T db psql -U planetai planetai`. Ask before doing this
the first time.

---

Done right, this is a box you don't think about. The daily pulse is how you know it's alive; the absence of the pulse
is the only alert the mini itself will ever send.
