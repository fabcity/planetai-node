"""ThingData (reuse-city) as a slow source: a repair commons, counted.

A ThingData server holds things, the guides and stories written about them, and the relationships
between all three. It has no count endpoint and no search, so the only honest total is the one you
page to — 100 rows at a time, up to THINGDATA_MAX, and it refuses rather than guess above that.

kind='portal', scale=city (THINGDATA_SCALE): this is a catalogue somebody maintains, never a
measurement of this place, so it lands in `observations` and never in a `live` cell.
Reads only: every endpoint used here is public in v0.1.3, no token, no writes.
Contract: fetch(hc) -> (sensors, readings), like everything in app/sources.py.
"""
import os
from datetime import datetime, timedelta, timezone

PAGE = 100


def _page_all(hc, base, path, cap):
    out, skip = [], 0
    while len(out) < cap:
        r = hc.get(f"{base}/api/v1/{path}", params={"skip": skip, "limit": PAGE})
        r.raise_for_status()
        rows = r.json()
        out += rows
        if len(rows) < PAGE:
            return out
        skip += PAGE
    raise RuntimeError(f"{base} has more than {cap} {path}; raise THINGDATA_MAX to count it")


def _when(row):
    """A row's last touch. ThingData writes naive UTC (datetime.utcnow), so a missing offset is UTC."""
    t = row.get("updated_at") or row.get("created_at")
    if not t:
        return None
    try:
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def fetch(hc):
    instances = dict(p.split("=", 1) for p in os.getenv("THINGDATA_INSTANCES", "").split(",") if "=" in p)
    if not instances:
        return [], []                      # nothing configured: idle, never take the node down
    scale = os.getenv("THINGDATA_SCALE", "city")
    cap = int(os.getenv("THINGDATA_MAX", "5000"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=90)
    sensors, readings = [], []
    for slug, base in instances.items():
        base = base.rstrip("/")
        things = _page_all(hc, base, "things", cap)
        guides = _page_all(hc, base, "guides", cap)
        stories = _page_all(hc, base, "stories", cap)
        rels = _page_all(hc, base, "relationships", cap)

        # A thing is documented when a guide or story names it directly, or a relationship points at it.
        # Category guides ("any laptop") document no particular thing and are deliberately not counted here.
        documented = {g["thing_id"] for g in guides + stories if g.get("thing_id")}
        documented |= {r["target_id"] for r in rels
                       if r.get("target_type") == "thing" and r.get("source_type") in ("guide", "story")}
        documented &= {t["id"] for t in things if t.get("id")}

        knowledge = guides + stories
        dated = [w for w in (_when(k) for k in knowledge) if w]
        fresh = sum(1 for w in dated if w > cutoff)

        sid = f"thingdata-{slug}"
        sensors.append({"sensor_id": sid, "source": "thingdata", "name": f"{slug} (ThingData server)",
                        "lat": None, "lon": None, "indoor": False, "local": False, "kind": "portal",
                        "scale": scale, "cadence": "P1D",
                        "meta": {"server": base, "registry_slug": f"economic/{scale}/{slug}",
                                 "attribution": "ThingData Protocol server (reuse-city)",
                                 "note": "a catalogue of repair knowledge, not a measurement of this place"}})
        readings += [(now, sid, "things_total", float(len(things))),
                     (now, sid, "guides_total", float(len(guides))),
                     (now, sid, "stories_total", float(len(stories))),
                     (now, sid, "things_documented_pct",
                      100.0 * len(documented) / len(things) if things else 0.0),
                     (now, sid, "knowledge_fresh_90d_pct", 100.0 * fresh / len(dated) if dated else 0.0)]
    return sensors, readings
