#!/usr/bin/env bash
# A reason line that names the wrong subsystem costs more than no reason line.
#
# Lucas's step 4 said "check the network". The log said `failed commit on ref "layer-sha256:..."` —
# the download had arrived and could not be written, on a laptop whose filesystem had gone read-only an
# hour earlier from drive errors. He was sent to look at his router.
#
# Drives the real diagnose() out of install.sh against real log lines.
set -uo pipefail
cd "$(dirname "$0")/.."
fails=0

fn="$(sed -n '/^diagnose() {/,/^}/p' install.sh)"
[[ -n "$fn" ]] || { echo "  FAIL could not lift diagnose() from install.sh"; exit 1; }

ok()  { echo "  ok   $1"; }
bad() { echo "  FAIL $1"; fails=$((fails+1)); }
check() { # check "<log line>" "<expected words>" "<must NOT contain>"
  local line="$1" want="$2" nope="${3:-}" out
  out="$(LOG_FILE=/tmp/dx.$$ bash -c "printf '%s\n' \"\$1\" > /tmp/dx.$$; $fn; diagnose" _ "$line")"
  rm -f /tmp/dx.$$
  if ! grep -qi -- "$want" <<<"$out"; then
    echo "  FAIL '$line' → did not say '$want'"; echo "       got: ${out:0:90}"; fails=$((fails+1)); return
  fi
  if [[ -n "$nope" ]] && grep -qi -- "$nope" <<<"$out"; then
    echo "  FAIL '$line' → wrongly mentions '$nope'"; fails=$((fails+1)); return
  fi
  echo "  ok   '$line' → ${out%%$'\n'*}"
}

echo "diagnose: the log decides, not the guess"
check 'failed commit on ref "layer-sha256:4a426440ea59e29bee"' "this is the disk, not the network" "check the network"
check 'write /var/lib/docker/tmp/x: no space left on device'    "the disk filled up"
check 'error: input/output error'                               "this is the disk"
check 'open /etc/foo: read-only file system'                    "this is the disk"
check 'dial tcp: lookup registry-1.docker.io: no such host'     "registry could not be reached" "disk"
check 'net/http: TLS handshake timeout'                         "registry could not be reached" "disk"
check 'denied: requested access to the resource is denied'      "refused the image name"
check 'manifest unknown'                                        "refused the image name"

echo "diagnose: it says nothing when it knows nothing"
out="$(LOG_FILE=/tmp/dq.$$ bash -c "printf 'all fine\n' > /tmp/dq.$$; $fn; diagnose")"; rm -f /tmp/dq.$$
[[ -z "$out" ]] && echo "  ok   an unrecognised log yields no reason, so the caller's own words stand" \
  || { echo "  FAIL invented a reason: $out"; fails=$((fails+1)); }

echo "diagnose: the pull step no longer blames the network on a guess"
grep -q 'check the network, then run the resume command' install.sh \
  && { echo "  FAIL the old network guess is still there"; fails=$((fails+1)); } \
  || echo "  ok   the pull step's own wording no longer claims to know"

echo "die: it says the message once, keeping its shape"
# Build a tiny script that has diagnose() and die() lifted out of the real file, and run it. Nesting
# heredocs inside command substitutions to do this is how the first version of this test broke.
d="$(mktemp -d)"
{
  echo 'set -uo pipefail'
  echo "LOG_FILE=$d/log; : > \"\$LOG_FILE\""
  echo 'STEP_NAME="a step"; STEP_T0=$SECONDS; RUN_T0=$SECONDS; STEP_N=1; STEP_TOTAL=7'
  sed -n '/^diagnose() {/,/^}/p' install.sh
  sed -n '/^die()  {/,/^}/p' install.sh
  printf 'die "first line here\n   second line\n   third line"\n'
} > "$d/run.sh"
out="$(bash "$d/run.sh" 2>&1)"; rm -rf "$d"

n="$(grep -c "second line" <<<"$out")"
if [[ "$n" == 1 ]]; then ok "a continuation line appears once, not twice"
else echo "  FAIL 'second line' appears $n times"; fails=$((fails+1)); fi
grep -qE '^  reason  first line here$' <<<"$out" && ok "the first line sits on the reason label" || bad "the reason label does not carry the first line"
grep -qE '^          second line$'     <<<"$out" && ok "and the rest is indented under it"      || bad "continuation lines are not aligned"
grep -qE '^  log '                     <<<"$out" && ok "log is on its own line"                 || bad "log ran into the previous line"
[[ "$(grep -c 'resume  planetai setup' <<<"$out")" == 1 ]] && ok "resume is said once" || bad "resume repeated"

[[ $fails -eq 0 ]] && { echo "diagnose tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
