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

# --- an update is signed, and a node checks who signed it ----------------------------------------
# The checksum above is served from the same origin as the tarball, so whoever can write one writes the
# other and the two agree: it catches a download that rotted in transit and nothing else. Anybody with
# write access to node0/get reaches every node on its next `planetai update`. The signature is the half
# that names the builder, with a key that is not on the web server.
#
# The signer line lives in four places and must be one line: tools/allowed_signers, and a heredoc in each
# of the two stubs, which run before there is a tarball to read a file out of. A stub that drifted from
# the file would refuse every real release, or accept one nobody signed.
signer_line() { grep '^release@planetai\.fab\.city ' "$1" | head -1; }
want_signer="$(signer_line tools/allowed_signers)"
[[ -n "$want_signer" ]] && ok "tools/allowed_signers publishes one signer line" \
  || no "tools/allowed_signers has no release@planetai.fab.city line"
for f in install update.sh; do
  is "$f embeds the same signer line, byte for byte" "$(signer_line "$f")" "$want_signer"
done
has "$(cat install)"    'ssh-keygen -Y verify' "install checks the signature, not only the checksum"
has "$(cat update.sh)"  'ssh-keygen -Y verify' "update.sh checks the signature, not only the checksum"
# The old path has to keep working through this release: a v0.57 node knows nothing about signatures and
# updates by checksum alone, so the first signed release still publishes SHA256.
has "$(cat tools/bundle.sh)" 'SHA256' "bundle.sh still publishes SHA256, so nodes older than this release still update"

# --- and it refuses one it cannot attribute, before it touches the node ---------------------------
if command -v ssh-keygen >/dev/null; then
  sk="$(mktemp -d)"; mkdir -p "$sk/get"
  ssh-keygen -q -t ed25519 -f "$sk/key" -N '' -C release@planetai.fab.city
  printf 'a tarball\n' > "$sk/get/planetai-node.tar.gz"
  ssh-keygen -Y sign -f "$sk/key" -n planetai-node "$sk/get/planetai-node.tar.gz" >/dev/null 2>&1
  blob="$(ssh-keygen -y -f "$sk/key" | awk '{print $2}')"

  # verify_signature and its heredoc, lifted verbatim out of update.sh: the file itself is under test,
  # not a copy typed in here. `real` keeps the committed signer; `ours` swaps in the throwaway key, which
  # is the only way to exercise the path that SUCCEEDS without the Foundation's private key being here.
  lift() {
    { echo 'set -euo pipefail'
      echo 'say(){ printf ">> %s\n" "$*"; }'
      echo 'die(){ printf "xx %s\n" "$*" >&2; exit 1; }'
      echo "GET=\"file://$sk/get\""
      sed -n "/^read -r -d '' ALLOWED_SIGNERS/,/^SIGNERS\$/p;/^verify_signature() {/,/^}\$/p" update.sh
      echo 'verify_signature "$1"'
    } > "$sk/$1.sh"
    [[ "$1" == ours ]] && { sed "s|PLACEHOLDER-NO-RELEASE-KEY-HAS-BEEN-ISSUED-YET|$blob|" "$sk/ours.sh" > "$sk/o" && mv "$sk/o" "$sk/ours.sh"; }
    grep -q verify_signature "$sk/$1.sh"
  }
  lift real && lift ours || no "could not lift verify_signature out of update.sh"

  # the caller owns the directory, so it can look at what was left in it afterwards
  run_on() {   # run_on <which> <dir> <contents> ; echoes the exit code
    printf '%s' "$3" > "$2/n.tar.gz"
    local rc=0; bash "$sk/$1.sh" "$2/n.tar.gz" >/dev/null 2>&1 || rc=$?
    echo "$rc"
  }

  d="$(mktemp -d)"
  is "a tarball signed by the key the node trusts is accepted" "$(run_on ours "$d" 'a tarball
')" "0"
  rm -rf "$d"

  d="$(mktemp -d)"
  rc="$(run_on ours "$d" 'a tarbalL
')"
  [[ "$rc" != 0 ]] && ok "one flipped byte and the node refuses it, before the extract" \
    || no "a modified tarball verified — the signature is not being checked"
  [[ -d "$d" ]] && { no "the refused download was left on disk at $d"; rm -rf "$d"; } \
    || ok "and the refused download is not left behind"

  # No key has been issued yet, so the committed line is a placeholder. A node carrying it must refuse
  # everything rather than accept anything: a placeholder that verified would be worse than no check.
  d="$(mktemp -d)"; rc="$(run_on real "$d" 'a tarball
')"; rm -rf "$d"
  [[ "$rc" != 0 ]] && ok "the committed signer refuses a tarball it did not sign" \
    || no "update.sh accepted a tarball the committed signer did not sign"

  mv "$sk/get/planetai-node.tar.gz.sig" "$sk/away"
  d="$(mktemp -d)"; rc="$(run_on ours "$d" 'a tarball
')"; rm -rf "$d"
  [[ "$rc" != 0 ]] && ok "no signature published at the origin is a refusal, not a pass" \
    || no "update.sh installed a tarball whose signature it could not fetch"
  mv "$sk/away" "$sk/get/planetai-node.tar.gz.sig"

  rc=0; PLANETAI_UNSIGNED=1 bash "$sk/ours.sh" "$sk/get/planetai-node.tar.gz" >/dev/null 2>&1 || rc=$?
  is "PLANETAI_UNSIGNED=1 lets a dev tarball through" "$rc" "0"
  hasnt "$(cat install)" 'PLANETAI_UNSIGNED:-1' "and it is never the default in install"
  hasnt "$(cat update.sh)" 'PLANETAI_UNSIGNED:-1' "and it is never the default in update.sh"
  rm -rf "$sk"
else
  printf '  --   signature checks not run (no ssh-keygen on this machine)\n'
fi

# --- what a release publishes ---------------------------------------------------------------------
GETDIR="$SITE_REPO/node0/get"
if [[ -f "$GETDIR/planetai-node.tar.gz.sig" ]]; then
  for f in planetai-node.tar.gz SHA256 planetai-node.tar.gz.sig; do
    [[ -s "$GETDIR/$f" ]] && ok "the site serves $f" || no "$GETDIR/$f is missing or empty"
  done
  if ssh-keygen -Y verify -f tools/allowed_signers -I release@planetai.fab.city -n planetai-node \
       -s "$GETDIR/planetai-node.tar.gz.sig" < "$GETDIR/planetai-node.tar.gz" >/dev/null 2>&1; then
    ok "and its signature verifies against tools/allowed_signers"
  else
    no "the published tarball does NOT verify against tools/allowed_signers — no node will install it"
  fi
else
  printf '  --   no signed build in %s yet; this starts asserting at the first signed release\n' "$GETDIR"
fi

printf '\n'
[[ $fail -eq 0 ]] && { echo "release consistency tests pass"; exit 0; }
echo "$fail failed"; exit 1
