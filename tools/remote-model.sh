#!/usr/bin/env bash
# Serve a big local model from a laptop or workstation as the node's `remote` rung, over the tailnet.
# llama.cpp server, OpenAI-compatible, with tool calling (--jinja) and an API key. Prints the .env lines for the node.
#
#   tools/remote-model.sh gptoss          # gpt-oss-120b MXFP4 (~63 GB): fast, reliable tool use
#   tools/remote-model.sh qwen122b        # Qwen3.5-122B-A10B MXFP4 (~75 GB): the ceiling; one big model at a time
#
# Paths default to Tomas's laptop; override with GGUF=... LLAMA=... PORT=... KEY=...
set -euo pipefail
which="${1:-gptoss}"
LLAMA="${LLAMA:-$HOME/llama-cpp-src/build/bin/llama-server}"
PORT="${PORT:-8082}"
KEYFILE="$HOME/.planetai-remote-model.key"
[[ -f "$KEYFILE" ]] || openssl rand -hex 16 > "$KEYFILE"
KEY="${KEY:-$(cat "$KEYFILE")}"
case "$which" in
  gptoss)   GGUF="${GGUF:-$HOME/.cache/huggingface/hub/models--ggml-org--gpt-oss-120b-GGUF/snapshots/238abdd290bb874b90a5da1b4549881b7d05c091/gpt-oss-120b-MXFP4.gguf}"; ALIAS=gpt-oss-120b;;
  qwen122b) D="$HOME/.cache/huggingface/hub/models--unsloth--Qwen3.5-122B-A10B-GGUF/snapshots"; GGUF="${GGUF:-$D/$(ls "$D" | head -1)/MXFP4_MOE/Qwen3.5-122B-A10B-MXFP4_MOE-00001-of-00003.gguf}"; ALIAS=qwen3.5-122b;;
  *) echo "gptoss | qwen122b"; exit 1;;
esac
[[ -f "$GGUF" ]] || { echo "no model at $GGUF"; exit 1; }
pkill -f "llama-server.*--port $PORT" 2>/dev/null && sleep 3 || true
nohup "$LLAMA" -m "$GGUF" --port "$PORT" --host 0.0.0.0 -c 65536 -ngl 99 --alias "$ALIAS" --jinja --api-key "$KEY" >> "$HOME/local-llm/${ALIAS}-server.log" 2>&1 &
echo ">> $ALIAS loading on :$PORT (pid $!). Log: ~/local-llm/${ALIAS}-server.log"
for i in $(seq 1 60); do sleep 5; curl -s --max-time 3 -H "Authorization: Bearer $KEY" "http://127.0.0.1:$PORT/v1/models" | grep -q '"id"' && { echo ">> loaded after $((i*5))s"; break; }; done
IP="$(tailscale ip -4 2>/dev/null || /Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "On the node, in .env (then planetai restart):"
echo "  AGENT_REMOTE_URL=http://${IP}:${PORT}/v1"
echo "  AGENT_REMOTE_MODEL=${ALIAS}"
echo "  AGENT_REMOTE_KEY=${KEY}"
echo
echo "The node falls back to its local model whenever this machine is off or away."
