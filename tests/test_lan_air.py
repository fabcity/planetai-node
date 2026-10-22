"""packs/airgradient and packs/purpleair: the household's own monitors on the WiFi, read again.

Both readers were core adapters until v0.16 (5 Sep 2026) dropped them from the poll by accident, while the settings and
the installer's flags stayed: a node that set AIRGRADIENT_HOSTS read nothing. They are packs since 22 Oct 2026, on
whenever their hosts are set, so nobody needs a new key, and update.sh adds them where a node lists its packs.
The readers' payloads are checked in tests/test_sources.py.

    PACKS_DIR=packs PYTHONPATH=app python3 tests/test_lan_air.py
"""
import os
import subprocess
import sys
import tempfile
import time

os.environ.update(PACKS_DIR="packs", NODE_LAT="-8.65", NODE_LON="115.22", PACKS_ALLOW_CODE="0")
sys.path.insert(0, "app")
import settings  # noqa: E402
import packs     # noqa: E402
import sources   # noqa: E402

ROWS = {"PACKS_ENABLED": "", "OPENMETEO_ENABLED": "0", "PACKS_ALLOW_CODE": "0"}
settings._cache = {"at": time.time() + 1e9, "rows": ROWS}

AG = {"serialno": "84fce612a5b4", "rco2": 612, "pm01": 4, "pm02": 9, "pm10": 11, "atmp": 29.4, "rhum": 61, "model": "I-9PSL"}
PA = {"SensorId": "84:f3:eb:12:34:56", "pm2_5_cf_1": 47.8, "pm2_5_cf_1_b": 46.9, "current_humidity": 62}


class R:
    def __init__(s, j): s.j = j
    def json(s): return s.j


class HC:
    """The LAN: an AirGradient answers /measures/current, a PurpleAir /json."""
    def __init__(s): s.urls = []
    def get(s, url, timeout=None):
        s.urls.append(url)
        return R(AG if "/measures/current" in url else PA)


# ---- 1. off with no host, on with one, with no PACKS_ALLOW_CODE
for pack, key in (("airgradient", "AIRGRADIENT_HOSTS"), ("purpleair", "PURPLEAIR_HOSTS")):
    d = packs.PACKS_DIR / pack
    ROWS[key] = ""
    assert not packs._official_on(d), pack
    ROWS[key] = "192.168.1.60"
    assert packs._official_on(d), pack
    ROWS[key] = ""
print("lan air: each pack is on whenever its hosts are set, with no PACKS_ALLOW_CODE")

# ---- 2. the poll reads them again, through the same sources.enabled() the core polls with
names = [n for n, _ in sources.enabled(HC())]
assert "airgradient" not in names and "purpleair" not in names, names
ROWS.update(AIRGRADIENT_HOSTS="airgradient_84fce6.local, 192.168.1.52", PURPLEAIR_HOSTS="192.168.1.60", SENSOR_INDOOR="1")
hc = HC()
got = dict(sources.enabled(hc))
s, r = got["airgradient"]()
assert [x["sensor_id"] for x in s] == ["ag-84fce612a5b4"] * 2 and all(x["indoor"] and x["local"] for x in s), s
assert s[0]["lat"] == -8.65 and s[0]["meta"]["host"] == "airgradient_84fce6.local", "the node's coordinates, the host as listed"
assert {m for _, _, m, _ in r} >= {"pm25", "pm25_raw", "co2", "temp", "humidity"}, r
s, r = got["purpleair"]()
assert s[0]["sensor_id"] == "pa-84f3eb123456" and s[0]["indoor"] and {m for _, _, m, _ in r} == {"pm25", "pm25_raw", "humidity"}
assert hc.urls == ["http://airgradient_84fce6.local/measures/current", "http://192.168.1.52/measures/current",
                   "http://192.168.1.60/json?live=true"], hc.urls
assert not hasattr(sources, "airgradient") and not hasattr(sources, "purpleair"), "one copy, in the packs"
ROWS["PACKS_ENABLED"] = "air-quality,heat"
assert not {"airgradient", "purpleair"} & {n for n, _ in sources.enabled(HC())}, "a node that lists its packs without them reads none"
ROWS.update(PACKS_ENABLED="", AIRGRADIENT_HOSTS="", PURPLEAIR_HOSTS="", SENSOR_INDOOR="")
print("lan air: the poll reads every listed host, indoors from SENSOR_INDOOR, and nothing with no host")

# ---- 3. update.sh step 5b: added where hosts are set and the node lists its packs, once
src = open("update.sh").read()
block = src[src.index("# 5b."):src.index("# 6. rebuild and restart")]
STUB = r'''
docker() {   # docker compose exec -T db psql -U planetai -tAc "<sql>" planetai, against a key=value file
  local sql=""; for a in "$@"; do case "$a" in SELECT*|UPDATE*) sql="$a";; esac; done
  if [[ "$sql" == SELECT* ]]; then k="$(sed -E "s/.*key = '([A-Z_]+)'.*/\1/" <<< "$sql")"; sed -n "s/^${k}=//p" "$DB"
  else add="$(sed -E "s/.*\|\| ',([a-z-]+)'.*/\1/" <<< "$sql")"; sed -i.bak -E "s/^(PACKS_ENABLED=.+)$/\1,${add}/" "$DB"; rm -f "$DB.bak"; fi
}
'''


def run(db: str, env: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as t:
        open(os.path.join(t, "db"), "w").write(db); open(os.path.join(t, ".env"), "w").write(env)
        subprocess.run(["bash", "-c", STUB + block], cwd=t, env={**os.environ, "DB": os.path.join(t, "db")},
                       capture_output=True, text=True, check=True)
        return open(os.path.join(t, "db")).read(), open(os.path.join(t, ".env")).read()


LIST = "PACKS_ENABLED=air-quality,heat\n"
db, _ = run("AIRGRADIENT_HOSTS=airgradient_84fce6.local\n" + LIST, "")
assert "PACKS_ENABLED=air-quality,heat,airgradient" in db and "purpleair" not in db, db
assert run(db, "")[0] == db, "a second update changed the list again"
_, env = run("", "PURPLEAIR_HOSTS=192.168.1.60\n" + LIST)
assert "PACKS_ENABLED=air-quality,heat,purpleair" in env and "airgradient" not in env, env
db, env = run(LIST, LIST)
assert "airgradient" not in db + env and "purpleair" not in db + env, "added with no host"
print("update.sh 5b: airgradient and purpleair added where their hosts are set and the node lists its packs, once")
print("lan air: every check passed")
