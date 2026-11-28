"""The keeper's statement of where this place's water comes from, parsed into one entry per source."""
from __future__ import annotations

import re
import unicodedata

KINDS = ("piped", "truck", "well", "spring", "rain", "bottled")
HOLDS = ("steady", "fails at times", "fails often")


def slug(name: str) -> str:
    folded = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def _origin(text: str):
    """A point, a name, None for blank, or False when it looks like a point but is out of range."""
    if not text:
        return None
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", text)
    if not m:
        return {"how": "name", "name": text}
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return {"how": "point", "lat": lat, "lon": lon}


def parse_sources(text: str) -> list[dict]:
    """`name | kind | holds | origin`, entries separated by `;`. A bad entry is kept with its problem, never dropped."""
    out: list[dict] = []
    seen: set[str] = set()
    for raw in (text or "").split(";"):
        if not raw.strip():
            continue
        parts = [p.strip() for p in raw.split("|")]
        e = {"entry": raw.strip(), "id": "", "name": "", "kind": "", "holds": None, "origin": None, "problem": None}
        if len(parts) != 4:
            e["problem"] = "fields"
        else:
            name, kind, holds, origin = parts
            e.update(name=name, kind=kind, id=slug(name))
            o = _origin(origin)
            if not e["id"]:
                e["problem"] = "name"
            elif kind not in KINDS:
                e["problem"] = "kind"
            elif holds and holds not in HOLDS:
                e["problem"] = "holds"
            elif o is False:
                e["problem"] = "origin"
            elif e["id"] in seen:
                e["problem"] = "duplicate"
            else:
                e["holds"], e["origin"] = holds or None, o
            if e["id"]:
                seen.add(e["id"])
        out.append(e)
    return out
