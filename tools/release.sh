#!/usr/bin/env bash
# Cut a release from the development machine. Nodes never run this.
#   tools/release.sh 0.4.5
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
V="${1:?usage: tools/release.sh <version>   e.g. 0.4.5}"

say(){ printf '\033[1;32m>>\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

[[ -n "$(git status --porcelain)" ]] && die "working tree is dirty — commit first, then release"
grep -q "^## v${V}" CHANGELOG.md || die "CHANGELOG.md has no '## v${V}' section. Say what changed and why."
git rev-parse "v${V}" >/dev/null 2>&1 && die "tag v${V} already exists"

# The signing key, checked BEFORE the tag is cut. A checksum served from the same origin as the tarball
# proves only that the bytes did not rot on the way: whoever can write to node0/get writes both files,
# and every node takes it on the next `planetai update`. The signature is the half that names the sender.
#
# ship.sh owns the check and does the signing; this asks it the question early, because the next two
# steps tag and push. Discovering a missing key after `git push --tags` leaves a public tag naming a
# release nobody can publish.
tools/ship.sh --check-key || exit 1

say "lint + tests"
make lint >/dev/null && make test >/dev/null || die "checks failed"

say "tagging v${V}"
git tag -a "v${V}" -m "v${V}"
git push origin main --tags

say "building the tarball, committing it in the site repo, deploying"
tools/ship.sh

# What a node downloads, all three of it. ship.sh built and signed them; this is the receipt.
GET="${PLANETAI_SITE_REPO:-../planetai}/node0/get"
for f in planetai-node.tar.gz SHA256 planetai-node.tar.gz.sig; do
  [[ "$f" == *.sig && "${PLANETAI_UNSIGNED:-0}" == 1 ]] && continue
  [[ -s "$GET/$f" ]] || die "$GET/$f is missing or empty after the build. Nothing was released."
done

say "released v${V}, signed. Nodes update with:  ./update.sh"
