"""The Predict section in Data: predictRows lifted out of doors-data.js and run in node, given what GET /predict says.

Run: PYTHONPATH=app python3 tests/test_predict_part.py
The JSON goes in on stdin (argv is capped at 128 KB on Linux CI).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
prog = r"""
const fs = require('fs'), vm = require('vm');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), data = fs.readFileSync('./app/static/doors-data.js', 'utf8');
const pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0], fn = n => data.match(new RegExp('function ' + n + '\\b[\\s\\S]*?\\n}\\n'))[0];
const ctx = {}; vm.createContext(ctx);
vm.runInContext(['esc', 'fmt', 'said'].map(pick).join('\n') + '\n' + ['pwhy', 'predictRows'].map(fn).join('\n') + '\nthis.predictRows = predictRows;', ctx);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(input.map(j => ctx.predictRows(j))));
"""


def draw(*js):
    r = subprocess.run(["node", "-e", prog], input=json.dumps(js), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


D = lambda low, high, m, n, d, shown: {"low": low, "high": high, "model": m, "naive": n, "days": d, "shown": shown}  # noqa: E731
BLANK = D(None, None, None, None, None, False)
OK = {"state": "ok", "model": {"name": "amazon/chronos-2", "revision": "29ec3766", "adapted": False}, "origin": "2026-11-22", "rows": [
    {"sensor": "Backyard <b>", "indoor": False, "metric": "pm25", "unit": "µg/m³", "why": None,
     "today": D(6.1, 11.0, 2.9, 3.7, 28, True), "tomorrow": D(5.8, 12.4, 3.7, 4.6, 27, True)},
    {"sensor": "Kids", "indoor": True, "metric": "temp", "unit": "°C", "why": {"reason": "naive-closer"},
     "today": D(None, None, 1.0, 0.8, 28, False), "tomorrow": D(None, None, 1.2, 0.9, 28, False)},
    {"sensor": "Roof", "indoor": False, "metric": "pm25", "unit": "µg/m³", "why": {"reason": "young", "have": 9, "need": 14},
     "today": BLANK, "tomorrow": BLANK}]}
off, noans, nomodel, young, ok, failed = draw({"state": "off"}, {"state": "no-answer"}, {"state": "no-model"}, {"state": "young"}, OK, {"state": "failed"})

assert ("This node does not forecast its own readings. <code>planetai models pull amazon/chronos-2</code> turns it on (456 MB)." in off
        and 'href="https://planetai.fab.city/docs/predict/"' in off), off
assert "The models container is not answering." in noans and "No model is pulled." in nomodel and "No series has 14 days yet." in young
assert "could not be read" in failed
print("  ok: pack off, no answer, no model, young and failed each say their sentence")

assert "amazon/chronos-2 · general model, not adapted here" in ok, ok
for col in ("series", "today", "tomorrow", "off by, last 28 days", "yesterday repeated"):
    assert f">{col}</th>" in ok, col
assert "6.1–11.0" in ok and "5.8–12.4" in ok and "2.9 · 3.7" in ok and "3.7 · 4.6" in ok, ok
assert ok.count("— <span") == 4, "four days are not shown, each prints a dash and its reason"
assert ok.count("yesterday is closer") == 2 and ok.count("too young: 9 of 14 days") == 2, ok
assert "Backyard &lt;b&gt;" in ok and "<b>" not in ok, "node text is escaped"
assert "trained" not in ok and "adapted here on" not in ok
assert "µ" not in Path("app/static/doors-data.js").read_text().split("function predictRows")[1].split("async function predictBlock")[0]
print("  ok: shown days print their range, the others a dash and why, node text is escaped")
sys.exit(0)
