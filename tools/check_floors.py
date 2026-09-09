"""Every version floor the installer asserts must carry a source and a date somebody read it.

A floor is a claim about someone else's product, and those move. OrbStack's went to 14.0, Multipass's to
14.0, VMware Fusion's current line to 15.0, and Docker Desktop's moves every autumn on its own. A number
typed from memory sends a tester to install software their machine cannot run — which is exactly what
happened on 7 September 2026.

So: FAIL when an entry has no source, no date, or a date older than meta.staleness_days. A moved floor is
a red build here, not a wasted evening on somebody's laptop.

Run: python3 tools/check_floors.py        (make check-floors)
"""
import datetime
import sys

import yaml

FLOORS = "data/platform_floors.yml"
SECTIONS = ("runtimes", "vm_hosts", "linux", "windows", "assets")

d = yaml.safe_load(open(FLOORS))
stale_days = int(d.get("meta", {}).get("staleness_days", 180))
today = datetime.date.today()
errs: list[str] = []
rows: list[tuple[str, str, int]] = []


def check(key: str, e: dict, path: str, vendor: bool = True) -> None:
    """vendor=False for a figure we measured ourselves: it needs `measured_on`, not a URL."""
    if not isinstance(e, dict):
        errs.append(f"{path}: not a mapping")
        return
    required = ("source", "checked", "says") if vendor else ("measured_on", "checked", "says")
    for field in required:
        if not e.get(field):
            errs.append(f"{path}: no {field}. A floor with no source is not a floor.")
    src = str(e.get("source", ""))
    if vendor and src and not src.startswith("http"):
        errs.append(f"{path}: source is not a URL: {src!r}")
    when = e.get("checked")
    if isinstance(when, datetime.date):
        age = (today - when).days
        rows.append((path, str(when), age))
        if age > stale_days:
            errs.append(f"{path}: last read {age} days ago ({when}), limit {stale_days}. "
                        f"Re-read {src} and update `checked`, or the installer is quoting a number "
                        f"nobody has verified this year.")
        if age < 0:
            errs.append(f"{path}: checked is in the future ({when})")
    elif when is not None:
        errs.append(f"{path}: checked must be a date (YYYY-MM-DD, unquoted), got {when!r}")


for section in SECTIONS:
    if section not in d:
        errs.append(f"{FLOORS}: no `{section}` section")
        continue
    for key, entry in (d[section] or {}).items():
        check(key, entry, f"{section}.{key}")

if "node" in d:
    check("node", d["node"], "node", vendor=False)

# A floor the installer asserts but nobody recorded is the failure mode this file exists to stop, so
# name the entries preflight is entitled to read and fail if one vanishes.
REQUIRED = {"assets.utm_dmg", "assets.ubuntu_server_iso", "assets.omarchy_iso", "runtimes.orbstack", "runtimes.docker_desktop_mac", "runtimes.colima",
            "vm_hosts.utm", "vm_hosts.vmware_fusion_13_0", "vm_hosts.virtualbox", "vm_hosts.multipass",
            "linux.docker_engine_ubuntu", "linux.docker_engine_debian", "windows.docker_desktop_wsl2"}
present = {p for p, _, _ in rows}
for miss in sorted(REQUIRED - present):
    errs.append(f"{miss} is missing from {FLOORS}, and preflight reads it")

if errs:
    print(f"  x {FLOORS}:")
    for e in errs:
        print(f"    - {e}")
    sys.exit(1)

oldest = max(rows, key=lambda r: r[2]) if rows else None
print(f"  {len(rows)} floors, all sourced and dated"
      + (f"; oldest read {oldest[2]} days ago ({oldest[0]}, {oldest[1]}), limit {stale_days}" if oldest else ""))
