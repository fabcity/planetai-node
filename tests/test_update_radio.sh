#!/usr/bin/env bash
# update.sh restarts the host LoRa gateway where its service is installed, so a node runs the radio.py it just pulled.
# restart_radio (and the spin and warn it uses) are lifted out of the real update.sh and run with HOME pointed at a
# throwaway folder and launchctl/systemctl stubbed on PATH: with no service, a launchd one, a systemd one, and a
# launchctl that fails. Then the file itself is read to show the call comes after the containers restart.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; fails=$((fails + 1)); }
d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT

{ grep '^warn()' update.sh; sed -n '/^spin() {/,/^}$/p' update.sh; sed -n '/^restart_radio() {/,/^}$/p' update.sh; } > "$d/lift.sh"
grep -q '^restart_radio() {' "$d/lift.sh" && grep -q '^spin() {' "$d/lift.sh" \
  || { echo "  FAIL could not lift spin and restart_radio out of update.sh"; exit 1; }

mkdir -p "$d/bin"
for c in launchctl systemctl; do
  printf '#!/bin/sh\necho "%s $*" >> "%s/calls"\nexit "${STUB_RC:-0}"\n' "$c" "$d" > "$d/bin/$c"; chmod +x "$d/bin/$c"
done
# run <home>: the lifted function in a fresh shell, stdout not a terminal (as under ssh or cron)
run() { rm -f "$d/calls"; : > "$d/calls"; HOME="$1" PATH="$d/bin:$PATH" ULOG="$d/ulog" bash -c "set -euo pipefail; source '$d/lift.sh'; restart_radio" 2>&1; }

H="$d/none"; mkdir -p "$H"
out="$(run "$H")"; rc=$?
[ $rc -eq 0 ] && [ -z "$out" ] && [ ! -s "$d/calls" ] && ok "a node with no gateway service sees nothing and nothing is called" \
  || bad "no service, but exit $rc, output '$out', calls '$(cat "$d/calls")'"

H="$d/mac"; mkdir -p "$H/Library/LaunchAgents"; touch "$H/Library/LaunchAgents/city.fab.planetai.radio.plist"
out="$(run "$H")"; rc=$?
[ $rc -eq 0 ] && grep -qx "launchctl kickstart -k gui/$(id -u)/city.fab.planetai.radio" "$d/calls" \
  && ok "with the launchd service, it kickstarts it (-k: the running gateway is stopped first)" || bad "launchd: exit $rc, calls '$(cat "$d/calls")'"
grep -q "✓ restarting the LoRa gateway" <<< "$out" && ok "and says so" || bad "no restart line: $out"

H="$d/linux"; mkdir -p "$H/.config/systemd/user"; touch "$H/.config/systemd/user/planetai-radio.service"
out="$(run "$H")"; rc=$?
[ $rc -eq 0 ] && grep -qx "systemctl --user try-restart planetai-radio" "$d/calls" \
  && ok "with the systemd service, it try-restarts it (a stopped gateway stays stopped)" || bad "systemd: exit $rc, calls '$(cat "$d/calls")'"

out="$(STUB_RC=3 run "$d/mac")"; rc=$?
[ $rc -eq 0 ] && grep -q "did not restart" <<< "$out" && grep -qF "By hand:  launchctl kickstart -k gui/" <<< "$out" \
  && ok "a gateway that will not restart warns with the command, and the update goes on" || bad "failing launchctl: exit $rc, output '$out'"

# ---------------------------------------------------------------- wired in: after the containers are back
at() { grep -nxF -- "$1" update.sh | head -1 | cut -d: -f1; }
u="$(grep -nF 'spin "restarting the containers" docker compose up -d' update.sh | head -1 | cut -d: -f1)"; r="$(at 'restart_radio')"
v="$(grep -nF '# 7. verify' update.sh | head -1 | cut -d: -f1)"
[ -n "$u" ] && [ -n "$r" ] && [ -n "$v" ] && [ "$u" -lt "$r" ] && [ "$r" -lt "$v" ] \
  && ok "update.sh calls it after the containers restart, before the doctor" || bad "call missing or out of order (up $u, restart_radio $r, verify $v)"

echo
[ "$fails" -eq 0 ] && { echo "update radio: the host gateway restarts on update where it is installed, and nowhere else"; exit 0; }
echo "update radio: $fails failure(s)"; exit 1
