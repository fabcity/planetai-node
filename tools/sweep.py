#!/usr/bin/env python3
"""The daily sweep: what is open, what is red, what is behind, what is owed. It reports. It never merges.

    python3 tools/sweep.py             # markdown on stdout; always exits 0
    python3 tools/sweep.py --json      # the same facts as data

`.github/workflows/sweep.yml` runs this once a day and writes the result into one pinned issue,
"Daily sweep", editing it in place so there is one page to read and no notification storm. It runs
with the workflow's own token and nothing else, so nothing here can leak a secret, and it has no
write access to anything but that issue.

Why a report and not a bot that acts: the week of 12–19 September had a revert PR opened by a button
four minutes after the merge it reverted, with an empty template. A maintainer that merges is a
maintainer that does that at machine speed. What was missing was somebody *saying* — for a day, CI
was red on main and nobody knew; for two weeks, four PRs sat unmerged; six releases went out with no
CHANGELOG heading. Saying is enough, and it is what this does.

Each check is a function that returns rows, so a new one is a function and a line in REPORT.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STALE_PR_DAYS = 5
SITE_VERSION = "https://planetai.fab.city/node0/get/VERSION"
TAG = re.compile(r"^v\d+(\.\d+)*$")


def sh(*args: str, cwd: Path = ROOT) -> str:
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def gh(*args: str) -> list | dict:
    out = sh("gh", *args)
    try:
        return json.loads(out) if out else []
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------- pure: what a CHANGELOG owes its tags

def changelog_versions(text: str) -> set[str]:
    """Every version with a `## vX.Y — …` heading."""
    return set(re.findall(r"^## (v\d+(?:\.\d+)*)\b", text, re.M))


def release_tags(names: list[str]) -> list[str]:
    """The tags that name releases, oldest first by version, ignoring anything that is not vN[.N]*."""
    return sorted((n for n in names if TAG.match(n)), key=lambda v: [int(x) for x in v[1:].split(".")])


def tags_without_heading(tags: list[str], versions: set[str], since: str = "v0.44") -> list[str]:
    """Release tags with no CHANGELOG section. `since` is where the convention started being kept —
    v0.4.3 through v0.43 were tagged faster than they were written up, and that is history, not debt."""
    floor = [int(x) for x in since[1:].split(".")]
    return [t for t in tags if [int(x) for x in t[1:].split(".")] >= floor and t not in versions]


# ---------------------------------------------------------------- the checks

def open_prs() -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for p in gh("pr", "list", "--state", "open", "--limit", "50",
                "--json", "number,title,headRefName,mergeable,createdAt,author,statusCheckRollup"):
        age = (now - dt.datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00"))).days
        checks = p.get("statusCheckRollup") or []
        failed = sorted({c.get("name") or c.get("context", "") for c in checks
                         if (c.get("conclusion") or c.get("state", "")).upper() in ("FAILURE", "ERROR", "TIMED_OUT")})
        rows.append({"number": p["number"], "title": p["title"], "branch": p["headRefName"], "age_days": age,
                     "mergeable": p["mergeable"], "author": (p.get("author") or {}).get("login", ""),
                     "failed_checks": failed,
                     "flag": age > STALE_PR_DAYS or p["mergeable"] == "CONFLICTING" or bool(failed)})
    return rows


def stray_branches(pr_heads: set[str]) -> list[dict]:
    """Branches on origin ahead of main with no PR. Most are leftovers of squash merges — the content
    is on main under a different commit — so this says how far ahead and how old, and leaves the
    judgement to a person. `git merge-tree` would say whether the content is on main; it is a second
    step, not this one."""
    rows = []
    for ref in sh("git", "for-each-ref", "--format=%(refname:short)|%(committerdate:short)", "refs/remotes/origin").splitlines():
        name, date = ref.split("|")
        short = name.removeprefix("origin/")
        if short in ("HEAD", "main") or name == "origin" or short in pr_heads:
            continue
        ahead = sh("git", "rev-list", "--count", f"origin/main..{name}")
        if ahead and int(ahead) > 0:
            rows.append({"branch": short, "ahead": int(ahead), "last_commit": date})
    return sorted(rows, key=lambda r: r["last_commit"], reverse=True)


def ci_on_main() -> dict:
    runs = gh("run", "list", "--branch", "main", "--limit", "8", "--json", "name,conclusion,headSha,url")
    if not runs:
        return {"head": "", "red": [], "green": [], "known": False}
    head = runs[0]["headSha"]
    at_head = [r for r in runs if r["headSha"] == head]
    return {"head": head[:7],
            "red": sorted({r["name"] for r in at_head if r["conclusion"] in ("failure", "cancelled", "timed_out")}),
            "green": sorted({r["name"] for r in at_head if r["conclusion"] == "success"}),
            "pending": sorted({r["name"] for r in at_head if r["conclusion"] in (None, "")}),
            "known": True}


def site() -> dict:
    main_at = sh("git", "describe", "--tags", "--always", "origin/main")
    # Cloudflare answers 403 to python's default User-Agent and 200 to anything that names itself.
    req = urllib.request.Request(f"{SITE_VERSION}?cb={dt.datetime.now().timestamp()}",
                                 headers={"User-Agent": "planetai-node tools/sweep.py (https://planetai.fab.city)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            live = r.read().decode().strip()
        reachable = True
    except Exception as e:                       # noqa: BLE001 — an unreachable site is a fact to report
        live, reachable = f"unreachable ({type(e).__name__})", False
    return {"main": main_at, "live": live, "reachable": reachable, "behind": reachable and live != main_at}


def suite_count() -> dict:
    text = (ROOT / "tests/all").read_text()
    listed = len(re.findall(r"^test_", text, re.M))
    m = re.search(r"-ne (\d+) \]", text)
    asserted = int(m.group(1)) if m else -1
    return {"listed": listed, "asserted": asserted, "agree": listed == asserted}


def changelog_debt() -> list[str]:
    tags = release_tags(sh("git", "tag", "-l").split())
    return tags_without_heading(tags, changelog_versions((ROOT / "CHANGELOG.md").read_text()))


# ---------------------------------------------------------------- the page

def report() -> dict:
    prs = open_prs()
    return {"at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "prs": prs, "stray": stray_branches({p["branch"] for p in prs}), "ci": ci_on_main(),
            "site": site(), "suites": suite_count(), "changelog_debt": changelog_debt()}


def markdown(r: dict) -> str:
    L = [f"_Swept {r['at']}. Edited in place once a day by `tools/sweep.py`; it reports and never merges._", ""]
    flags = 0

    ci = r["ci"]
    if not ci["known"]:
        L.append("## CI on main — could not read")
    elif ci["red"]:
        flags += 1; L.append(f"## 🔴 CI on main is red at `{ci['head']}`: {', '.join(ci['red'])}")
        L.append("Nothing should be added to main until this is understood. `gh run list --branch main`.")
    else:
        L.append(f"## CI on main — green at `{ci['head']}`" + (f" ({', '.join(ci['pending'])} pending)" if ci.get("pending") else ""))
    L.append("")

    s = r["site"]
    if not s["reachable"]:
        flags += 1; L.append(f"## 🔴 planetai.fab.city did not answer: {s['live']}")
        L.append("Every `planetai update` reads that URL first. If this is not a blip, it is the outage.")
    elif s["behind"]:
        flags += 1; L.append(f"## 🟡 The site is behind: main is at `{s['main']}`, the site serves `{s['live']}`")
        L.append("A tester downloading now gets the older node. `make ship` from the worktree that holds main — it needs the release key.")
    else:
        L.append(f"## The site serves what is on main: `{s['live']}`")
    L.append("")

    L.append(f"## Open PRs ({len(r['prs'])})")
    if not r["prs"]:
        L.append("None.")
    else:
        L += ["| | PR | age | mergeable | CI | by |", "|---|---|---|---|---|---|"]
        for p in r["prs"]:
            if p["flag"]: flags += 1
            ci_s = "🔴 " + ", ".join(p["failed_checks"]) if p["failed_checks"] else "green"
            L.append(f"| {'⚠️' if p['flag'] else ''} | #{p['number']} {p['title'][:60]} | {p['age_days']}d | {p['mergeable']} | {ci_s} | {p['author']} |")
        L.append(f"\n⚠️ = older than {STALE_PR_DAYS} days, conflicting, or red. A PR that sits is a PR that will conflict.")
    L.append("")

    d = r["changelog_debt"]
    if d:
        flags += 1; L.append(f"## 🟡 Tagged, shipped, and not in CHANGELOG.md: {', '.join(d)}")
        L.append("Every release has a `## vX.Y — date — title` section. These went out without one; a tester on them cannot read what they got.")
        L.append("")

    q = r["suites"]
    if not q["agree"]:
        flags += 1; L.append(f"## 🔴 tests/all lists {q['listed']} suites and asserts {q['asserted']}")
        L.append("Two branches each moved the number and git kept one. Fix the number on main now.")
        L.append("")

    st = r["stray"]
    L.append(f"## Branches on origin ahead of main with no PR ({len(st)})")
    if st:
        L.append("Most are squash leftovers whose content is on main under another commit. Check with "
                 "`git merge-tree --write-tree origin/main origin/<branch>` — a result tree equal to main's is a no-op — then delete. "
                 "The ones from the last two weeks deserve a look first.")
        L += ["", "| branch | ahead | last commit |", "|---|---|---|"]
        for b in st[:40]:
            L.append(f"| `{b['branch']}` | {b['ahead']} | {b['last_commit']} |")
        if len(st) > 40:
            L.append(f"| …and {len(st) - 40} more | | |")
    else:
        L.append("None.")
    L.append("")

    L.insert(0, ("**Nothing needs a person today.**" if flags == 0 else f"**{flags} thing{'s' if flags != 1 else ''} need{'s' if flags == 1 else ''} a person.**"))
    L.insert(1, "")
    return "\n".join(L)


if __name__ == "__main__":
    r = report()
    print(json.dumps(r, indent=2) if "--json" in sys.argv else markdown(r))
