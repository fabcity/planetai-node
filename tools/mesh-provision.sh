#!/usr/bin/env bash
# Provision a Meshtastic radio over USB in one go. Needs:  pip3 install --user meshtastic
#
#   tools/mesh-provision.sh <port> "<long name>" <SHORT> <SENSOR|CLIENT> [region] [channel-url-file]
#
#   tools/mesh-provision.sh /dev/cu.usbmodem1101 "Subak edge"    SBK SENSOR SG_923 ~/planetai-mesh.url
#   tools/mesh-provision.sh /dev/cu.usbmodem1101 "kitchen shelf"  SHF CLIENT SG_923 ~/planetai-mesh.url
#
# Gateway (the ESP32): same command with GATEWAY=1 and the broker details printed by `planetai meshtastic`,
# plus the WiFi it should join. Sets uplink/downlink on the channel, MQTT with JSON on, then WiFi last
# (WiFi on turns Bluetooth off on ESP32; USB keeps working, so this script still can).
#   GATEWAY=1 MQTT_ADDR=192.168.4.190:1883 MQTT_PASS=<printed> WIFI_SSID=<ssid> WIFI_PSK=<password> \
#     tools/mesh-provision.sh /dev/cu.usbmodem1101 "bayu-2 gateway" GW CLIENT SG_923 ~/planetai-mesh.url
#
# The first radio creates the private channel and writes its URL to the file; every later radio imports it, so
# the whole fleet shares one encrypted channel without anyone scanning QR codes. The gateway (ESP32) takes the
# same channel this way too; its WiFi and MQTT settings are separate (see docs/MESHTASTIC_APP.md D1).
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
PORT="${1:?port, e.g. /dev/cu.usbmodem1101}"; LONG="${2:?long name}"; SHORT="${3:?short name, 2-4 chars}"
ROLE="${4:-SENSOR}"; REGION="${5:-SG_923}"; CHFILE="${6:-$HOME/planetai-mesh.url}"
CHNAME="${CHNAME:-planetai}"
say() { printf '\033[1;32m>>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mxx %s\033[0m\n' "$*" >&2; exit 1; }
# every settings write reboots the radio; an ESP32 takes noticeably longer than an nRF52 to come back.
# Wait until the CLI can talk to it again rather than sleeping a fixed time and hoping.
ready() { for i in $(seq 1 30); do meshtastic --port "$PORT" --info >/dev/null 2>&1 && return 0; sleep 2; done; die "radio on $PORT did not come back after a reboot"; }
m() { local out; out="$(meshtastic --port "$PORT" "$@" 2>&1)" || { echo "$out" | tail -5; die "meshtastic $* failed"; }; echo "$out" | grep -vE '^Connected to radio|^$' || true; }

say "region $REGION, preset LONG_FAST, name '$LONG' ($SHORT), role $ROLE"
ready
m --set lora.region "$REGION" --set lora.modem_preset LONG_FAST --set-owner "$LONG" --set-owner-short "$SHORT" --set device.role "$ROLE"
sleep 3; ready
if [[ "$ROLE" == "SENSOR" ]]; then
  say "sensor: environment telemetry every 15 min, position every 30 min, GPS on"
  m --set telemetry.environment_measurement_enabled true --set telemetry.environment_update_interval 900 \
    --set position.gps_mode ENABLED --set position.position_broadcast_secs 1800
  sleep 3; ready
fi
if [[ -s "$CHFILE" ]]; then
  say "joining the fleet's channel from $CHFILE"
  m --seturl "$(cat "$CHFILE")"
  sleep 3; ready
  meshtastic --port "$PORT" --info 2>/dev/null | grep -q "\"name\": \"$CHNAME\"" || die "channel '$CHNAME' is not on the radio after import — check $CHFILE"
  say "channel '$CHNAME' confirmed on the radio"
else
  say "first radio: creating channel '$CHNAME' with a random key, saving its URL to $CHFILE"
  m --ch-add "$CHNAME"; sleep 3; ready
  m --ch-set psk random --ch-index 1; sleep 3; ready
  m --qr-all 2>/dev/null | grep -oE 'https://meshtastic.org/e/#[A-Za-z0-9_=-]+' | head -1 > "$CHFILE"
  [[ -s "$CHFILE" ]] && say "saved. Run this script for the other radios with the same file to share it." || echo "!! could not capture the channel URL; run: meshtastic --port $PORT --qr-all"
fi
if [[ "${GATEWAY:-0}" == "1" ]]; then
  : "${MQTT_ADDR:?MQTT_ADDR=host:1883 (planetai meshtastic prints it)}"; : "${MQTT_PASS:?MQTT_PASS (planetai meshtastic prints it)}"
  say "gateway: uplink + downlink on channel '$CHNAME'"
  m --ch-index 1 --ch-set uplink_enabled true --ch-set downlink_enabled true; sleep 3; ready
  say "gateway: MQTT → $MQTT_ADDR, JSON on, encryption off"
  m --set mqtt.enabled true --set mqtt.address "$MQTT_ADDR" --set mqtt.username "${MQTT_USER:-planetai}" --set mqtt.password "$MQTT_PASS" \
    --set mqtt.encryption_enabled false --set mqtt.json_enabled true --set mqtt.root msh; sleep 3; ready
  if [[ -n "${WIFI_SSID:-}" ]]; then
    say "gateway: WiFi '$WIFI_SSID' (last: this turns Bluetooth off; USB keeps working)"
    m --set network.wifi_enabled true --set network.wifi_ssid "$WIFI_SSID" --set network.wifi_psk "${WIFI_PSK:-}"; sleep 3; ready
  fi
fi
sleep 3; ready
say "result:"
m --get lora.region --get device.role --get telemetry.environment_measurement_enabled --info 2>/dev/null | grep -E 'lora.region|device.role|environment_measurement|longName|firmwareVersion' | head -6
