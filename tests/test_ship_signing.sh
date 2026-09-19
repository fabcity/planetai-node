#!/usr/bin/env bash
# ship.sh has to sign with a PASSPHRASE-PROTECTED key, because that is the only kind the release key
# is allowed to be. It could not, and nothing here noticed until the first real release was cut.
#
# `ssh-keygen -y -f <private key>` reads the private half and prompts; it does not consult ssh-agent.
# So `signing_key()` died on every passphrase-protected key — and its message said to run `ssh-add`,
# which cannot help a command that never asks the agent anything. The fix reads the `.pub` sitting
# beside the key, and signs with `-f <public key>` so the agent supplies the private half.
#
# Both halves are driven here against a throwaway ENCRYPTED key, because an unencrypted one passes
# either way and would have tested nothing.
set -uo pipefail
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_OBJECT_DIRECTORY GIT_COMMON_DIR
cd "$(dirname "$0")/.."
ROOT="$PWD"; fails=0
ok(){ echo "  ok   $1"; }; bad(){ echo "  FAIL $1"; fails=$((fails+1)); }

command -v ssh-keygen >/dev/null || { echo "  --   no ssh-keygen; ship signing not checked"; exit 0; }

# The key lives OUTSIDE the directory the driver runs in: signing_key() refuses a key inside the
# repository, which is the right refusal and which this test tripped over first time.
T="$(mktemp -d)"; trap 'ssh-agent -k >/dev/null 2>&1; rm -rf "$T"' EXIT
mkdir -p "$T/repo" "$T/secrets"
K="$T/secrets/key"
ssh-keygen -q -t ed25519 -f "$K" -N 'a passphrase' -C fabcity || { echo "  FAIL could not make a test key"; exit 1; }
cd "$T/repo"
# signing_key() reads tools/allowed_signers relative to its CWD, so the throwaway repo needs that
# shape. First cut wrote it at the top level: the function died on a missing file, and the message
# happened to contain "not the one", so the stranger-key check PASSED for the wrong reason.
mkdir -p tools
printf 'fabcity %s fabcity\n' "$(awk '{print $1" "$2}' "$K.pub")" > tools/allowed_signers

# The two functions, lifted out of the real file rather than retyped here.
lift() { sed -n '/^signing_key() {/,/^}$/p;/^sign_tarball() {/,/^}$/p' "$ROOT/tools/ship.sh"; }
[ -n "$(lift)" ] || { echo "  FAIL could not lift signing_key/sign_tarball out of tools/ship.sh"; exit 1; }
cat > drive.sh <<'DRV'
set -uo pipefail
say(){ printf '>> %s\n' "$*"; }
die(){ printf 'xx %s\n' "$*" >&2; exit 1; }
DRV
lift >> drive.sh

# --- 1. the exact regression: no agent at all, and signing_key() must still resolve the key ---------
cp drive.sh d1.sh; echo 'signing_key >/dev/null && say resolved' >> d1.sh
out="$(cd "$T/repo" && PLANETAI_SIGNING_KEY="$K" SSH_AUTH_SOCK= bash d1.sh </dev/null 2>&1)"
grep -q resolved <<<"$out" \
  && ok "signing_key() reads the public half, so a passphrase-protected key needs no prompt" \
  || bad "signing_key() could not resolve an encrypted key with no agent: $out"

# --- 2. and it still refuses a key that is not the one allowed_signers publishes --------------------
ssh-keygen -q -t ed25519 -f "$T/secrets/other" -N '' -C fabcity
out="$(cd "$T/repo" && PLANETAI_SIGNING_KEY="$T/secrets/other" SSH_AUTH_SOCK= bash d1.sh </dev/null 2>&1)"
grep -q 'nodes trust   ssh-ed25519' <<<"$out" && grep -q 'not the one' <<<"$out" \
  && ok "and refuses a key the committed signer line does not publish" \
  || bad "a stranger's key was accepted: $out"

# --- 3. sign_tarball, through an agent holding the encrypted key ------------------------------------
printf '#!/bin/sh\necho "a passphrase"\n' > "$T/ask.sh"; chmod +x "$T/ask.sh"
eval "$(ssh-agent -s)" >/dev/null 2>&1
if DISPLAY=:0 SSH_ASKPASS="$T/ask.sh" SSH_ASKPASS_REQUIRE=force ssh-add "$K" </dev/null >/dev/null 2>&1; then
  cp drive.sh d3.sh; echo 'sign_tarball "$1"' >> d3.sh
  printf 'a pretend tarball\n' > fake.tar.gz
  out="$(cd "$T/repo" && PLANETAI_SIGNING_KEY="$K" bash d3.sh fake.tar.gz </dev/null 2>&1)"
  if [ -s fake.tar.gz.sig ]; then
    ok "sign_tarball signs through the agent, with no passphrase prompt"
    ssh-keygen -Y verify -f tools/allowed_signers -I fabcity -n planetai-node -s fake.tar.gz.sig < fake.tar.gz >/dev/null 2>&1 \
      && ok "and a node's own check accepts what it wrote" \
      || bad "the signature does not verify against the signer line"
    printf 'tampered\n' > bad.tar.gz
    ssh-keygen -Y verify -f tools/allowed_signers -I fabcity -n planetai-node -s fake.tar.gz.sig < bad.tar.gz >/dev/null 2>&1 \
      && bad "a tampered tarball verified" \
      || ok "and refuses the same signature over different bytes"
  else
    bad "sign_tarball wrote no signature with the key in the agent: $out"
  fi
else
  echo "  --   ssh-add could not be scripted here; the agent path not checked"
fi

echo
[ "$fails" -eq 0 ] && echo "ship signing tests pass" || echo "ship signing: $fails failed"
exit $([ "$fails" -eq 0 ] && echo 0 || echo 1)
