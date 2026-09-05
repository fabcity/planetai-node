# coast

Waves, swell and sea temperature at the nearest ocean grid cell, every poll, from Open-Meteo's Marine API.
Free, key-free, global. A **code pack**: it ships `adapter.py`, so it loads only with `PACKS_ALLOW_CODE=1`.

**What it adds** — six metrics on `marine-point` (kind `model`, scale `bioregion`); a `heavy_swell` rule (≥ 2.5 m
at ≥ 12 s, the combination that means strong currents on exposed beaches); a daily `sea_warm_anomaly` when the sea is
a degree above its own last two months; and a `Environmental|Bioregion` cell for 7-day sea temperature, `partial`
forever because it is a model.

**Refuses inland.** The API snaps to the nearest ocean cell however far that is. The adapter measures the distance
and raises if it is over `COAST_MAX_KM` (30), so a node in Ubud does not receive the weather of a sea it cannot see.

**Where it was learned.** Kuta Selatan, 5 Sep 2026: the nearest cell was 5 km off the Bukit; 1.7 m at 11.8 s from
203°, sea 27.4 °C. Thresholds are for that coast; Barcelona's Mediterranean would set them lower.

**Attribution.** Open-Meteo Marine API (CC BY 4.0), carrying Copernicus Marine / MeteoFrance MFWAM model data.
