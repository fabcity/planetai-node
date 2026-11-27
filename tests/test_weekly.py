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
const D = { sens: { 'sc-1': { kind: 'sensor' } }, health: { kind: 'home' } };
let location = { hash: '' };
const reportBlock = () => {}, metricTiles = () => {}, sensorsBlock = () => {}, issuesBlock = () => {}, perdayBlock = () => {},
      modelsBlock = () => {}, imagesBlock = () => {}, thingsBlock = () => {}, ledgerBlock = () => {}, apiBlock = () => {}, workbenchBlock = () => {};
const notHouse = k => ['community', 'district'].includes(String(k ?? '').toLowerCase());
const lifted = eval(grab(/const DTABS = \{[\s\S]*?\n  workbench:[^\n]*\n/) + grab(/const DOLD = [^\n]*\n/)
     + grab(/function dataTabs\(kind\) \{[\s\S]*?\n\}\n/) + grab(/const DNODE = [^\n]*\n/) + grab(/function dataRoute\(hash\) \{[\s\S]*?\n\}\n/) + grab(/const repState = [^\n]*\n/)
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
check(o.get("state") == {"m": "pm10", "s": ["a", "b c"], "bad": "20", "high": "60", "w": "4", "wk": "", "lang": "id"}, "the address holds the report's state")
check(o.get("empty") == {"m": "", "s": [], "bad": "", "high": "", "w": "8", "wk": "", "lang": "en"}, "an empty address starts from the defaults")
block = js[js.index("/* REPORT"):js.index("/* SHARE") if "/* SHARE" in js else js.index("/* THE WORKBENCH")] if "/* REPORT" in js else ""   # the HTML the page writes; the share images are drawn on a canvas, not written as HTML
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

print("the chosen week: the last complete one unless asked, and what the node says about it")
starts = ["2026-11-02", "2026-11-09", "2026-11-16", "2026-11-23"]
check(w.pick_week("", starts, "2026-11-23") == ("2026-11-16", True), "no week asked: the last complete one")
check(w.pick_week("2026-11-09", starts, "2026-11-23") == ("2026-11-09", True), "a week in the window")
check(w.pick_week("2026-11-23", starts, "2026-11-23") == ("2026-11-23", False), "the week not over can be read")
check(w.pick_week("2025-01-06", starts, "2026-11-23") == ("2026-11-16", True) and w.pick_week("x';--", starts, "2026-11-23")[0] == "2026-11-16",
      "a week outside the window falls back to the default")
check(w.pick_week("", ["2026-11-23"], "2026-11-23") == ("2026-11-23", False), "a one-week window has only the week not over")
D = lambda day, hours, mean, peak, at: {"day": day, "label": "TPA Kutuh", "sensor_id": "k", "hours": hours, "mean": mean, "peak": peak, "peak_at": at}
days_rows = [D("2026-11-09", 24, 14.2, 48, "05:00"), D("2026-11-10", 12, 40.0, 90, "08:00"), D("2026-11-11", 24, 15.4, 64, "23:00"),
             D("2026-11-12", 24, 20.7, 67, "21:00"), D("2026-11-13", 24, 30.9, 67, "06:00"), D("2026-11-15", 24, 12.0, 125, "23:00")]
cols = ["week from", "sensor", "bad days", "against the week before"]
weeks_rows = [["2026-11-16", "TPA Kutuh", 1, "improving"], ["2026-11-09", "TPA Kutuh", 3, "worse"]]
sm = w.summarise(days_rows, weeks_rows, cols, "2026-11-09", "pm25", 15, 18, ["k", "gone"], {"k": "TPA Kutuh", "gone": "Silent"})
k, gone = sm["sensors"]
check(k["counted"] == 5 and k["bad"] == 3, f"5 days counted (a 12-hour day and a missing one are not), 3 over 15 {k['counted']}/{k['bad']}")
check([x["counted"] for x in k["days"]] == [True, False, True, True, True, False, True] and len(k["days"]) == 7, "seven days, Saturday missing")
check(k["days"][2]["edge"] is True and k["days"][2]["band"] == 0 and k["days"][3]["edge"] is False, "15.4 is a bad day inside the good band: the edge")
check(k["days"][1]["bad"] is False and k["days"][1]["band"] == 1, "a short day is never bad, though its band is drawn")
check(k["verdict"] == "worse" and k["worst_day"] == "2026-11-13" and k["worst_mean"] == 30.9, "the verdict is read from the weeks part; the worst counted day")
check((k["peak"], k["peak_day"], k["peak_at"]) == (125, "2026-11-15", "23:00"), "the highest hour of the week, and when")
check(gone["counted"] == 0 and gone["bad"] == 0 and not any(x["counted"] for x in gone["days"]) and gone["verdict"] is None, "a silent sensor: nothing counted")
check(sm["overall"]["worst"] == "TPA Kutuh" and sm["overall"]["avg_bad"] == 3.0 and sm["overall"]["peak_place"] == "TPA Kutuh",
      "the overview: average over the places heard, the worst place, where the highest hour was")
k25 = w.summarise(days_rows, weeks_rows, cols, "2026-11-09", "pm25", 25, 18, ["k"], {"k": "TPA Kutuh"})["sensors"][0]
check(k25["bad"] == 1 and not k25["days"][3]["bad"] and k25["days"][4]["bad"], "the reader's line: at 25 only the 30.9 day is bad")
tmp = w.summarise([dict(r, mean=r["mean"]) for r in days_rows], weeks_rows, cols, "2026-11-09", "temp", 15, 18, ["k"], {"k": "TPA Kutuh"})
check(all(x["band"] is None and not x.get("edge") for x in tmp["sensors"][0]["days"]), "no index: no band, no edge")
route = main[main.index('@app.get("/weekly")'):]
route = route[:route.index("\n@app.", 1)]
check("weekly.pick_week(" in route and "weekly.summarise(" in route and route.index('"t0"') < route.index("return"),
      "the route picks the week, summarises it, and says t0 in every answer")

print("the air index colours: tokens on the page, readable numbers, ISPU's hues, never the website palette")
import colorsys  # noqa: E402
html = open("app/static/doors.html").read()
tok = dict(re.findall(r"--(aqi-[0-4](?:-ink)?):\s*(#[0-9A-Fa-f]{6})", html))
def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
check(all(f"aqi-{i}" in tok and f"aqi-{i}-ink" in tok for i in range(5)), f"ten tokens, a band and its number colour each {sorted(tok)}")
for i in range(5):
    if f"aqi-{i}" in tok and f"aqi-{i}-ink" in tok:
        r = contrast(tok[f"aqi-{i}"], tok[f"aqi-{i}-ink"])
        check(r >= 4.5, f"band {i}: its numbers read at {r:.1f}:1")
hue = lambda h: colorsys.rgb_to_hls(*[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])
want = {0: (90, 160), 1: (200, 235), 2: (38, 60), 3: (0, 15)}
for i, (lo, hi) in want.items():
    if f"aqi-{i}" in tok:
        hdeg = hue(tok[f"aqi-{i}"])[0] * 360
        check(lo <= hdeg <= hi, f"band {i} reads as ISPU's {['green', 'blue', 'yellow', 'red'][i]} ({hdeg:.0f} degrees)")
check("aqi-4" in tok and hue(tok["aqi-4"])[1] < 0.15, "band 4 is black")
palette = open("tools/check_ui.py").read()
check(not any(v.upper() in palette.upper() for v in tok.values()), "none is in the website palette check_ui refuses")

print("the tab at a glance: the week in the address, a day drawn by what the node said, a scale one hour cannot flatten")
prog2 = r"""
const src = require('fs').readFileSync('app/static/doors-data.js', 'utf8');
const grab = re => (src.match(re) || [''])[0];
let location = { hash: '#data/report?m=pm25&s=a&wk=2026-11-09' };
const lifted = eval(grab(/const repState = [^\n]*\n/) + grab(/const dayBlock = [^\n]*\n/) + grab(/function capTop\(values\) \{[\s\S]*?\n\}\n/)
  + '; ({ repState, dayBlock, capTop })');
const out = { wk: lifted.repState().wk };
const d = (o) => lifted.dayBlock(o);
out.mod = d({ counted: true, bad: true, band: 1, edge: false, mean: 20.7 });
out.edge = d({ counted: true, bad: true, band: 0, edge: true, mean: 15.4 });
out.short = d({ counted: false, bad: false, band: 1, edge: false, mean: 40 });
out.missing = d({ counted: false, bad: false, band: null, edge: false, mean: null });
out.noidx = d({ counted: true, bad: true, band: null, edge: false, mean: 31 });
out.noidxok = d({ counted: true, bad: false, band: null, edge: false, mean: 22 });
const series = Array.from({ length: 200 }, (_, i) => 10 + (i % 7));
series[150] = 872;
out.cap = lifted.capTop(series);
console.log(JSON.stringify(out));
"""
r2 = subprocess.run(["node", "-e", prog2], capture_output=True, text=True)
o2 = json.loads(r2.stdout) if r2.returncode == 0 else {}
check(o2.get("wk") == "2026-11-09", f"the week is in the address {r2.stderr[-200:]}")
check(o2.get("mod", {}).get("cls") == "aqi-1" and o2["mod"].get("text") == "21", "a counted moderate day: blue, its mean")
check(o2.get("edge", {}).get("cls") == "aqi-0 edge" and o2["edge"].get("text") == "15", "15.4: green with the red edge")
check(o2.get("short", {}).get("cls") == "nc" and o2["short"].get("text") == "" and o2.get("missing", {}).get("cls") == "nc",
      "a short day and a missing one: grey, no number")
check(o2.get("noidx", {}).get("cls") == "nb bad" and o2.get("noidxok", {}).get("cls") == "nb", "no index: the bad mark, never a band")
cap = o2.get("cap", {})
check(cap.get("top") is not None and cap["top"] < 100 and cap.get("over") == [872], f"one 872 does not set the scale; it is printed {cap}")

print("share images: safe file names, the five worst, and never the keeper's token")
js = open("app/static/doors-data.js").read()
prog3 = r"""
const src = require('fs').readFileSync('app/static/doors-data.js', 'utf8');
const grab = re => (src.match(re) || [''])[0];
const lifted = eval(grab(/const slug = [^\n]*\n/) + grab(/const fiveWorst = [^\n]*\n/) + '; ({ slug, fiveWorst })');
const S = n => Array.from({ length: n }, (_, i) => ({ label: 'P' + i, bad: i % 4, worst_mean: i }));
console.log(JSON.stringify({ a: lifted.slug("Kulat residencd's 50% & co"), b: lifted.slug('TPA Kutuh (Smart Citizen)'), c: lifted.slug('Ünder  —  Pura'),
  d: lifted.slug('x'.repeat(90)).length, five: lifted.fiveWorst(S(8)).map(s => s.label), two: lifted.fiveWorst(S(2)).length }));
"""
r3 = subprocess.run(["node", "-e", prog3], capture_output=True, text=True)
o3 = json.loads(r3.stdout) if r3.returncode == 0 else {}
check(o3.get("a") == "kulat-residencds-50-co" and o3.get("b") == "tpa-kutuh-smart-citizen" and o3.get("c") == "under-pura" and o3.get("d") == 60,
      f"file names are safe slugs, 60 characters at most {o3} {r3.stderr[-200:]}")
check(o3.get("five") == ["P7", "P3", "P6", "P2", "P5"] and o3.get("two") == 2, "the comparison takes the five worst: bad days, then the worst day")
share = js[js.index("/* SHARE"):js.index("/* THE WORKBENCH")] if "/* SHARE" in js else ""
pub = share[share.index("function repPublic"):share.index("\n}\n", share.index("function repPublic"))] if "function repPublic" in share else ""
check(pub and "fetch(" in pub and "DOORS_AUTH" not in pub and "authorization" not in pub.lower(), "the share path asks the node without the token")
check("j.shareable" in js and "data-share" in js, "Share images is offered only when the node says the week can be shared")
html_share = share[share.index("function repShare"):] if "function repShare" in share else ""
check(html_share and not re.findall(r"\$\{\s*(s\.label|it\.name|L\.[a-z_]+)\s*\}", html_share), "the panel's HTML escapes what it writes")
check("L.rooms_out" in share and "'image/jpeg'" in share and "document.fonts.ready" in share and "1080" in share and "1350" in share,
      "the panel says rooms stay out, draws after the fonts, 1080×1350 JPEG")
check("-${" in share and ".jpg" in share and "comparison-" in share, "file names: <place>-<week>.jpg and comparison-<week>.jpg")

print("the PDF: A4 pages from the browser's print, the visitor's view, only for a week that is over")
html = open("app/static/doors.html").read()
js = open("app/static/doors-data.js").read()
check("@page weekly{size:A4 portrait" in html and "body.pweekly" in html and 'id="wpages"' in html, "an A4 portrait page, a print layout and its container")
check("print-color-adjust:exact" in html.replace(" ", ""), "the air colours print without the background-graphics box ticked")
pdfjs = js[js.index("/* PDF"):js.index("/* THE WORKBENCH")] if "/* PDF" in js else ""
check(pdfjs and "repPublic(" in pdfjs and "DOORS_AUTH" not in pdfjs, "the PDF is made from the visitor's view")
check("j.wk_complete" in js and "data-pdf" in js and "L.pdf_hint" in js, "Download the PDF is offered for a week that is over, with how to save it")
check("function buildWeeklyPages" in pdfjs and "function printWeekly" in pdfjs and "afterprint" in pdfjs and "L.page" in pdfjs,
      "the pages are built apart from printing, numbered, and taken away after printing")

print("the review's fixes: each line from its source, the unit of the metric, the images that fit and say what they count")
check(w.clean({"metric": "pm10"}, {"pm10"}, {})["bad"] == 45 and w.clean({"metric": "pm10"}, {"pm10"}, {})["high"] == 150
      and w.clean({"metric": "pm25"}, {"pm25"}, {})["bad"] == 15 and w.clean({"metric": "temp"}, {"temp"}, {})["bad"] == 15,
      "each metric starts at its own lines: PM10 at WHO 45 and ISPU 150, PM2.5 at 15 and 55, others at 15 and 55")
check(w.line_source("pm10", 45) == "who" and w.line_source("pm25", 15) == "who" and w.line_source("pm10", 15) == "reader" and w.line_source("temp", 15) == "reader",
      "the line is the WHO's only at the WHO's value for that metric")
check(all("{unit}" in w.WORDS[l][k] and "µg/m³" not in w.WORDS[l][k] for l in ("en", "id") for k in ("who_line", "set_by_reader")),
      "the line's words take the metric's unit, never a fixed µg/m³")
check(all(("bad" in w.WORDS["en"][k] or "line" in w.WORDS["en"][k]) for k in ("who_line", "set_by_reader")), "the footer says it is the bad-day line")
check("no_answer" in w.WORDS["id"], "the panel's failure is said in the page's language")
js = open("app/static/doors-data.js").read()
main = open("app/main.py").read()
check('"unit"' in main[main.index('@app.get("/weekly")'):][:6000] and "weekly.line_source(" in main, "the route says the metric's unit and where the line comes from")
prog4 = r"""
const src = require('fs').readFileSync('app/static/doors-data.js', 'utf8');
const grab = re => (src.match(re) || [''])[0];
const d3 = require('./app/static/d3.min.js');
const L = eval(grab(/const repState = [^\n]*\n/) + grab(/const dshort = [^\n]*\n/) + grab(/const compareLayout = [^\n]*\n/) + grab(/const sharedPlaces = [^\n]*\n/)
  + grab(/function aboveScale\(pts, top\) \{[\s\S]*?\n\}\n/) + '; ({ dshort, compareLayout, sharedPlaces, aboveScale })');
const lay = L.compareLayout(2, 5), pts = Array.from({ length: 60 }, (_, i) => [i, i === 10 ? 413 : i === 20 ? 300 : i === 30 ? 280 : 12]);
console.log(JSON.stringify({ id: L.dshort('2026-10-12', 'id-ID'), en: L.dshort('2026-10-12', 'en-GB'), lay, bottom: lay.top + 4 * lay.pitch + lay.row,
  places: L.sharedPlaces([{ counted: 0 }, { counted: 5 }, { counted: 7 }]).length, above: L.aboveScale(pts, 50) }));
"""
r4 = subprocess.run(["node", "-e", prog4], capture_output=True, text=True)
o4 = json.loads(r4.stdout) if r4.returncode == 0 else {}
check("Okt" in str(o4.get("id")) and "Oct" in str(o4.get("en")), f"dates in the page's language {o4.get('id')} {r4.stderr[-200:]}")
check(o4.get("bottom") is not None and o4["bottom"] <= 1150, f"five places under a two-line title end above the footer {o4.get('lay')} {o4.get('bottom')}")
check(o4.get("places") == 2, "a place with no counted day gets no image")
ab = o4.get("above", {})
check(ab.get("shown") and [p[1] for p in ab["shown"]] == [413, 300] and ab.get("more") == 1, f"above the scale: the two highest, and how many more {ab}")
block = js[js.index("function reportBlock"):js.index("/* SHARE")]
check("replaceState" in block and "j.wk" in block[block.index("REPLAST = j"):block.index("REPLAST = j") + 600], "the answer's week goes back into the address")
share = js[js.index("/* SHARE"):js.index("/* THE WORKBENCH")]
check("fitFont(" in share and "words.no_answer" in share and "did not answer" not in share and "s.counted" in share[share.index("function shareCompare"):share.index("function repShare")],
      "the count line is fitted to the image, the comparison says what each count is out of, a failure is in WORDS")
pdf = js[js.index("/* PDF"):js.index("/* THE WORKBENCH")]
pw = pdf[pdf.index("function printWeekly"):]
check("words.rooms_out" in pw and ".sensors || []).length" in pw and "words.no_answer" in pw and "catch(() => {})" not in pw, "the PDF does not print zero places, says why, and says when the node did not answer")

print(f"weekly: {'every check passed' if not fails else str(len(fails)) + ' failed'}")
sys.exit(1 if fails else 0)
