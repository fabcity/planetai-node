"""The community bot's subscriber routes, called by the agent container. Admin token only, community node only.

Every chat id travels in a POST body, never in a path or query string, so no access log carries one.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import feeds
import placewords
from auth import _admin


class Body(BaseModel):
    chat: str = ""
    what: str = ""


def _gate(authorization: str):
    """Admin only; on a private node a 409 response to return, otherwise None."""
    _admin(authorization)
    if placewords.is_house():
        return JSONResponse({"error": placewords.NO_ACT}, status_code=409)


def _db():
    from db import db  # noqa: PLC0415 — db.py needs DATABASE_URL at import
    return db()


router = APIRouter(prefix="/subscribers")


@router.post("/start")
def start(b: Body, authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        return feeds.start(cur, b.chat)


@router.post("/toggle")
def toggle(b: Body, authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        return feeds.toggle(cur, b.chat, b.what)


@router.post("/stop")
def stop(b: Body, authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        row = feeds._row(cur, b.chat)
        feeds.stop(cur, b.chat)
    return {"text": feeds.WORDS[row["lang"] if row else "en"]["stopped"]}


@router.post("/card")
def card(b: Body, authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        c = feeds.card(cur, b.chat)
    if c is None:
        raise HTTPException(404, "not a subscriber")
    return c


@router.post("/now")
def now(b: Body, authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        return {"text": feeds.now_text(cur, b.chat)}


@router.post("/week")
def week(b: Body, authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        return {"text": feeds.week_text(cur, b.chat)}


@router.get("/counts")
def counts(authorization: str = Header(default="")):
    if (no := _gate(authorization)):
        return no
    with _db() as con, con.cursor() as cur:
        return feeds.counts(cur)
