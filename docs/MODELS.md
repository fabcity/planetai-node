# Models

**A node needs none of this.**

A PLANETAI node reads its sensors, evaluates its rules, writes its report and sends its alerts with no
model anywhere. Every number on the dashboard is the node's own arithmetic; every sentence in a report
and every alert is written from a template by `app/report.py`. `/stack` in Telegram answers from the
node's own words and never consults a model at all. If you install nothing on this page, nothing stops
working.

What a model adds is **conversation**: somebody asking "is the air bad right now?" in their own words and
getting an answer, and being able to say "I closed the windows" and have that recorded. That is worth
having. It is not the node.

Two things worth knowing before you download several gigabytes:

- **The node is 230 MiB across both containers and under 5% of a core between polls.** The smallest model
  here is six times the node. On a revived 2015 laptop — the best hardware story this project has — the
  model is what will fail first, not the node.
- **The local model gets `read` and `act` only.** It cannot change a setting, run a pack's code, or make
  the node message the household by itself. `planetai agent` prints every tool and its class;
  `app/tool_classes.py` is the authority.

## Getting one

```bash
planetai agent local                    # Ollama, the loop, the Telegram bot. Downloads NO model.
planetai agent local pull qwen3.5:4b    # the large download, when you want it
```

`planetai agent local` prints the recommendation for this machine's memory, with its size, and stops.
`pull` fetches the tag and points `AGENT_MODEL` at it. The Model page in the dashboard has the same
button.

## The catalogue

**Sizes are the weights as the registry serves them, measured against `registry.ollama.ai` on
20 September 2026** — not the model's RAM footprint, which is larger while it is answering. Assume
roughly the file size again in RAM, and do not run a model whose file is more than about half the
machine's memory.

| tag | on disk | licence | what it is for |
|---|---|---|---|
| **`qwen3.5:4b`** | 3.4 GB | Apache-2.0 | **the recommendation on 8 GB.** Tool-calling, three languages, answers a household's question about its own node. |
| **`qwen3.5:9b`** | 6.6 GB | Apache-2.0 | **the recommendation on 16 GB and up.** Noticeably better at following a multi-step question; the same tools. |
| `qwen3:4b` | 2.5 GB | Apache-2.0 | what the node recommended before v0.63. Still fine; a gigabyte smaller, and the tag existing nodes hold. |
| `qwen3:8b` | 5.2 GB | Apache-2.0 | the 16 GB recommendation before v0.63. |
| `qwen3:1.7b` | 1.4 GB | Apache-2.0 | the floor. For a 4 GB machine where the alternative is no conversation at all. Expect it to be literal and to lose the thread. |

**It must do tool calling.** The loop hands the model the node's tools and expects it to call them;
a model that cannot will answer plausibly about a node it never read, which is worse than not answering.
`gemma3:4b` (3.3 GB) is a good small model and **does not** do tool calling — it is named here so that
nobody has to find that out on their own node.

Any OpenAI-compatible tool-calling model works. These five are the ones whose tags, sizes and licences
were checked; the table is not a permission list.

## Not on this machine

The local rung is the floor, not the ceiling. The Model page configures two more:

- **remote** — a bigger model on your own tailnet: a laptop's Ollama, an exo cluster. Private, no key.
- **online** — Anthropic, OpenAI or Gemini, with a key. The only rung that sends anything off your
  network, and `AGENT_PREFER` decides whether it is used at all. **Since v0.63 the default is `private`**,
  so a node that has never chosen sends nothing anywhere. `docs/GUI.md` has the three options.

A node with `private` and no local model still answers alerts, writes reports and draws its page. It just
does not chat.

## What is not here

No per-class default profile, no bundled weights, no model in the tarball, and no pack that requires one.
The 14 September models memo proposed 5–30 GB profiles per node class; a default profile is a different
product from a 230 MiB node, and nothing in this repository pulls a model unless a person asks for it by
tag.
