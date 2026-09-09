#!/usr/bin/env bash
# ship.sh guards a release, so what it refuses matters. It refused four times in one afternoon for a
# state that needed no decision: main merely BEHIND origin after a pull request was merged on GitHub —
# a fast-forward away, with nothing to choose between. That is not the same as diverged.
#
# Drives the real precondition block from tools/ship.sh against throwaway repositories.
set -uo pipefail
cd "$(dirname "$0")/.."
SHIP="$PWD/tools/ship.sh"; fails=0
ok(){ echo "  ok   $1"; }; bad(){ echo "  FAIL $1"; fails=$((fails+1)); }

block="$(sed -n '/^git fetch -q origin$/,/^fi$/p' "$SHIP")"
[[ -n "$block" ]] || { echo "  FAIL could not lift the sync check from ship.sh"; exit 1; }

# a bare "origin" and a clone of it, so ahead/behind/diverged are real rather than mocked
setup() {
  D="$(mktemp -d)"
  git init -q --bare -b main "$D/origin.git"
  git clone -q "$D/origin.git" "$D/work" 2>/dev/null
  cd "$D/work"
  git config user.email t@t; git config user.name t
  git checkout -q -B main
  echo one > f; git add f; git commit -q -m one
  git push -q -u origin main 2>/dev/null
}
runblock() {
  { echo 'set -uo pipefail'
    echo 'say(){ printf ">> %s\n" "$*"; }'
    echo 'die(){ printf "xx %s\n" "$*"; exit 1; }'
    printf '%s\n' "$block"
    echo 'echo RESULT_OK'
  } > "$D/b.sh"
  bash "$D/b.sh" 2>&1
}

echo "ship gate: what it lets through and what it stops"

setup                                                   # in sync
out="$(runblock)"; grep -q RESULT_OK <<<"$out" && ok "in sync → proceeds" || bad "in sync was refused: $out"
cd /; rm -rf "$D"

setup                                                   # behind: a merge landed on origin
git clone -q "$D/origin.git" "$D/other" 2>/dev/null && cd "$D/other" && git config user.email t@t && git config user.name t
git checkout -q main 2>/dev/null
echo two > g && git add g && git commit -q -m two && git push -q origin main 2>/dev/null
cd "$D/work" && git fetch -q origin
out="$(runblock)"
grep -q RESULT_OK <<<"$out" && ok "behind → fast-forwards and proceeds" || bad "behind was refused: $out"
grep -q "fast-forwarding" <<<"$out" && ok "and says it did so" || bad "it fast-forwarded silently"
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] && ok "and the tree really moved" || bad "HEAD did not move"
cd /; rm -rf "$D"

setup                                                   # ahead: an unpushed commit
echo three > h && git add h && git commit -q -m three
out="$(runblock)"
grep -q RESULT_OK <<<"$out" && bad "ahead was allowed — the tarball would not match what is public" \
  || ok "ahead → refuses, because the tarball must match what is public"
grep -q "git push" <<<"$out" && ok "and names the command" || bad "no command named"
cd /; rm -rf "$D"

setup                                                   # diverged: both sides moved
git clone -q "$D/origin.git" "$D/other" 2>/dev/null && cd "$D/other" && git config user.email t@t && git config user.name t
git checkout -q main 2>/dev/null
echo far > i && git add i && git commit -q -m far && git push -q origin main 2>/dev/null
cd "$D/work" && echo near > j && git add j && git commit -q -m near && git fetch -q origin
out="$(runblock)"
grep -q RESULT_OK <<<"$out" && bad "a diverged tree was allowed to build a release" \
  || ok "diverged → refuses, which is the case where guessing would be wrong"
grep -q "diverged" <<<"$out" && ok "and says so" || bad "does not say diverged"
cd /; rm -rf "$D"

[[ $fails -eq 0 ]] && { echo "ship gate tests pass"; exit 0; } || { echo "$fails failed"; exit 1; }
