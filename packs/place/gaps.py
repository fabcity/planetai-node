"""What is unmapped around this node: a briefing for a mapping afternoon.  planetai run place gaps

Compares the satellite's buildings with OpenStreetMap's, lists the categories with nothing on the map, the buildings
with no type, the named places with no opening hours, the roads with no name. Prints it and writes out/place-gaps.md.
Fix the map with StreetComplete, Every Door or iD at openstreetmap.org; never from Google imagery or Google Maps.
"""
import os
import psycopg

lat, lon = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
radius = int(os.getenv("PLACE_RADIUS_M", "1000"))
node = os.getenv("NODE_NAME", "node")
out_dir = os.getenv("PACK_OUT", "/app/out")

with psycopg.connect(os.environ["DATABASE_URL"]) as con, con.cursor() as cur:
    cur.execute("SELECT to_regclass('place_features') IS NOT NULL")
    if not cur.fetchone()[0]:
        raise SystemExit("no place data yet: enable the place pack and let it poll once (or: planetai run place refresh)")
    cur.execute("SELECT count(*) FROM place_features WHERE kind='building'"); osm_b = cur.fetchone()[0]
    cur.execute("SELECT to_regclass('place_buildings_sat') IS NOT NULL"); has_sat = cur.fetchone()[0]
    sat_b, sat_conf = 0, 0.0
    if has_sat:
        cur.execute("SELECT count(*), coalesce(avg(confidence),0) FROM place_buildings_sat WHERE source='open_buildings_v3'"); sat_b, sat_conf = cur.fetchone()
    # satellite buildings with no OSM building within 3 m: the ones to draw
    unmapped = 0
    if sat_b:
        cur.execute("""SELECT count(*) FROM place_buildings_sat s WHERE source='open_buildings_v3' AND NOT EXISTS (
                         SELECT 1 FROM place_features f WHERE f.kind='building' AND ST_DWithin(f.geom::geography, s.geom::geography, 3))""")
        unmapped = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM place_features WHERE kind='building' AND coalesce(tags->>'building','yes')='yes'"); untyped = cur.fetchone()[0]
    cur.execute("SELECT category, count(*) FROM place_features WHERE kind='poi' GROUP BY category"); by_cat = dict(cur.fetchall())
    cur.execute("SELECT count(*) FROM place_features WHERE kind='poi' AND name IS NOT NULL AND NOT (tags ? 'opening_hours')"); no_hours = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM place_features WHERE kind='poi' AND name IS NULL"); unnamed_poi = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM place_features WHERE kind='road' AND name IS NULL AND tags->>'highway' IN ('residential','tertiary','secondary','primary','unclassified')"); unnamed_roads = cur.fetchone()[0]
    cur.execute("SELECT name FROM place_features WHERE kind='poi' AND name IS NOT NULL AND NOT (tags ? 'opening_hours') ORDER BY name LIMIT 15"); sample = [r[0] for r in cur.fetchall()]

expected = ["food", "market", "retail", "education", "health", "worship", "services", "lodging"]
zero = [c for c in expected if not by_cat.get(c)]
lines = [f"# What is unmapped around {node}", "", f"Within {radius} m of {lat:.4f}, {lon:.4f}. OpenStreetMap against Google Open Buildings.", ""]
if sat_b:
    lines += [f"- **Buildings.** The satellite sees about **{sat_b:,}** (confidence ≥ 0.65, mean {sat_conf:.2f}); the map has **{osm_b:,}**. "
              f"About **{unmapped:,}** satellite footprints have no building drawn within 3 m: those are the ones to trace."]
else:
    lines += [f"- **Buildings.** The map has **{osm_b:,}**. No satellite footprints yet (Earth Engine not configured, or the monthly fetch has not run)."]
lines += [f"- **Building types.** {untyped:,} of the mapped buildings are just `building=yes`. Which are houses, which are villas, shops, warungs, temples: a walk decides.",
          f"- **Nothing on the map at all:** {', '.join(zero) if zero else 'every category has at least one entry'}. A zero here is almost always the map, not the place.",
          f"- **Places without opening hours:** {no_hours}. Unnamed places: {unnamed_poi}. Unnamed streets that should have names: {unnamed_roads}.", ""]
if sample:
    lines += ["Named places with no opening hours, to ask about:", ""] + [f"- {s}" for s in sample] + [""]
lines += ["## How", "", "StreetComplete (Android) asks the questions above as you walk. Every Door (iOS/Android) adds and fixes places. iD at openstreetmap.org "
          "traces buildings over Bing or Esri imagery. Never from Google Maps or Google imagery: its licence poisons the map. "
          "Edits reach this node within minutes: `planetai run place refresh`.", ""]
text = "\n".join(lines)
print(text)
os.makedirs(out_dir, exist_ok=True)
open(os.path.join(out_dir, "place-gaps.md"), "w").write(text)
print("\nwritten: out/place-gaps.md")
