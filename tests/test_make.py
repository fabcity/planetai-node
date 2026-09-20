"""packs/make: the nearest fab lab, and everything it must refuse to claim.

The fixture is twenty REAL records pulled from the Fab Lab Network directory on 2026-09-20,
chosen one per edge case rather than for being typical: labs near the Bali node, active labs
publishing no coordinates, one each of planned / closed / corona / no-status, a lab with
contact details, a lab with no capabilities, and a dozen on the other side of the world.

Everything here runs against pure functions. `nearest()` decides what a person is told, and
"the nearest lab" being wrong is worse than it being absent, so it is tested without a
network or a database standing between the assertion and the answer.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packs" / "make"))
os.environ.setdefault("NODE_LAT", "-8.65")
os.environ.setdefault("NODE_LON", "115.21")

import adapter  # noqa: E402

LABS = json.loads((Path(__file__).parent / "data" / "fablabs_twenty.json").read_text())
NODE = (-8.65, 115.21)          # the Bali node's coordinates, as in presets/bali.env

fails = []


def check(label, cond, detail=""):
    if cond:
        print(f"  {label}")
    else:
        fails.append(f"{label} — {detail}")
        print(f"  x {label} — {detail}")


# ---------------------------------------------------------------- distance

d = adapter.km(*NODE, -8.65, 115.21)
check("a point measured against itself is 0 km", d < 0.001, f"got {d}")
# Bali node to Barcelona, ~12,700 km great-circle. Wrong-by-a-factor errors show up here.
d = adapter.km(*NODE, 41.39, 2.16)
check("Bali to Barcelona is ~12,700 km", 12000 < d < 13500, f"got {d:.0f} km")

# ---------------------------------------------------------------- what is in the ring

found = adapter.nearest(LABS, *NODE, 50.0)
check("the fixture has labs within 50 km", len(found) >= 1, f"got {len(found)}")
check("nearest is Fab Lab Bali",
      found and (found[0][0]["slug"] == "fablabbali"),
      f"got {found[0][0]['slug'] if found else 'nothing'}")
check("distances come back sorted, nearest first",
      [p[1] for p in found] == sorted(p[1] for p in found))
check("every lab in the ring is inside the radius",
      all(dist <= 50.0 for _, dist in found))

# ---------------------------------------------------------------- what must never be in it

statuses = {(lab.get("activity_status") or "").strip() for lab, _ in found}
check("only active labs are returned", statuses <= {"active"}, f"got {statuses}")
check("a planned lab is never offered as somewhere to go",
      not any(lab.get("activity_status") == "planned" for lab, _ in adapter.nearest(LABS, *NODE, 20000.0)))
check("a closed lab is never offered",
      not any(lab.get("activity_status") == "closed" for lab, _ in adapter.nearest(LABS, *NODE, 20000.0)))
check("a lab with no status at all is never offered",
      not any(not (lab.get("activity_status") or "").strip()
              for lab, _ in adapter.nearest(LABS, *NODE, 20000.0)))
check("a lab with no coordinates is never placed on the map",
      all(lab.get("latitude") is not None for lab, _ in adapter.nearest(LABS, *NODE, 20000.0)))

# ...but it is counted, not lost.
n = adapter.skipped_without_coordinates(LABS)
check("active labs without coordinates are counted for the doctor row", n >= 1, f"got {n}")

# ---------------------------------------------------------------- the radius is a radius

check("a 1 km radius around this node finds nothing", adapter.nearest(LABS, *NODE, 1.0) == [])
check("a planet-sized radius finds every active, placed lab",
      len(adapter.nearest(LABS, *NODE, 20100.0))
      == sum(1 for l in LABS if (l.get("activity_status") or "").strip() == "active"
             and l.get("latitude") is not None))

# ---------------------------------------------------------------- the archive's filenames

check("a dotted snapshot name sorts", adapter.snapshot_key("2026.07.31_labs.json") == "20260731")
check("the one with a space sorts the same way", adapter.snapshot_key("2023.03.31 labs.json") == "20230331")
check("the YYYYMMDD_HHMM form sorts", adapter.snapshot_key("20260630_0928_labs.json") == "20260630")
check("a name with no date is never newest", adapter.snapshot_key("labs.json") == "")
newest = max(["2026.07.31_labs.json", "2023.03.31 labs.json", "20260630_0928_labs.json"],
             key=adapter.snapshot_key)
check("newest of the three mixed forms is 2026.07.31", newest == "2026.07.31_labs.json", newest)

# ---------------------------------------------------------------- the sentence a person reads

rows = [{"name": "Fab Lab Bali",
         "meta": {"distance_km": 17.2, "capabilities": ["laser", "three_d_printing", "cnc_milling"]}},
        {"name": "Somewhere Else", "meta": {"distance_km": 44.0, "capabilities": []}}]
line = adapter.ask_line(rows)
check("the ask line names the NEAREST lab", "Fab Lab Bali" in line, line)
check("the ask line carries the distance", "17.2 km" in line, line)
check("capability tokens become words a person uses",
      "laser cutting" in line and "3D printing" in line and "three_d_printing" not in line, line)
# Everything else the node says to a person is translated; a Spanish report ending in "laser
# cutting" reads like a leak. All three languages, because the report ships in all three.
check("the machine names are Indonesian in an Indonesian report",
      "pemotongan laser" in (adapter.ask_line(rows, "id") or ""), adapter.ask_line(rows, "id"))
check("the machine names are Spanish in a Spanish report",
      "corte láser" in (adapter.ask_line(rows, "es") or ""), adapter.ask_line(rows, "es"))
check("an unknown locale falls back to English rather than to nothing",
      "laser cutting" in (adapter.ask_line(rows, "pt") or ""), adapter.ask_line(rows, "pt"))
check("a regional tag resolves to its language", adapter.ask_line(rows, "es-CL") == adapter.ask_line(rows, "es"))
check("every locale covers the whole vocabulary",
      all(set(v) == set(adapter.CAPABILITY_WORDS["en"]) for v in adapter.CAPABILITY_WORDS.values()))
# Found by running the pack on pai-clean, not by reading it: a node inside a fab lab is the
# deployment this pack most wants, and "0.0 km" reads like a broken number however true it is.
check("a lab at the node's own address reads as <0.1 km, not 0.0 km",
      adapter.ask_line([{"name": "Here", "meta": {"distance_km": 0.0, "capabilities": []}}])
      == "Here, <0.1 km")
check("a lab 100 m away still gets its number",
      adapter.ask_line([{"name": "There", "meta": {"distance_km": 0.1, "capabilities": []}}])
      == "There, 0.1 km")
check("no ask line when nothing is near", adapter.ask_line([]) is None)
check("a lab with no capabilities still gets a line",
      adapter.ask_line([{"name": "Bare Lab", "meta": {"distance_km": 3.0, "capabilities": []}}])
      == "Bare Lab, 3.0 km")
# If fablabs.io adds a seventh token, an operator must see the new word rather than a shorter list.
check("an unknown capability is shown, not dropped",
      "telekinesis" in adapter.ask_line(
          [{"name": "L", "meta": {"distance_km": 1.0, "capabilities": ["telekinesis"]}}]))

# ---------------------------------------------------------------- what the pack promises about itself

import yaml  # noqa: E402

pack = yaml.safe_load((Path(__file__).resolve().parent.parent / "packs" / "make" / "pack.yaml").read_text())
check("the pack declares no metrics — it holds places, not numbers", pack["metrics"] == [])
check("the pack declares its registry sources",
      "economic/community/fablabs-io" in pack["sources"])
check("the pack has no cells.yml, so it can never claim an Index cell",
      not (Path(__file__).resolve().parent.parent / "packs" / "make" / "cells.yml").exists())
check("the attribution says the directory is not openly licensed",
      "NOT OPENLY LICENSED" in pack["attribution"])

print()
if fails:
    print(f"  {len(fails)} check(s) failed")
    sys.exit(1)
print("  make: the ring is active labs only, the sentence names the nearest, and nothing claims a cell")
