#!/usr/bin/env bash
# `planetai role` moves a node between private and community. It counts the indoor sensors a community node's public
# pages would hide, takes a backup, and only then writes NODE_KIND and restarts. With the containers down it changes
# nothing. Docker is a stub that records what it was asked.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"; fails=0
ok(){ echo "  ok   $1"; }; bad(){ echo "  FAIL $1"; fails=$((fails+1)); }
t="$(mktemp -d)"; trap 'rm -rf "$t"' EXIT
D="$t/node"; mkdir -p "$D/bin" "$t/stub"
cp "$REPO/bin/planetai" "$D/bin/planetai"; printf 'v0.0.0-test\n' > "$D/VERSION"
printf '#!/bin/sh\necho "backup ran" >> "%s/calls"\necho "Backup written to ./backups/test.sql.gz"\n' "$t" > "$D/backup.sh"; chmod +x "$D/backup.sh"
# docker: pg_isready answers unless DOCKER_DOWN; the indoor count answers 6; every `up` is recorded
cat > "$t/stub/docker" <<'STUB'
#!/bin/sh
[ -n "$DOCKER_DOWN" ] && exit 1
case "$*" in
  *pg_isready*) exit 0;;
  *"indoor"*) [ -n "$COUNT_FAIL" ] && exit 1; echo 6; exit 0;;
  *" up "*) echo "$*" >> "$CALLS"; exit 0;;
esac
exit 0
STUB
chmod +x "$t/stub/docker"
run() { PATH="$t/stub:/usr/bin:/bin:/usr/local/bin" PLANETAI_HOME="$D" CALLS="$t/calls" bash "$D/bin/planetai" role "$@" </dev/null 2>&1; }

printf 'NODE_NAME=t\nNODE_KIND=home\n' > "$D/.env"
[[ "$(run)" == private ]] && ok "planetai role prints private for NODE_KIND=home" || bad "role did not print private"
printf 'NODE_NAME=t\nNODE_KIND=district\n' > "$D/.env"
[[ "$(run)" == community ]] && ok "and community for district" || bad "role did not print community"

printf 'NODE_NAME=t\nNODE_KIND=home\n' > "$D/.env"; rm -f "$t/calls"
rm -f "$t/calls"; before="$(cat "$D/.env")"
out="$(run community)"; rc=$?
[[ $rc -ne 0 ]] && grep -qF 'No terminal here: run it in a terminal, or add --yes.' <<<"$out" && [[ "$(cat "$D/.env")" == "$before" && ! -e "$t/calls" ]] \
  && ok "with no terminal and no --yes it refuses, and changes nothing" || bad "no-tty rc=$rc out=$out"
out="$(run --yes community)"; rc=$?
[[ $rc -eq 0 ]] && ok "private to community succeeds with --yes" || bad "exit $rc: $out"
grep -q 'This node holds 6 indoor sensors' <<<"$out" && ok "it says how many indoor sensors the node holds" || bad "no indoor count: $out"
grep -q 'backups/test.sql.gz' <<<"$out" && ok "and where the backup goes" || bad "no backup path"
grep -q '^NODE_KIND=community$' "$D/.env" && ok "NODE_KIND=community is written" || bad ".env: $(cat "$D/.env")"
grep -q 'backup ran' "$t/calls" && grep -q 'force-recreate app agent' "$t/calls" && ok "the backup ran, then app and agent restarted" || bad "calls: $(cat "$t/calls" 2>/dev/null)"
grep -q 'Readings, settings and alerts stay as they are' <<<"$out" && ok "it names what changes" || bad "no what-changes lines"

run --yes private >/dev/null; grep -q '^NODE_KIND=home$' "$D/.env" && ok "community to private writes NODE_KIND=home" || bad ".env: $(cat "$D/.env")"

printf 'NODE_NAME=t\nNODE_KIND=home\n' > "$D/.env"; before="$(cat "$D/.env")"
out="$(DOCKER_DOWN=1 run --yes community)"; rc=$?
[[ $rc -eq 1 ]] && grep -qF 'The node is not running: start it with planetai start, then try again.' <<<"$out" && [[ "$(cat "$D/.env")" == "$before" ]] \
  && ok "with the containers down it says so, exits 1 and leaves .env alone" || bad "rc=$rc out=$out"

printf 'NODE_NAME=t\nNODE_KIND=home\n' > "$D/.env"
out="$(COUNT_FAIL=1 run --yes community)"
grep -qF 'This node may hold indoor sensors (the count could not be read).' <<<"$out" && ! grep -q 'holds 0' <<<"$out" && grep -q '^NODE_KIND=community$' "$D/.env" \
  && ok "a failed count says it is unknown and goes on to the confirm" || bad "count fail: $out"
# the role's starting settings: runtime keys go to the node's settings, PACKS_ADD joins PACKS_ENABLED, nothing is removed
cat > "$t/stub/curl" <<'STUB'
#!/bin/sh
case "$*" in
  *"-X PUT"*) while [ $# -gt 0 ]; do [ "$1" = -d ] && echo "$2" >> "$PUTS"; shift; done; printf '\n200'; exit 0;;
esac
cat "$SETTINGS"
STUB
chmod +x "$t/stub/curl"
settings() { python3 - "$1" > "$t/settings.json" <<'PY'
import json, sys
keys = ["SHARE_LEVEL", "REPORT_EVERY", "ALERT_ENGINE", "ALERT_LEVEL", "PACKS_ENABLED"]
rows = [dict(key=k, group="g", secret=False, restart=False, value=sys.argv[1] if k == "PACKS_ENABLED" else "", source="default", help="") for k in keys]
print(json.dumps(dict(runtime=rows, bootstrap=[])))
PY
}
runp() { PATH="$t/stub:/usr/bin:/bin:/usr/local/bin" PLANETAI_HOME="$D" CALLS="$t/calls" PUTS="$t/puts" SETTINGS="$t/settings.json" bash "$D/bin/planetai" role "$@" </dev/null 2>&1; }
mkdir -p "$D/presets"; cp -R "$REPO/presets/roles" "$D/presets/"
eval "$(sed -n '/^merge_packs() {/,/^}/p' "$REPO/bin/planetai")"
[[ "$(merge_packs "smartcitizen,heat" "heat,eyes")" == "smartcitizen,heat,eyes" ]] && ok "merge_packs adds the new ones after the current ones" || bad "merge_packs union"
[[ -z "$(merge_packs "" "eyes")" ]] && ok "an empty list stays empty (it means every pack)" || bad "merge_packs empty"

printf 'NODE_NAME=t\nNODE_KIND=home\nADMIN_TOKEN=x\n' > "$D/.env"; settings "smartcitizen,air-quality"; rm -f "$t/puts"
out="$(runp --yes community)"
grep -qF '"SHARE_LEVEL":"open"' "$t/puts" && grep -qF '"ALERT_LEVEL":"act"' "$t/puts" && ok "community.env sets its runtime keys through the settings" || bad "puts: $(cat "$t/puts" 2>/dev/null) out=$out"
grep -qF '"PACKS_ENABLED":"smartcitizen,air-quality,nearby,forecast,coast,fire,hydro,place,index"' "$t/puts" \
  && ok "its packs are added after the ones already on" || bad "packs: $(cat "$t/puts" 2>/dev/null)"
printf 'NODE_NAME=t\nNODE_KIND=community\nADMIN_TOKEN=x\n' > "$D/.env"; settings ""; rm -f "$t/puts"
runp --yes private >/dev/null
grep -q PACKS_ENABLED "$t/puts" && bad "an empty PACKS_ENABLED was narrowed" || ok "an empty PACKS_ENABLED is left alone"
grep -qF '"ALERT_ENGINE":"events"' "$t/puts" && ok "private.env sets its keys too" || bad "private puts: $(cat "$t/puts" 2>/dev/null)"
out="$(run banana)"; rc=$?
[[ $rc -eq 2 ]] && grep -q 'private or community' <<<"$out" && ok "an unknown role exits 2 and names the two" || bad "rc=$rc out=$out"
[[ $fails -eq 0 ]]
