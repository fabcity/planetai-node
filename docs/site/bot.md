# The bot and the model ladder

A bot on your Telegram, running a small model on your own machine, reads the node and explains it; point it
at a bigger model when you have one. It is a separate container, `agent`, running `app/agent_loop.py`,
started by `planetai agent local`. Alerts and reports never pass through the model: the app container
writes and sends those itself, and the agent container has no clock and sends nothing on a schedule.

## Setting it up

```bash
planetai agent local
```

Installs Ollama (Homebrew on a Mac, Ollama's script on Linux), starts it as a service, picks `AGENT_MODEL` —
`qwen3:4b`, or `qwen3:8b` on a machine with 16 GB — pulls it, adds the compose profile `agent`, builds and
starts the container. On Linux it sets `OLLAMA_URL=http://172.17.0.1:11434` and warns that Ollama must listen
on `0.0.0.0` for the container to reach it. The model must do tool calling. `planetai agent stop` stops the
container; `planetai logs agent` says whether Telegram is set and which model it found.

Containers on macOS get CPU only, Intel and Apple Silicon alike; this is the one place that matters.

## The ladder

Three rungs, all speaking the OpenAI-compatible chat protocol with tools:

| rung | what | settings | default model |
|---|---|---|---|
| `online` | Anthropic, OpenAI or Gemini with a key — the only rung that sends anything off your network | `AGENT_ONLINE_URL` and `AGENT_ONLINE_KEY`, both required; an Anthropic URL also gets `x-api-key` | `AGENT_ONLINE_MODEL` = `claude-sonnet-4-6` |
| `remote` | a bigger local model on the tailnet: a laptop's Ollama, exo, llama.cpp | `AGENT_REMOTE_URL`, optional `AGENT_REMOTE_KEY` | `AGENT_REMOTE_MODEL` = `gpt-oss-120b` |
| `local` | Ollama on this machine; always present | `OLLAMA_URL` + `/v1`; the container's `MODEL` | `qwen3:4b` |

`AGENT_PREFER` orders them: `strongest` (default) — online, remote, local; `fallback` — remote, online, local,
with online kept above local because a rung is skipped only when it *fails* and a 4B model never fails, it
answers weakly; `private` — the online rung removed, so nothing ever leaves the network. A rung that raises
is skipped for five minutes. The ladder is rebuilt every 60 seconds from the node's settings, so a change in Set up → Agent takes effect without a restart; a value in `AGENT_ONLINE_URL` that is not a URL (node #1 once
had the example's comment there) is logged and ignored.

`tools/remote-model.sh gptoss` runs llama.cpp's server on a laptop or workstation with gpt-oss-120b (about
63 GB) or `qwen122b` for Qwen3.5-122B (about 75 GB), with an API key and tool calling on, and prints the
three `AGENT_REMOTE_*` lines for the node's `.env`. Tested: gpt-oss-120b answers in about two seconds with
correct tool use; the node falls back to its local model when the laptop is away.

## How it answers

One MCP session per question — a long-lived one died silently once — over `http://app:8080/mcp` with the
admin token. The system prompt says: use the tools, never guess a number; `health_check` and `status` for
"how is it"; `context` for the sea, the weather, the land; `readings` for history; answer in Bahasa Indonesia
when `ALERT_LOCALE` is `id`, otherwise English; open with a fitting emoji; avoid statistics; when a person
says they did something, record it with `act`; never reveal a token; hand shell tasks back through
`maintenance`; plain text under a hundred words, without narrating.

Up to eight rounds of tool calls at temperature 0.2, with the last six messages of the chat — three exchanges — as context. On the
small rung the model is told not to think aloud and the final answer is requested as constrained JSON,
because a 4B model otherwise narrates its reasoning as prose. `<think>` blocks and Markdown are stripped
before sending, since Telegram shows them raw. Messages from a chat not in `TELEGRAM_CHAT_IDS` are ignored
and logged. If no rung answers, the reply says so and where to look: `ollama list` on the node, and the
`AGENT_*` settings.

## Commands that need no model

| in Telegram | does |
|---|---|
| `/act 12 closed the windows` | records the action on alert 12 with the actor `<AGENT_NAME>/telegram`; replies "Recorded: you acted on #12." |
| `/stack [issue]` | the issue's state, its sentence in your language, the four distances with their provenance and unit, and up to two open asks — a template over the `issues` tool, no model ever |
| `/model [local\|remote\|online\|auto]` | pins a rung for this chat and prints the ladder: each rung, its model, its host, whether it is currently skipped, and what `AGENT_PREFER` means |

## What leaves the network

Nothing, unless you give the online rung a key. `AGENT_ONLINE_KEY` is described in the settings as the only
thing that lets household data leave your network; with `AGENT_PREFER=private` even a key set is never used.
The bot's writes appear in the audit trail as `<AGENT_NAME>/<rung>`, and tool arguments containing `KEY`,
`TOKEN` or `PASS` are masked in its log.

> **Note.** There is no fence on the model's numbers yet. The only published test of a small model reading
> environmental time series found one inventing a year of data from three days; the report is written by the
> node from SQL for that reason, and a model-written report is refused by design until its numbers can be
> checked against the bundle. The bot's answers are the model's, told to use the tools and not to guess.
