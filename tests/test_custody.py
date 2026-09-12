"""The custody gate: a peer across the street reaches no cell, however local it looks.

THIS SUITE FAILS ON `main` BY DESIGN. It is the gate for docs/SPEC_custody.md, written against the tree as it
stands so that it says whether the spec landed rather than restating it. Two assertions fail today:

    _buckets   192 -> 204        a kind='peer' row with local=TRUE is counted as this node's own data
    heat cell    0.0 -> 4.0      packs/heat/cells.yml reads s.local with no kind filter

`local` was written on 2 September 2026 for a node that was a house (74a8b64). `kind` arrived the next day
with the child push (15785db), and nothing reconciled them. `local` still means "ours AND here"
(app/sources.py::stamp_local) — custody is `local OR kind='child'`, and a peer is neither. See §1 and §2.

Method: build the same node twice, once with one extra peer row, and assert every number comes out identical.
Comparing two databases rather than naming packs means a pack written next year that reads a peer breaks this
without anyone remembering the spec. Nothing here asserts HOW custody is expressed, so the implementation is
free to choose the generated column, the CHECK, or the two-clause predicate.

Not in tests/all yet — the runner asserts a suite count and fails on undeclared skips, so adding a failing
suite would turn CI red for everyone. docs/SPEC_custody.md §9 has the six steps that wire it in.

    bash -c 'PYTHONPATH=app python3 tests/test_custody.py'
    pip install duckdb          # dev only, same dependency as test_nearby and test_shipped
"""
from __future__ import annotations

import datetime as dt
import glob
import inspect
import math
import os
import re
import sys

if os.getenv("CI") == "1":
    print("  - custody gate skipped under CI=1 (fails until docs/SPEC_custody.md is implemented)")
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import duckdb
    import yaml
except ImportError:
    print("  - custody gate skipped (pip install duckdb pyyaml)")
    sys.exit(0)

import trustdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = trustdb.FIXTURE_NOW          # 7 Sep 2026 13:14:22 UTC, the last reading in the node #1 dump

# A stranger's node 40 m away: inside LOCAL_RADIUS_M (500 m), indoors, reporting three metrics right now, and
# written local=TRUE the way a hand-edited row or a restore from somebody else's dump would write it.
PEER = ("peer-1", "baliairdispatch", "Neighbour's node", -8.82744, 115.15741, True, True, "peer")


def _schema() -> str:
    """init.sql with line comments stripped — one of them ends in a semicolon (see trustdb._schema)."""
    sql = open(os.path.join(ROOT, "init.sql")).read()
    return "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())


def _ddl() -> str:
    """Three tables and the two views a cell can read. `observations` is here because several packs read it;
    it returns nothing under these fixtures, which is still an assertion worth making on both sides."""
    sql, out = _schema(), []
    for t in ("sensors", "readings", "channel_roles"):
        out.append(re.search(rf"CREATE TABLE IF NOT EXISTS {t} \(.*?\n\);", sql, re.S).group(0).replace("JSONB", "JSON"))
    out.append(re.search(r"CREATE VIEW readings_1h AS.*?;", sql, re.S).group(0))
    # DuckDB merges a USING column, so the view's own r.sensor_id will not bind. An explicit ON is the same join.
    out.append(re.search(r"CREATE VIEW observations AS.*?;", sql, re.S).group(0)
               .replace("JOIN sensors s USING (sensor_id)", "JOIN sensors s ON s.sensor_id = r.sensor_id"))
    return "\n".join(out)


def _pg(sql: str) -> str:
    """Postgres as shipped -> what DuckDB can run at a fixed instant. now() and the session TimeZone only."""
    return (sql.replace("now()", f"TIMESTAMPTZ '{NOW.isoformat()}'")
               .replace("current_setting('TimeZone')", "'UTC'")
               .replace("JOIN sensors s USING (sensor_id)", "JOIN sensors s ON s.sensor_id = r.sensor_id"))


def node(with_peer: bool):
    """Node #1's five real kits and its real last 24 hours, optionally plus one peer."""
    con = duckdb.connect()
    con.execute(_ddl())
    who, rows = trustdb.sensors(), trustdb.day(trustdb.readings())
    if with_peer:
        who = who + [PEER]
        rows = rows + [(NOW - dt.timedelta(minutes=m), "peer-1", metric, value)
                       for m in range(0, 180, 10)
                       for metric, value in (("pm25", 99.0), ("temp", 34.0), ("humidity", 80.0))]
    con.executemany("INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind) VALUES (?,?,?,?,?,?,?,?)", who)
    seen = set()
    con.executemany("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (?,?,?,?)",
                    [r for r in rows if not (r[:3] in seen or seen.add(r[:3]))])
    return con


def one(con, sql):
    row = con.execute(_pg(sql)).fetchone()
    return row[0] if row else None


clean, peered = node(False), node(True)
failures = []

# ---- 1. the core's honesty check, read OUT OF app/index.py rather than pasted here. A copy of the SQL in this
# file would fail forever: the implementation would change and the gate would keep testing the old string.
def buckets_sql() -> str:
    import index
    src = inspect.getsource(index._buckets)
    m = re.search(r'cur\.execute\(\s*"""(.*?)"""', src, re.S)
    assert m, "app/index.py::_buckets no longer runs one triple-quoted statement — update this extractor"
    return m.group(1)


BUCKETS = buckets_sql()
a, b = one(clean, BUCKETS), one(peered, BUCKETS)
if a != b:
    failures.append(f"_buckets counts the peer: {a} -> {b}. A node that measures nothing new would be able to "
                    f"claim `live` off a stranger's sensor (app/index.py:52).")

# ---- 2. no pack cell may see it. Every cells.yml in the tree, both databases, same answer.
# Tolerance, not equality: air-quality's first cell filters kind='sensor' and is already correct, but its sum
# reassociates when a row it excludes is present, moving the 15th decimal. An exact test would cry wolf there.
for f in sorted(glob.glob(os.path.join(ROOT, "packs/*/cells.yml"))):
    pack = os.path.basename(os.path.dirname(f))
    for i, c in enumerate(yaml.safe_load(open(f)) or []):
        try:
            va, vb = one(clean, c["sql"]), one(peered, c["sql"])
        except Exception as e:  # noqa: BLE001
            failures.append(f"{pack}/cells.yml #{i} ({c['cell']}) would not run: {str(e).splitlines()[0]}")
            continue
        same = (va is None and vb is None) or (
            va is not None and vb is not None and math.isclose(float(va), float(vb), rel_tol=1e-9, abs_tol=1e-12))
        if not same:
            failures.append(f"{pack}/cells.yml #{i} ({c['cell']}) counts the peer: {va} -> {vb}. "
                            f"A neighbour's air is in this node's Index cell.")

# ---- 3. and the fix must not be "exclude everything": node #1's own five kits still count.
if a in (0, None):
    failures.append(f"node #1's own kits stopped counting: _buckets = {a} on a database holding five local kits")

print(f"custody: {'FAILED' if failures else 'ok'} — {len(failures)} leak(s); "
      f"_buckets {a} clean / {b} with one peer")
for msg in failures:
    print(f"    ✗ {msg}")
assert not failures, (
    "a kind='peer' row with local=TRUE reaches this node's numbers. This is the gate for "
    "docs/SPEC_custody.md and it is expected to fail until §2 and §4 are implemented.")
print("    a peer across the street reaches no cell, and node #1's own kits still do")
