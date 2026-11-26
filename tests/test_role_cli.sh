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
  *"indoor"*) echo 6; exit 0;;
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
out="$(run community)"; rc=$?
[[ $rc -eq 0 ]] && ok "private to community succeeds" || bad "exit $rc: $out"
grep -q 'This node holds 6 indoor sensors' <<<"$out" && ok "it says how many indoor sensors the node holds" || bad "no indoor count: $out"
grep -q 'backups/test.sql.gz' <<<"$out" && ok "and where the backup goes" || bad "no backup path"
grep -q '^NODE_KIND=community$' "$D/.env" && ok "NODE_KIND=community is written" || bad ".env: $(cat "$D/.env")"
grep -q 'backup ran' "$t/calls" && grep -q 'force-recreate app agent' "$t/calls" && ok "the backup ran, then app and agent restarted" || bad "calls: $(cat "$t/calls" 2>/dev/null)"
grep -q 'Readings, settings and alerts stay as they are' <<<"$out" && ok "it names what changes" || bad "no what-changes lines"

run private >/dev/null; grep -q '^NODE_KIND=home$' "$D/.env" && ok "community to private writes NODE_KIND=home" || bad ".env: $(cat "$D/.env")"

printf 'NODE_NAME=t\nNODE_KIND=home\n' > "$D/.env"; before="$(cat "$D/.env")"
out="$(DOCKER_DOWN=1 run community)"; rc=$?
[[ $rc -eq 1 ]] && grep -qF 'The node is not running: start it with planetai start, then try again.' <<<"$out" && [[ "$(cat "$D/.env")" == "$before" ]] \
  && ok "with the containers down it says so, exits 1 and leaves .env alone" || bad "rc=$rc out=$out"

out="$(run banana)"; rc=$?
[[ $rc -eq 2 ]] && grep -q 'private or community' <<<"$out" && ok "an unknown role exits 2 and names the two" || bad "rc=$rc out=$out"
[[ $fails -eq 0 ]]
