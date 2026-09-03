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

say "lint + tests"
make lint >/dev/null && make test >/dev/null || die "checks failed"

say "tagging v${V}"
git tag -a "v${V}" -m "v${V}"
git push origin main --tags

say "building tarball (no .git, no .env)"
tools/package.sh "$V" ~/Downloads

say "released v${V}. Nodes update with:  ./update.sh"
