"""What an issue is computed from, and the two questions the engine asks about a row.

Everything in `app/issues/` reads the database through this module's CONTRACT. Nothing here runs SQL,
opens a connection, or knows what a metric means: `place_of` sorts sensors by distance, `stage_of`
sorts alerts by what a person did about them, and the field lists below say which columns the engine
is allowed to assume exist. `tests/test_issues_schema.py` asserts every name in CONTRACT against
`init.sql`, the way `tools/check_ui.py` already asserts the fields the dashboard reads off `/stats`.

Two seams are deliberate and marked:

  · `place_of` is the ONE function the custody spec changes when it is accepted (docs/SPEC_custody.md,
    which is pending). Today `local` carries two meanings at once — "ours" and "here" — and this function reads it as geography.
    Custody makes `kind IN ('own','child')` the ownership test and leaves `local` as geography, at
    which point the `local` clauses below become `kind` clauses and nothing else in this package moves.

  · `stage_of` does not read `/alerts.acted_at`. That column is
    `min(ts) WHERE stage IN ('acknowledged','acted')` (app/main.py:894), so an ask somebody merely
    SAW reads as acted on, and every open ask in the house would go quiet the moment a person
    glanced at it. Openness is asked of the `actions` table directly.
"""
from __future__ import annotations

# --------------------------------------------------------------------------------------------------
# CONTRACT — every column app/issues/ reads. A name here that is not in init.sql is a broken engine
# on the next schema change, which is why the test asserts the list rather than trusting it.
# --------------------------------------------------------------------------------------------------
CONTRACT = {
    # the `stats` view: 15m/1h/24h rolling means per (sensor, metric), sensors only
    "stats": (
        "sensor_id", "metric", "indoor", "local", "kind", "scale", "lat", "lon", "name",
        "last", "last_ts", "silent_minutes", "mean_15m", "mean_1h", "mean_24h",
    ),
    # the `observations` view: latest per (slow source, metric) — portals, models, satellites
    "observations": (
        "sensor_id", "metric", "value", "ts", "name", "kind", "scale", "local", "cadence", "meta",
    ),
    # what a rule wrote
    "alerts": ("id", "ts", "rule_id", "sensor_id", "level", "text"),
    # what a person did about it. This table is the ρ instrument; see SPEC.md §1.
    "actions": ("ts", "alert_id", "stage", "actor", "note"),
    # hourly means, for each distance's 24 h series
    "readings_1h": ("bucket", "sensor_id", "metric", "mean", "min", "max", "n"),
}

# The four distances, nearest first. They are the columns of every issue, and their order is the
# order a stack is drawn in. `child` is a fifth place and not a column: a node below this one
# describes its own place, not a distance from this one.
DISTANCES = ("room", "yard", "ring", "region")

# `acknowledged` means somebody saw it. Only these two mean somebody did something.
CLOSED_STAGES = ("acted", "measured")


def place_of(row: dict) -> str:
    """Which distance a sensor row stands at: room · yard · ring · region · child.

    Reads `kind`, `local` and `indoor`, in that order, from a `stats` or `observations` row.

      child   a node below this one pushing hourly means up
      region  anything not a device: a model sampled at this point, a portal, a survey
      room    ours, and indoors
      yard    ours, and outdoors
      ring    somebody else's device near here

    A row with no `kind` is treated as a device, because that is the column's own default
    (`init.sql:16`) and a sensor posted through `POST /readings` may carry nothing else.
    """
    kind = (row.get("kind") or "sensor").strip()
    if kind == "child":
        return "child"
    if kind != "sensor":
        return "region"
    if not row.get("local"):
        return "ring"
    return "room" if row.get("indoor") else "yard"


def stage_of(alert: dict, actions: list[dict]) -> str | None:
    """The furthest stage anybody reached on this alert, or None if nobody has touched it.

    `measured` beats `acted` beats `acknowledged`, whatever order the rows arrived in — a person can
    record "I did it" before "I saw it", and over Telegram they usually do.
    """
    aid = alert.get("id")
    if aid is None:
        return None
    reached = {a.get("stage") for a in actions if a.get("alert_id") == aid}
    for stage in ("measured", "acted", "acknowledged"):
        if stage in reached:
            return stage
    return None


def is_open(alert: dict, actions: list[dict]) -> bool:
    """True while nobody has done anything about this alert. Seeing it is not doing anything."""
    return stage_of(alert, actions) not in CLOSED_STAGES


def is_seen(alert: dict, actions: list[dict]) -> bool:
    """True when somebody acknowledged it and stopped there. The ask strip may say so."""
    return stage_of(alert, actions) == "acknowledged"
