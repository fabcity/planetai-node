#!/usr/bin/env bash
# A tester used to receive two versions at once: the bootstrap and the preflight check came live from
# main, the node came from the last `make ship`. On 2026-09-08 that meant a bootstrap that knew about
# `planetai remove` handing over a node that did not have it. These are the two halves of the fix —
# the stub pins itself to the released commit, and a node that lacks a command says so plainly.
set -uo pipefail
cd "$(dirname "$0")/.."
SITE_REPO="${PLANETAI_SITE_REPO:-../planetai}"
pass=0; fail=0
ok()   { printf '  ok   %s\n' "$1"; pass=$((pass+1)); }
no()   { printf '  XX   %s\n' "$1"; fail=$((fail+1)); }
is()   { [[ "$2" == "$3" ]] && ok "$1" || { no "$1"; printf '         wanted %q\n         got    %q\n' "$3" "$2"; }; }
has()  { grep -qF -- "$2" <<< "$1" && ok "$3" || { no "$3"; printf '         no %q in the output\n' "$2"; }; }
hasnt(){ grep -qF -- "$2" <<< "$1" && { no "$3"; printf '         found %q, which should not be there\n' "$2"; } || ok "$3"; }

echo "release consistency: one commit reaches a tester, and a node admits what it lacks"

# --- the stub pins to what is published, with no network: curl reads file:// happily -------------
if [[ -f "$SITE_REPO/install" ]]; then
  fx="$(mktemp -d)"; mkdir -p "$fx/get"
  printf 'v0.41.2-23-g75da6ab\n' > "$fx/get/VERSION"
  # Run the stub's own resolution — SITE=, released(), REF= lifted verbatim out of the real file —
  # and stop before it fetches anything. Leaving SITE= out of this list made SITE empty, curl fail,
  # and every case land in the main fallback, so the test agreed with itself and read nothing.
  resolves() { PLANETAI_SITE="$1" bash -c '
    eval "$(sed -n "/^SITE=/p;/^released()/,/^}/p;/^REF=/p" "$1")"; printf %s "$REF"' _ "$SITE_REPO/install" 2>/dev/null; }
  is "reads the published version, not main" "$(resolves "file://$fx")" "75da6ab"

  printf 'v0.41.1\n' > "$fx/get/VERSION"
  is "a bare tag is a ref too" "$(resolves "file://$fx")" "v0.41.1"
  is "an unreachable site falls back to main, not to nothing" "$(resolves "file:///nowhere-$$")" "main"
  is "PLANETAI_REF still wins, so an unreleased fix can be tested" \
     "$(PLANETAI_REF=somebranch resolves "file://$fx")" "somebranch"
  rm -rf "$fx"
else
  printf '  --   site stub not checked (no %s; set PLANETAI_SITE_REPO)\n' "$SITE_REPO/install"
fi

# --- and a node that does not have the command says which command and which version --------------
# `remove` exists at HEAD, so ask for something no release will ever have
out="$(./bin/planetai definitely-not-a-command 2>&1)"; rc=0; ./bin/planetai definitely-not-a-command >/dev/null 2>&1 || rc=$?
is   "an unknown command exits non-zero" "$rc" "1"
has  "$out" "definitely-not-a-command" "and names the word that was typed"
has  "$out" "planetai update" "and gives the command that would fetch it"
has  "$out" "this node is" "and says which version this node is"

for a in "" help -h --help; do
  rc=0; ./bin/planetai $a >/dev/null 2>&1 || rc=$?
  is "planetai ${a:-<nothing>} is not an error" "$rc" "0"
done
out="$(./bin/planetai help 2>&1)"
hasnt "$out" "there is no" "and asking for help is not treated as a typo"

# --- an update refuses a download it could not verify (S3) ---------------------------------------
# `update.sh` trusted the tarball whenever the check could not run, and both ways it could not run were
# silent: `shasum` is macOS's name and Debian ships `sha256sum`, and any hiccup fetching the checksum
# skipped it too. The extract was then the LEFT operand of an `&&` list, which `set -e` exempts, so a
# truncated download installed nothing and the run continued to the schema step, the rebuild and the
# doctor, and ended `>> updated. Nothing was lost` with exit 0. `install` fixed the same three paths
# already; these assert the two files cannot drift apart again.
for f in update.sh install; do
  src="$(cat "$f")"
  has "$src" 'sha256sum' "$f knows Debian's name for the tool, not only macOS's"
  hasnt "$src" 'if command -v shasum >/dev/null &&' "$f does not make the checksum conditional on shasum alone"
done
hasnt "$(cat update.sh)" 'tar xzf "$tmp/n.tar.gz" -C "$tmp" &&' "update.sh does not leave the extract as the left operand of &&, where set -e cannot see it fail"
has "$(cat update.sh)" 'so the download cannot be verified' "update.sh says why it refused"

printf '\n'
[[ $fail -eq 0 ]] && { echo "release consistency tests pass"; exit 0; }
echo "$fail failed"; exit 1
