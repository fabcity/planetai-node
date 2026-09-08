#!/usr/bin/env bash
# Put what is on main in front of a tester. Three steps that were three separate things to remember:
#   tools/ship.sh              rebuild the tarball, commit it in the site repo, deploy the site
#   tools/ship.sh --no-deploy  everything except the deploy
#   tools/ship.sh --check      say only whether the site is behind main, and exit 1 if it is
#
# A merge is not a release. `/install` and `/preflight` are stubs that fetch the current file from this
# repository on every run, so those two are never stale — but `install.sh` and `bin/planetai` reach a
# tester inside the tarball, and the tarball only changes when somebody rebuilds it. That gap shipped
# silent sudos to Linux testers for an hour on 8 September 2026, twice, because it was a step to recall.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

say(){ printf '\033[1;32m>>\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

SITE="${PLANETAI_SITE_REPO:-../planetai}"
DEPLOY=1; CHECK=0
for a in "$@"; do case "$a" in --no-deploy) DEPLOY=0;; --check) CHECK=1;; *) die "unknown flag $a";; esac; done

HERE="$(git describe --tags --always)"
[[ -d "$SITE/.git" ]] || die "no site repo at $SITE. Clone fabcity/planetai beside this one, or set PLANETAI_SITE_REPO."

if [[ $CHECK -eq 1 ]]; then
  LIVE="$(curl -fsSL "https://planetai.fab.city/node0/get/VERSION?cb=$RANDOM" 2>/dev/null || echo unreachable)"
  printf '  main is at          %s\n  the site serves     %s\n' "$HERE" "$LIVE"
  [[ "$HERE" == "$LIVE" ]] && { say "a tester gets what is on main"; exit 0; }
  printf '\033[1;33m!!\033[0m the site is behind. A tester downloading now gets the older node: tools/ship.sh\n'
  exit 1
fi

[[ -z "$(git status --porcelain)" ]] || die "this repository is dirty. Commit first — a tester should never get an uncommitted file."
[[ "$(git rev-parse --abbrev-ref HEAD)" == main ]] || die "ship from main, not $(git rev-parse --abbrev-ref HEAD)."
git fetch -q origin && [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || die "main and origin/main differ. Pull or push first, so the tarball matches what is public."

say "building the tarball at ${HERE}"
tools/bundle.sh "$SITE/node0/get"

# The site repo may hold work of its own. Only ever touch node0/get, and refuse if anything else is dirty.
OTHER="$(git -C "$SITE" status --porcelain -- . ':(exclude)node0/get' | head -5)"
[[ -z "$OTHER" ]] || { printf '%s\n' "$OTHER" >&2; die "the site repo has other uncommitted changes. Deal with those first; I will not sweep them into a release."; }
if [[ -n "$(git -C "$SITE" status --porcelain -- node0/get)" ]]; then
  say "committing the tarball into the site repo"
  git -C "$SITE" add node0/get
  git -C "$SITE" commit -q -m "node0/get: tester tarball at ${HERE}"
  git -C "$SITE" push -q origin HEAD
else
  say "the site repo already has this tarball"
fi

if [[ $DEPLOY -eq 1 ]]; then
  say "deploying the site — this publishes planetai.fab.city (npx wrangler@4 deploy)"
  make -C "$SITE" deploy
  say "live: $(curl -fsSL "https://planetai.fab.city/node0/get/VERSION?cb=$RANDOM" 2>/dev/null || echo '(check by hand)')"
else
  say "not deployed. To publish:  make -C $SITE deploy"
fi
