"""The issue declarations: they validate, they cover every shipped pack, and a fifth one is one file.

  · the four shipped app/issues/*.yml validate, in all three locales
  · every enabled pack's domain reaches an issue, or is named here as deliberately not one
  · every alert rule a cross-domain pack ships is claimed by an issue, or named here
  · the line each issue names is the same number as the pack rule it points at
  · a synthetic water.yml loads and appears, with no code change anywhere
  · NODE_ISSUES parsing: unknown names dropped, empty falls back, duplicates collapse

Run: PACKS_DIR=packs PYTHONPATH=app python3 tests/test_issues.py
"""
import logging
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("PACKS_DIR", "packs")
sys.path.insert(0, str(ROOT / "app"))

import issues as I  # noqa: E402
import packs        # noqa: E402

# order() logs every dropped name, which is the point of it — but this test drops names on purpose
# seven times and the reasons belong in the assertions, not above them.
logging.getLogger("planetai.issues").setLevel(logging.ERROR)

fails = []
DECL = I.load()

# --- the four shipped files validate -------------------------------------------------------------
for want in ("air", "heat", "land", "coast"):
    if want not in DECL:
        raw = yaml.safe_load((ROOT / f"app/issues/{want}.yml").read_text()) or {}
        fails += [f"app/issues/{want}.yml: {b}" for b in I._problems(want, raw)] or \
                 [f"app/issues/{want}.yml does not load"]
shipped = {p.stem for p in (ROOT / "app/issues").glob("*.yml")}
for extra in shipped - set(DECL):
    fails.append(f"app/issues/{extra}.yml exists but did not validate")

# The validator has to actually refuse things, or "it validates" means nothing. Ten ways in.
BREAKS = {
    "no kind": lambda d: d.pop("kind"),
    "no compare mode": lambda d: d["compare"].pop("mode"),
    "verb with no verbs": lambda d: d["sentences"]["en"].pop("verbs"),
    "a where for a fifth distance": lambda d: d.__setitem__("where", {"en": {"street": "x"}}),
    "a fifth distance": lambda d: d["distances"].__setitem__("street", None),
    "an unfillable placeholder": lambda d: d["sentences"]["en"]["attribution"].__setitem__("clear", "{room} µg"),
    "a line with no source": lambda d: d["line"].pop("source"),
    "a rule id with no pack": lambda d: d["packs"]["rules"].append("digest"),
    "one locale missing": lambda d: d["sentences"].pop("id"),
    "apparent on one metric": lambda d: d["distances"]["room"].__setitem__("metrics", ["temp"]),
}
for name, break_it in BREAKS.items():
    d = yaml.safe_load((ROOT / "app/issues/air.yml").read_text())
    if name == "apparent on one metric":
        d["distances"]["room"]["function"] = "apparent"
    try:
        break_it(d)
    except Exception:                                   # a break that no longer applies to this file
        fails.append(f"the validator's own test case {name!r} could not be set up")
        continue
    if not I._problems("air", d):
        fails.append(f"the validator accepts a declaration with {name}")

# --- every pack reaches an issue, or is named as not one ------------------------------------------
# A pack domain that is deliberately outside the environmental picture. Weather feeds air and heat
# (wind for attribution, the forecast for the day ahead) but is not itself something a place is
# better or worse at; place is the ground everything sits on; governance is the loop and the Index.
NOT_ISSUES = {"weather", "place", "governance"}
# Alert rules from cross-domain packs, or from packs with no domain at all, that belong to no issue.
# trust is the node's own instruments: whether they are frozen, missing hours, or disagreeing.
UNMAPPED_RULES = {
    "trust/channel_dead", "trust/coverage_low", "trust/peer_disagreement",
}
claimed_domains = {dom for d in DECL.values() for dom in d["packs"]["domains"]}
claimed_rules = {r for d in DECL.values() for r in (d["packs"]["rules"] or [])}

manifests = {m["id"]: m for m in packs.manifests()}
if not manifests:
    fails.append("no packs loaded — run with PACKS_DIR=packs from the repo root")
for pid, m in manifests.items():
    dom = m.get("domain")
    if dom in claimed_domains or dom in NOT_ISSUES:
        continue
    # cross-domain, or a pack with no domain: every alert it ships must be claimed rule by rule
    for r in packs.alerts():
        if not r["id"].startswith(pid + "/"):
            continue
        if r["id"] not in claimed_rules and r["id"] not in UNMAPPED_RULES:
            fails.append(f"{r['id']} belongs to no issue. Add it to an issue's packs.rules, or to "
                         f"UNMAPPED_RULES in this test with the reason it is not an issue.")
for r in sorted(claimed_rules):
    if r not in {a["id"] for a in packs.alerts()}:
        fails.append(f"an issue claims {r}, which no enabled pack ships")
for dom in sorted(claimed_domains):
    if dom not in {m.get("domain") for m in manifests.values()}:
        fails.append(f"an issue claims the pack domain {dom!r}, which no enabled pack declares")

# --- the line is the pack's own number -----------------------------------------------------------
# No pack declares a threshold as data (`thresholds:` is prose in both pack.yaml files that have
# one), so each issue writes its line down and names the rule whose SQL carries the same number.
# This is the gate that keeps the two from drifting; it is why retyping the number is safe.
for key, d in DECL.items():
    line = d.get("line")
    if not line:
        continue
    ref = line.get("sql")
    if not ref:
        fails.append(f"{key}: line has no sql: pointer, so nothing holds it to the pack's own rule")
        continue
    pack, _, rule = ref.partition("/")
    hit = next((r for r in packs.rules() if r["id"] == ref), None)
    if not hit:
        fails.append(f"{key}: line.sql names {ref}, which is not a rule any enabled pack ships")
        continue
    n = line["value"]
    body = str(hit.get("sql", ""))
    if not re.search(rf"(?<![\d.]){re.escape(str(n))}(?![\d])", body):
        fails.append(f"{key}: the line is {n} but {ref}'s SQL does not contain that number. One of "
                     f"the two moved; they must say the same thing.")

# --- a fifth issue is a fifth file ---------------------------------------------------------------
WATER = {
    "name": {"en": "Water", "id": "Air bersih", "es": "Agua"},
    "kind": "sensed", "metric": "turbidity", "unit": "NTU", "dp": 1,
    "compare": {"mode": "ratio", "margin": 1.5},
    "line": {"value": 5, "unit": "NTU", "source": "WHO drinking-water guideline", "sql": None},
    "packs": {"domains": ["water"], "rules": []},
    "distances": {
        "room": {"from": "stats", "place": "room", "metrics": ["turbidity"], "field": "mean_15m",
                 "aggregate": "mean"},
        "yard": None, "ring": None,
        "region": None,
    },
    "sentences": {loc: {"attribution": {c: "{n} {unit} {where}. {cmp}" for c in I.CLASSES},
                        "state": {"none": "No water sensor here yet."}} for loc in I.LOCALES},
    "empty": {loc: "No water sensor here yet." for loc in I.LOCALES},
}
with tempfile.TemporaryDirectory() as tmp:
    for f in (ROOT / "app/issues").glob("*.yml"):
        shutil.copy(f, tmp)
    (Path(tmp) / "water.yml").write_text(yaml.safe_dump(WATER, allow_unicode=True))
    five = I.load(tmp)
    if "water" not in five:
        fails.append("a synthetic water.yml did not load — adding an issue is not one file after all")
    elif five["water"]["name"]["en"] != "Water":
        fails.append("water.yml loaded but its name did not survive")
    if len(five) != len(DECL) + 1:
        fails.append(f"loading five files gave {len(five)} issues")
    got, dropped = I.order("air,water,heat", five)
    if got != ["air", "water", "heat"]:
        fails.append(f"NODE_ISSUES=air,water,heat gave {got} — a new issue must be orderable at once")
    if dropped:
        fails.append(f"nothing should have been dropped, but {dropped} was")

# --- NODE_ISSUES parsing -------------------------------------------------------------------------
for declared, want_order, want_dropped in [
    ("air,heat,land,coast", ["air", "heat", "land", "coast"], []),
    ("heat,air", ["heat", "air"], []),
    (" heat , air ", ["heat", "air"], []),                       # a keeper's spaces
    ("air,watar,heat", ["air", "heat"], ["watar"]),              # a typo is dropped, never fatal
    ("air,air,heat", ["air", "heat"], []),                       # said twice, drawn once
    ("", sorted(DECL), []),                                       # empty falls back to the files' order
    ("watar", sorted(DECL), ["watar"]),                           # every name unknown: still a page
]:
    got, dropped = I.order(declared, DECL)
    if got != want_order:
        fails.append(f"NODE_ISSUES={declared!r} ordered {got}, expected {want_order}")
    if dropped != want_dropped:
        fails.append(f"NODE_ISSUES={declared!r} dropped {dropped}, expected {want_dropped}")

print("\n".join(f"  x {f}" for f in fails) or
      f"  issues: {len(DECL)} declarations validate in {len(I.LOCALES)} locales; "
      f"{len(manifests)} packs all reach an issue or are named as not one; every line matches its "
      f"pack's SQL; a fifth issue is one file")
sys.exit(1 if fails else 0)
