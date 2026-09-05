"""A model runs the node, over Telegram. Which model: the strongest one reachable, from a ladder you configure.

  online   Anthropic or OpenAI, with a key. The most capable. The only rung that sends anything off your network.
  remote   a bigger local model elsewhere on your tailnet: a laptop's Ollama, an exo cluster. Private, no key.
  local    Ollama on this machine, qwen3:4b. Always there.

AGENT_PREFER=strongest tries online, remote, local in that order; AGENT_PREFER=private never uses online. A rung that
is unreachable, unauthorised or erroring is skipped for five minutes. `/model` in Telegram shows the ladder and which
rung answered; `/model local` pins one for the conversation.

All three speak the OpenAI-compatible chat protocol with tools, which Ollama, exo, OpenAI and Anthropic all serve.
The node's own MCP tools are the model's hands; every write records X-Agent=<AGENT_NAME>/<rung>.

Alerts do not pass through the model. The node sends them; the model answers questions about them.
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
for noisy in ("httpx", "mcp"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

MCP_URL = os.getenv("MCP_URL", "http://app:8080/mcp")
TOKEN = os.getenv("ADMIN_TOKEN", "")
NAME = os.getenv("AGENT_NAME", "local-model")
NODE = os.getenv("NODE_NAME", "node")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHATS = {c.strip() for c in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()}
BRIEF_HOUR = int(os.getenv("BRIEF_HOUR", "7"))
LOCALE = os.getenv("ALERT_LOCALE", "en")
MAX_ROUNDS = 8
SKIP_FOR = 300


class Rung:
    def __init__(self, name, url, model, key="", small=False):
        self.name, self.url, self.model, self.key, self.small = name, url.rstrip("/"), model, key, small
        self.skip_until = 0.0

    def headers(self):
        h = {"content-type": "application/json"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
            if "anthropic.com" in self.url:
                h["x-api-key"] = self.key
        return h


RUNGS: list[Rung] = []
_SKIPS: dict[str, float] = {}


def ladder(cfg: dict) -> list[Rung]:
    """Build the ladder from settings (the dashboard's Model page) with the environment as fallback."""
    g = lambda k, d="": (cfg.get(k) or os.getenv(k) or d)  # noqa: E731
    rungs = []
    if g("AGENT_ONLINE_URL") and g("AGENT_ONLINE_KEY"):
        rungs.append(Rung("online", g("AGENT_ONLINE_URL"), g("AGENT_ONLINE_MODEL", "claude-sonnet-4-6"), g("AGENT_ONLINE_KEY")))
    if g("AGENT_REMOTE_URL"):
        rungs.append(Rung("remote", g("AGENT_REMOTE_URL"), g("AGENT_REMOTE_MODEL", "gpt-oss-120b"), g("AGENT_REMOTE_KEY")))
    rungs.append(Rung("local", os.getenv("OLLAMA_URL", "http://host.docker.internal:11434") + "/v1", os.getenv("MODEL", "qwen3:4b"), small=True))
    if g("AGENT_PREFER", "strongest") == "private":
        rungs = [r for r in rungs if r.name != "online"]
    for r in rungs:                        # keep the skip clocks across rebuilds
        r.skip_until = _SKIPS.get(r.name, 0.0)
    return rungs


async def refresh_ladder(hc: httpx.AsyncClient) -> None:
    """Every minute: re-read the runtime settings so a change in the dashboard reaches the bot without a restart."""
    global RUNGS
    while True:
        try:
            r = await hc.get(MCP_URL.replace("/mcp", "/settings/raw"))
            cfg = r.json() if r.status_code == 200 else {}
        except Exception:  # noqa: BLE001
            cfg = {}
        for r_ in RUNGS:
            _SKIPS[r_.name] = r_.skip_until
        new = ladder(cfg)
        if [(x.name, x.model, x.url) for x in new] != [(x.name, x.model, x.url) for x in RUNGS]:
            log.info("ladder: %s", [f"{x.name}:{x.model}" for x in new])
        RUNGS = new
        await asyncio.sleep(60)

SYSTEM = f"""You run PLANETAI node '{NODE}', a small computer that reads environmental sensors at one place and tells
the people there what to do. You have tools that read the node and act on it. You are talking to the people who live
or work here, on Telegram.
- Use tools to answer; never guess numbers. For "how is it" questions call health_check and status.
- Answer in {'Bahasa Indonesia' if LOCALE == 'id' else 'English'}. Explain, do not just report: say what is happening, what it means for them, and what to do.
- Start with an emoji that fits (🏠 inside, 🌳 outside, 🛰️ satellites, 🌊 sea, 🥵 heat, 📡 a sensor, ✅ fine, ⚠️ watch, 🚨 act). Use a few more where they help the eye. Short paragraphs, not lists.
- Avoid statistics. No means, peaks, correlations, percentages or counts unless the person asks for numbers. One number is fine when it drives the advice (a PM2.5 level, a temperature).
- When a person says they did something about an alert, record it with `act`, their words as the note, and thank them.
- Never reveal tokens or values that look like secrets.
- Tasks that need the node's shell (update, backup, restart): give the exact command from `maintenance` and say it runs on the node.
- Plain text only: Telegram shows it raw. No asterisks, no backticks, no headings. Line breaks and emojis are your formatting.
- Under 100 words unless the person asks for detail. One message, not a report.
- If you do not know, say so. Reply with the answer only; do not narrate what you did."""


def clean(text: str) -> str:
    """Strip thinking blocks and Markdown: Telegram gets plain text, and a model reaches for ** and ``` anyway."""
    import re
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    t = re.sub(r"```[a-z]*\n?", "", t)
    t = re.sub(r"(\*\*|__|`)", "", t)
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def to_openai_tools(tools) -> list[dict]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": getattr(t, "input_schema", None) or getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}}} for t in tools]


async def chat(hc: httpx.AsyncClient, rung: Rung, messages: list, tools: list | None, final: bool = False) -> dict:
    body = {"model": rung.model, "messages": messages, "temperature": 0.2}
    if tools and not final:
        body["tools"] = tools
    if final and rung.small:            # a small model narrates its reasoning as prose; a schema stops that
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}}}
    if rung.small:
        messages[0] = {"role": "system", "content": SYSTEM + "\n/no_think"}
    r = await hc.post(f"{rung.url}/chat/completions", json=body, headers=rung.headers())
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


async def ask(session: ClientSession, tools: list[dict], user: str, history: list[dict] | None = None, pin: str | None = None) -> tuple[str, str]:
    """Returns (answer, rung name). Walks the ladder; a rung that fails is skipped for five minutes."""
    now = time.time()
    order = [r for r in RUNGS if (pin is None or r.name == pin) and r.skip_until < now] or [r for r in RUNGS if pin is None or r.name == pin]
    last_err = None
    async with httpx.AsyncClient(timeout=240) as hc:
        for rung in order:
            messages = [{"role": "system", "content": SYSTEM}, *(history or []), {"role": "user", "content": user}]
            try:
                for _ in range(MAX_ROUNDS):
                    msg = await chat(hc, rung, messages, tools)
                    messages.append(msg)
                    calls = msg.get("tool_calls") or []
                    if not calls:
                        if rung.small:
                            messages.append({"role": "user", "content": "Give the final answer for the person now: a short explanation with an emoji or two, what it means, what to do. No statistics unless they asked."})
                            fin = await chat(hc, rung, messages, None, final=True)
                            try:
                                return clean(json.loads(fin.get("content") or "{}").get("answer", "")) or clean(msg.get("content")), rung.name
                            except Exception:  # noqa: BLE001
                                return clean(msg.get("content")) or "(no answer)", rung.name
                        return clean(msg.get("content")) or "(no answer)", rung.name
                    for c in calls:
                        fn = c["function"]["name"]
                        args = c["function"].get("arguments") or {}
                        if isinstance(args, str):
                            try: args = json.loads(args)
                            except Exception: args = {}
                        spec = next((t for t in tools if t["function"]["name"] == fn), {}).get("function", {}).get("parameters", {}).get("properties", {})
                        if "agent" in spec:
                            args.setdefault("agent", f"{NAME}/{rung.name}")
                        log.info("[%s] tool %s %s", rung.name, fn, json.dumps(args)[:160])
                        try:
                            res = await session.call_tool(fn, args)
                            text = "\n".join(getattr(x, "text", "") for x in res.content)[:8000]
                        except Exception as e:  # noqa: BLE001
                            text = f"tool error: {type(e).__name__}: {e}"
                        messages.append({"role": "tool", "tool_call_id": c.get("id", fn), "content": text})
                return "I ran out of steps. Ask something narrower.", rung.name
            except (httpx.HTTPError, KeyError, ValueError) as e:
                last_err = e
                rung.skip_until = time.time() + SKIP_FOR
                log.warning("[%s] unavailable (%s: %s); trying the next rung", rung.name, type(e).__name__, str(e)[:100])
    return f"No model answered ({type(last_err).__name__ if last_err else 'none configured'}). On the node: `ollama list`, and check AGENT_* in .env.", "none"


async def telegram(method: str, **params):
    async with httpx.AsyncClient(timeout=40) as hc:
        r = await hc.post(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", json=params)
        r.raise_for_status()
        return r.json()


def ladder_text(pins: dict, chat: str) -> str:
    now = time.time()
    lines = [f"{'→' if pins.get(chat) == r.name else ' '} {r.name:7} {r.model} @ {r.url.replace('http://','').replace('https://','')[:40]}" + ("  (skipped, retry soon)" if r.skip_until > now else "") for r in RUNGS]
    return "Model ladder, strongest first:\n" + "\n".join(lines) + f"\nPrefer: {'private' if not any(r.name=='online' for r in RUNGS) and os.getenv('AGENT_PREFER')=='private' else 'strongest'}. Pin one: /model local | remote | online. Unpin: /model auto"


async def main():
    if not TOKEN:
        raise SystemExit("ADMIN_TOKEN is required")
    hc = httpx.AsyncClient(headers={"Authorization": f"Bearer {TOKEN}", "X-Agent": NAME}, timeout=120)
    asyncio.create_task(refresh_ladder(hc))
    await asyncio.sleep(2)
    log.info("%s: ladder %s", NODE, [f"{r.name}:{r.model}" for r in RUNGS])
    async with streamable_http_client(MCP_URL, http_client=hc) as (r, w, *_):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = to_openai_tools((await session.list_tools()).tools)
            log.info("%d tools", len(tools))
            offset, last_brief_day, history, pins = 0, None, {}, {}
            while True:
                now = datetime.now()
                if TG_TOKEN and CHATS and now.hour == BRIEF_HOUR and last_brief_day != now.date():
                    last_brief_day = now.date()
                    try:
                        brief, rung = await ask(session, tools, "Run health_check and status. Write the morning note for the household: 🌅 how the air and the node are this morning, in plain words, and whether anything needs doing today. No statistics. Warm, short.")
                        for chat in CHATS:
                            await telegram("sendMessage", chat_id=chat, text=brief)
                        log.info("brief sent via %s", rung)
                    except Exception as e:  # noqa: BLE001
                        log.warning("brief failed: %s", e)
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
                    if text.startswith("/act"):
                        parts = text.split(maxsplit=2)
                        if len(parts) >= 2 and parts[1].isdigit():
                            await session.call_tool("act", {"alert_id": int(parts[1]), "note": parts[2] if len(parts) > 2 else "acted", "agent": f"{NAME}/telegram"})
                            await telegram("sendMessage", chat_id=chat, text=f"Recorded: you acted on #{parts[1]}.")
                            continue
                    if text.startswith("/model"):
                        arg = text.split(maxsplit=1)[1].strip().lower() if " " in text else ""
                        if arg in {r.name for r in RUNGS}: pins[chat] = arg
                        elif arg == "auto": pins.pop(chat, None)
                        await telegram("sendMessage", chat_id=chat, text=ladder_text(pins, chat))
                        continue
                    t0 = time.time()
                    answer, rung = await ask(session, tools, text, history.get(chat, [])[-6:], pins.get(chat))
                    history.setdefault(chat, []).extend([{"role": "user", "content": text}, {"role": "assistant", "content": answer}])
                    log.info("chat %s via %s: %.1fs", chat, rung, time.time() - t0)
                    await telegram("sendMessage", chat_id=chat, text=answer[:4000])


if __name__ == "__main__":
    asyncio.run(main())
