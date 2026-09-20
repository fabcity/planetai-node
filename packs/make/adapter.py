"""The nearest fab labs, as places rather than measurements.

Reads the Fab Lab Network directory and keeps the active labs within MAKE_RADIUS_KM of this node
as `sensors` rows with kind='facility'. No readings, no metrics, no cell, no alert: a facility is a
place with a name and a point, and the node stores it so a person can be told where to go.

WHY kind='facility' AND local=False. `custody` is generated as `kind='child' OR (local AND kind
<>'peer')`, so a facility can never make an Index cell say `live` — which is correct, because a fab
lab five kilometres away is not this node's instrument and never becomes one. init.sql's kind comment
names `facility` for this reason.

WHERE IT READS FROM. `MAKE_SOURCE=archive` (default) reads the Fab Foundation's own monthly freezes
at gitlab.fabcloud.org/fl-management/fablab-network-data, which can be pinned to a dated filename —
two nodes on the same pin answer identically, which is the whole argument for the vendored registry
this pack's `sources:` point at. `MAKE_SOURCE=live` reads api.fablabs.io/0/labs.json, whose own root
page says "This is the legacy API endpoint, which has now been removed" while serving 5.38 MB anyway.
Archive is the default because a dated file is a better dependency than a contradiction.

LICENCE. The directory is not openly licensed; see pack.yaml's attribution and the registry entry
economic/community/fablabs-io. Contact details are in the payload on most records and are never read.

Contract: fetch(hc) -> (sensors, readings), like everything in app/sources.py.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt

import psycopg

log = logging.getLogger("planetai.make")

ARCHIVE_TREE = ("https://gitlab.fabcloud.org/api/v4/projects/"
                "fl-management%2Ffablab-network-data/repository/tree"
                "?path=archive/labs.json&per_page=100")
ARCHIVE_FILE = ("https://gitlab.fabcloud.org/api/v4/projects/"
                "fl-management%2Ffablab-network-data/repository/files/{path}/raw?ref=main")
LIVE_URL = "https://api.fablabs.io/0/labs.json"
SOURCE = "fablabs-io"

# The six tokens fablabs.io publishes, in the words a person would use, in the three languages the
# node speaks. A token absent from the map is shown as ITSELF rather than dropped: if the vocabulary
# grows, an operator should see an unfamiliar word and not a silently shorter list.
CAPABILITY_WORDS = {
    "en": {"three_d_printing": "3D printing", "cnc_milling": "CNC milling", "laser": "laser cutting",
           "vinyl_cutting": "vinyl cutting", "circuit_production": "circuit boards",
           "precision_milling": "precision milling"},
    "id": {"three_d_printing": "pencetakan 3D", "cnc_milling": "frais CNC", "laser": "pemotongan laser",
           "vinyl_cutting": "pemotongan vinil", "circuit_production": "papan sirkuit",
           "precision_milling": "frais presisi"},
    "es": {"three_d_printing": "impresión 3D", "cnc_milling": "fresado CNC", "laser": "corte láser",
           "vinyl_cutting": "corte de vinilo", "circuit_production": "placas de circuito",
           "precision_milling": "fresado de precisión"},
}


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2, dl = radians(lat1), radians(lat2), radians(lon2 - lon1)
    return 6371 * 2 * asin(sqrt(sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2))


def snapshot_key(name: str) -> str:
    """Sortable YYYYMMDD from an archive filename.

    The directory is not uniformly named: most files are `2026.07.31_labs.json`, one is
    `2023.03.31 labs.json` with a space, and two are `20260630_0928_labs.json`. Anything globbing it
    has to expect all three, so this takes the first eight digits and ignores how they were separated.
    A name with fewer than eight digits sorts first and is therefore never chosen as "newest".
    """
    digits = re.sub(r"\D", "", name)[:8]
    return digits if len(digits) == 8 else ""


def nearest(labs: list[dict], lat: float, lon: float, radius_km: float) -> list[tuple[dict, float]]:
    """Active labs with coordinates inside the radius, nearest first, each with its distance.

    Pure, so the filtering is testable without a network or a database — which matters because this
    is the part that decides what a person is told, and "the nearest lab" being wrong is worse than
    it being absent.
    """
    out = []
    for lab in labs:
        if (lab.get("activity_status") or "").strip() != "active":
            continue
        la, lo = lab.get("latitude"), lab.get("longitude")
        if la is None or lo is None:
            continue
        try:
            d = km(lat, lon, float(la), float(lo))
        except (TypeError, ValueError):
            continue
        if d <= radius_km:
            out.append((lab, d))
    out.sort(key=lambda p: p[1])
    return out


def skipped_without_coordinates(labs: list[dict]) -> int:
    """Active labs the radius filter can never see. 179 of them network-wide on 2026-09-20: real
    labs in a real city that published no point. Counted so `planetai doctor` can say so rather than
    letting them vanish into a smaller number."""
    return sum(1 for lab in labs
               if (lab.get("activity_status") or "").strip() == "active"
               and (lab.get("latitude") is None or lab.get("longitude") is None))


def _archive_snapshot(hc) -> tuple[str, list[dict]]:
    """(filename, labs) from the Fab Foundation's archive. MAKE_SNAPSHOT pins it; blank takes the
    newest, which is a floating pin and says so in the log."""
    pinned = os.getenv("MAKE_SNAPSHOT", "").strip()
    if not pinned:
        r = hc.get(ARCHIVE_TREE, timeout=30)
        r.raise_for_status()
        names = [e["name"] for e in r.json() if e.get("type") == "blob" and snapshot_key(e["name"])]
        if not names:
            raise RuntimeError("the labs.json archive listed no dated snapshots")
        pinned = max(names, key=snapshot_key)
        log.info("make: MAKE_SNAPSHOT is blank, taking the newest (%s). Pin it to freeze this.", pinned)
    from urllib.parse import quote
    url = ARCHIVE_FILE.format(path=quote(f"archive/labs.json/{pinned}", safe=""))
    r = hc.get(url, timeout=120)
    r.raise_for_status()
    return pinned, r.json()


def _live(hc) -> tuple[str, list[dict]]:
    r = hc.get(LIVE_URL, timeout=120)
    r.raise_for_status()
    return "live", r.json()


def _last_fetch(con) -> datetime | None:
    with con.cursor() as cur:
        cur.execute("SELECT max((meta->>'fetched')::timestamptz) FROM sensors "
                    "WHERE kind = 'facility' AND source = %s", (SOURCE,))
        row = cur.fetchone()
    return row[0] if row else None


def fetch(hc):
    lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
    radius = float(os.getenv("MAKE_RADIUS_KM", "50"))
    days = int(os.getenv("MAKE_REFRESH_DAYS", "30"))

    # One read is ~5.3 MB and there is no way to ask the publisher for less — every query parameter
    # is ignored and the whole directory comes back. So the staleness check happens before the fetch,
    # not after it, and a node that already has its labs does nothing at all.
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        last = _last_fetch(con)
    if last is not None and last > datetime.now(timezone.utc) - timedelta(days=days):
        return [], []

    source = os.getenv("MAKE_SOURCE", "archive").strip().lower()
    which, labs = _live(hc) if source == "live" else _archive_snapshot(hc)
    if not isinstance(labs, list):
        raise RuntimeError(f"{which}: expected a JSON list of labs, got {type(labs).__name__}")

    found = nearest(labs, lat, lon, radius)
    no_coords = skipped_without_coordinates(labs)
    now = datetime.now(timezone.utc).isoformat()
    log.info("make: %d active labs within %.0f km of the node, from %s (%d active labs network-wide "
             "publish no coordinates and cannot be placed)", len(found), radius, which, no_coords)

    sensors = []
    for lab, dist in found:
        slug = (lab.get("slug") or "").strip() or f"id{lab.get('id')}"
        caps = lab.get("capabilities") or []
        sensors.append({
            "sensor_id": f"lab-{slug}",
            "source": SOURCE,
            "name": (lab.get("name") or slug).strip(),
            "lat": float(lab["latitude"]), "lon": float(lab["longitude"]),
            "indoor": False,
            # Never local. A fab lab is somebody else's building, at any distance, and `custody` is
            # generated from `local`, so this is also what keeps a facility out of every Index cell.
            "local": False,
            "kind": "facility", "scale": "community", "cadence": "P30D",
            "meta": {
                "slug": slug,
                "capabilities": caps,
                "kind_name": lab.get("kind_name"),
                "city": lab.get("city"), "country_code": lab.get("country_code"),
                "distance_km": round(dist, 1),
                "url": f"https://www.fablabs.io/labs/{slug}",
                "registry_slug": "economic/community/fablabs-io",
                "snapshot": which,
                "fetched": now,
                # Contact details are in the payload on most records and are deliberately not here.
                "attribution": "fablabs.io — Fab Lab Network. Not openly licensed; see registry_slug.",
            },
        })
    return sensors, []


def ask_line(rows: list[dict], locale: str = "en") -> str | None:
    """One sentence for the report and the ask vocabulary, or None when there is nothing to say.

    Takes `sensors` rows as stored, so the report does not re-derive distance and cannot disagree
    with what the database holds. The machine names are translated because everything else the node
    says to a person is — a Spanish report that ends in "laser cutting" reads like a leak.
    """
    if not rows:
        return None
    words = CAPABILITY_WORDS.get((locale or "en").split("-")[0], CAPABILITY_WORDS["en"])
    best = min(rows, key=lambda r: (r.get("meta") or {}).get("distance_km", 1e9))
    m = best.get("meta") or {}
    caps = [words.get(c, c) for c in (m.get("capabilities") or [])]
    what = ", ".join(caps[:3]) if caps else None
    where = f"{best.get('name')}, {m.get('distance_km')} km"
    return f"{where} ({what})" if what else where
