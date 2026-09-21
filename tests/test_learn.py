"""The learn layer quotes the documentation, so this proves it still is a quote.

Every panel in learn mode puts words in front of a household and says they are the node's own
documentation. The only thing standing between that claim and a paraphrase is tools/build_learn.py,
and the only thing standing between the claim and rot is its --check. So:

  · the seventeen quotes in app/static/learn.json are each a verbatim substring of the docs/site
    page they cite, right now, against the real tree — the invariant itself, asserted directly and
    not through the tool that maintains it;
  · editing a quote out of its page fails the build, naming the mark;
  · a quote that grows past sixty words fails the build rather than being drawn and cut off;
  · --check fails when the committed file is not what the docs say, and passes again after a
    rebuild. Both directions, because a gate that only ever passes is not a gate.

Run: python3 tests/test_learn.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEARN = ROOT / "app" / "static" / "learn.json"


def edit(page, old, new):
    """Change one span of a docs page, and prove the change landed. A mutation that matched nothing
    leaves the tree clean, the gate passes, and the test says the gate works. It is the failure this
    whole file exists to catch, so it may not be the failure this file has."""
    before = page.read_text(encoding="utf-8")
    assert before.count(old) == 1, f"{page.name}: the anchor is not there once: {old[:60]!r}"
    page.write_text(before.replace(old, new), encoding="utf-8")
    return before


def run(cwd, *args):
    r = subprocess.run([sys.executable, "tools/build_learn.py", *args],
                       cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def tree():
    """A throwaway copy of the three things build_learn.py touches."""
    tmp = Path(tempfile.mkdtemp(prefix="planetai-learn-"))
    (tmp / "tools").mkdir()
    (tmp / "app" / "static").mkdir(parents=True)
    shutil.copy(ROOT / "tools" / "build_learn.py", tmp / "tools" / "build_learn.py")
    shutil.copytree(ROOT / "docs" / "site", tmp / "docs" / "site")
    shutil.copy(LEARN, tmp / "app" / "static" / "learn.json")
    return tmp


# --- the invariant, against the tree that ships ---------------------------------------------------
built = json.loads(LEARN.read_text(encoding="utf-8"))
assert built["order"], "learn.json has no marks"
assert set(built["order"]) == set(built["marks"]), "the walk order and the marks disagree"
for key in built["order"]:
    m = built["marks"][key]
    page = (ROOT / "docs" / "site" / m["page"]).read_text(encoding="utf-8")
    assert m["quote"] in page, (
        f"the {key} panel quotes docs/site/{m['page']} and those words are not in that page. "
        f"A panel that says 'the words above are from' and then paraphrases is the one thing this "
        f"layer may not do.")
    n = len(m["quote"].split())
    assert n <= 60, f"{key}: {n} words, over the sixty the panel holds"
    assert m["more"], f"{key}: no line of the page's own"
    assert m["url"].startswith("https://planetai.fab.city/docs/"), f"{key}: {m['url']}"
print(f"  · all {len(built['order'])} quotes are verbatim spans of the page they name, and under 60 words")

# --- the gate fails when the documentation moves --------------------------------------------------
tmp = tree()
try:
    rc, out = run(tmp, "--check")
    assert rc == 0, f"a clean tree should pass --check:\n{out}"
    print("  · a clean tree passes --check")

    # 1. the quote is edited out of its page entirely
    page = tmp / "docs" / "site" / "rho.md"
    before = edit(page, "ρ (rho) is the share of the node's act-level alerts",
                  "ρ is roughly how often somebody did something")
    rc, out = run(tmp)
    assert rc != 0, f"the build accepted a quote that is no longer in its page:\n{out}"
    assert "rho:" in out, f"it failed, but did not name the mark:\n{out}"
    print("  · a quote edited out of its page fails the build, and the build names the mark")
    page.write_text(before, encoding="utf-8")

    # 2. the paragraph grows past what the panel holds
    page = tmp / "docs" / "site" / "alerts.md"
    before = edit(page, "`ALERT_LEVEL` (default `act`) is the floor for interrupting a person.",
                  "`ALERT_LEVEL` (default `act`) is the floor for interrupting a person. "
                  + "and so on " * 30)
    rc, out = run(tmp)
    assert rc != 0, f"the build accepted a quote past the word ceiling:\n{out}"
    assert "levels:" in out and "over the 60" in out, f"wrong failure:\n{out}"
    print("  · a span that grows past sixty words fails the build rather than being drawn and cut")
    page.write_text(before, encoding="utf-8")

    # 3. the prose moves but the span still resolves: --check fails, a rebuild fixes it, --check passes
    page = tmp / "docs" / "site" / "how-it-works.md"
    edit(page, "No agent dispatches without a human row in `actions`.",
         "No agent ever dispatches without a human row in `actions`.")
    rc, out = run(tmp, "--check")
    assert rc != 0, f"--check passed a learn.json that is not what the docs say:\n{out}"
    assert "not what docs/site says" in out, out
    print("  · --check fails when the committed file and the documentation have drifted apart")
    rc, out = run(tmp)
    assert rc == 0, out
    rc, out = run(tmp, "--check")
    assert rc == 0, f"--check still fails after a rebuild:\n{out}"
    assert "No agent ever dispatches" in json.loads((tmp / "app" / "static" / "learn.json")
                                                    .read_text(encoding="utf-8"))["marks"]["refusals"]["quote"]
    print("  · a rebuild takes the new words, and --check passes again")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("learn: the panels quote the documentation, and the build fails when they stop")
