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
    """A throwaway copy of the three files check_ui.py reads."""
    tmp = Path(tempfile.mkdtemp(prefix="planetai-ui-"))
    (tmp / "app" / "static").mkdir(parents=True)
    shutil.copy(ROOT / "app" / "static" / "index.html", tmp / "app" / "static" / "index.html")
    shutil.copy(ROOT / "app" / "main.py", tmp / "app" / "main.py")
    shutil.copy(ROOT / "init.sql", tmp / "init.sql")
    return tmp


def broken(name, mutate, expect):
    """Apply one violation to the real page and require check_ui.py to name it."""
    tmp = tree()
    try:
        p = tmp / "app" / "static" / "index.html"
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
        assert s.count(old) >= 1, f"anchor not in index.html: {old[:60]!r}"
        return s.replace(old, new, 1)
    return f


# The page as it ships must pass, or every assertion below proves nothing.
tmp = tree()
rc, out = run(tmp)
assert rc == 0, f"the shipped page does not pass its own gates:\n{out}"
shutil.rmtree(tmp, ignore_errors=True)
print("  · the shipped page passes")

# 1. a regular hexagon as decoration — the .bighex that shipped, near enough verbatim
broken("hexagon", sub(
    ".hero .ground{",
    ".hero .bighex{position:absolute;right:-8%;top:-30%;width:min(60%,420px);"
    "clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%);background:#333}\n.hero .ground{"),
    r"six-sided clip-path")

# ...but the small glyph on every alert row is a bullet, not wallpaper, and must still pass
tmp = tree()
p = tmp / "app" / "static" / "index.html"
p.write_text(p.read_text().replace(".alert .hex{width:10px", ".alert .hex{width:24px", 1))
rc, out = run(tmp)
assert rc == 0, f"a 24px hexagon bullet should pass; the gate is too wide:\n{out}"
shutil.rmtree(tmp, ignore_errors=True)
print("  · a 24px hexagon bullet still passes")

# 2. the website palette
broken("web-green", sub("--red:#E62038", "--hue:#7AC943;--red:#E62038"), r"#7AC943.*web-green")
broken("web-blue", sub("stroke=\"var(--blue)\"", "stroke=\"#3FA9F5\""), r"#3FA9F5.*web-blue")

# 3. gradients and glows
broken("radial-gradient", sub(
    ".grain{position:fixed",
    ".glow{position:fixed;background:radial-gradient(circle,rgba(32,56,141,.35),transparent 60%)}\n.grain{position:fixed"),
    r"radial-gradient\(\) is in the stylesheet")

# 4. radius, on a selector that is not on the legacy list
broken("pill control", sub(
    ".prov .g{flex:none",
    ".newbtn{border-radius:999px;padding:6px 14px}\n.prov .g{flex:none"),
    r"rounds a control to 999px")
broken("round card", sub(
    ".hero .ground{",
    ".panel{border-radius:26px;background:var(--card)}\n.hero .ground{"),
    r"rounds a card to 26px")

# 5. provenance carrying a verdict
broken("prov colour", sub(".prov{display:inline-flex", ".prov{color:var(--green);display:inline-flex"),
       r"prov.*carries a colour")
broken("prov inline colour", sub('<span class="prov" id="earth-prov">',
                                 '<span class="prov" id="earth-prov" style="color:#00A057">'),
       r"prov in its class or id carries an inline colour")

# 6. orange away from the satellite
broken("orange act button", sub(".btn.act{background:var(--green)", ".btn.act{background:var(--orange)"),
       r"paints with orange away from the satellite")

# 7. the dark register's blue
broken("Fab Blue on ink", sub("--blue:#7FA5E8", "--blue:#20388D"), r"#20388D.*dark register")
broken("lifted blue on paper", sub('<html lang="en" data-variant="dark">', '<html lang="en">'),
       r"#7FA5E8.*(outside the dark register|does not declare)")

# 8. an asset the node does not serve
broken("unserved asset", sub('src="static/node-ground.svg"', 'src="node-ground.svg"'),
       r"loads node-ground\.svg, which is not under static/")
broken("asset off the allowlist", sub('src="static/node-ground.svg"', 'src="static/ground2.svg"'),
       r"COMPANIONS allowlist does not serve")

print("check_ui: every visual-language gate fails when the page breaks its rule")
