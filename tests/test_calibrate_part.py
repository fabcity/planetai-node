"""The Corrections section in Data: calibrateRows and calibrateMarks lifted out of doors-data.js and run in node.

Run: PYTHONPATH=app python3 tests/test_calibrate_part.py
The JSON goes in on stdin (argv is capped at 128 KB on Linux CI).
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
prog = r"""
const fs = require('fs'), vm = require('vm');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), data = fs.readFileSync('./app/static/doors-data.js', 'utf8');
const pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0], fn = n => data.match(new RegExp('function ' + n + '\\b[\\s\\S]*?\\n}\n'))[0];
const ctx = {}; vm.createContext(ctx);
vm.runInContext(['esc', 'fmt', 'said'].map(pick).join('\n') + '\n' + ['cwhy', 'calibrateRows', 'calibrateMarks'].map(fn).join('\n')
  + '\nthis.rows = calibrateRows; this.marks = calibrateMarks;', ctx);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(input.map(([k, ...a]) => ctx[k](...a))));
"""


def draw(*calls):
    r = subprocess.run(["node", "-e", prog], input=json.dumps(calls), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def row(sid, name, why, shown=False, **kw):
    return {"entry": f"{sid} ref pm25 2026-10-01", "sensor": {"id": sid, "name": name},
            "reference": kw.pop("reference", {"id": "ref", "name": "Rooftop", "own": True, "network": None, "official": None, "from_index": None}),
            "metric": kw.pop("metric", "pm25"), "unit": "µg/m³", "metres": kw.pop("metres", 30), "since": "2026-10-01", "until": None,
            "measured": kw.pop("measured", 12.0), "corrected": None, "hour": None, "line": kw.pop("line", {"a": 1, "b": 1, "hours": 300}),
            "paired_hours": 0, "last_paired": None, "checked": kw.pop("checked", None), "shown": shown, "why": why}


CK = {"days": 7, "measured": 2.6, "corrected": 1.4}
SHOWN = row("s1", "Backyard <b>", None, True, measured=14.2, checked=CK,
            reference={"id": "r1", "name": "<img src=x>", "own": True, "network": None, "official": None, "from_index": None})
SHOWN["corrected"] = 13.6
STATION = {"id": "st", "name": "Sempidi", "own": False, "network": "BAD", "official": True, "from_index": True}
OK = {"state": "ok", "could": [], "rows": [
    SHOWN,
    row("s2", "Flat", {"reason": "flat"}, line=None),
    row("s3", "Young hours", {"reason": "young", "hours": 120, "need_hours": 168, "days": 0, "need_days": 7}, line=None),
    row("s4", "Young days", {"reason": "young", "hours": 300, "need_hours": 168, "days": 3, "need_days": 7}),
    row("s5", "Closer", {"reason": "measured-closer"}, checked=CK),
    row("s6", "Tenth", {"reason": "not-a-tenth"}, checked=CK),
    row("s7", "Gone", {"reason": "withdrawn", "since": "2026-11-03"}),
    row("s8", "Empty", {"reason": "no-hours"}, line=None),
    row("s9", "Station", {"reason": "measured-closer"}, reference=STATION, metres=None, checked=CK),
    row("s10", "Own far", {"reason": "measured-closer"}, metres=None, checked=CK)]}
REFUSED = {"state": "ok", "could": [], "rows": [row("a", "A", {"reason": "refused", **w}) for w in (
    {"test": "unknown", "side": "reference"}, {"test": "not-a-sensor", "side": "sensor"}, {"test": "sensor-is-station"},
    {"test": "no-channel", "side": "reference"}, {"test": "indoor-outdoor"}, {"test": "apart", "metres": 812})]}
BAD = {"state": "ok", "could": [], "rows": [{"entry": 'x <i> y', "shown": False, "why": {"reason": "malformed", "problem": p}} for p in (
    "fields", "date", "until-before-since", "since-in-future", "same", "duplicate")]}
COULD = {"state": "ok", "rows": [], "could": [{"a": {"id": "s<1>", "name": "Roof <u>"}, "b": {"id": "s2", "name": "Yard"}, "metric": "pm25", "metres": 30}]}
SENS = {"ref": {"source": "plantower"}}
off, failed, ok, refused, bad, could, mark, mark_temp, nomark = draw(
    ["rows", {"state": "off"}, "https://d.example/"], ["rows", {"state": "failed"}], ["rows", OK, "", {}, "2026-11-22"],
    ["rows", REFUSED, "", SENS], ["rows", BAD], ["rows", COULD, "", {}, "2026-11-22"],
    ["marks", OK, "pm25"], ["marks", OK, "temp"], ["marks", {"state": "off"}, "pm25"])

assert "No sensor on this node is corrected against another. Name a pair in Set up, under Calibrate." in off, off
assert 'href="https://d.example/calibrate/"' in off, off
assert "The corrections could not be read." in failed
print("  ok: off says its sentence with the docs link, failed says it could not be read")

assert "A straight line fitted on the last 14 days against the sensor named. Shown only while it has been closer on days the line never saw. The measured number is what the node stores, alerts on and shares." in ok
for t in ("no line: the sensor read one value for two weeks", "too young: 120 of 168 hours together", "too young: 3 of 7 days checked",
          "not shown: measured is closer", "not shown: not a tenth closer", "withdrawn: nothing beside it since 3 Nov",
          "nothing beside it for six weeks", ">shown<"):
    assert t in ok, t
assert ok.count("not shown: measured is closer") == 3
assert "&lt;img src=x&gt;, your own sensor, 30 m" in ok, ok
assert "Sempidi (BAD), official station, its numbers are an index converted back" in ok, ok
assert "Rooftop, your own sensor, distance not known" in ok, ok
assert "off by 2.6 → 1.4" in ok and "13.6" in ok and "14.2" in ok, ok
for col in ("sensor", "measured", "corrected", "against", "last checked days", "state"):
    assert f">{col}</th>" in ok, col
print("  ok: every state prints its words, each against line and the columns")

for t in ("not known to this node: ref", "a is not a sensor", "a public station cannot be the one corrected", "plantower declares no pm25 channel",
          "one is indoors and the other outdoors", "812 m apart"):
    assert t in refused, t
assert "ref declares no pm25 channel" in draw(["rows", {"state": "ok", "could": [], "rows": REFUSED["rows"][3:4]}])[0]
for t in ('cannot read &quot;x &lt;i&gt; y&quot;: needs four or five parts', "a date is not a date", "the last day is before the first",
          "the first day is in the future", "both ids are the same", "this sensor is already in an earlier pair"):
    assert t in bad, t
assert "<i>" not in bad
print("  ok: each refusal and each malformed entry says its one sentence")

assert "You could name: Roof &lt;u&gt; and Yard (30 m, pm25). Write the one to correct first:" in could, could
assert "<code>s&lt;1&gt; s2 pm25 2026-11-22</code>" in could, could
print("  ok: could names the pair and writes the entry to start from")

assert "Backyard &lt;b&gt;" in ok and "&lt;img src=x&gt;" in ok
assert list(mark) == ["s1"] and nomark == {} and mark_temp == {}, (mark, mark_temp)
assert "corrected 13.6 against &lt;img src=x&gt;" in mark["s1"] and 'href="#data/models"' in mark["s1"], mark
for h in (ok, refused, bad, could, mark["s1"]):
    assert "<b>" not in h and "<img" not in h and "<u>" not in h and "<i>" not in h, h
    assert "calibrated" not in h.lower() and "reference-grade" not in h.lower() and "true value" not in h.lower() and "accurate" not in h.lower(), h
print("  ok: node text is escaped, the mark exists for the shown row on its own metric only, nothing says calibrated")
