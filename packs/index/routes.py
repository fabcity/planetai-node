"""GET /index/place: what the Fab City Index says about the place this node belongs to, as the adapter last stored it.

Reads only index_reads (adapter.py), never index.fab.city, so the dashboard never waits on someone else's server.
The body is trusted only for the slug the node is configured for: the adapter clears another slug's place on the next
read, but until it runs the row may still hold the old one, and a city's score must never show under another's name.
`read.at` is the file's own date; the row's fetched_at is only the last attempt and is not the body's age.
"""
from __future__ import annotations

import os
import sys

from fastapi import APIRouter

import registry
import settings
from db import q

sys.path.insert(0, os.path.dirname(__file__))
import place as PL  # noqa: E402

router = APIRouter()


def _rows() -> dict:
    try:
        return {r["what"]: r for r in q("SELECT what, sha, fetched_at, ok, error, body FROM index_reads")}
    except Exception:  # noqa: BLE001 — the adapter has not run yet: the table does not exist, and that is "no rows"
        return {}


@router.get("/index/place")
def index_place():
    chosen = (settings.get("INDEX_PLACE") or "").strip()
    rows = _rows()
    pr, rr = rows.get("place") or {}, rows.get("registry") or {}
    body = pr.get("body")
    if not (isinstance(body, dict) and (body.get("place") or {}).get("slug") == chosen):
        body = None                                    # no body, or another place's: the page shows the chosen name only
    known = next((p for p in PL.load() if p["slug"] == chosen), None)
    place = (body or {}).get("place") or (known and {"slug": known["slug"], "name": known["name"],
                                                     "country": known["country"], "territory": None})
    live = isinstance(rr.get("body"), list) and rr["body"]
    entries, version = (rr["body"], {"sha": rr.get("sha")}) if live else registry.load()
    return {
        "chosen": chosen, "place": place or None,
        "read": {"at": (body or {}).get("generated"), "ok": bool(body and pr.get("ok")), "error": pr.get("error"),
                 "tried": pr.get("fetched_at")},
        "score": (body or {}).get("score"),
        "indicators": [{"label": i.get("label"), "unit": i.get("unit"), "source": i.get("source"),
                        "latest": (i.get("series") or [None])[-1]} for i in (body or {}).get("indicators") or []],
        "links": (body or {}).get("links") and {k: body["links"].get(k) for k in ("page", "report")},
        "registry": {"sha": (version or {}).get("sha") or "", "at": rr.get("fetched_at") if live else None,
                     "from": "live" if live else "pinned",
                     "filed_here": sum(1 for e in entries if chosen in (e.get("places") or []))},
    }
