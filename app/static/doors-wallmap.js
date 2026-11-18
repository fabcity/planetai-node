'use strict';
/* WALLMAP — the Wall as a satellite map (SPEC wall-scales-map, 18 Nov 2026). Two halves: a pure one that holds the
   numbers (which hour a reading is read at, which way the wind and the swell move on the screen, how a station is
   coloured), and a DOM one that mounts the map and draws the crests and streaks on a canvas over it. Screen y grows
   downward, and a direction is a meteorological "from" bearing in degrees: 0 is from the north, so that wind blows toward
   the south, down the screen. The pure half has no DOM and no D, and is what tests/test_doors_wallmap.py runs. */

/* ---- pure: no DOM ---- */

/* the reading at hour h; with none there, the nearest hour that has one, the earlier hour first on a tie; null if the
   whole day is empty (a gap in a station is shown as a gap, never as the neighbour's number passed off as its own) */
const atHour = (v, h) => {
  for (let d = 0; d < v.length; d++) {
    if (v[h - d] != null) return v[h - d];
    if (v[h + d] != null) return v[h + d];
  }
  return null;
};

/* the unit vector on the screen the air or the water moves along: a "from" bearing turned half a circle, y down */
const toward = fromDeg => {
  const a = (fromDeg + 180) * Math.PI / 180;
  return { ux: Math.sin(a), uy: -Math.cos(a) };
};

/* parallel crest lines [x1, y1, x2, y2] across a w×h box, square to the way the swell goes and `spacingPx` apart; each
   runs the box's whole diagonal so no angle leaves a corner bare, and `phasePx` slides them along the direction */
const crestSegments = (w, h, waveFromDeg, phasePx, spacingPx = 26) => {
  const { ux, uy } = toward(waveFromDeg), cx = w / 2, cy = h / 2, R = Math.hypot(w, h) / 2, out = [];
  for (let o = phasePx % spacingPx - Math.ceil(R / spacingPx) * spacingPx; o <= R; o += spacingPx) {
    const mx = cx + ux * o, my = cy + uy * o;
    out.push([mx + uy * R, my - ux * R, mx - uy * R, my + ux * R]);
  }
  return out;
};

/* how far the crests have travelled in a spacing at time t, so one wave period moves them exactly one spacing and the
   loop has no jump */
const crestPhase = (tSeconds, periodS, spacingPx = 26) => (tSeconds / periodS % 1) * spacingPx;

/* a wind streak's speed in px/s and its tail in px from the wind in km/h; the steps are what reads at a wall's distance */
const streak = kmh => ({ v: 8 + 5 * kmh, tail: 10 + 2.5 * kmh });

/* the stations as GeoJSON at hour h; v is −1 for a gap (the layer draws it grey), over is above the clean-air line */
const stationFeatures = (stations, h, line) => ({ type: 'FeatureCollection', features: stations.map(s => {
  const v = (s.pm25 || [])[h] ?? null;
  return { type: 'Feature', geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
    properties: { v: v ?? -1, over: v != null && v > line } };
}) });

if (typeof window !== 'undefined') Object.assign(window, { atHour, toward, crestSegments, crestPhase, streak, stationFeatures });
if (typeof module !== 'undefined') module.exports = { atHour, toward, crestSegments, crestPhase, streak, stationFeatures };
