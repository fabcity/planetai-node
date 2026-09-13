"""Proof that the dashboard's design gates fail when they should.

A gate nobody has watched fail is a gate that passes for the wrong reason — a regex that never matched, a file
read from the wrong path. Every rule in tools/check_ui.py's visual-language section exists because that thing
shipped to real households, so each one gets broken here on purpose against a copy of the real index.html.

Run: python3 tests/test_check_ui.py
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(tmp):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_ui.py")],
                       cwd=tmp, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def tree():
    """A throwaway copy of the files check_ui.py reads. The page is three of them now."""
    tmp = Path(tempfile.mkdtemp(prefix="planetai-ui-"))
    (tmp / "app" / "static").mkdir(parents=True)
    for f in ("index.html", "dashboard.js", "dashboard.css"):
        shutil.copy(ROOT / "app" / "static" / f, tmp / "app" / "static" / f)
    shutil.copy(ROOT / "app" / "main.py", tmp / "app" / "main.py")
    (tmp / "app" / "issues").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "app" / "issues" / "api.py", tmp / "app" / "issues" / "api.py")
    shutil.copy(ROOT / "init.sql", tmp / "init.sql")
    return tmp


def broken(name, mutate, expect, where="dashboard.css"):
    """Apply one violation to the real page and require check_ui.py to name it.

    `where` because the page is three files now. The visual-language rules are about the
    stylesheet, so that is the default; a rule about the markup or the script names its own.
    """
    tmp = tree()
    try:
        p = tmp / "app" / "static" / where
        before = p.read_text()
        after = mutate(before)
        assert after != before, f"{name}: the mutation changed nothing — this test is not testing anything"
        p.write_text(after)
        rc, out = run(tmp)
        assert rc == 1, f"{name}: check_ui.py passed a page that breaks the rule\n{out}"
        assert re.search(expect, out, re.I), f"{name}: it failed, but not about this\nwanted /{expect}/\ngot:\n{out}"
        print(f"  · {name}: caught — {out.strip().splitlines()[0].strip()[:96]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def sub(old, new):
    def f(s):
        assert s.count(old) >= 1, f"anchor not found in the file under test: {old[:60]!r}"
        return s.replace(old, new, 1)
    return f


def prepend(css):
    """Most of these violations are `add a rule that breaks one`. Where in the file does not
    matter, so they go at the top rather than hunting an anchor that may be renamed."""
    return lambda s: css + "\n" + s


# The page as it ships must pass, or every assertion below proves nothing.
tmp = tree()
rc, out = run(tmp)
assert rc == 0, f"the shipped page does not pass its own gates:\n{out}"
shutil.rmtree(tmp, ignore_errors=True)
print("  · the shipped page passes")

# 1. a regular hexagon as decoration — the .bighex that shipped, near enough verbatim
broken("hexagon", prepend(
    ".bighex{position:absolute;right:-8%;width:min(60%,420px);"
    "clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%);background:var(--ink)}"),
    r"six-sided clip-path")

# ...but a small glyph is a bullet, not wallpaper, and must still pass
tmp = tree()
q = tmp / "app" / "static" / "dashboard.css"
q.write_text(".hexbullet{width:24px;clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%)}\n"
             + q.read_text())
rc, out = run(tmp)
assert rc == 0, f"a 24px hexagon bullet should pass; the gate is too wide:\n{out}"
shutil.rmtree(tmp, ignore_errors=True)
print("  · a 24px hexagon bullet still passes")

# 2. the website palette
broken("web-green", prepend(".x{color:#7AC943}"), r"#7AC943.*web-green")
broken("web-blue", prepend(".x{stroke:#3FA9F5}"), r"#3FA9F5.*web-blue")

# 3. gradients and glows
broken("radial-gradient", prepend(
    ".glow{position:fixed;background:radial-gradient(circle,rgba(32,56,141,.35),transparent 60%)}"),
    r"radial-gradient\(\) is in the stylesheet")

# 4. radius, on a selector that is not on the legacy list
broken("pill control", prepend(".newbtn{border-radius:999px;padding:6px 14px;width:40px}"),
       r"rounds a control to 999px")
broken("round card", prepend(".panel{border-radius:26px}"), r"rounds a card to 26px")

# 5. provenance carrying a verdict — the layer's role tokens, which is what the page uses now
broken("prov colour", prepend(".prov{color:var(--rings)}"), r"prov.*carries a colour")
broken("prov inline colour",
       sub('<div class="status">', '<div class="status prov" style="color:#00A057">'),
       r"prov in its class or id carries an inline colour", where="index.html")

# 6. orange away from the satellite, in both registers' oranges
broken("orange act button", prepend(".btn.act{background:var(--satellite-only)}"),
       r"paints with orange away from the satellite")
broken("paper orange astray", prepend(".chip{color:#DB7200}"),
       r"paints with orange away from the satellite")

# 7. the dark register's blue. The page declares no register in its markup — render() sets
#    data-theme on <html> for the Wall — so the lifted blue must not be in the stylesheet at all.
broken("lifted blue on paper", prepend(".x{color:#7FA5E8}"),
       r"#7FA5E8.*(outside the dark register|does not declare)")

# 8. an asset the node does not serve, and one that is not under static/ at all
# the ground is written by the renderer now, not by the document, and it carries a query string —
# `?variant=${ctx.register}` — so these anchor on the path and leave the query where it is.
GROUND = 'src="static/node-ground.svg?variant='
broken("unserved asset", sub(GROUND, 'src="node-ground.svg?variant='),
       r"loads node-ground\.svg, which is not under static/", where="dashboard.js")
broken("asset off the allowlist", sub(GROUND, 'src="static/ground2.svg?variant='),
       r"COMPANIONS allowlist does not serve", where="dashboard.js")
# and the document's own stylesheet links, which nothing checked before
broken("stylesheet off the allowlist",
       sub('href="static/dashboard.css"', 'href="static/theme2.css"'),
       r"COMPANIONS allowlist does not serve", where="index.html")

# 9. the stylesheets: a font nothing serves, and a CDN
broken("font off the allowlist", prepend('@font-face{font-family:"Z";src:url("Nope.ttf")}'),
       r"loads Nope\.ttf, which app/main\.py's COMPANIONS allowlist does not serve")
broken("a CDN in a stylesheet", prepend("@import url('https://fonts.googleapis.com/css2?family=X');"),
       r"from the network")

print("check_ui: every visual-language gate fails when the page breaks its rule")
