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

print("pick_metric: the metric is checked before any query reads it")
for asked, held, want in (("", {"pm25", "pm10"}, "pm25"), ("", {"pm10", "co2"}, "co2"), ("pm10", {"pm25", "pm10"}, "pm10"), ("", set(), None)):
    check(w.pick_metric(asked, held) == want, f"pick_metric({asked!r}, {sorted(held)}) is {want!r}")
for asked in ("\x00", "pm25\x00", "co2"):
    try:
        w.pick_metric(asked, {"pm25"})
        check(False, f"refused: {asked!r}")
    except ValueError:
        check(True, f"refused: {asked!r}")
metrics_sql, offered_sql = w.offer_sql(private=False, public="PUB")
check("s.indoor IS NOT TRUE" in metrics_sql and "s.indoor IS NOT TRUE" in offered_sql and "PUB" in metrics_sql and "PUB" in offered_sql
      and "room" not in offered_sql, "a visitor is offered outdoor sensors on public channels, labelled without the room")
check("indoor IS NOT TRUE" not in w.offer_sql(private=True, public="PUB")[1] and "PUB" not in w.offer_sql(private=True, public="PUB")[1] and "room" in w.offer_sql(private=True, public="PUB")[1], "the keeper is offered every sensor, by room")

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
check("weekly.offer_sql(" in route and "weekly.pick_metric(" in route and route.index("weekly.pick_metric(") < route.index("q(offered_sql"),
      "the route checks the metric before it runs the offered query")

print("the Report tab in Data: its address, its state, and nothing it is sent drawn unescaped")
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
js = open("app/static/doors-data.js").read()
check(re.search(r"\breport:\s*\['", js) is not None and 'id="d-report"' in open("app/static/doors.html").read(), "Data has a Report tab and its section")
prog = r"""
const src = require('fs').readFileSync('app/static/doors-data.js', 'utf8');
const grab = re => (src.match(re) || [''])[0];
const D = { sens: { 'sc-1': { kind: 'sensor' } } };
let location = { hash: '' };
const reportBlock = () => {}, metricTiles = () => {}, sensorsBlock = () => {}, issuesBlock = () => {}, perdayBlock = () => {},
      modelsBlock = () => {}, imagesBlock = () => {}, thingsBlock = () => {}, ledgerBlock = () => {}, apiBlock = () => {}, workbenchBlock = () => {};
const lifted = eval(grab(/const DTABS = \{[\s\S]*?\n  workbench:[^\n]*\n/) + grab(/const DOLD = [^\n]*\n/)
     + grab(/const DNODE = [^\n]*\n/) + grab(/function dataRoute\(hash\) \{[\s\S]*?\n\}\n/) + grab(/const repState = [^\n]*\n/)
     + '; ({ dataRoute, repState })');   // a const made inside eval stays inside it, so the eval hands them back
const out = {};
out.route = lifted.dataRoute('#data/report?m=pm25&s=a,b');
out.routeSensor = lifted.dataRoute('#data/sc-1');
location.hash = '#data/report?m=pm10&s=a,b%20c&bad=20&high=60&w=4&lang=id';
out.state = lifted.repState();
location.hash = '#data/report';
out.empty = lifted.repState();
console.log(JSON.stringify(out));
"""
r = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
o = json.loads(r.stdout) if r.returncode == 0 else {}
check(o.get("route") == {"tab": "report"} and o.get("routeSensor") == {"tab": "readings", "sensor": "sc-1"}, f"#data/report?… opens the tab, a sensor still opens its row {r.stderr[-300:]}")
check(o.get("state") == {"m": "pm10", "s": ["a", "b c"], "bad": "20", "high": "60", "w": "4", "lang": "id"}, "the address holds the report's state")
check(o.get("empty") == {"m": "", "s": [], "bad": "15", "high": "55", "w": "8", "lang": "en"}, "an empty address starts from the defaults")
block = js[js.index("/* REPORT"):js.index("/* THE WORKBENCH")] if "/* REPORT" in js else ""
check(block.count("new URLSearchParams(") >= 2 and "'/weekly?' + new URLSearchParams(" in block and "history.replaceState(" in block,
      "the request and the address are built with URLSearchParams, and the address is kept with replaceState")
# Every value the node sends that is a name, an id, a word or a cell is drawn through esc(): none is interpolated bare.
raw = re.findall(r"\$\{\s*(cell|c|k|src|id|m|o\.label|o\.id|o\.source|j\.detail|j\.bad|j\.high|L\.[a-z_]+|names\[[^\]]*\])\s*[}?|]", block)
check(block and not raw, f"what the node sends is escaped before it is drawn {raw[:3]}")
check("j.detail || j.error" in block, "a refusal from the share level (its {error}) is shown, not 'did not answer'")
check("j.max_sensors" in block and " disabled" in block, "at twelve sensors the boxes not ticked are disabled")
check("data-reset" in block and "b.dataset.reset" in block, "after a refusal, Start again really starts again")
check("document.activeElement" in block and ".focus()" in block and "find.value" in block,
      "a redraw keeps the focus and what was typed in the name box")

print("the air index: Indonesia's ISPU bands on the 24-hour mean (Permen LHK P.14/2020, Lampiran I)")
check([w.band("pm25", v) for v in (0, 15.5, 15.6, 55.4, 55.5, 150.4, 150.5, 250.4, 250.5)] == [0, 0, 1, 1, 2, 2, 3, 3, 4],
      "PM2.5 bands, upper bounds inclusive")
check([w.band("pm10", v) for v in (50, 50.1, 150, 151, 350, 351, 420, 421)] == [0, 1, 1, 2, 2, 3, 3, 4], "PM10 bands")
check(w.band("temp", 40) is None and w.band("pm25", None) is None, "no index, no band")
check("days" in w.PARTS and "%(sensors)s" in w.bind(w.sql_days(w.WORDS["en"])), "the days part is bound like the others")
check(set(w.WORDS["en"]) == set(w.WORDS["id"]), "every word in both languages")
for k in ("so_far", "of_counted", "set_by_reader", "who_line", "pdf", "pdf_hint", "share", "not_counted", "rooms_out",
          "band_0", "band_4", "not_calibrated", "colours_from", "bad_of", "week_pick", "worst_place", "worst_day", "highest_hour", "avg_bad"):
    check(k in w.WORDS["en"], f"the word {k!r} is there")

print(f"weekly: {'every check passed' if not fails else str(len(fails)) + ' failed'}")
sys.exit(1 if fails else 0)
