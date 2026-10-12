#!/usr/bin/env bash
# `planetai hello` (docs/SPEC_hello.md §5): it shows what goes public, sends nothing on a no, and on a yes opens one
# pull request that adds this node to registry.json, or replaces it, keeping its history. curl and gh are stubs; git
# is real, pushing to a bare repo standing in for the fork.
set -uo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"; fails=0
ok(){ echo "  ok   $1"; }; bad(){ echo "  FAIL $1"; fails=$((fails+1)); }

D="$(mktemp -d)"; mkdir -p "$D/node/bin" "$D/stub"
printf 'NODE_NAME=mahon1\nNODE_CITY=Mahon\nAPP_PORT=8080\n' > "$D/node/.env"
cp "$REPO/bin/planetai" "$D/node/bin/planetai"
cat > "$D/stub/curl" <<S
#!/bin/sh
case "\$*" in
  */nodes*) [ -e "$D/listed" ] && cat "$D/listed" || echo '{"nodes": []}';;
  *) echo '{"node": "mahon1", "position": "cell", "lat": 39.889, "lon": 4.265, "cell": {"id": "8839a1b2c3fffff", "res": 8}}';;
esac
S
# gh: logged in; a fork is a clone of the registry with a bare repo as its origin; the PR is recorded, not sent
cat > "$D/stub/gh" <<S
#!/bin/sh
case "\$1 \$2" in
  "auth status") exit 0;;
  "repo fork") git init -q --bare "$D/fork.git" && git clone -q "$D/fork.git" planetai-node 2>/dev/null \\
      && cp "$REPO/registry.json" planetai-node/ && cd planetai-node && git add . && git -c user.name=t -c user.email=t@t commit -qm base && git push -q origin HEAD:main;;
  "api user") echo someone;;
  "pr create") echo "\$@" > "$D/pr";;
esac
S
chmod +x "$D/stub/curl" "$D/stub/gh"
run() { PATH="$D/stub:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" PLANETAI_HOME="$D/node" GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t \
        GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t python3 "$REPO/tests/pty_run.py" "$@" -- bash "$D/node/bin/planetai" hello 2>&1; }

echo "hello: what goes public is shown first, and a yes opens one pull request"

out="$(run "Mahon, Menorca, ES" "Lucas" "" n)"
[[ "$out" == *"8839a1b2c3fffff"* && "$out" == *"39.889"* ]] && ok "the cell and its centre are shown before anything is sent" || bad "the entry was not shown: $out"
[[ ! -e "$D/pr" && ! -d "$D/fork.git" ]] && ok "a no sends nothing" || bad "a no forked or opened a pull request"

out="$(run "Mahon, Menorca, ES" "Lucas" "" y)"
[[ -e "$D/pr" ]] && grep -q -- "--repo fabcity/planetai-node" "$D/pr" && ok "a yes opens the pull request on fabcity/planetai-node" || bad "no pull request: $out"
reg="$(git --git-dir="$D/fork.git" show "$(git --git-dir="$D/fork.git" for-each-ref --format='%(refname)' refs/heads/hello-mahon1-*)":registry.json)"
printf '%s' "$reg" | python3 -c '
import json, sys
r = json.load(sys.stdin)["nodes"]
m = [n for n in r if n["name"] == "mahon1"]
assert len(m) == 1 and m[0]["operator"] == "Lucas" and m[0]["place"] == "Mahon, Menorca, ES", m
assert m[0]["lat"] == 39.889 and "contact" not in m[0], m
assert any(n["name"] == "bayu-ungasan" for n in r), "the other nodes stay"
' && ok "the branch adds mahon1 once, with no contact when none was given, and keeps the others" || bad "registry.json on the branch is wrong"

# already listed: the list's words are the defaults, and the same entry again sends nothing (12 Oct 2026: node #1's
# hello offered "bali" and an empty operator while the list said "Ungasan, Badung, Bali, ID" and who runs it)
rm -rf "$D/pr" "$D/fork.git"
echo '{"nodes": [{"name": "mahon1", "place": "Mahon, Menorca, ES", "operator": "Lucas", "cell": "8839a1b2c3fffff", "since": "2026-09"}]}' > "$D/listed"
out="$(run "" "" "")"
[[ "$out" == *"already listed, since 2026-09"* && "$out" == *"[Mahon, Menorca, ES]"* && "$out" == *"[Lucas]"* ]] \
  && ok "a listed node is told so, and its listed place and operator are the defaults" || bad "the listing was not offered: $out"
[[ "$out" == *"Nothing to send"* && ! -e "$D/pr" && ! -d "$D/fork.git" ]] && ok "the same entry again sends nothing" || bad "an unchanged listing was sent again: $out"

[[ "$fails" == 0 ]] || { rm -rf "$D"; exit 1; }
rm -rf "$D"
