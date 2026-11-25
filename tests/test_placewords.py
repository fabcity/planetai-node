"""app/placewords.py: what a node that is not a house calls itself.

A community or district node (NODE_KIND) rewrites the house words in its sentence templates, per language, before any
name is put in; a home, a business or a node that never said keeps every word. The words are Tomas's (25 Nov 2026,
specs/2026-11-25-community-words-and-child-kits-design.md).

    PYTHONPATH=app python3 tests/test_placewords.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
os.environ.pop("NODE_KIND", None)

import placewords as pw  # noqa: E402

fails = 0


def check(ok, msg):
    global fails
    print(("  ok  " if ok else "  FAIL ") + msg)
    fails += 0 if ok else 1


def kind(k):
    if k is None:
        os.environ.pop("NODE_KIND", None)
    else:
        os.environ["NODE_KIND"] = k


# ---- which kinds are a house
for k, house in ((None, True), ("", True), ("home", True), ("business", True), ("Home ", True),
                 ("community", False), ("district", False), ("Community", False)):
    kind(k)
    check(pw.is_house() is house, f"NODE_KIND={k!r} is {'a house' if house else 'not a house'}")
check(pw.is_house("community") is False and pw.is_house("home") is True, "is_house takes a kind directly too")
kind(None)
for k, own in ((None, "base"), ("home", "base"), ("business", "base"), ("community", "community"), ("district", "city")):
    check(pw.own_scale(k) == own, f"own_scale({k!r}) == {own!r}")

# ---- the approved rows, each language, a leading capital kept
ROWS = [
    ("en", "under this house's own heat line", "under the heat line set here"),
    ("en", "Somebody in the house has answered 3.", "Somebody here has answered 3."),
    ("en", "This house has 2 stations, and 4 within a kilometre.", "This node has 2 stations, and 4 within a kilometre."),
    ("en", "Fine dust in the house", "Fine dust indoors"),
    ("en", "the probes in this house", "the probes in this place"),
    ("en", "The house crossed the line earlier today.", "This place crossed the line earlier today."),
    ("id", "Rumah ini punya 2 stasiun.", "Tempat ini punya 2 stasiun."),
    ("id", "Seseorang di rumah telah menjawab 3.", "Seseorang di sini telah menjawab 3."),
    ("id", "debu di dalam rumah", "debu di dalam ruangan"),
    ("es", "Esta casa tiene 2 estaciones.", "Este lugar tiene 2 estaciones."),
    ("es", "Alguien en la casa ha respondido 3.", "Alguien aquí ha respondido 3."),
    ("es", "el polvo en la casa", "el polvo en este lugar"),
]
for loc, before, after in ROWS:
    got = pw.swap(before, loc)
    check(got == after, f"{loc}: {before!r} -> {after!r} (got {got!r})")

# ---- words that only contain the word are left alone
for loc, s in (("en", "Lighthouse Road"), ("en", "Warehouse 4"), ("en", "household"), ("es", "casada"),
               ("id", "perumahan")):
    check(pw.swap(s, loc) == s, f"{loc}: {s!r} is not touched")

# ---- swap_tree walks dicts and lists, keeps everything that is not a string
tree = {"a": "this house", "b": ["the house", 3, None], "c": {"d": "In the house"}}
out = pw.swap_tree(tree, "en")
check(out == {"a": "this place", "b": ["this place", 3, None], "c": {"d": "Indoors"}}, f"swap_tree: {out}")
check(tree["a"] == "this house", "swap_tree leaves its input as it was")

# ---- Localized: the house reads its templates as written; a place reads them swapped, and follows a change of kind
T = pw.Localized({"en": {"line": "this house's own heat line"}, "id": {"x": "rumah ini"}})
kind("home")
check(T["en"] == {"line": "this house's own heat line"}, "home: T['en'] as written")
kind("community")
check(T["en"] == {"line": "the heat line set here"}, "community: T['en'] swapped")
check(T.get("id") == {"x": "tempat ini"}, "community: T.get('id') swapped")
check(T.get("es", "none") == "none", "a missing language returns the default")
kind("home")
check(T["en"] == {"line": "this house's own heat line"}, "back to home: as written again (the cache keys on the kind)")
kind(None)

# ---- say: one string the code writes itself, as written on a house and swapped elsewhere
kind("home")
check(pw.say("the probes in this house") == "the probes in this house", "home: say() keeps the words")
kind("district")
check(pw.say("the probes in this house") == "the probes in this place", "district: say() swaps them")
check(pw.say("Esta casa", "es") == "Este lugar", "district: say() takes a language")
kind(None)

# ---- the sweep: every template the engine reads, the core's tables and every pack's sentences, per language
os.environ.setdefault("PACKS_DIR", str(ROOT / "packs"))
import re  # noqa: E402
import issues  # noqa: E402

HOUSE = {"en": re.compile(r"\bhouse\b", re.I), "id": re.compile(r"\brumah\b", re.I), "es": re.compile(r"\bcasa\b", re.I)}


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


TABLES = {n: getattr(issues, n) for n in
          ("WHERE_WORDS", "NOUN_WORDS", "LABEL_WORDS", "DIGEST_WORDS", "SIMPLE_WORDS", "REASON_WORDS")}
for name, t in TABLES.items():
    check(isinstance(t, pw.Localized), f"{name} is read through Localized")
    for loc in ("en", "id", "es"):
        kind("home")
        check(t.get(loc) == dict.get(t, loc), f"home: {name}.{loc} as written")
        kind("community")
        left = [s for s in strings(t.get(loc)) if HOUSE[loc].search(s)]
        check(not left, f"community: {name}.{loc} has no house word left {left[:2]}")


def per_language(o, path=""):
    """(path, language, string) for every string under a field written per language."""
    if isinstance(o, dict):
        if {"en", "id", "es"} <= set(o):
            for loc in ("en", "id", "es"):
                for s in strings(o[loc]):
                    yield path, loc, s
        for k, v in o.items():
            if k not in ("en", "id", "es"):
                yield from per_language(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from per_language(v, f"{path}[{i}]")


files = sorted((ROOT / "packs").glob("*/issue.yml")) + sorted((ROOT / "app/issues").glob("*.yml"))
check(len(files) >= 5, f"the sweep reads {len(files)} issue files")
for f in files:
    got = {}
    issues._read(f, f.stem if f.parent.name == "issues" else f.parent.name, got, pack=None)
    kind("home")
    check(issues.for_kind(got) is got, f"home: {f.parent.name}/{f.name} is given back as it was")
    kind("community")
    left = [(p, loc, s[:60]) for p, loc, s in per_language(issues.for_kind(got)) if HOUSE[loc].search(s)]
    check(not left, f"community: {f.parent.name}/{f.name} has no house word in any language {left[:2]}")
kind("community")
for loc in ("en", "id", "es"):
    for d in issues.DISTANCES:
        lab, noun = issues.LABEL_WORDS[loc][d], issues.NOUN_WORDS[loc][d]
        check(lab.lower() in noun.lower(), f"community: {loc} label {lab!r} is inside its noun {noun!r}")
kind(None)

print(f"\n{'FAILED' if fails else 'passed'}: placewords ({fails} failure{'s' if fails != 1 else ''})")
sys.exit(1 if fails else 0)
