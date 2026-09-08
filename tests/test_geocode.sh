#!/usr/bin/env bash
# "Mahon" must find Maó in Menorca. Runs the real geocode() lifted out of bin/planetai, with both
# geocoders stubbed on PATH — the answers they actually gave on 8 September 2026 — so the test is
# offline and what is under test is the ranking, not the internet.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT

# Nominatim knows Mahon. Open-Meteo does not: five places called Mahon, none of them in Spain.
cat > "$d/nominatim.json" <<'J'
[{"lat":"39.8894922","lon":"4.2662071","name":"Maó","display_name":"Maó, Menorca, Illes Balears, España",
  "address":{"town":"Maó","state":"Illes Balears","country_code":"es"}},
 {"lat":"40.9386577","lon":"-85.3805300","name":"Mahon","display_name":"Mahon, Indiana",
  "address":{"village":"Mahon","state":"Indiana","country_code":"us"}}]
J
cat > "$d/openmeteo.json" <<'J'
{"results":[
 {"latitude":12.85,"longitude":-14.81667,"name":"Mahon","admin1":"Kolda","country_code":"SN","timezone":"Africa/Dakar"},
 {"latitude":11.0426,"longitude":-5.22144,"name":"Mahon","admin1":"Hauts-Bassins","country_code":"BF","timezone":"Africa/Ouagadougou"},
 {"latitude":39.03778,"longitude":-94.94608,"name":"Mahon","admin1":"Kansas","country_code":"US","timezone":"America/Chicago"}]}
J
printf '%s\n' \
  '#!/bin/sh' \
  'for a in "$@"; do' \
  '  case "$a" in' \
  "    *nominatim.openstreetmap.org*)    cat '$d/nominatim.json'; exit 0 ;;" \
  "    *geocoding-api.open-meteo.com*)   cat '$d/openmeteo.json'; exit 0 ;;" \
  '    *api.open-meteo.com/v1/forecast*) echo "{\"timezone\":\"Europe/Madrid\"}"; exit 0 ;;' \
  '  esac' \
  'done' \
  'exit 1' > "$d/curl"
chmod +x "$d/curl"

# geocode() alone, out of the real file: its definition to the closing brace. Never a retyped copy.
sed -n '/^geocode() {/,/^}$/p' bin/planetai > "$d/geocode.sh"
grep -q 'nominatim' "$d/geocode.sh" || { echo "  FAIL could not lift geocode() out of bin/planetai"; exit 1; }

printf '%s\n' \
  'set -uo pipefail' \
  'urlenc() { python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$1"; }' \
  'json() { python3 -c "import sys,json' \
  'd=json.load(sys.stdin)' \
  '$1"; }' \
  'tz_for() { curl -sf "https://api.open-meteo.com/v1/forecast?latitude=$1&longitude=$2" | json '"'"'print(d.get("timezone","UTC"))'"'"' 2>/dev/null || echo UTC; }' \
  '. "$GEOCODE_SH"' \
  'geocode "$1"' > "$d/run.sh"

out="$(PATH="$d:$PATH" GEOCODE_SH="$d/geocode.sh" bash "$d/run.sh" Mahon 2>&1)"
first="$(head -1 <<<"$out")"

echo "geocode: the tester in Menorca"
chk() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; echo "$out" | sed 's/^/       /'; fails=$((fails+1)); fi; }
chk '"Mahon" puts Maó first'                       'grep -q "Maó" <<<"$first"'
chk 'and it is in Spain'                           'grep -q "|ES|" <<<"$first"'
chk 'and carries a time zone'                      'grep -q "Europe/Madrid" <<<"$first"'
n="$(grep -c . <<<"$out")"
chk "both geocoders were asked (got $n hits)"      '[[ "$n" -ge 4 ]]'
chk "and the list is capped at 6 (got $n)"         '[[ "$n" -le 6 ]]'

[[ $fails -eq 0 ]] && { echo "geocode tests pass"; exit 0; } || { echo "$fails geocode test(s) failed"; exit 1; }
