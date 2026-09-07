import re, csv, sys, os, collections

ROOT_A = "/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai"
ROOT_B = "/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node"

FILES = [
    ("planetai", "index.html"),
    ("planetai", "observatory/index.html"),
    ("planetai", "node0/index.html"),
    ("planetai", "node0/setup/index.html"),
    ("planetai", "node0/more/index.html"),
    ("planetai", "timeline/index.html"),
    ("planetai", "local-hubs/serangan/index.html"),
    ("planetai", "assets/site-chrome.css"),
    ("planetai-node", "app/static/index.html"),
]

PATS = [
    ("hex",           re.compile(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b')),
    ("rgb",           re.compile(r'rgba?\(\s*[^)]{1,60}\)')),
    ("hsl",           re.compile(r'hsla?\(\s*[^)]{1,60}\)')),
    ("oklch",         re.compile(r'oklch\(\s*[^)]{1,60}\)')),
    ("font-family",   re.compile(r'font-family\s*:\s*([^;}"\']{1,120})')),
    ("font-size",     re.compile(r'font-size\s*:\s*([^;}]{1,60})')),
    ("border-radius", re.compile(r'border-radius\s*:\s*([^;}]{1,60})')),
    ("box-shadow",    re.compile(r'box-shadow\s*:\s*([^;}]{1,120})')),
    ("letter-spacing",re.compile(r'letter-spacing\s*:\s*([^;}]{1,40})')),
    ("z-index",       re.compile(r'z-index\s*:\s*([^;}]{1,20})')),
]
# shorthand `font:` also carries family/size/letter-spacing; capture family tail separately
FONT_SHORT = re.compile(r'\bfont\s*:\s*([^;}"]{1,140})')

rows = []
for repo, rel in FILES:
    root = ROOT_A if repo == "planetai" else ROOT_B
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        sys.stderr.write("MISSING %s\n" % p); continue
    counts = collections.Counter()
    firstline = {}
    with open(p, encoding="utf-8", errors="replace") as f:
        for ln, line in enumerate(f, 1):
            for prop, pat in PATS:
                for m in pat.finditer(line):
                    v = (m.group(1) if pat.groups else m.group(0)).strip().strip('"\'')
                    v = re.sub(r'\s+', ' ', v)
                    if prop == "hex":
                        v = v.lower()
                    key = (prop, v)
                    counts[key] += 1
                    firstline.setdefault(key, ln)
            for m in FONT_SHORT.finditer(line):
                shorthand = re.sub(r'\s+', ' ', m.group(1)).strip()
                key = ("font-shorthand", shorthand)
                counts[key] += 1
                firstline.setdefault(key, ln)
    for (prop, val), n in counts.items():
        rows.append([repo, rel, firstline[(prop, val)], prop, val, n])

rows.sort(key=lambda r: (r[0], r[1], r[3], -r[5], r[4]))
out = "/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai-node/docs/design/audit/tokens.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["repo", "file", "line", "property", "value", "count"])
    w.writerows(rows)
print("rows:", len(rows), "->", out)
