"""Every Python snippet embedded in bin/planetai must run on Python 3.9, the version Apple ships with the
command line tools. This extracts each `json '...'` and `python3 -c '...'` argument and compiles it with
feature_version=(3,9), so an f-string trick that only 3.12 accepts fails here and not on a node."""
import ast, re, sys
src = open("bin/planetai").read()
# json '<code>'  and  python3 -c '<code>'   — code is inside single quotes; a literal ' inside is written '"'"'
pat = re.compile(r"(?:\bjson|python3 -c)\s+'((?:[^']|'\"'\"')*)'", re.S)
bad = 0; n = 0
for m in pat.finditer(src):
    code = m.group(1).replace("'\"'\"'", "'")
    # the json helper wraps the snippet: it has `d` in scope. Give it a stub so name errors don't matter; we only parse.
    n += 1
    try:
        ast.parse(code, feature_version=(3, 9))
    except SyntaxError as e:
        bad += 1
        line = src[:m.start()].count("\n") + 1
        print(f"  x bin/planetai:{line}: {e.msg} -> {e.text.strip()[:80] if e.text else code[:80]}")
# the CLI runs on the node, whose Python is Apple's stdlib-only 3.9. A command that imports a third-party
# library works on the developer's machine and fails on every node (planetai packs did, with PyYAML).
THIRD_PARTY = ("yaml", "httpx", "requests", "psycopg", "numpy", "pandas", "sqlglot")
for m in pat.finditer(src):
    code = m.group(1).replace("'\"'\"'", "'")
    for lib in THIRD_PARTY:
        if f"import {lib}" in code:
            line = src[:m.start()].count("\n") + 1
            print(f"  x bin/planetai:{line}: imports {lib}, which a node's Python does not have")
            bad += 1

print(f"  {n} snippets checked, {bad} would fail on Python 3.9")
sys.exit(1 if bad else 0)
