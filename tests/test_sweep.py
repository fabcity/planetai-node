"""The sweep's one piece of arithmetic: which release tags have no CHANGELOG heading.

Everything else in tools/sweep.py is a read of gh, git or the site, and a test of those is a test of
the network. This is the part that could be quietly wrong — a regex that misses a heading, a version
sort that puts v0.9 after v0.60 — and it is the part that names six releases in public every morning."""
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location("sweep", pathlib.Path("tools/sweep.py"))
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)

CHANGELOG = """# Changelog

- 2026-09-17 — an unreleased bullet, not a heading

## v0.60 — 2026-09-18 — an update has to say who built it

text

## v0.53 — 2026-09-14 — the page stops telling a household things

## v0.44.2 — 2026-09-11 — an update refuses a download it could not verify
## v0.44 — 2026-09-11 — the node knows its issues
## v0.44 — 2026-09-11 — planetai config, and whose project this is
"""

v = sweep.changelog_versions(CHANGELOG)
assert v == {"v0.60", "v0.53", "v0.44.2", "v0.44"}, v
assert "v0.9" not in v and "2026-09-17" not in v, "a bullet is not a heading"

tags = sweep.release_tags(["v0.9", "v0.60", "v0.6", "v0.44.2", "v0.44", "v0.53", "v0.54", "v0.59", "deploy-2026", "v1"])
assert tags == ["v0.6", "v0.9", "v0.44", "v0.44.2", "v0.53", "v0.54", "v0.59", "v0.60", "v1"], tags
assert "deploy-2026" not in tags, "only vN[.N]* names a release"

debt = sweep.tags_without_heading(tags, v)
assert debt == ["v0.54", "v0.59", "v1"], debt           # v0.6 and v0.9 are below the floor: history, not debt
assert sweep.tags_without_heading(tags, v, since="v0.1") == ["v0.6", "v0.9", "v0.54", "v0.59", "v1"]
assert sweep.tags_without_heading([], v) == []

# against the real files: whatever it says today, it must say it about tags that exist
real = sweep.changelog_debt()
have = set(sweep.sh("git", "tag", "-l").split())
assert all(t in have for t in real), real
print(f"sweep: the changelog-debt arithmetic holds; today it names {len(real)}")
