"""The energy pack's grid lookup, OSM parser, mix and daily series, offline: no network, no database.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_energy.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "packs/energy/tests/fixtures"
sys.path.insert(0, str(ROOT / "packs/energy"))

import grids as G  # noqa: E402
import mix as M  # noqa: E402
import osm as O  # noqa: E402
import ree as R  # noqa: E402

fails: list[str] = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


# ---------------------------------------------------------------- grids and OSM
g = G.load()
# Node #1's point is the centre of its public H3 cell 8895a4c843fffff, never the house.
check(G.grid_for(-8.8161, 115.1635, g)["id"] == "bali", "node #1's cell is on the Bali grid")
check(G.grid_for(39.9493, 4.0500, g)["id"] == "balearic", "mahon1 is on the Balearic grid")
check(G.grid_for(41.39, 2.17, g) is None, "Barcelona is on no grid in grids.yml: no figure, no fallback")
check(G.ring_for(39.9493, 4.0500, G.grid_for(39.9493, 4.0500, g)) == "city", "mahon1 sits in Menorca's city ring")
check(G.ring_for(-8.1975, 114.8536, G.grid_for(-8.8161, 115.1635, g)) == "region",
      "Celukan Bawang sits in Bali's region ring")
check("out tags center;" in O.QUERY.format(s=-8.9, w=114.4, n=-8.0, e=115.7), "QUERY formats s, w, n, e")
check(O.mw("380 MW") == 380.0 and O.mw("100 kW") == 0.1 and O.mw("1,5 MW") == 1.5, "MW units")
check(O.mw("yes") is None and O.mw(None) is None, "no capacity is None, never 0")
bali = O.parse(json.load(open(FIX / "overpass-bali-2026-11-08.json")))
plants = [s for s in bali if s["kind"] == "plant"]
check(len(plants) == 19, f"19 plants in Bali on 8 Nov, got {len(plants)}")
check(any(s["kind"] == "cable_head" and "Gilimanuk" in s["name"] for s in bali), "the Java cable head is a cable_head")
n = O.near(bali, -8.816082625619444, 115.16354382246635)
check(n[0]["name"] == "GIS Pecatu" and abs(n[0]["km"] - 2.4) < 0.1, "nearest is GIS Pecatu, 2.4 km")
big = next(s for s in n if s["kind"] == "plant" and (s["mw"] or 0) >= 100)
check("Pesanggaran" in big["name"] and abs(big["km"] - 12.0) < 0.2, "nearest large plant is Pesanggaran, 12 km")
men = O.parse(json.load(open(FIX / "overpass-menorca-2026-11-08.json")))
check(any(s["fuel"] == "oil" and s["mw"] == 270.0 and s["fossil"] for s in men), "Maó's oil plant, 270 MW, fossil")
check(sum(1 for s in men if s["kind"] == "plant" and s["fuel"] == "solar" and s["mw"] is None and s["fossil"] is False) == 4,
      "Menorca's four solar plants with output=yes stay listed with mw=None")
unk = O.parse({"elements": [{"type": "node", "lat": 0.0, "lon": 0.0,
                             "tags": {"power": "plant", "plant:source": "nuclear"}}]})
gen = O.parse({"elements": [{"type": "node", "lat": 0.0, "lon": 0.0,
                             "tags": {"power": "generator", "generator:source": "wind",
                                      "generator:output:electricity": "2 MW"}}]})
check(gen[0]["kind"] == "generator", "a generator is listed apart, so a plant's MW is never counted twice")
check(unk[0]["fuel"] is None and unk[0]["fossil"] is None, "unlisted fuel has fossil=None")

# ---------------------------------------------------------------- Bali's range (mix.py)
g_syn = {
    "polygon": [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
    "rings": {"city": [[0, 0], [0, 5], [5, 5], [5, 0], [0, 0]]},
    "capacity_factors": {"coal": 0.6, "solar": 0.2},
    "links": [{"rated_mw": 100, "fossil_share": 0.8, "ring": "beyond"}],
    "demand_mw": 400,
}
src = [
    {"kind": "plant", "fuel": "coal", "fossil": True, "mw": 300, "lat": 2, "lon": 2},
    {"kind": "plant", "fuel": "solar", "fossil": False, "mw": 100, "lat": 7, "lon": 7},
    {"kind": "plant", "fuel": "coal", "fossil": True, "mw": None, "lat": 3, "lon": 3},
    {"kind": "generator", "fuel": "solar", "fossil": False, "mw": 500, "lat": 2, "lon": 2},
]
e = M.estimate(src, g_syn)
check(abs(e["island"] - 180 / 200) < 1e-9, "island share is 180 of 200 MW-weighted (generators and null MW excluded)")
check(abs(e["import_max"] - 0.25) < 1e-9, "100 MW cable against 400 MW demand")
check(abs(e["low"] - 0.875) < 1e-9 and abs(e["high"] - 0.9) < 1e-9, "range 87.5–90%")
check(abs(e["mid"] - 0.8875) < 1e-9 and e["method"] == "capacity-factors" and e["kind"] == "estimated",
      "mid, method and kind")
check(abs(sum(e["split"].values()) - 1) < 1e-9, "the ring split sums to one")
g2 = dict(g_syn, demand_mw=None)
e2 = M.estimate(src, g2)
check(e2["import_max"] is None and e2["mid"] is None and e2["split"]["beyond"] is None,
      "an unknown cable rating gives no import share and no midpoint, never a guess")
check(abs(e2["low"] - 0.8) < 1e-9 and abs(e2["high"] - 0.9) < 1e-9,
      "unknown rating: the range runs from the island (90%) to the cable's own share (80%)")
g3 = dict(g_syn, links=[{"rated_mw": 100, "fossil_share": None, "ring": "beyond"}])
check(M.estimate(src, g3)["low"] is None, "a link with no known mix gives no figure")
e_empty = M.estimate([], g_syn)
check(e_empty["low"] is None and e_empty["island"] is None, "no known plants gives None, never 0 or 1")
e_bali = M.estimate(bali, G.grid_for(-8.8161, 115.1635, g))
check(e_bali["low"] is not None and 0.80 < e_bali["low"] < e_bali["high"] <= 1,
      f"node #1 Bali range sanity, got {e_bali['low']}–{e_bali['high']}")

# ---------------------------------------------------------------- Menorca measured (ree.py)
rows = R.parse(json.load(open(FIX / "ree-baleares-2026-05-10.json")))
check(len(rows) == 1 and rows[0][0] == date(2026, 5, 10), "one day is one row")
check(all(0 <= f <= t for _, f, t in rows), "fossil never exceeds total")
check(abs(R.share(rows) - 8612.125 / 11012.72) < 1e-6, "Balearic share on 2026-05-10")
check(R.share([]) is None, "empty rows give None, never 0")
pen_rows = R.parse(json.load(open(FIX / "ree-peninsular-2026-05-10.json")))
check(len(pen_rows) == 1 and abs(R.share(pen_rows) - 193713.6 / 555167.63) < 1e-6, "peninsular share on 2026-05-10")
linked = R.with_link(rows, pen_rows, {date(2026, 5, 10): 1000.0})
check(abs(linked[0][2] - 12012.72) < 1e-6 and abs(linked[0][1] - (8612.125 + 1000.0 * R.share(pen_rows))) < 1e-4,
      "each day's imports count at that day's peninsular share")
neg_doc = {"included": [
    {"attributes": {"type": "No-Renovable", "values": [{"value": 500.0, "datetime": "2026-05-10T00:00:00.000+02:00"}]}},
    {"attributes": {"type": "Renovable", "values": [{"value": 300.0, "datetime": "2026-05-10T00:00:00.000+02:00"}]}},
    {"attributes": {"type": "Almacenamiento", "values": [{"value": -50.0, "datetime": "2026-05-10T00:00:00.000+02:00"}]}},
    {"attributes": {"type": "total", "values": [{"value": 750.0, "datetime": "2026-05-10T00:00:00.000+02:00"}]}},
]}
neg_rows = R.parse(neg_doc)
check(neg_rows == [(date(2026, 5, 10), 450.0, 750.0)], "negative storage consumption is subtracted from fossil")
check(R.months_to_fetch(set(), date(2026, 11, 8))[0] == "2025-12", "the trailing year starts December 2025")
check(R.months_to_fetch({"2025-12", "2026-01"}, date(2026, 11, 8))[0] == "2026-02", "held months are skipped")


class Down:                       # REE down, as on 8 Nov
    def get(self, *a, **k):
        raise RuntimeError("502")


st = {"months": {"2026-10": [0.4, 600.0, 1500.0]}, "last": {"value": 0.4, "as_of": "2026-11-07T23:00Z"}}
out = R.fetch(Down(), st, date(2026, 11, 8))
check(out["stale"] and out["value"] == 0.4, "a failed fetch keeps the last figure and says it is stale, never 0")
check(out["months"] == 1, "headline says how many months it holds until twelve are in")
out_empty = R.fetch(Down(), {}, date(2026, 11, 8))
check(out_empty["stale"] and out_empty["value"] is None and out_empty["months"] == 0,
      "a failed first fetch with no state gives None, never 0")


class StubREE:
    def __init__(self, doc):
        self.doc = doc
        self.calls = []

    def get(self, url, params=None, **kw):
        self.calls.append((url, params))
        doc = self.doc
        return type("Resp", (), {"status_code": 200, "raise_for_status": lambda s: None, "json": lambda s: doc})()


class StubREE3:                   # mix, link, peninsula: a link of 1000 MWh a day in, as REE serves it
    def __init__(self):
        self.calls = []
        self.bal = json.load(open(FIX / "ree-baleares-2026-05-10.json"))
        self.pen = json.load(open(FIX / "ree-peninsular-2026-05-10.json"))

    def get(self, url, params=None, **kw):
        self.calls.append((url, params))
        if url == R.LINK_URL:
            doc = {"included": [{"attributes": {"values": [{"value": 1000.0, "datetime": "2026-05-10T00:00:00.000+02:00"}]}}]}
        else:
            doc = self.pen if params["geo_ids"] == "8741" else self.bal
        return type("Resp", (), {"raise_for_status": lambda s: None, "json": lambda s: doc})()


stub = StubREE3()
st_live: dict = {}
out_live = R.fetch(stub, st_live, date(2026, 11, 8))
check(len(stub.calls) == 9 and out_live["months"] == 3 and not out_live["stale"] and out_live["kind"] == "measured",
      "fetches at most 3 months per call, three requests each, and records a measured share")
check(stub.calls[0][1]["start_date"] == "2026-11-01T00:00" and stub.calls[0][1]["end_date"] == "2026-11-07T23:59",
      "the current month goes first and ends yesterday, so 'yesterday' is never a backfill day or today's part")
check(all(c[1]["time_trunc"] == "day" for c in stub.calls) and {c[1]["geo_ids"] for c in stub.calls} == {"8743", "8741"},
      "day resolution, geo_ids 8743 and 8741 from grids.yml")
check(abs(out_live["value"] - linked[0][1] / linked[0][2]) < 1e-9, "the headline counts the link at the peninsula's share")
check(abs(out_live["beyond"] - 1000.0 / 12012.72) < 1e-9, "beyond is the link's share of supply")
check(R.fetch(StubREE3(), {}, date(2026, 11, 1))["now"] is None, "on the 1st the month has no full day yet: no 'yesterday'")

g_bal = G.grid_for(39.9493, 4.0500, g)
men_plus_mal = men + [{"name": "Alcúdia", "kind": "plant", "fuel": "coal", "fossil": True,
                       "mw": 260.0, "lat": 39.81, "lon": 3.15}]
sp = R.ring_split(men_plus_mal, g_bal, beyond_share=0.2)
check(sp["kind"] == "estimated" and abs(sp["beyond"] - 0.2) < 1e-9 and abs(sp["city"] + sp["region"] + sp["beyond"] - 1.0) < 1e-9,
      "Menorca ring split uses OSM capacity for city vs region and marks the split estimated")

# ── Task 5: adapter.py and issue.yml ─────────────────────────────────────────
import os
import tempfile
import adapter as A
import issues


class StubHC:
    def __init__(self, osm_doc):
        self.osm_doc = osm_doc
        self.ree = StubREE3()

    def post(self, url, data=None, **kw):
        doc = self.osm_doc
        return type("Resp", (), {"status_code": 200, "raise_for_status": lambda s: None, "json": lambda s: doc})()

    def get(self, url, params=None, **kw):
        if "overpass" in url:
            return self.post(url, data=params, **kw)
        return self.ree.get(url, params=params, **kw)


with tempfile.TemporaryDirectory() as tmp:
    os.environ["PACK_OUT"] = tmp
    os.environ["LATITUDE"], os.environ["LONGITUDE"] = "-8.8161", "115.1635"
    s_bali, r_bali = A.fetch(StubHC(json.load(open(FIX / "overpass-bali-2026-11-08.json"))))
    m_bali = {m: v for _, sid, m, v in r_bali if sid == "energy-grid"}
    check(len(s_bali) == 1 and s_bali[0]["sensor_id"] == "energy-grid" and s_bali[0]["kind"] == "model"
          and s_bali[0]["scale"] == "region" and not s_bali[0]["local"],
          "energy-grid sensor is a regional model sensor")
    check("fossil_share_low_pct" in m_bali and "fossil_share_high_pct" in m_bali
          and "fossil_share_pct" not in m_bali and "fossil_share_day_pct" not in m_bali,
          "node #1 returns fossil_share_low_pct and high_pct, with no fossil_share_pct")
    check(80 <= m_bali["fossil_share_low_pct"] <= m_bali["fossil_share_high_pct"] <= 100
          and m_bali["substation_km"] < 5 and 10 <= m_bali["large_plant_km"] <= 15
          and "import_share_max_pct" not in m_bali,
          f"node #1 readings match Bali range and distances, and omit unknown import_share_max_pct: {m_bali}")
    res_bali = A.result()
    cable = next(b for b in res_bali["bar"] if b["hatched"])
    check(cable["share"] is None and cable["note"] == "share not published",
          "the Java cable's segment has no width while its share is unknown, never a guessed one")
    check("lat" not in res_bali and "lon" not in res_bali, "the body served at /energy carries no coordinates")
    check(res_bali.get("grid") == "bali" and res_bali.get("kind") == "estimated"
          and res_bali.get("sources", [{}])[0].get("kind") == "substation",
          "result() writes out/energy/result.json for Bali with nearest substation first")

    os.environ["LATITUDE"], os.environ["LONGITUDE"] = "39.9493", "4.0500"
    s_men, r_men = A.fetch(StubHC(json.load(open(FIX / "overpass-menorca-2026-11-08.json"))))
    m_men = {m: v for _, sid, m, v in r_men if sid == "energy-grid"}
    check("fossil_share_pct" in m_men and "fossil_share_day_pct" in m_men
          and m_men["fossil_share_low_pct"] == m_men["fossil_share_high_pct"] == m_men["fossil_share_pct"]
          and m_men.get("grid_months") == 3.0,
          f"mahon1 returns fossil_share_pct, fossil_share_day_pct, and low == high: {m_men}")

    check(s_men[0]["meta"]["licence"] == "non-commercial" and s_bali[0]["meta"]["licence"] == "open",
          "REE on the Balearic grid is marked non-commercial, so the open export leaves it out; Bali's sources are open")
    os.environ["LATITUDE"], os.environ["LONGITUDE"] = "41.39", "2.17"
    check(A.fetch(StubHC({})) == ([], []), "Barcelona is outside grids.yml and returns ([], [])")

os.environ["PACKS_DIR"] = str(ROOT / "packs")
decl = issues.load()
check("energy" in decl and decl["energy"]["kind"] == "context" and decl["energy"]["line"] is None
      and decl["energy"]["metric"] == "fossil_share_low_pct",
      "issues.load() finds energy with kind == 'context' and line is None")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
    sys.exit(1)
print("  ✓ energy: grids, OSM sources, Bali's range, Menorca's REE mix, adapter and issue")
sys.exit(0)
