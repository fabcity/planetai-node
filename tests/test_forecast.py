"""The forecast pack, against BMKG's and Open-Meteo's real answers for node #1's point on 7 September 2026.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_forecast.py
The fixtures are the payloads as they came back, saved whole. What is checked is what fails silently: a village
code for the wrong village, a unit that changed under us, and a forecast with no issue time — which cannot be
told from a fresh one afterwards.
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packs", "forecast"))
import adapter as A  # noqa: E402

LAT, LON = -8.8271, 115.15709
ADM4 = "51.03.05.2002"


def fixture(n):
    with open(os.path.join(ROOT, "tests/data", n)) as f:
        return json.load(f)


class R:
    def __init__(s, j): s.j = j
    def raise_for_status(s): pass
    def json(s): return s.j


class HC:
    def __init__(s, j): s.j = j
    def get(s, url, params=None, headers=None, timeout=None): return R(s.j)


# ---- the point. A Permendagri code is six digits of opaque; the only check that means anything is where BMKG
# says it is. 51.03.05.2002 is Ungasan, Kuta Selatan, Badung — 0.19 km from node #1.
bm = fixture("bmkg_ungasan_2026-09-07.json")
loc = bm["lokasi"]
assert (loc["kotkab"], loc["kecamatan"], loc["desa"]) == ("Badung", "Kuta Selatan", "Ungasan"), loc
km = A._km(LAT, LON, loc["lat"], loc["lon"])
assert km < 0.5, f"the forecast point must be this node's, not another village: {km:.2f} km"

sensors, readings = A.bmkg(HC(bm), ADM4, LAT, LON)
assert len(sensors) == 1 and sensors[0]["sensor_id"] == "forecast-bmkg"
assert sensors[0]["kind"] == "model" and sensors[0]["local"] is False, "a forecast is never a measurement here"
assert sensors[0]["meta"]["km_from_node"] < 0.5
assert sensors[0]["scale"] == "community", "this pack describes an address, not a region"

# ---- the issue time, stored per value. A forecast that has stopped refreshing reads exactly like a current one.
issued = A._utc(bm["data"][0]["cuaca"][0][0]["analysis_date"])
assert issued is not None and sensors[0]["meta"]["issued"] == issued.isoformat()
lead = {v for _ts, _s, m, v in readings if m == "fc_lead_hours"}
assert lead and all(l >= 0 for l in lead), "every value says how far ahead of its own forecast it is"

# ---- units as BMKG documents them, carried through unchanged. ws is km/h, wd_deg is degrees the wind comes FROM.
step = bm["data"][0]["cuaca"][0][0]
got = {(ts, m): v for ts, _s, m, v in readings}
ts0 = A._utc(step["utc_datetime"])
for key, metric in (("t", "fc_temp"), ("hu", "fc_humidity"), ("ws", "fc_wind_speed"),
                    ("wd_deg", "fc_wind_direction"), ("tcc", "fc_cloud"), ("tp", "fc_rain")):
    if step.get(key) is not None and (ts0, metric) in got:
        assert got[(ts0, metric)] == float(step[key]), f"{metric} was changed on the way in"

# ---- Open-Meteo. Its wind is km/h by default, which is what makes the gap channel subtractable from BMKG's.
om = fixture("openmeteo_ungasan_2026-09-07.json")
assert om["hourly_units"]["wind_speed_10m"] == "km/h", \
    "BMKG publishes km/h; if Open-Meteo ever changes default units the gap channel silently compares apples to pears"
PT = {"sid": "forecast-om", "cell": None, "lat": LAT, "lon": LON}
osens, oread = A.openmeteo(HC(om), [PT])
assert osens[0]["sensor_id"] == "forecast-om" and osens[0]["kind"] == "model"
# Open-Meteo has no model run time. Recording a fetch time as an issue time would be inventing provenance.
assert osens[0]["meta"]["issued"] is None and osens[0]["meta"]["fetched"], \
    "no issue time is published, so none is claimed"

# ---- the gap channel, only where both sources speak for the same hour
sg, gr = A.gap(readings, oread)
if gr:
    assert sg[0]["sensor_id"] == "forecast-gap"
    assert {m for _ts, _s, m, _v in gr} <= {"fc_temp_gap", "fc_wind_speed_gap"}
    assert all(v >= 0 for _ts, _s, _m, v in gr), "a gap is a distance, never signed toward one source"
assert A.gap(readings, []) == ([], []), "one source alone has nothing to disagree with"

# ---- the horizon. The card and the report want a day; the sources offer three.
horizon = max(ts for ts, _s, _m, _v in readings) if readings else None
if horizon:
    assert horizon <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=A.HOURS + 3), \
        "the pack stores the next day, not everything BMKG will say"

# ---- this pack never speaks. Three wrong warnings reached node #1's Telegram on 7 September; a forecast pack
# that starts talking is the next batch.
import yaml  # noqa: E402
rules = yaml.safe_load(open(os.path.join(ROOT, "packs/forecast/rules.yml")))
assert rules and all(r.get("contributes") == "report" for r in rules), "no rule here may have a level"
assert all("message" not in r for r in rules), "no rule here may have a message"
assert not os.path.exists(os.path.join(ROOT, "packs/forecast/cells.yml")), \
    "a forecast is not measured here and is nobody's Index cell"

# ---- the wind field the map draws moving: 64 points in ONE request, answered in the order asked, south to north and
# west to east, so the page reads row j, column i without working out where a point is.
wg = fixture("openmeteo_wind_grid_ungasan_2026-10-07.json")
lats, lons = A.wind_grid(LAT, LON)
assert len(lats) == len(lons) == 8 and lats == sorted(lats) and lons == sorted(lons), "south to north, west to east"
assert abs(lats[-1] - lats[0] - 60 / 110.574) < 1e-3, "the square is 2 x FORECAST_WIND_KM tall"
assert len(wg) == 65 and all(abs(p["latitude"] - lats[k // 8]) < .06 and abs(p["longitude"] - lons[k % 8]) < .06 for k, p in enumerate(wg[:64])), \
    "Open-Meteo answers in the order asked, within one model cell (cell_selection=nearest, never a land cell 12 km off)"
assert wg[0]["hourly_units"]["wind_speed_10m"] == "km/h", "the field is km/h, as the point forecast stores it"
_real_now = A.datetime
class _At(dt.datetime):
    @classmethod
    def now(cls, tz=None): return dt.datetime(2026, 10, 7, 6, 50, tzinfo=dt.timezone.utc)
A.datetime = _At
wf = A.wind_field(HC(wg), LAT, LON)
A.datetime = _real_now
assert wf["n"] == 8 and len(wf["times"]) == len(wf["speed_kmh"]) == len(wf["from_deg"]) and 24 <= len(wf["times"]) <= 26, len(wf["times"])
assert len(wf["speed_kmh"][0]) == 8 and len(wf["speed_kmh"][0][0]) == 8, "time, then row (south to north), then column"
k = wg[3 * 8 + 5]["hourly"]["time"].index(wf["times"][0][:-1])
assert wf["speed_kmh"][0][3][5] == wg[3 * 8 + 5]["hourly"]["wind_speed_10m"][k], "row 3, column 5 is point 29"
assert len(wf["at_node"]["speed_kmh"]) == len(wf["times"]) and wf["at_node"]["speed_kmh"][0] == wg[64]["hourly"]["wind_speed_10m"][k], \
    "the readout is the node's own point, asked as the 65th, not a value picked off the grid"
try:
    A.wind_field(HC(wg[:10]), LAT, LON); raise AssertionError("a short answer must be refused")
except ValueError:
    pass

# ---- 72 hours, and the five variables a day needs. A synthetic answer built from now, so the cut is where we say it is.
def om_payload(extra=(), hours=100):
    """An Open-Meteo hourly answer: every OM_HOURLY key, value = the hour's index, starting two hours ago."""
    t0 = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=2)
    keys = A.OM_HOURLY.split(",") + list(extra)
    h = {"time": [(t0 + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]}
    h.update({k: [float(i) for i in range(hours)] for k in keys})
    return {"latitude": LAT, "longitude": LON, "hourly": h}


assert A.HOURS == 72
_, rows = A.openmeteo(HC(om_payload()), [PT])
now = dt.datetime.now(dt.timezone.utc)
assert rows and max(ts for ts, *_ in rows) <= now + dt.timedelta(hours=72), "nothing past 72 hours is kept"
assert max(ts for ts, *_ in rows) > now + dt.timedelta(hours=70), "and the 72 hours are kept, not 24"
assert min(ts for ts, *_ in rows) >= now - dt.timedelta(hours=1), "the past is not kept"
NEW5 = {"wind_gusts_10m": "fc_wind_gusts", "precipitation_probability": "fc_rain_prob", "shortwave_radiation": "fc_shortwave",
        "et0_fao_evapotranspiration": "fc_et0", "soil_moisture_0_to_1cm": "fc_soil_moisture"}
for k, m in NEW5.items():
    assert k in A.OM_HOURLY.split(",") and A.OM_MAP[k] == m, (k, m)
assert {m for _ts, _s, m, _v in rows} >= set(NEW5.values()) | {"fc_lead_hours"}
# a multi-point answer is a list, and every point gets its own sensor, its cell in its meta
pts = [PT, {"sid": "forecast-om-8a1", "cell": "8a1", "lat": LAT + .1, "lon": LON}]
ss, rr = A.openmeteo(HC([om_payload(), om_payload()]), pts)
assert [x["sensor_id"] for x in ss] == ["forecast-om", "forecast-om-8a1"] and ss[1]["meta"]["cell"] == "8a1"
assert {s for _ts, s, *_ in rr} == {"forecast-om", "forecast-om-8a1"}
try:
    A.openmeteo(HC([om_payload()]), pts); raise AssertionError("a short answer must be refused")
except ValueError:
    pass
import yaml  # noqa: E402,F811
ch = {(c["source"], c["metric"]): c for c in yaml.safe_load(open(os.path.join(ROOT, "packs/forecast/channels.yml")))}
pk = yaml.safe_load(open(os.path.join(ROOT, "packs/forecast/pack.yaml")))
for m, u in (("fc_wind_gusts", "km/h"), ("fc_rain_prob", "%"), ("fc_shortwave", "W/m²"), ("fc_et0", "mm"), ("fc_soil_moisture", "m³/m³")):
    c = ch[("forecast-om", m)]
    assert c["role"] == "derived" and c["comparable"] is False and c["unit"] == u, (m, c)
    assert m in pk["metrics"], f"{m} is declared in pack.yaml"

# ---- the cadence. The pack runs in the core 300 s loop; FORECAST_POLL_HOURS is how often it may ask, and a restart
# or a failed fetch must not ask again sooner. 13 Oct: asking every poll spent Open-Meteo's daily limit by 06:15 UTC.
# Each source has its own stamp, out/forecast.<source>.last, so one that is refused does not hold the others.
import tempfile  # noqa: E402
os.environ["PACK_OUT"] = tempfile.mkdtemp()
calls = []
class Count:
    def get(s, url, params=None, headers=None, timeout=None): calls.append(url); raise RuntimeError("429")
os.environ.update(FORECAST_OPENMETEO="1", FORECAST_BMKG="0", NODE_LAT=str(LAT), NODE_LON=str(LON), FORECAST_POLL_HOURS="6")
A.fetch(Count()); first = len(calls)
assert first == 1, f"a refused point is asked once and the field is not tried behind it: {calls}"
A.fetch(Count()); A.fetch(Count())
assert len(calls) == first, "a second poll inside the retry wait asks nothing, even after a failure"
A.fetch(Count(), force=True)
assert len(calls) == 2 * first, "`planetai run forecast fetch` asks now"
stamp = lambda src: os.path.join(os.environ["PACK_OUT"], f"forecast.{src}.last")  # noqa: E731
assert not os.path.exists(os.path.join(os.environ["PACK_OUT"], "forecast.last")), "one stamp a source, not one for the pack"
os.utime(stamp("om"), (0, 0))
A.fetch(Count())
assert len(calls) == 3 * first, "once the hours have passed, it asks again"


def aged(src, minutes):
    """Move a stamp `minutes` further into the past and say whether the source is due."""
    m = os.stat(stamp(src)).st_mtime - minutes * 60
    os.utime(stamp(src), (m, m))
    return A._due(src)


# a failure makes the source due again in 30 minutes: not on the next 300 s poll, and not after six hours
assert A.RETRY_S == 1800
A._stamp("om", ok=False)
assert not A._due("om") and not aged("om", 25), "a refused source is not asked again on the next poll or two"
assert aged("om", 10), "...but it is asked again after half an hour"
# a success is the full wait
A._stamp("om")
assert not aged("om", 31) and not aged("om", 300) and aged("om", 60), "a source that answered waits FORECAST_POLL_HOURS"
assert A._due("om", force=True) and A._due("never-stamped"), "force asks, and a source never asked is due"
os.environ["FORECAST_POLL_HOURS"] = "0.1"            # a poll shorter than the retry: the retry never waits longer than the poll
A._stamp("om", ok=False)
assert aged("om", 7), "the retry wait is never longer than FORECAST_POLL_HOURS"
os.environ["FORECAST_POLL_HOURS"] = "6"


class Route:
    """A fake hc that answers by URL, records what it was asked, and fails the URLs in `down`."""
    def __init__(s, down=()): s.down, s.asked = set(down), []
    def get(s, url, params=None, headers=None, timeout=None):
        s.asked.append(url)
        if url in s.down:
            raise RuntimeError("429")
        return R({A.BMKG: bm, A.OPEN_METEO: om_payload()}[url])


def fresh(**env):
    os.environ["PACK_OUT"] = tempfile.mkdtemp()
    os.environ.update({"FORECAST_BMKG": "0", "FORECAST_OPENMETEO": "1", "FORECAST_BMKG_ADM4": ADM4}); os.environ.update(env)
    A.write_wind_field = lambda *a: None                  # the field is one more call on the om stamp; counted above


# one source refused: the others still fetch and store, and only the refused one waits 30 minutes
fresh(FORECAST_BMKG="1")
hc = Route(down=[A.OPEN_METEO]); sens, rd = A.fetch(hc)
assert {s["sensor_id"] for s in sens} == {"forecast-bmkg"}, "BMKG answered and is stored"
assert not A._due("bmkg") and not A._due("om")
assert aged("om", 31) and not aged("bmkg", 31), "the refused one retries in 30 minutes, the other in six hours"
# two due sources make exactly two calls, a source that is not due makes none
fresh(FORECAST_BMKG="1")
hc = Route(); A.fetch(hc)
assert sorted(hc.asked) == sorted([A.BMKG, A.OPEN_METEO]), f"bmkg and om are due: {hc.asked}"
hc = Route(); A.fetch(hc)
assert hc.asked == [], "neither is due now"
os.utime(stamp("om"), (0, 0))
hc = Route(); A.fetch(hc)
assert hc.asked == [A.OPEN_METEO], f"only om is due again: {hc.asked}"
# the point answers and the field is refused: the points are stored, and om is asked again in 30 minutes
fresh(FORECAST_BMKG="0")
def _no_field(*a): raise RuntimeError("429")
A.write_wind_field = _no_field
sens, rd = A.fetch(Route())
assert [s["sensor_id"] for s in sens] == ["forecast-om"] and rd, "the point forecast is kept"
assert not A._due("om") and aged("om", 31), "and the field is asked again in half an hour, not six hours"
# Open-Meteo off (the default) asks it nothing, BMKG still answers
fresh(FORECAST_BMKG="1"); os.environ.pop("FORECAST_OPENMETEO")
hc = Route(); sens, rd = A.fetch(hc)
assert hc.asked == [A.BMKG] and [s["sensor_id"] for s in sens] == ["forecast-bmkg"], hc.asked

print(f"test_forecast: ok — {loc['desa']}, {km*1000:.0f} m from the node, issued {issued:%d %b %H:%M} UTC, "
      f"{len(readings)} readings, {len(gr)} gap values, and not one thing it can say out loud")
