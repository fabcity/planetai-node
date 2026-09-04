#!/usr/bin/env bash
# Provision a Meshtastic radio over USB in one go. Needs:  pip3 install --user meshtastic
#
#   tools/mesh-provision.sh <port> "<long name>" <SHORT> <SENSOR|CLIENT> [region] [channel-url-file]
#
#   tools/mesh-provision.sh /dev/cu.usbmodem1101 "Subak edge"    SBK SENSOR SG_923 ~/planetai-mesh.url
#   tools/mesh-provision.sh /dev/cu.usbmodem1101 "kitchen shelf"  SHF CLIENT SG_923 ~/planetai-mesh.url
#
# The first radio creates the private channel and writes its URL to the file; every later radio imports it, so
# the whole fleet shares one encrypted channel without anyone scanning QR codes. The gateway (ESP32) takes the
# same channel this way too; its WiFi and MQTT settings are separate (see docs/MESHTASTIC_APP.md D1).
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
PORT="${1:?port, e.g. /dev/cu.usbmodem1101}"; LONG="${2:?long name}"; SHORT="${3:?short name, 2-4 chars}"
ROLE="${4:-SENSOR}"; REGION="${5:-SG_923}"; CHFILE="${6:-$HOME/planetai-mesh.url}"
CHNAME="${CHNAME:-planetai}"
m() { meshtastic --port "$PORT" "$@" 2>&1 | grep -vE '^Connected to radio|^$' || true; }
say() { printf '\033[1;32m>>\033[0m %s\n' "$*"; }

say "region $REGION, preset LONG_FAST, name '$LONG' ($SHORT), role $ROLE"
m --set lora.region "$REGION" --set lora.modem_preset LONG_FAST --set-owner "$LONG" --set-owner-short "$SHORT" --set device.role "$ROLE"
sleep 6
if [[ "$ROLE" == "SENSOR" ]]; then
  say "sensor: environment telemetry every 15 min, position every 30 min, GPS on"
  m --set telemetry.environment_measurement_enabled true --set telemetry.environment_update_interval 900 \
    --set position.gps_mode ENABLED --set position.position_broadcast_secs 1800
  sleep 6
fi
if [[ -s "$CHFILE" ]]; then
  say "joining the fleet's channel from $CHFILE"
  m --seturl "$(cat "$CHFILE")"
else
  say "first radio: creating channel '$CHNAME' with a random key, saving its URL to $CHFILE"
  m --ch-add "$CHNAME"; sleep 6
  m --ch-set psk random --ch-index 1; sleep 6
  m --qr-all 2>/dev/null | grep -oE 'https://meshtastic.org/e/#[A-Za-z0-9_=-]+' | head -1 > "$CHFILE"
  [[ -s "$CHFILE" ]] && say "saved. Run this script for the other radios with the same file to share it." || echo "!! could not capture the channel URL; run: meshtastic --port $PORT --qr-all"
fi
sleep 6
say "result:"
m --get lora.region --get device.role --get telemetry.environment_measurement_enabled --info 2>/dev/null | grep -E 'lora.region|device.role|environment_measurement|longName|firmwareVersion' | head -6
