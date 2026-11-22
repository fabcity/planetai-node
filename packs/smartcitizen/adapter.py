"""Smart Citizen: this node's own kits, read from api.smartcitizen.me.

Every kit here is the household's: listed by id (SC_DEVICES) or found in its account (SC_USER, less SC_EXCLUDE), so
every one is stored `local`, indoor or outdoor from the kit's own `exposure` field. A pack since 22 Oct 2026; until then
this was app/sources.py. The sensor ids (`sc-<kit>`), the source name (`smartcitizen`) and the settings are unchanged,
so a node's history carries on. Which kits in an account are the node's own stays in the core
(sources.smartcitizen_account), because packs/bali-air-dispatch and packs/nearby ask it too.

It runs whenever a kit is configured or a broker is set: `switch: [SC_USER, SC_DEVICES, MQTT_HOST]` in pack.yaml, on
when any is set. With no kit listed it asks the API nothing. The kits that publish straight to this node's broker
(device/sck/#) are read by hooks.py, beside this.

Contract: fetch(hc) -> (sensors, readings), like everything in app/sources.py.
"""
from __future__ import annotations

import logging
import sys

import httpx

sys.path.insert(0, "/app")
import settings  # noqa: E402
import sources  # noqa: E402
from sources import _iso  # noqa: E402

log = logging.getLogger("planetai")

# Map on measurement *name*, not sensor id — ids change between kit generations (2.1 vs 2.3), names don't.
SC_METRICS = {
    "PM2.5": "pm25", "PM10": "pm10", "PM1": "pm1",
    "Air Temperature": "temp", "Relative Humidity": "humidity", "Barometric Pressure": "pressure",
    # `Bosch BME68X - AQI` is the BME680's own gas index, not an air quality index. Bali Air Dispatch's IQAir rows
    # publish a real `aqi`; keeping both under one name made an average of two different quantities.
    "AQI": "bme_iaq",
    "Gas Resistance": "gas_resistance", "Noise Level": "noise", "Light": "light",
    "eCO2": "eco2", "TVOC": "tvoc",
}
# A box can carry two particle sensors (a DIY node's HM-3301 beside a SEN5X, 22 Nov 2026). Both are "PM2.5" to the
# platform, and two rows with one key reach an insert that keeps the first: one sensor was dropped without a word.
# The first by sensor name keeps the plain metric, which is the one that always had it (the API lists by name), so a
# box's history carries on. A later one is stored beside it as pm25_<model>, private (config/channels.yml), for
# these three; any other second sensor is still dropped, because a metric with no declared role is public.
# Written out, not built from the model's name: tools/check_docs.py reads this file for every metric a channel declares.
SC_SECOND_PM = {
    "SEN5X": {"pm1": "pm1_sen5x", "pm25": "pm25_sen5x", "pm10": "pm10_sen5x"},
    "HM-3301": {"pm1": "pm1_hm3301", "pm25": "pm25_hm3301", "pm10": "pm10_hm3301"},
    "PMS5003": {"pm1": "pm1_pms5003", "pm25": "pm25_pms5003", "pm10": "pm10_pms5003"},
}
_dropped: set = set()


def smartcitizen(hc: httpx.Client, device_ids: list[int]):
    """Every kit here is yours (listed by id or discovered from your account), so every one is local. Indoor or
    outdoor comes from the kit's own `exposure` field, which is what the rules use to tell the house from the street."""
    sensors, readings = [], []
    for did in device_ids:
        r = hc.get(f"https://api.smartcitizen.me/v0/devices/{did}")
        r.raise_for_status()
        d = r.json()
        data = d.get("data") or {}
        loc = d.get("location") or data.get("location") or {}
        ts = _iso(data.get("recorded_at") or d.get("last_reading_at"))
        sid = f"sc-{did}"
        sensors.append({
            "sensor_id": sid, "source": "smartcitizen", "name": d.get("name") or sid,
            "lat": loc.get("latitude"), "lon": loc.get("longitude"),
            "indoor": (loc.get("exposure") == "indoor"),
            "local": True,
            "meta": {"hardware": (d.get("hardware") or {}).get("name"), "state": d.get("state"),
                     "url": f"https://smartcitizen.me/kits/{did}"},
        })
        seen = set()
        for s in sorted(data.get("sensors") or [], key=lambda s: str(s.get("name") or "")):
            m = s.get("measurement") or {}
            metric = SC_METRICS.get(m.get("name") if isinstance(m, dict) else m)
            if not metric or s.get("value") is None:
                continue
            at = ts         # the kit's time, as always: trust/channel_dead finds a dead channel by the flat day this draws
            if metric in seen:
                name = str(s.get("name") or "")
                second = next((v.get(metric) for k, v in SC_SECOND_PM.items() if k in name), None)
                if not second or second in seen:
                    if (did, name) not in _dropped:
                        _dropped.add((did, name)); log.info("smartcitizen: kit %s has a second %s, %r, and it is not stored", did, metric, name)
                    continue
                metric = second
                # the second sensor's own time. A sensor that stopped weeks ago is still listed with its last value
                # (kit 20137's HM-3301, quiet since 29 Oct, read 16.0 at every poll), and no rule watches a private
                # channel for a flat day, so under the kit's time it would be stored as fresh for ever.
                at = _iso(s.get("last_reading_at")) or ts
            if at is None:
                continue
            seen.add(metric)
            readings.append((at, sid, metric, float(s["value"])))
    return sensors, readings


def fetch(hc):
    """The kits listed by id, and those an account has published from in the last three days, less the excluded."""
    ids = {int(x) for x in settings.get("SC_DEVICES", "").replace(" ", "").split(",") if x}
    if settings.get("SC_USER", "").strip():
        try:
            exclude = {int(x) for x in settings.get("SC_EXCLUDE", "").replace(" ", "").split(",") if x}
            ids |= set(sources.smartcitizen_account(hc, settings.get("SC_USER").strip(), exclude=exclude))
        except Exception as e:  # noqa: BLE001
            log.warning("smartcitizen account discovery failed: %s", e)
    ids = sorted(ids)
    return smartcitizen(hc, ids) if ids else ([], [])
