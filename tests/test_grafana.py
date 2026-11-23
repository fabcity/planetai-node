"""The grafana profile (docs/site/grafana.md): the keeper's own panels over this node's readings, beside the dashboard.

What has to stay true for it to be safe to ship: it is off unless asked for, it reaches the database only as a
read-only login that cannot see settings, it is not handed the node's secrets, and the starter dashboard does not
draw tomorrow's forecast as a measurement or bridge a sensor's silence with a line. Proven against a copy of node
#1's database on 24 Oct 2026; this holds the files to what was proven.

    python3 tests/test_grafana.py
"""
import json
import os
import re
import subprocess
import sys

import yaml

fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


compose = yaml.safe_load(open("docker-compose.yml"))
svc = compose["services"]
role, graf = svc.get("grafana-role", {}), svc.get("grafana", {})

print("compose: off unless asked for, and handed nothing it does not read")
check(role.get("profiles") == ["grafana"] and graf.get("profiles") == ["grafana"], "both services are in the grafana profile only")
check("env_file" not in role and "env_file" not in graf, "neither is handed the whole .env")
check(set(role.get("environment", {})) == {"PGHOST", "PGUSER", "PGDATABASE", "PGPASSWORD", "NODE_TZ"},
      "grafana-role reads exactly the five keys it needs")
check(not any("POSTGRES" in k or "TOKEN" in k for k in graf.get("environment", {})), "grafana holds no database password or node token")
check(graf.get("ports") == ["${GRAFANA_BIND:-127.0.0.1}:${GRAFANA_PORT:-3000}:3000"], "grafana listens on loopback unless GRAFANA_BIND says otherwise")
check(re.fullmatch(r"grafana/grafana-oss:\d+\.\d+\.\d+", graf.get("image", "")) is not None, "the grafana image is pinned to a release")
check(graf.get("depends_on", {}).get("grafana-role", {}).get("condition") == "service_completed_successfully",
      "grafana waits for its login to exist")
check({"grafana", "grafana-secret"} <= set(compose.get("volumes", {})), "its two volumes are declared")
check(any(v.endswith(":/secret:ro") for v in graf.get("volumes", [])), "grafana reads the password volume read-only")

print("role.sh: a member of planetai_ro, and less")
sh = open("config/grafana/role.sh").read()
check("GRANT planetai_ro TO planetai_grafana;" in sh, "planetai_grafana inherits planetai_ro, which init.sql keeps off settings")
check("default_transaction_read_only = on" in sh, "every session it opens is read-only")
check("statement_timeout = '30s'" in sh, "a query stops at 30 s")
check("CONNECTION LIMIT 4" in sh, "four connections at most")
check(not re.search(r"\bGRANT\s+(SELECT|ALL|INSERT|UPDATE|DELETE)\b|SUPERUSER|CREATEROLE|\bsettings\b", sh.split("set -eu", 1)[1]),
      "it grants nothing of its own")
check(":'pw'" in sh and "<<'SQL'" in sh, "the password reaches psql as a variable, never through the shell")

print("provisioning: the node's database, as that login")
ds = yaml.safe_load(open("config/grafana/provisioning/datasources/node.yml"))["datasources"][0]
check(ds["uid"] == "planetai-node" and ds["user"] == "planetai_grafana", "the datasource logs in as planetai_grafana")
check(ds["secureJsonData"]["password"] == "$__file{/secret/db_password}", "its password comes from the volume, not from .env")
check(ds.get("editable") is False, "it cannot be edited into another login from the UI")
prov = yaml.safe_load(open("config/grafana/provisioning/dashboards/node.yml"))["providers"][0]
check(prov["allowUiUpdates"] is False and prov["options"]["path"] == "/etc/grafana/dashboards",
      "the starter is replaced on update, so a keeper's edits go to their own copy")

print("starter dashboard: honest by default, and nobody's house but this one")
raw = open("config/grafana/dashboards/node.json").read()
dash = json.loads(raw)
panels = dash["panels"]
check(len({p["id"] for p in panels}) == len(panels), "panel ids are unique")
queries = [(p["title"], t["rawSql"]) for p in panels for t in p["targets"]] + [(v["name"], v["query"]) for v in dash["templating"]["list"]]
check(all(t["datasource"]["uid"] == "planetai-node" for p in panels for t in p["targets"]), "every panel reads the node's datasource")
# The forecast pack stores each hour at the time it is FOR, days ahead (packs/forecast/adapter.py). A picker set past
# now must not draw that as measured.
future = [n for n, q in queries if "readings" in q and "ts <= now()" not in q]
check(not future, "every query that reads readings stops at now()" + (f": {future}" if future else ""))
check(all("$__timeFilter(r.ts)" in t["rawSql"] for p in panels for t in p["targets"]), "every panel follows the time picker")
lines = [p["title"] for p in panels if p["type"] == "timeseries" and not p["fieldConfig"]["defaults"].get("custom", {}).get("insertNulls")]
check(not lines, "every line breaks at a silence instead of drawing across it" + (f": {lines}" if lines else ""))
node1 = [w for w in ("Kids", "Backyard", "Studio", "Living Room", "msh-", "sc-1", "Asia/Makassar", "bayu") if w in raw]
check(not node1, "nothing in it names node #1's rooms, sensors or timezone" + (f": {node1}" if node1 else ""))
check(dash["title"].endswith("no provenance"), "its title says it carries none of the page's rules")
check(all("opened_at <= now()" in a["target"]["rawSql"] for a in dash["annotations"]["list"]), "the alert annotations stop at now() too")
check("current_setting('TimeZone')" in raw, "hour of day is the session's, which role.sh sets to NODE_TZ")

print("weekly report: one source, two languages, the same honesty as the starter")
gen = subprocess.run([sys.executable, "tools/gen_grafana_report.py", "--check"], capture_output=True, text=True)
check(gen.returncode == 0, "both report files are what tools/gen_grafana_report.py writes" + (": " + gen.stderr.strip() if gen.returncode else ""))
reports = {lang: json.load(open(f"config/grafana/dashboards/report-{lang}.json", encoding="utf-8")) for lang in ("en", "id")}
uids = {dash["uid"], *(r["uid"] for r in reports.values())}
check(len(uids) == 3, "the starter and the two reports have three different uids")
for lang, rep in reports.items():
    rq = [(p["title"], t["rawSql"]) for p in rep["panels"] for t in p.get("targets", [])] + \
         [(v["name"], v["query"]) for v in rep["templating"]["list"] if v["type"] == "query"]
    check(all("readings_1h" in q and "bucket <= now()" in q for _, q in rq), f"{lang}: every query reads the hourly means and stops at now()")
    check(all("$__timeFilter(r.bucket)" in q for n, q in rq if n not in ("metric", "sensor")), f"{lang}: every panel follows the time picker")
    check(all(t["datasource"]["uid"] == "planetai-node" for p in rep["panels"] for t in p.get("targets", [])), f"{lang}: every panel reads the node's datasource")
    check(all(p["fieldConfig"]["defaults"]["custom"].get("insertNulls") for p in rep["panels"] if p["type"] == "timeseries"),
          f"{lang}: every line breaks at a silence")
    check(not [w for w in ("Kids", "Backyard", "Studio", "Living Room", "msh-", "sc-1", "Asia/Makassar", "bayu", "Kutuh") if w in json.dumps(rep)],
          f"{lang}: nothing in it names node #1's rooms, sensors or timezone")
    check(rep["links"][0]["url"] == "/d/planetai-report-" + ("id" if lang == "en" else "en"), f"{lang}: it links to the other language")
    names = "".join(q for _, q in rq)
    check(names.count("'") % 2 == 0, f"{lang}: no word with an apostrophe left a SQL string open")
shape = lambda r: [(p["id"], p["type"], p["gridPos"]) for p in r["panels"]]
check(shape(reports["en"]) == shape(reports["id"]), "the two languages are the same report")

print("one source: the report's SQL lives in app/weekly.py, for Grafana and the node's page alike")
gen_src = open("tools/gen_grafana_report.py").read()
check("from weekly import" in gen_src and "def sql_weeks" not in gen_src, "the generator imports the SQL, it does not hold a copy")
check(os.path.exists("app/weekly.py") and "def sql_weeks" in open("app/weekly.py").read(), "app/weekly.py holds the report's SQL")

# The counting itself, on a real Postgres (CI's lint job has one at RHO_PG_URL). Temporary tables stand in for
# sensors and readings_1h, so nothing of the database is read or written.
if os.getenv("RHO_PG_URL"):
    import psycopg
    sys.path.insert(0, "tools")
    import gen_grafana_report as g
    q = g.sql_weeks(g.WORDS["en"])
    for k, v in {"$__timeFilter(r.bucket)": "r.bucket BETWEEN now() - interval '60 days' AND now() + interval '7 days'",
                 "${metric}": "pm25", "${sensor:sqlstring}": "'a'", "${bad}": "15", "${high}": "55"}.items():
        q = q.replace(k, v)
    with psycopg.connect(os.environ["RHO_PG_URL"]) as c:
        c.execute("SET TIME ZONE 'UTC'")
        c.execute("CREATE TEMP TABLE sensors (sensor_id text, name text, room text, kind text, local boolean, indoor boolean)")
        c.execute("CREATE TEMP TABLE readings_1h (bucket timestamptz, sensor_id text, metric text, mean float8)")
        c.execute("INSERT INTO sensors VALUES ('a','A','','sensor',false,false), ('b','B','','sensor',false,false), "
                  "('i','I','','sensor',true,true), ('m','M','','model',false,false)")
        # a: two whole weeks at 10. Two weeks ago, three days at 20. Last week: one day with two episodes over 55
        # (05:00-06:00, 10:00), and one episode across a midnight (Thu 23:00 - Fri 00:00), which counts once.
        c.execute("""INSERT INTO readings_1h
            SELECT t, 'a', 'pm25', CASE
              WHEN t >= w - interval '14 days' AND t < w - interval '11 days' THEN 20
              WHEN t IN (w - interval '6 days' + interval '5 hours', w - interval '6 days' + interval '6 hours') THEN 60
              WHEN t = w - interval '6 days' + interval '10 hours' THEN 70
              WHEN t IN (w - interval '3 days' - interval '1 hour', w - interval '3 days') THEN 60
              ELSE 10 END
            FROM (SELECT date_trunc('week', now()) AS w) x, generate_series(w - interval '14 days', now(), interval '1 hour') t""")
        c.execute("INSERT INTO readings_1h SELECT t, s, 'pm25', v FROM (VALUES ('b', 30), ('i', 500), ('m', 1000)) y(s, v), "
                  "generate_series(date_trunc('week', now()) - interval '14 days', now(), interval '1 hour') t")
        c.execute("INSERT INTO readings_1h VALUES (now() + interval '1 day', 'a', 'pm25', 999)")   # a forecast hour
        cur = c.execute(q)
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        # The node's page runs the same five queries with bound parameters (app/weekly.py bind). On the same tables,
        # in UTC and in Bali's time zone, both readers have to return the same rows. q is a sensor whose name holds a
        # quote and a %; z never sent anything.
        sys.path.insert(0, "app")
        import weekly
        c.execute("INSERT INTO sensors VALUES ('q','O''Brien 50%','','sensor',false,false), ('z','Z','','sensor',false,false)")
        c.execute("INSERT INTO readings_1h SELECT t, 'q', 'pm25', 12 FROM "
                  "generate_series(date_trunc('week', now()) - interval '14 days', now(), interval '1 hour') t")
        t0, t1 = c.execute("SELECT now() - interval '60 days', now() + interval '7 days'").fetchone()
        params = {"t0": t0, "t1": t1, "metric": "pm25", "sensors": ["a", "q", "z"], "bad": 15, "high": 55}
        grafana = {"$__timeFilter(r.bucket)": "r.bucket BETWEEN now() - interval '60 days' AND now() + interval '7 days'",
                   "$__timeFrom()": "(now() - interval '60 days')", "$__timeTo()": "(now() + interval '7 days')",
                   "${metric}": "pm25", "${sensor:sqlstring}": "'a','q','z'", "${bad}": "15", "${high}": "55"}
        both = {}
        for tz in ("UTC", "Asia/Makassar"):
            c.execute(f"SET TIME ZONE '{tz}'")
            for part, sql_of in weekly.PARTS.items():
                sql = sql_of(weekly.WORDS["en"])
                as_grafana = sql
                for k, v in grafana.items():
                    as_grafana = as_grafana.replace(k, v)
                both[tz, part] = (c.execute(as_grafana).fetchall(), c.execute(weekly.bind(sql), params).fetchall())
        c.rollback()
    for (tz, part), (by_grafana, by_node) in both.items():
        check(by_node == by_grafana and len(by_node) > 0, f"pg: {part} in {tz}, the node's rows are Grafana's ({len(by_node)} rows)")
    # What GET /weekly offers (weekly.offer_sql), on its own temporary tables: a visitor sees the outdoor sensor on a
    # public channel, by its name; never the room, the indoor sensor, the private channel, the model, or a metric only
    # a room reads. The keeper sees them all, by room.
    sys.path.insert(0, "app")
    import packs as _packs
    with psycopg.connect(os.environ["RHO_PG_URL"]) as c:
        c.execute("CREATE TEMP TABLE sensors (sensor_id text, source text, name text, room text, kind text, local boolean, indoor boolean)")
        c.execute("CREATE TEMP TABLE channel_roles (source text, metric text, role text)")
        c.execute("CREATE TEMP TABLE readings_1h (bucket timestamptz, sensor_id text, metric text, mean float8)")
        c.execute("INSERT INTO sensors VALUES ('o1','sc','Out','Yard','sensor',true,false), ('i1','sc','Living','Living','sensor',true,true), "
                  "('p1','priv','Private','','sensor',false,false), ('m1','cams','Model','','model',false,false)")
        c.execute("INSERT INTO channel_roles VALUES ('priv','pm25','private')")
        c.execute("INSERT INTO readings_1h SELECT now() - interval '2 hours', s, m, 9 FROM "
                  "(VALUES ('o1','pm25'), ('i1','pm25'), ('i1','co2'), ('p1','pm25'), ('m1','pm25')) x(s, m)")
        offered = {}
        for private in (False, True):
            msql, osql = weekly.offer_sql(private=private, public=_packs.public_sql("r"))
            offered[private] = ({r[0] for r in c.execute(msql).fetchall()}, c.execute(osql, ("pm25",)).fetchall())
        c.rollback()
    check(offered[False][0] == {"pm25"} and [(r[0], r[1]) for r in offered[False][1]] == [("o1", "Out")],
          "pg: a visitor is offered the outdoor sensor on a public channel, by name; no room, indoor sensor, private channel or model")
    check({r[0] for r in offered[True][1]} == {"o1", "i1", "p1"} and ("o1", "Yard") in [(r[0], r[1]) for r in offered[True][1]]
          and offered[True][0] == {"pm25", "co2"}, "pg: the keeper is offered every sensor, by room")
    labels = {r[1] for r in both["UTC", "weeks"][1]}
    check("O'Brien 50%" in labels and "Z" not in labels, "pg: a name with a quote and a % is drawn; a sensor that never sent has no week")
    check(len(rows) == 3, "pg: this week, last week and the one before")
    now_, last, before = rows
    check(last["bad days"] == 1 and before["bad days"] == 3, "pg: a bad day is a counted day whose 24-hour mean is over the line")
    check(last["times over the high"] == 3 and last["hours over the high"] == 5, "pg: an episode counts once, across a midnight too")
    check(last["highest hour"] == 70 and now_["highest hour"] <= 10, "pg: the forecast hour is not read")
    check(float(last["weekly median"]) == 10 and float(last["all sensors' median"]) == 20, "pg: all sensors is the outdoor sensors, no room and no model")
    check((now_["against the week before"], last["against the week before"], before["against the week before"]) ==
          ("week not over", "improving", "no week before"), "pg: fewer bad days than the week before is improving")
else:
    print("  - the report's counting on a real database skipped (set RHO_PG_URL)")

print("cli: planetai grafana, and remove knows its volumes")
cli = open("bin/planetai").read()
check("cmd_grafana()" in cli and 'grafana) shift; cmd_grafana "$@";;' in cli and "profiles_add grafana" in cli, "planetai grafana turns the profile on")
check("DROP ROLE IF EXISTS planetai_grafana" in cli and "grep -vx grafana" in cli, "planetai grafana off takes the profile out and drops the login")
check("ipfsdata grafana grafana-secret; do" in cli and "ipfsdata|grafana|grafana-secret)$" in cli, "planetai remove names both volumes")

print(f"grafana: {'every check passed' if not fails else str(len(fails)) + ' failed'}")
sys.exit(1 if fails else 0)
