"""A local model runs the node.

Ollama on the same machine, a small tool-calling model (qwen3:4b), the node's own MCP tools, and the Telegram bot the
node already has as the way to talk to it. No cloud, no API key, no model on any server but this one.

  a person messages the bot     -> the model reads the node with tools and answers in one or two sentences
  every morning at BRIEF_HOUR   -> the model runs health_check and status and sends a brief
  an alert fires                -> unchanged: the node sends it; the model does not stand between a rule and a phone

Only chat ids in TELEGRAM_CHAT_IDS are answered. Everything the model does through tools is recorded with
X-Agent=<AGENT_NAME>, so `planetai actions` shows what the model did and for whom.

  OLLAMA_URL   http://host.docker.internal:11434   MODEL  qwen3:4b   AGENT_NAME  local-model   BRIEF_HOUR  7
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agent")

OLLAMA = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
MODEL = os.getenv("MODEL", "qwen3:4b")
MCP_URL = os.getenv("MCP_URL", "http://app:8080/mcp")
TOKEN = os.getenv("ADMIN_TOKEN", "")
NAME = os.getenv("AGENT_NAME", "local-model")
NODE = os.getenv("NODE_NAME", "node")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHATS = {c.strip() for c in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()}
BRIEF_HOUR = int(os.getenv("BRIEF_HOUR", "7"))
LOCALE = os.getenv("ALERT_LOCALE", "en")
MAX_ROUNDS = 6

SYSTEM = f"""You run PLANETAI node '{NODE}', a small computer that reads environmental sensors at one place and tells
the people there what to do. You have tools that read the node and act on it. Rules:
- Use tools to answer; do not guess numbers. Call health_check first when asked how things are.
- Answer in {'Bahasa Indonesia' if LOCALE == 'id' else 'English'}, in one to three plain sentences. No lists unless asked.
- When a person says they did something about an alert, record it with `act`, using their words as the note.
- Never reveal tokens or settings values that look like secrets.
- If a task needs the node's shell (update, backup, restart), say the exact command from `maintenance` and that it must be run on the node.
- If you do not know, say so.
- Reply with the answer only. Never describe what the person asked or what you did; do not think aloud."""



def clean(text: str) -> str:
    """Strip thinking blocks; small models sometimes emit them as content anyway."""
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def to_ollama_tools(tools) -> list[dict]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": getattr(t, "input_schema", None) or getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}}} for t in tools]


async def ask(session: ClientSession, tools: list[dict], user: str, history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM}, *(history or []), {"role": "user", "content": user}]
    async with httpx.AsyncClient(timeout=180) as hc:
        for _ in range(MAX_ROUNDS):
            r = await hc.post(f"{OLLAMA}/api/chat", json={"model": MODEL, "messages": messages, "tools": tools, "stream": False,
                                                            "think": False, "options": {"temperature": 0.2}})
            r.raise_for_status()
            msg = r.json()["message"]
            messages.append(msg)
            calls = msg.get("tool_calls") or []
            if not calls:
                # Final answer as constrained JSON: a small model narrates its reasoning as prose even with thinking
                # off, and no instruction fixes that reliably. A schema does.
                messages.append({"role": "user", "content": "Give the final answer for the person now: one to three plain sentences, no narration."})
                r2 = await hc.post(f"{OLLAMA}/api/chat", json={"model": MODEL, "messages": messages, "stream": False, "think": False,
                                                                 "format": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]},
                                                                 "options": {"temperature": 0.1}})
                r2.raise_for_status()
                try:
                    return clean(json.loads(r2.json()["message"]["content"])["answer"]) or "(no answer)"
                except Exception:  # noqa: BLE001
                    return clean(msg.get("content") or "") or "(no answer)"
            for c in calls:
                fn = c["function"]["name"]; args = c["function"].get("arguments") or {}
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except Exception: args = {}
                if "agent" in (next((t for t in tools if t["function"]["name"] == fn), {}).get("function", {}).get("parameters", {}).get("properties", {})):
                    args.setdefault("agent", NAME)
                log.info("tool %s %s", fn, json.dumps(args)[:200])
                try:
                    res = await session.call_tool(fn, args)
                    text = "\n".join(getattr(x, "text", "") for x in res.content)[:8000]
                except Exception as e:  # noqa: BLE001
                    text = f"tool error: {type(e).__name__}: {e}"
                messages.append({"role": "tool", "content": text, "tool_name": fn})
        return "I ran out of steps before finishing. Ask me something narrower."


async def telegram(method: str, **params):
    async with httpx.AsyncClient(timeout=40) as hc:
        r = await hc.post(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", json=params)
        r.raise_for_status()
        return r.json()


async def main():
    if not TOKEN:
        raise SystemExit("ADMIN_TOKEN is required (the agent writes through the node's MCP surface)")
    hc = httpx.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}", "X-Agent": NAME}, timeout=120)
    async with streamable_http_client(MCP_URL, http_client=hc) as (r, w, *_):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = to_ollama_tools((await session.list_tools()).tools)
            log.info("%s: %d tools, model %s at %s", NODE, len(tools), MODEL, OLLAMA)
            offset, last_brief_day, history = 0, None, {}
            while True:
                # the morning brief
                now = datetime.now()
                if TG_TOKEN and CHATS and now.hour == BRIEF_HOUR and last_brief_day != now.date():
                    last_brief_day = now.date()
                    try:
                        brief = await ask(session, tools, "Run health_check and status. Then tell me, in three sentences at most, how the node is this morning and whether anything needs doing.")
                        for chat in CHATS:
                            await telegram("sendMessage", chat_id=chat, text=brief)
                    except Exception as e:  # noqa: BLE001
                        log.warning("brief failed: %s", e)
                # the conversation
                if not TG_TOKEN:
                    await asyncio.sleep(30); continue
                try:
                    upd = await telegram("getUpdates", offset=offset, timeout=25, allowed_updates=["message"])
                except Exception as e:  # noqa: BLE001
                    log.warning("telegram: %s", e); await asyncio.sleep(10); continue
                for u in upd.get("result", []):
                    offset = u["update_id"] + 1
                    m = u.get("message") or {}
                    chat = str((m.get("chat") or {}).get("id", "")); text = (m.get("text") or "").strip()
                    if not text or chat not in CHATS:
                        continue
                    if text.startswith("/act"):        # "/act 23 closed the windows" stays fast and deterministic
                        parts = text.split(maxsplit=2)
                        if len(parts) >= 2 and parts[1].isdigit():
                            await session.call_tool("act", {"alert_id": int(parts[1]), "note": parts[2] if len(parts) > 2 else "acted", "agent": f"{NAME}/telegram"})
                            await telegram("sendMessage", chat_id=chat, text=f"Recorded: you acted on #{parts[1]}.")
                            continue
                    t0 = time.time()
                    try:
                        answer = await ask(session, tools, text, history.get(chat, [])[-6:])
                    except Exception as e:  # noqa: BLE001
                        answer = f"I could not answer that ({type(e).__name__}). Is the model running? `ollama list` on the node."
                    history.setdefault(chat, []).extend([{"role": "user", "content": text}, {"role": "assistant", "content": answer}])
                    log.info("chat %s: %.1fs", chat, time.time() - t0)
                    await telegram("sendMessage", chat_id=chat, text=answer[:4000])


if __name__ == "__main__":
    asyncio.run(main())
