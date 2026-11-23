"""The weekly report on the node's page (app/weekly.py, GET /weekly, the Data door's Report tab).

What has to stay true for anyone to be allowed to open it: nothing a visitor types becomes SQL text, a sensor the
node does not offer cannot be asked for, and a visitor's labels never read a room's name. The counting itself is held
to Grafana's on a real Postgres in tests/test_grafana.py.

    python3 tests/test_weekly.py
"""
import sys

sys.path.insert(0, "app")
import weekly as w  # noqa: E402

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


def refused(args, metrics, offered):
    try:
        w.clean(args, metrics, offered)
    except ValueError:
        return True
    return False


print("bind: Grafana's placeholders become parameters, never text")
for name, f in w.PARTS.items():
    s = w.bind(f(w.WORDS["en"]))
    check("$" not in s, f"{name}: no Grafana placeholder left")
    check("%(sensors)s" in s and "%(metric)s" in s, f"{name}: the sensors and the metric are parameters")
    check("room" not in s and "room" in w.bind(f(w.WORDS["en"]), private=True), f"{name}: a visitor's labels never read a room")
for stray in ("SELECT 1 WHERE x LIKE 'a%'", "SELECT ${other}"):
    try:
        w.bind(stray)
        check(False, f"refused: {stray}")
    except ValueError:
        check(True, f"refused: {stray}")

print("clean: a request is checked before it reaches the database")
M, OFF = {"pm25", "pm10"}, {"sc-1": "Kulat residencd's", "bad-1": "50% shade"}
check(w.clean({"metric": "pm25", "sensors": "sc-1,bad-1"}, M, OFF) ==
      {"metric": "pm25", "sensors": ["sc-1", "bad-1"], "bad": 15.0, "high": 55.0, "weeks": 8, "lang": "en"}, "the defaults")
check(w.clean({"metric": "pm25"}, M, OFF)["sensors"] == [], "no sensors picked is allowed: the page shows the pickers")
for args in ({"metric": "co2"}, {"metric": "pm25", "sensors": "sc-19849"}, {"metric": "pm25", "bad": "1;drop"},
             {"metric": "pm25", "high": "nan"}, {"metric": "pm25", "high": "inf"}):
    check(refused(args, M, OFF), f"refused: {args}")
many = {f"s{i}": f"S{i}" for i in range(13)}
check(refused({"metric": "pm25", "sensors": ",".join(many)}, M, many), "refused: thirteen sensors")
check(w.clean({"metric": "pm25", "weeks": "500"}, M, OFF)["weeks"] == 12 and w.clean({"metric": "pm25", "weeks": "0"}, M, OFF)["weeks"] == 1
      and w.clean({"metric": "pm25", "weeks": "x"}, M, OFF)["weeks"] == 8, "weeks: 1 to 12, 8 when it is not a number")
check(w.clean({"metric": "pm25", "lang": "id"}, M, OFF)["lang"] == "id" and w.clean({"metric": "pm25", "lang": "fr"}, M, OFF)["lang"] == "en",
      "lang: id, or else en")
check(w.clean({"metric": "pm25", "sensors": " sc-1 ,,sc-1"}, M, OFF)["sensors"] == ["sc-1"], "spaces, empties and repeats drop out")

check(w.O in w.sql_weeks(w.WORDS["en"]) and "s.indoor IS NOT TRUE AND PUB)" in w.bind(w.sql_weeks(w.WORDS["en"]), public="PUB")
      and "PUB" not in w.bind(w.sql_weeks(w.WORDS["en"]), private=True, public="PUB"),
      "a visitor's all-sensors median reads only public channels (packs.public_sql)")

print("GET /weekly: open at SHARE_LEVEL=open, every value bound")
auth = open("app/auth.py").read()
open_list = auth[auth.index("_SHARE_OPEN = ("):auth.index("}), (", auth.index("_SHARE_OPEN = ("))]
check('"/weekly"' in open_list, "/weekly is on the open list, exactly")
main = open("app/main.py").read()
route = main[main.index('@app.get("/weekly")'):] if '@app.get("/weekly")' in main else ""
route = route[:route.index("\n@app.", 1)] if "\n@app." in route[1:] else route
for need in ("_shows_private(", "weekly.clean(", "weekly.bind(", "db()", "packs.public_sql("):
    check(need in route, f"the route calls {need}")
check(route and 'f"' not in route and "f'" not in route and '" % ' not in route and ".format(" not in route,
      "the route formats nothing into its SQL")

print(f"weekly: {'every check passed' if not fails else str(len(fails)) + ' failed'}")
sys.exit(1 if fails else 0)
