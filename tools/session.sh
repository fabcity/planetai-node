#!/usr/bin/env bash
# The two ends of a working session on this repository.
#
#   tools/session.sh preflight     before touching anything: where main is, what is open, what is red
#   tools/session.sh land          before closing the laptop: nothing exists only here, and it is green
#
# Everything that went wrong in the week of 12–19 September 2026 went wrong at a seam, not inside a
# feature: four PRs unmerged for two weeks, two branches each bumping the suite count in tests/all and
# git merging both without a conflict, CI red on main for a day and nobody told, a sibling checkout
# eight days behind feeding a gate the wrong answer, six releases with no CHANGELOG heading. None of
# that is caught by make lint, because make lint looks at a tree and every one of these is about two
# trees. This looks at two trees.
#
# preflight is read-only and fast. land runs the whole of make lint and make test, because the point of
# it is that a session does not end on a green that was assumed. Both exit non-zero on a stop
# condition and print what to do; a warning prints and continues.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE="${1:-}"
[[ "$MODE" == preflight || "$MODE" == land ]] || { echo "usage: tools/session.sh preflight|land" >&2; exit 2; }

FAIL=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[1;33m!\033[0m %s\n' "$*"; }
stop() { printf '  \033[31mx\033[0m %s\n' "$*"; FAIL=1; }
have() { command -v "$1" >/dev/null 2>&1; }

git fetch -q origin --prune 2>/dev/null || warn "could not fetch origin — everything below is as of the last fetch"

BR="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
MAIN_WT="$(git worktree list --porcelain | awk '/^worktree /{w=substr($0,10)} /^branch refs\/heads\/main$/{print w}')"
AHEAD="$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)"
BEHIND="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)"

# ---------------------------------------------------------------- where you are standing
echo "where"
if [[ -n "$MAIN_WT" ]]; then ok "main is checked out at $MAIN_WT"; else warn "no worktree holds main; shipping needs one (git worktree add ../planetai-node-main main)"; fi
if [[ "$BR" == main ]]; then
  [[ "$MODE" == preflight ]] && warn "you are on main. Feature work goes on a branch in its own worktree; this checkout is for shipping."
else
  ok "on $BR — $AHEAD ahead of origin/main, $BEHIND behind"
  [[ "$BEHIND" -gt 20 && "$MODE" == preflight ]] && warn "$BEHIND commits behind main. Merge origin/main in before you start, not after."
fi
[[ -f "$(git rev-parse --git-common-dir)/index.lock" ]] && warn "a stale .git/index.lock is present; check ps for a live git before deleting it"
[[ -n "$(git stash list 2>/dev/null)" ]] && warn "the stash is not empty. It is shared across every worktree; do not pop what you did not push."

# ---------------------------------------------------------------- the suite count, which git merges silently
echo "tests/all"
LISTED="$(grep -c '^test_' tests/all)"
ASSERTED="$(sed -n 's/.*-ne \([0-9]*\) \].*/\1/p' tests/all | head -1)"
if [[ "$LISTED" == "$ASSERTED" ]]; then ok "$LISTED suites listed, $ASSERTED asserted"; else stop "tests/all lists $LISTED suites and asserts $ASSERTED — move the number by hand; git will not"; fi

# ---------------------------------------------------------------- what is open
echo "open work"
if have gh; then
  PRS="$(gh pr list --state open --json number,title,headRefName,mergeable,createdAt,files --limit 50 2>/dev/null || echo '[]')"
  N="$(printf '%s' "$PRS" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))' 2>/dev/null || echo '?')"
  if [[ "$N" == 0 ]]; then ok "no open PRs"; else
    printf '%s' "$PRS" | python3 -c '
import json,sys,datetime as d
now=d.datetime.now(d.timezone.utc)
for p in json.load(sys.stdin):
    age=(now-d.datetime.fromisoformat(p["createdAt"].replace("Z","+00:00"))).days
    flag="!" if age>5 or p["mergeable"]=="CONFLICTING" else " "
    print("  %s #%d %-12s %2dd  %s  — %s" % (flag, p["number"], p["mergeable"], age, p["headRefName"], p["title"][:70]))'
  fi
  # branches on origin ahead of main with no PR: work that exists and nobody is looking at
  STRAY="$(git for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -v '^origin/HEAD$\|^origin/main$\|^origin$' | while read -r b; do
      n=$(git rev-list --count origin/main.."$b" 2>/dev/null); [[ "${n:-0}" -gt 0 ]] || continue
      printf '%s' "$PRS" | grep -q "\"headRefName\": *\"${b#origin/}\"" || echo "${b#origin/}"; done | wc -l | tr -d ' ')"
  [[ "$STRAY" -gt 0 ]] && warn "$STRAY branch(es) on origin are ahead of main with no PR (tools/sweep.py lists them). Most are squash leftovers; check before assuming, delete after."
  # CI on main
  RED="$(gh run list --branch main --limit 6 --json name,conclusion,headSha 2>/dev/null | python3 -c '
import json,sys
runs=json.load(sys.stdin); head=runs[0]["headSha"] if runs else ""
bad=sorted({r["name"] for r in runs if r["headSha"]==head and r["conclusion"] in ("failure","cancelled","timed_out")})
print(",".join(bad))' 2>/dev/null)"
  if [[ -n "$RED" ]]; then stop "CI is red on main: $RED. Fix or understand that before adding to it."; else ok "CI is green on main's head"; fi
else
  warn "no gh here — open PRs and CI not checked"
fi

# ---------------------------------------------------------------- the site, and the neighbours
if [[ "$MODE" == preflight ]]; then
  echo "released"
  if [[ -n "$MAIN_WT" ]]; then
    (cd "$MAIN_WT" && tools/ship.sh --check 2>/dev/null | sed 's/^/  /' | head -3) || true
  fi
  echo "siblings"
  BESIDE="$(dirname "${MAIN_WT:-$ROOT}")"
  for sib in planetai-design awesome-fabcity-data; do
    d="$BESIDE/$sib"; [[ -d "$d/.git" ]] || { warn "$sib is not checked out beside this repo (check_theme skips without it; the registry gate does not — it reads the pin in data/sources)"; continue; }
    sb="$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)"; git -C "$d" fetch -q origin 2>/dev/null
    beh="$(git -C "$d" rev-list --count HEAD..origin/main 2>/dev/null || echo '?')"
    unt="$(git -C "$d" status --porcelain 2>/dev/null | grep -c '^??')"
    if [[ "$beh" == 0 && "$unt" == 0 ]]; then ok "$sib on $sb, level with its main"; else warn "$sib is on $sb, $beh behind its main, $unt untracked file(s). The gates read its origin/main; your eyes read this."; fi
  done
fi

# ---------------------------------------------------------------- landing: nothing lives only here
if [[ "$MODE" == land ]]; then
  echo "landing $BR"
  [[ "$BR" == main ]] && stop "you are landing from main. Work lands through a branch and a PR."
  if [[ -n "$(git status --porcelain)" ]]; then stop "uncommitted changes. Commit them or throw them away; a session does not end with work in a working tree."; else ok "working tree clean"; fi
  UP="$(git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)"
  if [[ -z "$UP" ]]; then stop "branch has no upstream. git push -u origin $BR"; else
    if [[ "$(git rev-list --count "$UP"..HEAD)" -gt 0 ]]; then stop "$(git rev-list --count "$UP"..HEAD) commit(s) not pushed. git push"; else ok "pushed to $UP"; fi
  fi
  [[ "$BEHIND" -gt 0 ]] && warn "$BEHIND behind origin/main. Merge it in and re-run land, or the PR merges against a tree you did not test."
  # a change in the code without a line in the changelog
  CHANGED="$(git diff --name-only origin/main...HEAD 2>/dev/null)"
  if grep -qE '^(app|packs|bin|install|update\.sh|init\.sql|docker-compose\.yml)' <<<"$CHANGED" && ! grep -q '^CHANGELOG.md$' <<<"$CHANGED"; then
    warn "code changed and CHANGELOG.md did not. A dated bullet at the top is the convention for unreleased work."
  fi
  # the count moved here AND in another open PR: the one collision git cannot see
  if grep -q '^tests/all$' <<<"$CHANGED" && have gh; then
    OTHERS="$(printf '%s' "${PRS:-[]}" | python3 -c '
import json,sys; me=sys.argv[1]
print(" ".join("#%d" % p["number"] for p in json.load(sys.stdin) if p["headRefName"]!=me and any(f["path"]=="tests/all" for f in p.get("files",[]))))' "$BR" 2>/dev/null)"
    [[ -n "$OTHERS" ]] && stop "this branch moves the suite count and so does $OTHERS. Merge one, then re-count the other. Never both."
  fi
  # a PR exists
  if have gh; then
    PRN="$(gh pr view "$BR" --json number,mergeable,mergeStateStatus --jq '"#\(.number) \(.mergeable) \(.mergeStateStatus)"' 2>/dev/null)"
    if [[ -n "$PRN" ]]; then ok "PR $PRN"; else stop "no PR for $BR. gh pr create — the template asks the questions a reviewer needs answered."; fi
  fi
  # and it is green here, for real
  echo "gates"
  if make lint >/tmp/land-lint.log 2>&1; then ok "make lint"; else stop "make lint failed — tail /tmp/land-lint.log"; fi
  if make test >/tmp/land-test.log 2>&1; then ok "$(grep -o '[0-9]* suites: [0-9]* passed' /tmp/land-test.log | tail -1)"; else stop "make test failed — tail /tmp/land-test.log"; fi
fi

echo
if [[ $FAIL -eq 1 ]]; then
  printf '\033[31mnot clear.\033[0m the x lines above are the reasons.\n'; exit 1
else
  [[ "$MODE" == land ]] && printf '\033[32mclear.\033[0m nothing from this session exists only on this machine.\n' || printf '\033[32mclear.\033[0m\n'
fi
