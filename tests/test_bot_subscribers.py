"""The community bot's subscriber side: a chat outside TELEGRAM_CHAT_IDS on a community node gets the card, the
toggles and four commands through the app's /subscribers/* routes, never the model, and its chat id never reaches
a log line or a URL. A private node is unchanged.

No import of agent_loop (importing it starts side effects): the functions are lifted whole by AST, as
tests/test_agent_buttons.py does."""

import ast
import asyncio
import logging
import re
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))


def _lift(path, names, ns):
    tree = ast.parse((ROOT / "app" / path).read_text())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            exec(compile(ast.Module([node], []), str(path), "exec"), ns)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in names for t in node.targets):
            exec(compile(ast.Module([node], []), str(path), "exec"), ns)
    return ns


OTHER = {"en": "I send what you picked here. /feeds changes it, /stop ends it.",
         "id": "Saya mengirim yang kamu pilih di sini. /feeds untuk mengubah, /stop untuk berhenti."}
TG, ROUTES, ROUTE_URLS, ASKED, LOGS = [], [], [], [], []
ROWS: dict = {}       # chat -> lang, the app's subscribers table as the routes see it


class _Resp:
    def __init__(self, code, body):
        self.status_code, self._body = code, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(str(self.status_code))


def _card(chat):
    lang = ROWS[chat]
    return {"text": f"card {lang}", "keyboard": [[{"text": "Air", "callback_data": "fd:air"}]], "lang": lang,
            "other": OTHER[lang]}


class _Hc:
    """The app's /subscribers/* routes, as the bot sees them."""
    async def get(self, url, **kw):
        return _Resp(200, {"kind": NS["KIND"]})

    async def post(self, url, json=None, **kw):
        ROUTE_URLS.append(url)
        route = url.split("/subscribers", 1)[1]
        ROUTES.append("/subscribers" + route)
        chat = json["chat"]
        if route == "/start":
            ROWS.setdefault(chat, "en")
            return _Resp(200, _card(chat))
        if route == "/card":
            return _Resp(200, _card(chat)) if chat in ROWS else _Resp(404, {"detail": "not a subscriber"})
        if route == "/toggle":
            if json["what"].startswith("lang:"):
                ROWS[chat] = json["what"][5:]
            return _Resp(200, _card(chat))
        if route == "/stop":
            ROWS.pop(chat, None)
            return _Resp(200, {"text": "stopped"})
        return _Resp(200, {"text": route[1:] + " text"})


async def _telegram(method, **kw):
    TG.append({"method": method, **kw})
    return {}


class _List(logging.Handler):
    def emit(self, record):
        LOGS.append(record.getMessage())


log = logging.getLogger("test_bot_subscribers")
log.addHandler(_List())
log.propagate = False
log.setLevel(logging.DEBUG)


async def _ask(*a, **kw):
    ASKED.append(a)
    return "a model answer", "local"


NS = {"re": re, "time": __import__("time"), "log": log, "telegram": _telegram, "CHATS": lambda: {"42"},
      "LOCALE": "en", "MCP_URL": "http://app:8080/mcp", "KIND": "community", "ask": _ask,
      "placewords": __import__("placewords")}
_lift("agent_loop.py", {"node_url", "T", "no_act", "NO_ACT", "_sub", "subscriber_message", "subscriber_tap",
                        "SUB_COMMANDS", "handle_callback", "keep_picture", "picture_of", "_name_of",
                        "parse_callback", "parse_alert_callback", "main", "tg_status"}, NS)
subscriber_message, subscriber_tap = NS["subscriber_message"], NS["subscriber_tap"]
hc = _Hc()
run = asyncio.run

# ---- a stranger on a community node ----
run(subscriber_message(hc, "5550001", "hello"))                       # the first message
assert ROUTES == ["/subscribers/card", "/subscribers/start"], ROUTES
assert TG[-1]["reply_markup"] == {"inline_keyboard": [[{"text": "Air", "callback_data": "fd:air"}]]}, TG[-1]
assert TG[-1]["text"] == "card en" and TG[-1]["chat_id"] == "5550001"

run(subscriber_message(hc, "5550001", "what is the air like?"))
assert TG[-1]["text"] == OTHER["en"], TG[-1]
assert ASKED == [], "a stranger's words never reach the model"

run(subscriber_tap(hc, {"id": "q1", "data": "fd:waves", "message": {"chat": {"id": 5550001}, "message_id": 9}}))
assert ROUTES[-1] == "/subscribers/toggle", ROUTES
assert TG[-2]["method"] == "editMessageText" and TG[-2]["message_id"] == 9 and TG[-2]["text"] == "card en"
assert TG[-2]["reply_markup"] == {"inline_keyboard": [[{"text": "Air", "callback_data": "fd:air"}]]}
assert TG[-1] == {"method": "answerCallbackQuery", "callback_query_id": "q1"}, TG[-1]

# A language tap sets the language, and the `other` line follows it.
run(subscriber_tap(hc, {"id": "q2", "data": "fl:id", "message": {"chat": {"id": 5550001}, "message_id": 9}}))
assert ROWS["5550001"] == "id" and TG[-2]["text"] == "card id"
run(subscriber_message(hc, "5550001", "halo"))
assert TG[-1]["text"] == OTHER["id"], TG[-1]

# The four commands go to their routes; /feeds sends the card again.
for cmd, route in (("/feeds", "/subscribers/card"), ("/now", "/subscribers/now"), ("/week", "/subscribers/week")):
    run(subscriber_message(hc, "5550001", cmd))
    assert ROUTES[-1] == route, (cmd, ROUTES)
assert TG[-1]["text"] == "week text"
assert TG[-3]["text"] == "card id" and "reply_markup" in TG[-3], "/feeds sends the card with its keyboard"
run(subscriber_message(hc, "5550001", "/stop"))
assert ROUTES[-1] == "/subscribers/stop" and TG[-1]["text"] == "stopped" and "5550001" not in ROWS
# /start after /stop: a fresh row.
run(subscriber_message(hc, "5550001", "/start"))
assert ROUTES[-2:] == ["/subscribers/card", "/subscribers/start"] and "5550001" in ROWS
# /start from a chat that has a row: the card, no second row.
run(subscriber_message(hc, "5550001", "/start"))
assert ROUTES[-1] == "/subscribers/card" and TG[-1]["text"] == "card en"

# The tap goes through handle_callback, from any chat, on a community node; event taps keep their path.
n = len(ROUTES)
run(NS["handle_callback"](hc, {"id": "q3", "data": "fd:air", "message": {"chat": {"id": 5550001}, "message_id": 9}}, {}))
assert ROUTES[n:] == ["/subscribers/toggle"] and TG[-1]["method"] == "answerCallbackQuery"
run(NS["handle_callback"](hc, {"id": "q4", "data": "ev:1:acted", "message": {"chat": {"id": 5550001}, "message_id": 3}}, {}))
assert len(ROUTES) == n + 1 and TG[-1] == {"method": "answerCallbackQuery", "callback_query_id": "q4"}

# A stranger's picture on a community node: no reply, nothing logged about the chat.
TG.clear()
assert run(NS["keep_picture"](hc, {"photo": [{"file_id": "x", "width": 1, "height": 1}]}, "5550001")) is False
assert TG == []

assert all("5550001" not in r for r in LOGS), ("no chat id in the log", LOGS)
assert all("5550001" not in url for url in ROUTE_URLS), "no chat id in a URL"
assert all(u == "http://app:8080/subscribers" + r.split("/subscribers", 1)[1] for u, r in zip(ROUTE_URLS, ROUTES))


# ---- main()'s branch, one fake update each ----
class _Stop(BaseException):
    pass


class TelegramError(Exception):
    pass


def drive(kind, update):
    """main() with one update, then out of the loop."""
    NS["KIND"] = kind
    got = [{"result": [dict(update, update_id=1)]}]

    async def tg(method, **kw):
        if method == "getUpdates":
            if not got:
                raise _Stop
            return got.pop()
        return await _telegram(method, **kw)

    async def sleep(_s):
        return None

    @asynccontextmanager
    async def session(_hc):
        yield object(), []

    async def nothing(*a, **kw):
        return False

    NS.update({"telegram": tg, "TOKEN": "t", "NODE": "n", "NAME": "a", "RUNGS": [], "TG_TOKEN": lambda: "tok",
               "httpx": types.SimpleNamespace(AsyncClient=lambda **kw: hc),
               "asyncio": types.SimpleNamespace(create_task=lambda c: c.close(), sleep=sleep),
               "refresh_ladder": nothing, "node_session": session, "announce_buttons": nothing,
               "relay_offer": nothing, "_keep_alert_note": nothing, "note_pending": lambda *a: None,
               "act_command": nothing, "TelegramError": TelegramError})
    TG.clear(); ROUTES.clear(); LOGS.clear()
    try:
        run(NS["main"]())
    except _Stop:
        pass


def text(chat, words):
    return {"message": {"chat": {"id": int(chat)}, "text": words, "from": {"first_name": "X"}}}


ROWS.clear()
drive("community", text("5550002", "hello"))
assert ROUTES == ["/subscribers/card", "/subscribers/start"] and TG[-1]["text"] == "card en", (ROUTES, TG)
assert all("5550002" not in r for r in LOGS), LOGS
assert any("answering subscribers and 1 keeper chat(s)" in r for r in LOGS) and all("42" not in r for r in LOGS), \
    "the startup line on a community node names no chat"
NS["CHATS"] = lambda: set()                 # a community node with a token and no keeper chat still answers subscribers
assert NS["tg_status"]() == "bot set, answering subscribers; no keeper chat (TELEGRAM_CHAT_IDS is empty)"
NS["KIND"] = "home"
assert "will not answer anyone" in NS["tg_status"](), "a private node with no chat answers nobody"
NS["CHATS"] = lambda: {"42"}

drive("home", text("5550003", "hello"))
assert ROUTES == [] and TG[-1]["text"].startswith("This node answers its household only."), TG
assert any("message from chat 5550003 ignored" in r for r in LOGS), "a private node keeps today's lines"
assert any("['42']" in r for r in LOGS), "a private node's startup line keeps its list"

drive("community", text("42", "/feeds"))
assert ROUTES[0] == "/subscribers/card" and ASKED == [], ROUTES

drive("community", text("42", "/feeds@planetai_bot"))
assert ROUTES[0] == "/subscribers/card", "a command addressed to the bot in a group"

print("anyone can subscribe to a community node's feeds; no model, no chat id in the log or a URL")
