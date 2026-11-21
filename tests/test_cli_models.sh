#!/usr/bin/env bash
# `planetai models`, run for real against a throwaway node folder. docker is a stub on PATH that records its
# arguments and fails on request, so nothing here starts a container or touches the network: what is under test is
# the command, its order of steps, and what it leaves in .env when a step fails.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; fails=$((fails + 1)); }
d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT
mkdir -p "$d/bin" "$d/node/packs/predict"
cp packs/predict/models.json "$d/node/packs/predict/"
cat > "$d/bin/docker" <<STUB
#!/bin/sh
echo "docker \$*" >> "$d/docker.log"
case "\$*" in
  *"pull.py --have"*) [ -f "$d/have" ] ;;
  *"pull.py"*) [ ! -f "$d/pull-fails" ] ;;
  *"compose build"*) [ ! -f "$d/build-fails" ] ;;
  *) exit 0 ;;
esac
STUB
printf '#!/bin/sh\nexit 7\n' > "$d/bin/curl"; chmod +x "$d/bin/docker" "$d/bin/curl"
N="$d/node"
pm() { PATH="$d/bin:$PATH" PLANETAI_HOME="$N" bash bin/planetai models "$@" 2>&1; }
env0() { printf '%s\n' "$@" > "$N/.env"; : > "$d/docker.log"; rm -f "$d/pull-fails" "$d/build-fails" "$d/have"; }
M=amazon/chronos-2

# ---------------------------------------------------------------- an unknown name, before anything is touched
env0 APP_PORT=1 PACKS_ENABLED=air-quality,heat; cp "$N/.env" "$d/before"
out="$(pm pull nosuch/model --yes)"; rc=$?
[ $rc -ne 0 ] && grep -q "amazon/chronos-2, amazon/chronos-bolt-tiny" <<< "$out" && cmp -s "$N/.env" "$d/before" && [ ! -s "$d/docker.log" ] \
  && ok "an unknown name is refused, names the catalogue, and changes nothing (no docker call, .env the same)" || bad "unknown name (exit $rc): $out / $(cat "$d/docker.log")"
out="$(pm pull)"; [ $? -ne 0 ] && [ ! -s "$d/docker.log" ] && ok "no name is refused" || bad "no name: $out"

# ---------------------------------------------------------------- a pull, with a list of packs
out="$(pm pull $M --yes)"; rc=$?
[ $rc -eq 0 ] && grep -qx "PREDICT_MODEL=$M" "$N/.env" && grep -qx "PACKS_ENABLED=air-quality,heat,predict" "$N/.env" && grep -qx "COMPOSE_PROFILES=models" "$N/.env" \
  && ok "pull --yes: PREDICT_MODEL set, predict joins the list, the models profile is on" || bad "pull --yes (exit $rc): $out / $(cat "$N/.env")"
grep -q "456 MB" <<< "$out" && grep -q "Apache-2.0" <<< "$out" && ok "it says the size and the licence" || bad "no size or licence: $out"
steps="$(sed -n 's/^docker //p' "$d/docker.log" | cut -c1-90 | tr '\n' '|')"
[ "$steps" = "compose build models|compose run --rm -e HF_HUB_OFFLINE=0 models python pull.py $M|compose up -d models|compose up -d --force-recreate app|" ] \
  && ok "in order: build, pull with the network on, start models, recreate the app" || bad "steps were: $steps"
cp "$N/.env" "$d/before"; : > "$d/docker.log"
out="$(pm pull $M --yes)"; rc=$?
[ $rc -eq 0 ] && cmp -s "$N/.env" "$d/before" && ok "a second pull of the same name changes nothing in .env" || bad "second pull changed .env (exit $rc): $(diff "$d/before" "$N/.env")"

# ---------------------------------------------------------------- PACKS_ENABLED unset stays unset
env0 APP_PORT=1
out="$(pm pull amazon/chronos-bolt-tiny --yes)"
grep -qx "PREDICT_MODEL=amazon/chronos-bolt-tiny" "$N/.env" && ! grep -q "PACKS_ENABLED" "$N/.env" \
  && ok "with PACKS_ENABLED unset (every pack), it stays unset" || bad "PACKS_ENABLED was written: $(cat "$N/.env")"
env0 APP_PORT=1 COMPOSE_PROFILES=mqtt
pm pull $M --yes >/dev/null; grep -qx "COMPOSE_PROFILES=mqtt,models" "$N/.env" && ok "the profile is added to the ones already on" || bad "profiles: $(cat "$N/.env")"

# ---------------------------------------------------------------- failures leave .env as it was
for f in pull-fails build-fails; do
  env0 APP_PORT=1 PACKS_ENABLED=heat COMPOSE_PROFILES=mqtt; cp "$N/.env" "$d/before"; touch "$d/$f"
  out="$(pm pull $M --yes)"; rc=$?
  [ $rc -ne 0 ] && cmp -s "$N/.env" "$d/before" && ! grep -q "up -d" "$d/docker.log" \
    && ok "$f: exits non-zero, .env untouched (profile and list included), nothing started" || bad "$f (exit $rc): $(diff "$d/before" "$N/.env") / $(cat "$d/docker.log")"
done

# ---------------------------------------------------------------- no terminal and no --yes: it will not guess
env0 APP_PORT=1; cp "$N/.env" "$d/before"
out="$(pm pull $M < /dev/null)"; rc=$?
if ( : </dev/tty ) 2>/dev/null; then ok "(a terminal is present here; the no-terminal check is skipped)"
else [ $rc -ne 0 ] && cmp -s "$N/.env" "$d/before" && [ ! -s "$d/docker.log" ] && grep -q -- "--yes" <<< "$out" \
  && ok "without a terminal and without --yes it asks for --yes and does nothing" || bad "no-tty pull (exit $rc): $out"; fi

# ---------------------------------------------------------------- rm
env0 APP_PORT=1 COMPOSE_PROFILES=models PREDICT_MODEL=$M
out="$(pm rm $M)"; rc=$?
grep -qx "PREDICT_MODEL=" "$N/.env" && grep -q "pull.py --remove $M" "$d/docker.log" && grep -q "compose stop models" "$d/docker.log" && [ $rc -eq 0 ] \
  && ok "rm removes the weights through the image, blanks PREDICT_MODEL and stops the container" || bad "rm (exit $rc): $out / $(cat "$N/.env") / $(cat "$d/docker.log")"
env0 APP_PORT=1 COMPOSE_PROFILES=models PREDICT_MODEL=$M
pm rm amazon/chronos-bolt-tiny >/dev/null
grep -qx "PREDICT_MODEL=$M" "$N/.env" && ! grep -q "compose stop" "$d/docker.log" && ok "rm of a model that is not the one running leaves PREDICT_MODEL and the container" || bad "rm of the other one changed the node: $(cat "$N/.env")"
out="$(pm rm nosuch/model)"; [ $? -ne 0 ] && ok "rm of an unknown name is refused" || bad "rm unknown: $out"

# ---------------------------------------------------------------- the listing
env0 APP_PORT=1
out="$(pm)"
grep -q "amazon/chronos-2 .*456 MB .*Apache-2.0" <<< "$out" && grep -q "amazon/chronos-bolt-tiny .*33 MB" <<< "$out" && grep -q "container is off" <<< "$out" && [ ! -s "$d/docker.log" ] \
  && ok "profile off: it lists the catalogue, says the container is off, and asks docker nothing" || bad "listing, profile off: $out"
env0 APP_PORT=1 COMPOSE_PROFILES=models PREDICT_MODEL=$M; touch "$d/have"
out="$(pm)"
grep -q "amazon/chronos-2 .*on this machine.*<- runs" <<< "$out" && ! grep -q "chronos-bolt-tiny.*runs" <<< "$out" \
  && ok "profile on: says which weights are here and which one runs" || bad "listing, profile on: $out"
rm -f "$d/have"; out="$(pm)"; grep -q "chronos-2 .*not on this machine" <<< "$out" && ok "and when they are not" || bad "not-on-machine: $out"

# ---------------------------------------------------------------- doctor, update.sh, help
grep -q "planetai models pull" <<< "$(PATH="$d/bin:$PATH" PLANETAI_HOME="$PWD" bash bin/planetai help 2>&1)" && ok "help names the models commands" || bad "help lacks models"
us="$(cat update.sh)"
[ "$(grep -c 'compose build models' update.sh)" -eq 1 ] && grep -B1 'compose build models' update.sh | grep -q '\*,models,\*' \
  && ok "update.sh builds models in one place, inside a case on the models profile" || bad "update.sh does not build models only under its profile"
awk '/\*,models,\*\)/{f=1} f&&/;;? *esac|^esac/{f=0} !f&&/models/' update.sh | grep -v '^ *#' | grep -q . \
  && bad "update.sh names models outside its profile case" || ok "outside that case no line of update.sh names the service"

[ $fails -eq 0 ] && { echo "  all ok"; exit 0; } || { echo "  $fails failed"; exit 1; }
