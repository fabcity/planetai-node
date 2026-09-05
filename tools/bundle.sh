#!/usr/bin/env bash
# Build the tarball the website serves, so beta testers can install without access to the repository.
#   tools/bundle.sh [outdir]        default: ../planetai/node0/get
# Excludes git history, secrets, local state and the developer's own tooling.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
OUT="${1:-../planetai/node0/get}"
VER="$(git describe --tags --always 2>/dev/null || echo dev)"
mkdir -p "$OUT"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/planetai-node"
# everything git tracks, minus what a tester must not receive or does not need
git ls-files -z | grep -zvE '^(\.github/|tools/(package|release|bundle)\.sh|tools/check_|tests/)' \
  | xargs -0 -I{} cp --parents {} "$TMP/planetai-node/" 2>/dev/null \
  || git ls-files | grep -vE '^(\.github/|tools/(package|release|bundle)\.sh|tools/check_|tests/)' \
     | while read -r f; do mkdir -p "$TMP/planetai-node/$(dirname "$f")"; cp "$f" "$TMP/planetai-node/$f"; done
echo "$VER" > "$TMP/planetai-node/VERSION"
mkdir -p "$TMP/planetai-node/out" && cp out/.gitkeep "$TMP/planetai-node/out/" 2>/dev/null || true
tar czf "$OUT/planetai-node.tar.gz" -C "$TMP" planetai-node
tar tzf "$OUT/planetai-node.tar.gz" | grep -qE '(^|/)\.(git|env)(/|$)' && { echo "REFUSING: bundle contains .git or .env"; rm -f "$OUT/planetai-node.tar.gz"; exit 1; }
printf '%s\n' "$VER" > "$OUT/VERSION"
shasum -a 256 "$OUT/planetai-node.tar.gz" | awk '{print $1}' > "$OUT/SHA256"
echo "$OUT/planetai-node.tar.gz  ($VER, $(du -h "$OUT/planetai-node.tar.gz" | cut -f1), $(tar tzf "$OUT/planetai-node.tar.gz" | wc -l | tr -d ' ') files)"
