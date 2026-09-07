"""When the node writes a report, and what an updating node inherits.

The bug this file exists for: three schedules sending messages from two containers, none of them aware of the
others. Node #1's household got the 06:00 report from the app, nothing at all from the agent's 07:00 attempt
(it passed a tuple to Telegram and logged a 400 every morning since v0.30), and a digest every three hours that
only reached the phone at ALERT_LEVEL=info. Everything here runs offline, against the files themselves.
"""
import os, sys

os.environ.setdefault("DATABASE_URL", "postgresql://x/x")
sys.path.insert(0, "app")

import settings as st

# ---------------------------------------------------------------- what an updating node inherits
# A fresh install: nothing to move, and the defaults are 6 and 6.
assert st.brief_migration({}) == {}
assert st.brief_migration({"ALERT_LEVEL": "act"}) == {}

# Node #2 and #3 shipped with BRIEFINGS=1 in .env and never touched the hours: twice a day, from 6.
assert st.brief_migration({"BRIEFINGS": "1"}) == {"REPORT_EVERY": "12", "REPORT_ANCHOR": "6"}
# A household that moved its morning report to seven keeps seven, and keeps twice a day.
assert st.brief_migration({"BRIEFINGS": "1", "BRIEF_MORNING": "7"}) == {"REPORT_EVERY": "12", "REPORT_ANCHOR": "7"}
assert st.brief_migration({"BRIEF_EVENING": "20"}) == {"REPORT_EVERY": "12", "REPORT_ANCHOR": "6"}
# Someone who has already chosen a rhythm is not overruled.
assert st.brief_migration({"BRIEFINGS": "1", "BRIEF_MORNING": "7", "REPORT_EVERY": "4"}) == {}
assert st.brief_migration({"BRIEFINGS": "1", "REPORT_ANCHOR": "9"}) == {}
# ...but a value that is not one of the accepted ones is not a choice. `update.sh` copies a key from
# .env.example with its whole line; if a comment ever comes along for the ride, the migration must still run.
assert st.brief_migration({"BRIEFINGS": "1", "REPORT_EVERY": "# 3 | 4 | 6"}) == {"REPORT_EVERY": "12", "REPORT_ANCHOR": "6"}
assert st.brief_migration({"BRIEFINGS": "1", "BRIEF_MORNING": "99"})["REPORT_ANCHOR"] == "6", "an hour that is not an hour"
# Idempotent: the second start finds REPORT_EVERY set and writes nothing.
_first = st.brief_migration({"BRIEFINGS": "1", "BRIEF_MORNING": "7"})
assert st.brief_migration({"BRIEFINGS": "1", "BRIEF_MORNING": "7", **_first}) == {}
print("an updating node keeps the rhythm it had; a fresh one gets 6 and 6")

# ---------------------------------------------------------------- the settings themselves
for k in ("REPORT_EVERY", "REPORT_ANCHOR", "REPORT_DEPTH"):
    assert k in st.RUNTIME and st.RUNTIME[k][0] == "alerts", f"{k} belongs to the alerts group"
    assert k in st.PUBLIC, f"{k} is the household's own rhythm; the dashboard shows it without the token"
    assert k in st.CHOICES, f"{k} must refuse a value the scheduler cannot honour"
for k in st.RETIRED:
    assert k not in st.RUNTIME, f"{k} is retired: no control for a key nothing reads"
assert all(24 % int(h) == 0 for h in st.CHOICES["REPORT_EVERY"]), "an interval that does not divide 24 walks round the clock"
assert st.RUNTIME["ALERT_LEVEL"][4].startswith("act = only when something needs doing (default)"), "the help text must say which is the default"

# The refusal names the accepted values, by quoting the help text rather than keeping a second copy of it.
for bad in ("5", "0", "seven", "24h"):
    try:
        st.set("REPORT_EVERY", bad)
    except ValueError as e:
        assert "3, 4, 6, 8, 12 or 24" in str(e), f"the refusal must name what is accepted: {e}"
    else:
        raise AssertionError(f"REPORT_EVERY accepted {bad!r}")
try:
    st.set("REPORT_DEPTH", "verbose")
except ValueError as e:
    assert "auto, brief, standard or deep" in str(e), e
else:
    raise AssertionError("REPORT_DEPTH accepted 'verbose'")
print("a report interval the scheduler cannot honour is refused, and the refusal says what it takes")

# ---------------------------------------------------------------- the default survives an empty key
os.environ["REPORT_EVERY"] = ""          # what update.sh writes into an updating node's .env
assert st.num("REPORT_EVERY", 6) == 6, "a key that is present but empty must not beat the default"
os.environ["REPORT_EVERY"] = "12"
st._cache["at"] = 0.0
assert st.num("REPORT_EVERY", 6) == 12
os.environ["REPORT_EVERY"] = "nonsense"
assert st.num("REPORT_EVERY", 6) == 6, "and neither must a value that is not a number"
del os.environ["REPORT_EVERY"]
print("the report settings hold their defaults through an empty .env key")

# ---------------------------------------------------------------- the agent container has no clock
import yaml

_loop = open("app/agent_loop.py").read()
_compose = yaml.safe_load(open("docker-compose.yml"))
assert "BRIEF_HOUR" not in _loop, "the agent's own report hour is gone; one schedule, in the app container"
assert "BRIEF_HOUR" not in yaml.dump(_compose), "docker-compose.yml still hands the agent a report hour"
# A wall-clock read in this file is what a second schedule is made of: the 07:00 copy came from `datetime.now()`
# next to a BRIEF_HOUR. time.time() is the model ladder's five-minute skip clock and stays.
assert "datetime" not in _loop, "the agent container reads no wall clock: that is how the second schedule started"
assert "daily_report" not in _loop, "a scheduled report is not something the bot asks the model for"
print("the agent container answers when written to and sends nothing on a schedule")
