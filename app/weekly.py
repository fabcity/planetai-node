"""The weekly sensor report's counting, written once (PR #410, 23 Nov 2026).

Two readers use it. tools/gen_grafana_report.py writes the keeper's Grafana dashboards from it, and GET /weekly runs
the same queries for the Report tab in the Data door, which anyone may open. The SQL carries Grafana's placeholders
(${metric}, ${sensor:sqlstring}, ${bad}, ${high}, $__timeFilter); bind() turns them into psycopg parameters for the
node, so nothing a visitor types ever becomes SQL text.

What it counts, for the sensors picked:
  a bad day     a day whose 24-hour mean is over ${bad}, heard for at least FULL_DAY of its hours
  over the high each time an hourly mean rises past ${high}; an episode counts once, on the day it began
  the medians   of the hourly means, per day and per week, beside the median of every outdoor sensor the node reads
  the verdict   bad days against the week before, the weekly median breaking a tie when it moved more than BAND
Everything reads readings_1h, the node's hourly means, so a sensor that sends every minute and one that sends every
quarter of an hour are counted the same way.
"""

FULL_DAY = 18   # hours heard before a day is counted, the usual three quarters for a 24-hour mean
MIN_DAYS = 5    # counted days a week needs, and the week before it, for a verdict
BAND = 0.10     # the weekly median has to move this share to break a tie in bad days

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
