"""Place maps on a real database: the two tables, their CHECKs, the cascade and the widened actions stage.

On 4 Nov 2026 the light GIS put place_maps and place_marks in core, with init.sql enabling PostGIS ahead of them.
This holds the schema's own rules where they live, in the database: a mark is a marker, line, area or note, a colour
is 1 to 6, deleting a map takes its drawings with it, and the actions ledger accepts the stage `place`. Needs a
Postgres with init.sql applied, at RHO_PG_URL (CI's lint job starts one, on the PostGIS image); without it the
suite skips.
Run: RHO_PG_URL=postgresql://planetai:x@127.0.0.1:5432/planetai PYTHONPATH=app PACKS_DIR=packs python3 tests/test_maps_pg.py
"""
import os
import sys

url = os.getenv("RHO_PG_URL")
if not url:
    print("  - maps on a real database skipped (set RHO_PG_URL to a Postgres with init.sql applied)")
    sys.exit(0)
import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

con = psycopg.connect(url, row_factory=dict_row)          # one transaction, rolled back: nothing stays
cur = con.cursor()


def table_exists(name):
    cur.execute("SELECT to_regclass(%s) AS t", (name,))
    return cur.fetchone()["t"] is not None


def count(name):
    cur.execute(f"SELECT count(*) AS n FROM {name}")
    return cur.fetchone()["n"]


def raises(sql, *args):
    """True if the statement is refused by a constraint; a savepoint keeps the outer transaction alive."""
    try:
        with con.transaction():
            cur.execute(sql, args)
    except (psycopg.errors.CheckViolation, psycopg.errors.IntegrityError):
        return True
    return False


assert table_exists("place_maps") and table_exists("place_marks"), "init.sql creates both tables"
cur.execute("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
assert cur.fetchone(), "init.sql enabled PostGIS"
print("  both tables exist and PostGIS is on")

cur.execute("INSERT INTO place_maps (name) VALUES ('t') RETURNING id")
mid = cur.fetchone()["id"]
cur.execute("SELECT shared, from_node, remote_id, pushed_at, push_tried_at FROM place_maps WHERE id = %s", (mid,))
row = cur.fetchone()
assert row == {"shared": False, "from_node": None, "remote_id": None, "pushed_at": None, "push_tried_at": None}, row
cur.execute("""INSERT INTO place_marks (map_id, kind, geom) VALUES
  (%s, 'area', ST_GeomFromText('POLYGON((115.167 -8.819,115.168 -8.819,115.168 -8.818,115.167 -8.819))',4326))""", (mid,))
cur.execute("SELECT colour FROM place_marks WHERE map_id = %s", (mid,))
assert cur.fetchone()["colour"] == 1, "colour defaults to 1"
cur.execute("INSERT INTO actions (stage, actor, note, choice) VALUES ('place','t','x','drew')")   # the check allows it
print("  a map, an area on it and a `place` action are accepted")

for bad in ("INSERT INTO place_marks (map_id, kind, geom) VALUES (%s,'circle',ST_Point(0,0,4326))",
            "INSERT INTO place_marks (map_id, kind, geom, colour) VALUES (%s,'marker',ST_Point(0,0,4326),7)",
            "INSERT INTO place_marks (map_id, kind, geom, colour) VALUES (%s,'marker',ST_Point(0,0,4326),0)"):
    assert raises(bad, mid), bad          # kind and colour CHECKs hold
assert raises("INSERT INTO place_marks (map_id, kind, geom) VALUES (999999999,'marker',ST_Point(0,0,4326))"), "a mark needs its map"
assert raises("INSERT INTO actions (stage, actor, note) VALUES ('nonsense','t','x')"), "the old stages still guard the ledger"
for stage in ("acknowledged", "acted", "measured", "settings", "decided", "dismissed"):
    cur.execute("INSERT INTO actions (stage, actor, note) VALUES (%s,'t','x')", (stage,))   # none of them was dropped
print("  kind, colour, the map reference and the action stages hold")

cur.execute("INSERT INTO place_maps (name, from_node, remote_id) VALUES ('a', 'n1', 5)")
assert raises("INSERT INTO place_maps (name, from_node, remote_id) VALUES ('b', 'n1', 5)"), "UNIQUE (from_node, remote_id)"
cur.execute("INSERT INTO place_maps (name) VALUES ('c'), ('d')")            # NULLs are drawn-here maps and never collide
print("  a pulled map is unique per node and remote id; maps drawn here are not")

cur.execute("DELETE FROM place_maps WHERE id = %s", (mid,))
cur.execute("SELECT count(*) AS n FROM place_marks WHERE map_id = %s", (mid,))
assert cur.fetchone()["n"] == 0, "deleting a map takes its drawings"
print("  deleting a map deletes its drawings")

con.rollback()
print("maps: every check passed")
sys.exit(0)
