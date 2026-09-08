"""Generate the floor constants preflight reads, from data/platform_floors.yml.

Why generate instead of parse: tools/preflight.sh is fetched and run on its own, by curl, on a Mac that
may have no Xcode Command Line Tools and therefore no python3 and no yaml — that is the whole reason the
script is pure bash. It cannot read a YAML file at runtime, and it cannot be handed a second file. So the
numbers are written INTO it, between markers, and `--check` fails when they have drifted from the data.

  python3 tools/gen_floors.py            rewrite the block in tools/preflight.sh
  python3 tools/gen_floors.py --check    fail if the block is stale (make lint runs this)
"""
import re
import sys

import yaml

FLOORS, TARGET = "data/platform_floors.yml", "tools/preflight.sh"
BEGIN = "# ---- BEGIN GENERATED FLOORS"
END = "# ---- END GENERATED FLOORS"


def sh(v) -> str:
    return "" if v is None else str(v)


def block() -> str:
    d = yaml.safe_load(open(FLOORS))
    out = [BEGIN,
           "# From data/platform_floors.yml, where each floor carries its vendor URL and the date it was read.",
           "# Do not edit by hand. Regenerate: python3 tools/gen_floors.py   Verify: make lint",
           f"FLOORS_CHECKED={sh(min(str(e.get('checked')) for s in ('runtimes','vm_hosts') for e in d[s].values()))}"]
    # macOS runtimes and VM hosts, in the order preflight offers them
    for section, ids in (("runtimes", ["orbstack", "docker_desktop_mac", "colima"]),
                         ("vm_hosts", ["utm", "vmware_fusion_13_0", "virtualbox", "multipass"])):
        for i in ids:
            e = d[section][i]
            out.append(f'{section.upper()}_{i}_name="{e["name"]}"')
            out.append(f'{section.upper()}_{i}_min_os="{sh(e.get("min_os"))}"')
            out.append(f'{section.upper()}_{i}_min_os_x86_64="{sh(e.get("min_os_x86_64") or e.get("min_os"))}"')
            out.append(f'{section.upper()}_{i}_install="{sh(e.get("install"))}"')
            out.append(f'{section.upper()}_{i}_source="{sh(e.get("source"))}"')
    lin, win, node = d["linux"], d["windows"], d["node"]
    out += [f'LINUX_ubuntu_min="{lin["docker_engine_ubuntu"]["min_os"]}"',
            f'LINUX_debian_min="{lin["docker_engine_debian"]["min_os"]}"',
            f'LINUX_fedora_min="{lin["docker_engine_fedora"]["min_os"]}"',
            f'WINDOWS_min="{win["docker_desktop_wsl2"]["min_os"]}"',
            f'WINDOWS_min_ram_gb={win["docker_desktop_wsl2"]["min_ram_gb"]}',
            f'NODE_min_ram_gb={node["min_ram_gb"]}',
            f'NODE_min_free_disk_gb={node["min_free_disk_gb"]}',
            END]
    return "\n".join(out) + "\n"


def current(text: str) -> str:
    m = re.search(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n", text, re.S)
    return m.group(0) if m else ""


text = open(TARGET).read()
have, want = current(text), block()
if not have:
    sys.exit(f"  x {TARGET} has no generated-floors block. Add the markers, then run this.")

if "--check" in sys.argv:
    if have == want:
        print(f"  floors in {TARGET} match {FLOORS}")
        sys.exit(0)
    print(f"  x {TARGET} is out of date with {FLOORS}. Run: python3 tools/gen_floors.py")
    for a, b in zip(have.splitlines(), want.splitlines()):
        if a != b:
            print(f"    - {a}\n    + {b}")
    sys.exit(1)

open(TARGET, "w").write(text.replace(have, want))
print(f"  wrote {want.count(chr(10))} lines of floors into {TARGET}")
