#!/usr/bin/env python3
"""The weekly sensor report, a second Grafana dashboard that ships with the node (docs/site/grafana.md).

One source, two languages: config/grafana/dashboards/report-en.json and report-id.json are written from this file,
and tests/test_grafana.py fails when they drift from it. A third language is one more column in WORDS.

    python3 tools/gen_grafana_report.py          # write both
    python3 tools/gen_grafana_report.py --check  # exit 1 if a file on disk is not what this would write

What it counts, for the sensors picked at the top (asked for by a Bali Air Dispatch reader, 23 Nov 2026):
  a bad day     a day whose 24-hour mean is over ${bad}, heard for at least FULL_DAY of its hours
  over the high each time an hourly mean rises past ${high}; an episode counts once, on the day it began
  the medians   of the hourly means, per day and per week, beside the median of every outdoor sensor the node reads
  the verdict   bad days against the week before, the weekly median breaking a tie when it moved more than BAND
Everything reads readings_1h, the node's hourly means, so a sensor that sends every minute and one that sends every
quarter of an hour are counted the same way.
"""
import json
import sys

FULL_DAY = 18   # hours heard before a day is counted, the usual three quarters for a 24-hour mean
MIN_DAYS = 5    # counted days a week needs, and the week before it, for a verdict
BAND = 0.10     # the weekly median has to move this share to break a tie in bad days
OUT = "config/grafana/dashboards/report-%s.json"
DS = {"type": "grafana-postgresql-datasource", "uid": "planetai-node"}

WORDS = {
    "en": {
        "title": "Weekly sensor report", "other": "id", "other_name": "Bahasa Indonesia",
        "v_metric": "Metric", "v_sensor": "Sensors", "v_bad": "Bad day over (24 h mean)", "v_high": "High over (1 h mean)",
        "p_how": "How to read it", "p_weeks": "Week by week", "p_badweeks": "Bad days in each week",
        "p_daily": "Daily median, beside all sensors' median", "p_baddays": "The bad days, and how often each went over the high",
        "p_hours": "Hour by hour, with the high line",
        "how": ("A **bad day** is a day whose 24-hour mean is over the first line set at the top. It starts at 15, the "
                "WHO guideline for PM2.5 in µg/m³. The sensor went **over the high** each time an hourly mean rose past "
                "the second line. That one starts at 55, where Indonesia's air index (ISPU) turns unhealthy. Set both "
                "to your own lines, and set them again for any other metric.\n\n"
                "A day is counted when the sensor was heard for 18 of its 24 hours. A median is the middle hour of the "
                "day or the week. **All sensors** is the median of every outdoor sensor this node reads. A week is "
                "judged against the week before it, on its bad days first and on its median when the bad days are "
                "equal.\n\n"
                "The readings are shown as each sensor sent them. Nothing here is calibrated against a reference "
                "station."),
        "week": "week from", "day": "day", "sensor": "sensor", "days": "days counted", "bad_days": "bad days",
        "high_times": "times over the high", "high_hours": "hours over the high", "peak": "highest hour", "at": "at",
        "hours": "hours heard", "mean": "24 h mean", "median": "median", "wmedian": "weekly median",
        "all": "all sensors' median", "diff": "against all sensors", "verdict": "against the week before",
        "improving": "improving", "worse": "worse", "stable": "stable", "open": "week not over", "thin": "too few days",
        "first": "no week before", "high_line": "high line",
    },
    "id": {
        "title": "Laporan mingguan sensor", "other": "en", "other_name": "English",
        "v_metric": "Metrik", "v_sensor": "Sensor", "v_bad": "Hari buruk di atas (rerata 24 jam)", "v_high": "Tinggi di atas (rerata 1 jam)",
        "p_how": "Cara membaca", "p_weeks": "Minggu ke minggu", "p_badweeks": "Hari buruk tiap minggu",
        "p_daily": "Median harian, dibanding median semua sensor", "p_baddays": "Hari-hari buruk, dan berapa kali melewati batas tinggi",
        "p_hours": "Jam ke jam, dengan garis batas tinggi",
        "how": ("**Hari buruk** adalah hari dengan rerata 24 jam di atas batas pertama di bagian atas. Awalnya 15, "
                "pedoman WHO untuk PM2.5 dalam µg/m³. Sensor dihitung **melewati batas tinggi** setiap kali rerata satu "
                "jam naik melewati batas kedua. Awalnya 55, saat ISPU masuk kategori tidak sehat. Ubah keduanya sesuai "
                "batas Anda sendiri, dan ubah lagi untuk metrik lain.\n\n"
                "Satu hari dihitung bila sensor mengirim data 18 dari 24 jam. Median adalah nilai tengah dari jam-jam "
                "dalam sehari atau seminggu. **Semua sensor** adalah median semua sensor luar ruang yang dibaca node "
                "ini. Tiap minggu dibandingkan dengan minggu sebelumnya, pertama dari jumlah hari buruk, lalu dari "
                "median bila jumlah hari buruknya sama.\n\n"
                "Angka ditampilkan seperti yang dikirim tiap sensor. Belum ada yang dikalibrasi dengan stasiun acuan."),
        "week": "minggu mulai", "day": "tanggal", "sensor": "sensor", "days": "hari terhitung", "bad_days": "hari buruk",
        "high_times": "kali melewati batas tinggi", "high_hours": "jam di atas batas tinggi", "peak": "jam tertinggi", "at": "pukul",
        "hours": "jam terukur", "mean": "rerata 24 jam", "median": "median", "wmedian": "median mingguan",
        "all": "median semua sensor", "diff": "selisih dengan semua sensor", "verdict": "dibanding minggu sebelumnya",
        "improving": "membaik", "worse": "memburuk", "stable": "stabil", "open": "minggu berjalan", "thin": "data kurang",
        "first": "belum ada minggu sebelumnya", "high_line": "batas tinggi",
    },
}

# The pickers. A sensor is offered when it reported the metric in the last 30 days; the household's own come first.
V_METRIC = ("SELECT DISTINCT r.metric FROM readings_1h r JOIN sensors s USING (sensor_id) WHERE s.kind = 'sensor' "
            "AND r.bucket > now() - interval '30 days' AND r.bucket <= now() ORDER BY 1")
V_SENSOR = ("SELECT coalesce(nullif(s.room, ''), nullif(s.name, ''), s.sensor_id) AS __text, s.sensor_id AS __value "
            "FROM sensors s WHERE s.kind = 'sensor' AND EXISTS (SELECT 1 FROM readings_1h r WHERE r.sensor_id = s.sensor_id "
            "AND r.metric = '${metric}' AND r.bucket > now() - interval '30 days' AND r.bucket <= now()) "
            "ORDER BY s.indoor IS TRUE, s.local DESC, 1")

# The shared steps. h: the picked sensors' hours. e: h with the hours that began an episode over the high marked.
# d: one row per sensor and day. o: the hours of every outdoor sensor the node reads. sn: what to call a sensor.
H = ("h AS (SELECT r.sensor_id, r.bucket, r.mean AS v FROM readings_1h r WHERE $__timeFilter(r.bucket) "
     "AND r.bucket <= now() AND r.metric = '${metric}' AND r.sensor_id IN (${sensor:sqlstring}))")
E = ("e AS (SELECT *, v > ${high} AND NOT coalesce(lag(v) OVER (PARTITION BY sensor_id ORDER BY bucket) > ${high}, false) "
     "AS rose FROM h)")
D = ("d AS (SELECT sensor_id, date_trunc('day', bucket) AS day, count(*) AS hours, avg(v) AS mean, "
     "percentile_cont(0.5) WITHIN GROUP (ORDER BY v) AS median, max(v) AS peak, "
     "(array_agg(bucket ORDER BY v DESC))[1] AS peak_at, count(*) FILTER (WHERE v > ${high}) AS high_hours, "
     "count(*) FILTER (WHERE rose) AS high_times FROM e GROUP BY 1, 2)")
O = ("o AS (SELECT r.sensor_id, r.bucket, r.mean AS v FROM readings_1h r JOIN sensors s USING (sensor_id) "
     "WHERE $__timeFilter(r.bucket) AND r.bucket <= now() AND r.metric = '${metric}' AND s.kind = 'sensor' "
     "AND s.indoor IS NOT TRUE)")
SN = "sn AS (SELECT sensor_id, coalesce(nullif(room, ''), nullif(name, ''), sensor_id) AS label FROM sensors)"
W = ("w AS (SELECT sensor_id, date_trunc('week', day) AS week, count(*) FILTER (WHERE hours >= %d) AS days, "
     "count(*) FILTER (WHERE hours >= %d AND mean > ${bad}) AS bad_days, sum(high_times) AS high_times, "
     "sum(high_hours) AS high_hours, max(peak) AS peak FROM d GROUP BY 1, 2)" % (FULL_DAY, FULL_DAY))


def lit(word):
    """A word as a SQL string. "all sensors' median" carries an apostrophe."""
    return "'" + word.replace("'", "''") + "'"


def all_median(unit):
    """Each outdoor sensor's median for the day or week, then the median across the sensors: one sensor, one voice."""
    return ("a AS (SELECT t, percentile_cont(0.5) WITHIN GROUP (ORDER BY m) AS all_median FROM (SELECT sensor_id, "
            "date_trunc('%s', bucket) AS t, percentile_cont(0.5) WITHIN GROUP (ORDER BY v) AS m FROM o GROUP BY 1, 2) q "
            "GROUP BY 1)" % unit)


def sql_weeks(L):
    return ("WITH " + ", ".join([H, E, D, O, SN, W, all_median("week")]) + ", "
            "wm AS (SELECT sensor_id, date_trunc('week', bucket) AS week, percentile_cont(0.5) WITHIN GROUP (ORDER BY v) "
            "AS median FROM h GROUP BY 1, 2), "
            "j AS (SELECT w.*, wm.median, lag(w.week) OVER p AS pweek, lag(w.days) OVER p AS pdays, "
            "lag(w.bad_days) OVER p AS pbad, lag(wm.median) OVER p AS pmedian FROM w JOIN wm USING (sensor_id, week) "
            "WINDOW p AS (PARTITION BY w.sensor_id ORDER BY w.week)) "
            f"SELECT to_char(j.week, 'YYYY-MM-DD') AS \"{L['week']}\", sn.label AS \"{L['sensor']}\", j.bad_days AS \"{L['bad_days']}\", "
            f"CASE WHEN j.week + interval '7 days' > now() THEN {lit(L['open'])} WHEN j.pweek IS NULL THEN {lit(L['first'])} "
            f"WHEN j.pweek <> j.week - interval '7 days' OR j.days < {MIN_DAYS} OR j.pdays < {MIN_DAYS} THEN {lit(L['thin'])} "
            f"WHEN j.bad_days < j.pbad THEN {lit(L['improving'])} WHEN j.bad_days > j.pbad THEN {lit(L['worse'])} "
            f"WHEN j.median < j.pmedian * {1 - BAND} THEN {lit(L['improving'])} "
            f"WHEN j.median > j.pmedian * {1 + BAND} THEN {lit(L['worse'])} ELSE {lit(L['stable'])} END AS \"{L['verdict']}\", "
            f"j.high_times AS \"{L['high_times']}\", j.high_hours AS \"{L['high_hours']}\", round(j.peak::numeric) AS \"{L['peak']}\", "
            f"round(j.median::numeric, 1) AS \"{L['wmedian']}\", round(a.all_median::numeric, 1) AS \"{L['all']}\", "
            f"round((j.median - a.all_median)::numeric, 1) AS \"{L['diff']}\", j.days AS \"{L['days']}\" "
            "FROM j JOIN sn USING (sensor_id) LEFT JOIN a ON a.t = j.week ORDER BY j.week DESC, sn.label")


def sql_badweeks(L):
    return ("WITH " + ", ".join([H, E, D, SN, W]) + " SELECT w.week AS time, sn.label AS metric, w.bad_days AS value "
            "FROM w JOIN sn USING (sensor_id) ORDER BY 1")


def sql_daily(L):
    return ("WITH " + ", ".join([H, O, SN, all_median("day")]) + " "
            "SELECT date_trunc('day', h.bucket) AS time, sn.label AS metric, "
            "percentile_cont(0.5) WITHIN GROUP (ORDER BY h.v) AS value FROM h JOIN sn USING (sensor_id) GROUP BY 1, 2 "
            f"UNION ALL SELECT a.t, {lit(L['all'])}, a.all_median FROM a ORDER BY 1")


def sql_baddays(L):
    return ("WITH " + ", ".join([H, E, D, O, SN, all_median("day")]) + " "
            f"SELECT to_char(d.day, 'YYYY-MM-DD') AS \"{L['day']}\", sn.label AS \"{L['sensor']}\", d.hours AS \"{L['hours']}\", "
            f"round(d.mean::numeric, 1) AS \"{L['mean']}\", round(d.median::numeric, 1) AS \"{L['median']}\", "
            f"round(a.all_median::numeric, 1) AS \"{L['all']}\", d.high_times AS \"{L['high_times']}\", "
            f"d.high_hours AS \"{L['high_hours']}\", round(d.peak::numeric) AS \"{L['peak']}\", "
            f"to_char(d.peak_at, 'HH24:MI') AS \"{L['at']}\" "
            "FROM d JOIN sn USING (sensor_id) LEFT JOIN a ON a.t = d.day WHERE d.mean > ${bad} ORDER BY d.day DESC, sn.label")


def sql_hours(L):
    return ("WITH " + ", ".join([H, SN]) + " SELECT h.bucket AS time, sn.label AS metric, h.v AS value "
            f"FROM h JOIN sn USING (sensor_id) UNION ALL SELECT x.t, {lit(L['high_line'])}, ${{high}} "
            "FROM (VALUES ($__timeFrom()::timestamptz), (least($__timeTo()::timestamptz, now()))) x(t) ORDER BY 1")


def panel(pid, kind, title, grid, sql=None, fmt="table", **more):
    p = {"id": pid, "type": kind, "title": title, "gridPos": dict(zip("xywh", grid)), "datasource": DS}
    if sql:
        p["targets"] = [{"refId": "A", "datasource": DS, "format": fmt, "rawQuery": True, "rawSql": sql}]
    p.update(more)
    return p


def by_name(name, **props):
    return {"matcher": {"id": "byName", "options": name}, "properties": [{"id": k, "value": v} for k, v in props.items()]}


def steps(*pairs):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for c, v in pairs]}


def lines(gap_ms, **custom):
    return {"defaults": {"custom": {"drawStyle": "line", "lineWidth": 2, "showPoints": "never", "spanNulls": False,
                                    "insertNulls": gap_ms, **custom}}, "overrides": []}


TABLE = {"custom": {"align": "auto", "minWidth": 70, "wrapHeaderText": True}}   # eleven columns have to fit a laptop without scrolling sideways
ONE = {"decimals": 1}


def dashboard(lang):
    L = WORDS[lang]
    text_cell, back_cell = {"type": "color-text"}, {"type": "color-background", "mode": "basic"}
    verdict = [{"type": "value", "options": {L["improving"]: {"color": "green", "index": 0}, L["worse"]: {"color": "red", "index": 1},
                                             L["stable"]: {"color": "blue", "index": 2}}}]
    weeks = panel(2, "table", L["p_weeks"], (0, 6, 24, 11), sql_weeks(L), fieldConfig={"defaults": TABLE, "overrides": [
        by_name(L["sensor"], **{"custom.width": 230}),
        by_name(L["bad_days"], **{"custom.cellOptions": back_cell, "thresholds": steps(("transparent", None), ("orange", 1), ("red", 3))}),
        by_name(L["wmedian"], **ONE, **{"custom.cellOptions": back_cell, "thresholds": steps(("dark-blue", None))}),
        by_name(L["all"], **ONE, **{"custom.cellOptions": back_cell, "thresholds": steps(("dark-blue", None))}),
        by_name(L["diff"], **ONE, **{"custom.cellOptions": text_cell, "thresholds": steps(("green", None), ("orange", 0.05))}),
        by_name(L["verdict"], **{"custom.cellOptions": text_cell, "mappings": verdict, "thresholds": steps(("text", None)), "custom.width": 170}),
    ]})
    badweeks = panel(3, "timeseries", L["p_badweeks"], (0, 17, 9, 8), sql_badweeks(L), "time_series", fieldConfig={
        "defaults": {"min": 0, "max": 7, "decimals": 0, "custom": {"drawStyle": "line", "lineInterpolation": "stepAfter",
                     "lineWidth": 2, "fillOpacity": 15, "showPoints": "always", "pointSize": 7, "spanNulls": False,
                     "insertNulls": 8 * 86400000}}, "overrides": []})
    daily = panel(4, "timeseries", L["p_daily"], (9, 17, 15, 8), sql_daily(L), "time_series", fieldConfig=lines(36 * 3600000))
    daily["fieldConfig"]["overrides"] = [by_name(L["all"], **{"custom.lineStyle": {"fill": "dash", "dash": [8, 6]},
                                                             "custom.lineWidth": 3, "color": {"mode": "fixed", "fixedColor": "text"}})]
    baddays = panel(5, "table", L["p_baddays"], (0, 25, 24, 10), sql_baddays(L), fieldConfig={"defaults": TABLE, "overrides": [
        by_name(L["sensor"], **{"custom.width": 230}),
        by_name(L["hours"], **{"custom.cellOptions": text_cell, "thresholds": steps(("red", None), ("text", FULL_DAY))}),
        by_name(L["mean"], **ONE),
        by_name(L["median"], **ONE, **{"custom.cellOptions": back_cell, "thresholds": steps(("dark-blue", None))}),
        by_name(L["all"], **ONE, **{"custom.cellOptions": back_cell, "thresholds": steps(("dark-blue", None))}),
        by_name(L["high_times"], **{"custom.cellOptions": back_cell, "thresholds": steps(("transparent", None), ("orange", 1), ("red", 3))}),
    ]})
    hours = panel(6, "timeseries", L["p_hours"], (0, 35, 24, 9), sql_hours(L), "time_series", fieldConfig=lines(3 * 3600000))
    hours["fieldConfig"]["overrides"] = [by_name(L["high_line"], **{"custom.insertNulls": False, "custom.spanNulls": True,
                                                                   "custom.lineStyle": {"fill": "dash", "dash": [8, 6]},
                                                                   "color": {"mode": "fixed", "fixedColor": "red"}})]
    for p in (badweeks, daily, hours):
        p["options"] = {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi", "sort": "desc"}}

    def query_var(name, label, query, **more):
        return {"name": name, "label": label, "type": "query", "datasource": DS, "query": query, "definition": query,
                "refresh": 2, "sort": 0, **more}

    def text_var(name, label, value):
        return {"name": name, "label": label, "type": "textbox", "query": value, "current": {"text": value, "value": value},
                "options": [{"selected": True, "text": value, "value": value}]}

    return {
        "uid": "planetai-report-" + lang, "title": L["title"], "tags": ["planetai", "report"], "schemaVersion": 39, "version": 1,
        "editable": True, "graphTooltip": 1, "timezone": "", "weekStart": "monday", "refresh": "",
        "time": {"from": "now-8w/w", "to": "now"},
        "links": [{"type": "link", "title": L["other_name"], "url": "/d/planetai-report-" + L["other"], "keepTime": True,
                   "includeVars": True, "targetBlank": False}],
        "annotations": {"list": []},
        "templating": {"list": [
            query_var("metric", L["v_metric"], V_METRIC, current={"text": "pm25", "value": "pm25"}),
            query_var("sensor", L["v_sensor"], V_SENSOR, multi=True, includeAll=False),
            text_var("bad", L["v_bad"], "15"),
            text_var("high", L["v_high"], "55"),
        ]},
        "panels": [
            panel(1, "text", L["p_how"], (0, 0, 24, 6), options={"mode": "markdown", "content": L["how"]}),
            weeks, badweeks, daily, baddays, hours,
        ],
    }


def render(lang):
    return json.dumps(dashboard(lang), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    stale = []
    for lang in WORDS:
        if "--check" in sys.argv:
            try:
                same = open(OUT % lang, encoding="utf-8").read() == render(lang)
            except FileNotFoundError:
                same = False
            if not same:
                stale.append(OUT % lang)
        else:
            open(OUT % lang, "w", encoding="utf-8").write(render(lang))
            print("wrote", OUT % lang)
    if stale:
        sys.exit("stale, run python3 tools/gen_grafana_report.py: " + ", ".join(stale))
