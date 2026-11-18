"""The Wall map's pure half (app/static/doors-wallmap.js): hour lookup, wind and swell motion maths, station features.
Run under node from here; nothing is drawn, so nothing needs a browser."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

out = subprocess.run(["node", "-e", """
const W = require('./app/static/doors-wallmap.js');
const segs = W.crestSegments(800, 600, 204, 0), t = W.toward(204);
const st = [{lat: -8.7, lon: 115.2, pm25: [10, null, 40]}, {lat: -8.8, lon: 115.1, pm25: [null, null, null]}];
console.log(JSON.stringify({
  at: [W.atHour([null, null, 3, null], 0), W.atHour([1, null, null], 2), W.atHour([null, null], 1), W.atHour([5, null, 7], 1), W.atHour([1, 2, 3], 1)],
  south: W.toward(180), n350: W.toward(350), unit: Math.hypot(W.toward(37).ux, W.toward(37).uy),
  n: segs.length, t,
  dot: segs.map(([x1, y1, x2, y2]) => (x2 - x1) * t.ux + (y2 - y1) * t.uy),
  len: segs.map(([x1, y1, x2, y2]) => Math.hypot(x2 - x1, y2 - y1)),
  gap: segs.slice(1).map((s, i) => ((s[0] + s[2]) / 2 - (segs[i][0] + segs[i][2]) / 2) * t.ux + ((s[1] + s[3]) / 2 - (segs[i][1] + segs[i][3]) / 2) * t.uy),
  shifted: W.crestSegments(800, 600, 204, 10).map(s => ((s[0] + s[2]) / 2 - 400) * t.ux + ((s[1] + s[3]) / 2 - 300) * t.uy),
  small: W.crestSegments(800, 600, 204, 0, 100).length,
  phase: [W.crestPhase(8.6, 8.6), W.crestPhase(4.3, 8.6), W.crestPhase(4.3, 8.6, 10), W.crestPhase(12.9, 8.6)],
  streak: [W.streak(10), W.streak(0)],
  feat: [0, 1, 2].map(h => W.stationFeatures(st, h, 15)), onWindow: typeof window,
}));
"""], capture_output=True, text=True, check=True)
R = json.loads(out.stdout)

assert R["at"] == [3, 1, None, 5, 2], R["at"]
assert abs(R["south"]["ux"]) < 1e-9 and abs(R["south"]["uy"] + 1) < 1e-9, R["south"]
assert R["n350"]["uy"] > 0.98 and 0 < R["n350"]["ux"] < 0.2, R["n350"]   # from the north, so down the screen, a little right
assert abs(R["unit"] - 1) < 1e-9
print("  wallmap: hours and directions")

assert R["n"] > 10 and all(abs(d) < 1e-9 for d in R["dot"]), "every crest is square to the way the swell goes"
assert all(abs(g - 26) < 1e-9 for g in R["gap"]), R["gap"][:3]
assert all(l >= (800 ** 2 + 600 ** 2) ** .5 - 1e-6 for l in R["len"]), "each line spans the box whatever the angle"
assert R["small"] < R["n"], "wider spacing, fewer crests"
assert any(abs((o - 10) % 26) < 1e-9 or abs((o - 10) % 26 - 26) < 1e-9 for o in R["shifted"]), "phase shifts the lines along the direction"
assert R["phase"][0] == 0 and abs(R["phase"][1] - 13) < 1e-9 and abs(R["phase"][2] - 5) < 1e-9 and abs(R["phase"][3] - 13) < 1e-9, R["phase"]
assert R["streak"] == [{"v": 58, "tail": 35}, {"v": 8, "tail": 10}], R["streak"]
print("  wallmap: crests, phase and streaks")

f0, f1, f2 = R["feat"]
assert f0["type"] == "FeatureCollection" and len(f0["features"]) == 2
p = lambda f, i: f["features"][i]["properties"]
assert (p(f0, 0)["v"], p(f0, 0)["over"]) == (10, False) and (p(f2, 0)["v"], p(f2, 0)["over"]) == (40, True)
assert (p(f1, 0)["v"], p(f1, 0)["over"]) == (-1, False), "a station with no reading is -1 and never over the line"
assert (p(f0, 1)["v"], p(f0, 1)["over"]) == (-1, False)
assert f0["features"][0]["geometry"] == {"type": "Point", "coordinates": [115.2, -8.7]}
assert R["onWindow"] == "undefined"
print("  wallmap: stations as features")
