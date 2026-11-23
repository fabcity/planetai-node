#!/usr/bin/env python3
"""The weekly sensor report, a second Grafana dashboard that ships with the node (docs/site/grafana.md).

One source, two languages: config/grafana/dashboards/report-en.json and report-id.json are written from this file,
and tests/test_grafana.py fails when they drift from it. A third language is one more column in WORDS.

    python3 tools/gen_grafana_report.py          # write both
    python3 tools/gen_grafana_report.py --check  # exit 1 if a file on disk is not what this would write

What it counts, and the SQL, are in app/weekly.py: the node's Report tab runs the same queries (GET /weekly).
Asked for by a Bali Air Dispatch reader, 23 Nov 2026.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
from weekly import (  # noqa: E402 — the report's SQL, written once for Grafana and the node's page (app/weekly.py)
    FULL_DAY, WORDS, V_METRIC, V_SENSOR, sql_weeks, sql_badweeks, sql_daily, sql_baddays, sql_hours)

OUT = "config/grafana/dashboards/report-%s.json"
DS = {"type": "grafana-postgresql-datasource", "uid": "planetai-node"}


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
