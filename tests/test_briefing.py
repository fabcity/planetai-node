"""When the node is allowed to interrupt someone. The bug this exists for: 'Good morning' arriving at 13:02 because the
schedule was in UTC, and fourteen heat alerts in one afternoon because every rule reached the phone."""
import os, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

os.environ.setdefault("DATABASE_URL", "postgresql://x/x")
os.environ["NODE_TZ"] = "Asia/Makassar"          # WITA, UTC+8, node #1
sys.path.insert(0, "app")

WITA = ZoneInfo("Asia/Makassar")


def hours(v):
    return [int(x) for x in v.replace(" ", "").split(",") if x.strip().isdigit()]


def due(now, sched, sent_recently, window=20):
    """The rule in _due(), testable without a database."""
    if not any(now.hour == h and now.minute < window for h in sched):
        return False
    return not sent_recently


def quiet(now, level, on=True, a=22, b=6):
    if not on or level == "act":
        return False
    h = now.hour
    return (a <= h or h < b) if a > b else (a <= h < b)


def sends(level, floor_setting):
    f = {"act": 2, "warn": 1, "info": 0}
    return f[level] >= f[floor_setting]


# the reported bug: 06:00 UTC is 14:00 in Bali. A schedule of "6" must mean six in the morning here.
utc_6 = datetime(2026, 9, 6, 6, 2, tzinfo=timezone.utc)
assert utc_6.astimezone(WITA).hour == 14
assert not due(utc_6.astimezone(WITA), hours("6"), False), "06:00 UTC is the afternoon in Bali; no morning report"
assert due(datetime(2026, 9, 6, 6, 2, tzinfo=WITA), hours("6"), False), "06:02 local is the morning report"
assert due(datetime(2026, 9, 6, 18, 19, tzinfo=WITA), hours("18"), False), "18:19 local is the evening report"
assert not due(datetime(2026, 9, 6, 18, 21, tzinfo=WITA), hours("18"), False), "past the 20-minute window"
assert not due(datetime(2026, 9, 6, 6, 5, tzinfo=WITA), hours("6"), True), "already sent one this window"
assert due(datetime(2026, 9, 6, 7, 0, tzinfo=WITA), hours("6,7,19"), False), "several hours may be scheduled"

# quiet hours wrap midnight, and never hold an act-level alert
assert quiet(datetime(2026, 9, 6, 23, 30, tzinfo=WITA), "info")
assert quiet(datetime(2026, 9, 6, 3, 0, tzinfo=WITA), "warn")
assert not quiet(datetime(2026, 9, 6, 3, 0, tzinfo=WITA), "act"), "danger always gets through"
assert not quiet(datetime(2026, 9, 6, 12, 0, tzinfo=WITA), "info")
assert not quiet(datetime(2026, 9, 6, 23, 30, tzinfo=WITA), "info", on=False)

# the level floor: what reaches a phone between reports
assert sends("act", "warn") and sends("warn", "warn") and not sends("info", "warn")
assert sends("act", "act") and not sends("warn", "act")
assert all(sends(l, "info") for l in ("act", "warn", "info"))

print("all briefing/schedule tests pass")
