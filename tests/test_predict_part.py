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

# never a number the node does not have: no scored day, a sparse series, per-day counts, a day not made yet
NONE = D(None, None, None, None, 0, False)
odd = {**OK, "rows": [
    {"sensor": "Gate", "indoor": False, "metric": "pm25", "unit": "µg/m³", "why": {"reason": "young", "have": 0, "need": 7},
     "today": NONE, "tomorrow": NONE},
    {"sensor": "Mesh", "indoor": False, "metric": "temp", "unit": "°C", "why": {"reason": "sparse"}, "today": BLANK, "tomorrow": BLANK},
    {"sensor": "Shed", "indoor": False, "metric": "temp", "unit": "°C", "why": {"reason": "young", "have": 6, "need": 7},
     "today": D(None, None, 3.0, 2.0, 7, False), "tomorrow": D(None, None, 3.1, 2.0, 6, False)},
    {"sensor": "Yard", "indoor": False, "metric": "pm25", "unit": "µg/m³", "why": {"reason": "waiting"},
     "today": D(None, None, 2.0, 3.0, 20, False), "tomorrow": D(None, None, None, None, 0, False)}]}
(html,) = draw(odd)
rows = html.split("<tr>")[2:]
assert "0.0" not in rows[0] and rows[0].count("too young: 0 of 7 days") == 2, rows[0]
assert '<td class="n">—</td>' in rows[0], rows[0]
assert rows[1].count("too many hours missing") == 2 and "too young" not in rows[1], rows[1]
assert "yesterday is closer" in rows[2] and "too young: 6 of 7 days" in rows[2] and "7 of 7" not in html, rows[2]
assert rows[3].count("not made yet today") == 2 and "2.0 · —" in rows[3], rows[3]
assert ">off by, last 20 days</th>" in html
(none,) = draw({**OK, "rows": odd["rows"][:2]})
assert ">off by</th>" in none and "last 0 days" not in none, none
print("  ok: no error is a dash, sparse and not-yet say so, each day its own count, no 'last 0 days'")

# predictBlock: which of 403, 404, a failed fetch, an unreadable body and a good answer shows what
block = r"""
const fs = require('fs'), vm = require('vm');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), data = fs.readFileSync('./app/static/doors-data.js', 'utf8');
const pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0], fn = n => data.match(new RegExp('function ' + n + '\\b[\\s\\S]*?\\n}\\n'))[0];
const input = JSON.parse(fs.readFileSync(0, 'utf8')), out = [];
(async () => {
  for (const a of input) {
    const el = { innerHTML: '' }, ctx = { $: () => el, D: { health: {} }, mWord: x => x, UNLOCK_AT: 'UNLOCK',
      doorsFetch: () => a.fail ? Promise.reject(new Error('x')) : Promise.resolve({ ok: a.status === 200, status: a.status, json: async () => { if (a.bad) throw new Error('not json'); return a.body; } }) };
    vm.createContext(ctx);
    vm.runInContext(['esc', 'fmt', 'said'].map(pick).join('\n') + '\n' + ['pwhy', 'predictRows'].map(fn).join('\n') + '\nasync ' + fn('predictBlock') + '\nthis.predictBlock = predictBlock;', ctx);
    await ctx.predictBlock(); out.push(el.innerHTML);
  }
  console.log(JSON.stringify(out));
})();
"""
r = subprocess.run(["node", "-e", block], input=json.dumps([{"status": 403}, {"status": 404}, {"status": 500}, {"status": 200, "bad": True}, {"fail": True},
                                                               {"status": 200, "body": OK}, {"status": 200, "body": {"state": "no-model"}}]), capture_output=True, text=True)
assert r.returncode == 0, r.stderr
locked, off404, err500, badjson, down, good, nomodel = json.loads(r.stdout)
assert "only a screen holding a node token reads it: unlock this one in UNLOCK" in locked and "forecast" in locked and "<table" not in locked, locked
assert "This node does not forecast its own readings." in off404 and "could not be read" not in off404, off404
for h in (err500, badjson, down):
    assert "The forecast could not be read." in h and "does not forecast" not in h and "token" not in h, h
assert "general model, not adapted here" in good and "6.1–11.0" in good and "<h2>Its own readings, forecast</h2>" in good
assert "No model is pulled." in nomodel
# the predict sensor row carries the Next days line, not a model for this point: Node's counts and its flow leave it out
import re  # noqa: E402
for f, pat in (("app/static/doors-flow.js", r"models = D\.sensors\.filter\(s => s\.kind === 'model'[^;]*\);"),
               ("app/static/doors-node.js", r"models = D\.sensors\.filter\(s => s\.kind === 'model'[^,]*\)\.length")):
    m = re.search(pat, Path(f).read_text())
    assert m and "s.sensor_id !== 'predict'" in m.group(0), (f, m and m.group(0))
print("  ok: predictBlock: 403 is the locked lede, 404 the pack-off sentence, a 500, a bad body and no answer say it could not be read")
sys.exit(0)
