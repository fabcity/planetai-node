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

live_version() { curl -fsSL "https://planetai.fab.city/node0/get/VERSION?cb=$RANDOM.$$" 2>/dev/null || echo unreachable; }

if [[ $CHECK -eq 1 ]]; then
  # VERSION is served with max-age=300, so for a few minutes after a deploy some Cloudflare edges
  # still answer from the old entry. Read once; only if that disagrees, read again a few times before
  # calling the site behind — this check said "behind" seconds after a deploy that had worked, which
  # is the one thing a release check must never get wrong.
  LIVE="$(live_version)"
  if [[ "$HERE" != "$LIVE" ]]; then
    for _ in 1 2 3 4; do
      sleep 10
      LIVE="$(live_version)"
      [[ "$HERE" == "$LIVE" ]] && break
    done
  fi
  printf '  main is at          %s\n  the site serves     %s\n' "$HERE" "$LIVE"
  [[ "$HERE" == "$LIVE" ]] && { say "a tester gets what is on main"; exit 0; }
  printf '\033[1;33m!!\033[0m the site is behind. A tester downloading now gets the older node: tools/ship.sh\n'
  exit 1
fi

[[ -z "$(git status --porcelain)" ]] || die "this repository is dirty. Commit first — a tester should never get an uncommitted file."
[[ "$(git rev-parse --abbrev-ref HEAD)" == main ]] || die "ship from main, not $(git rev-parse --abbrev-ref HEAD)."
# "Behind" is not "diverged". After a PR is merged on GitHub the local checkout is simply behind, a
# fast-forward away, and refusing there sent somebody to run `git pull` and come back four separate
# times today. Fast-forward it and carry on; refuse only when the two have actually diverged, which is
# the case where guessing would be wrong.
git fetch -q origin
AHEAD="$(git rev-list --count origin/main..HEAD)"
BEHIND="$(git rev-list --count HEAD..origin/main)"
if [[ "$AHEAD" != 0 && "$BEHIND" != 0 ]]; then
  die "main and origin/main have diverged — $AHEAD here, $BEHIND there. Sort that out first; a release
   should never be built from a tree nobody else has."
elif [[ "$AHEAD" != 0 ]]; then
  die "main is $AHEAD commit(s) ahead of origin. Push first, so the tarball matches what is public:
     git push"
elif [[ "$BEHIND" != 0 ]]; then
  say "main is $BEHIND commit(s) behind origin — fast-forwarding, then building from that"
  # NOT backticks: inside a double-quoted string they run the command and paste its output, so this
  # message used to execute `git pull` a second time while building itself and then print a hole where
  # the command name should be.
  git pull -q --ff-only || die "the fast-forward failed. Run this and read what it says:
     git pull"
fi

# A release should be a commit whose tests passed. This was added because I shipped v0.41.2-69 while
# its install-smoke run was still queued, and it went red — a workflow edit of mine had split a grep
# across two lines, which is valid bash and so no local check could see it. The tarball was fine that
# time; the point is that nothing knew it was fine.
#
# Missing or unauthenticated `gh` is not a reason to block a release: warn and carry on. A red run is.
if command -v gh >/dev/null 2>&1; then
  CI="$(gh run list --commit "$(git rev-parse HEAD)" --limit 20 \
        --json conclusion,status,workflowName,url 2>/dev/null || true)"
  if [[ -z "$CI" || "$CI" == "[]" ]]; then
    say "no CI run for this commit yet — building anyway, but nothing has tested it"
  else
    BAD="$(printf '%s' "$CI" | python3 -c 'import json,sys
r=json.load(sys.stdin)
bad=[x for x in r if x.get("conclusion") in ("failure","timed_out","cancelled")]
print("\n".join("   %s: %s  %s" % (x["workflowName"], x["conclusion"], x["url"]) for x in bad))' 2>/dev/null || true)"
    PENDING="$(printf '%s' "$CI" | python3 -c 'import json,sys
r=json.load(sys.stdin)
print(len([x for x in r if x.get("status") not in ("completed",)]))' 2>/dev/null || echo 0)"
    if [[ -n "$BAD" ]]; then
      printf '%s\n' "$BAD" >&2
      die "CI is red on this commit. A tester should not be handed a build nothing vouched for.
   Fix it, or ship deliberately with:
     SHIP_WITHOUT_CI=1 make ship"
    elif [[ "${PENDING:-0}" != 0 ]]; then
      [[ "${SHIP_WITHOUT_CI:-0}" == 1 ]] || die "CI is still running on this commit ($PENDING run(s)). Wait for it, then ship — or:
     SHIP_WITHOUT_CI=1 make ship"
      say "CI still running, shipping anyway because SHIP_WITHOUT_CI=1"
    else
      say "CI is green on this commit"
    fi
  fi
else
  say "no gh here, so CI was not checked"
fi

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
