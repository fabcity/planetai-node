"""Validate every rule and Index cell against the schema in init.sql, without a database.

Catches the failures that are silent at runtime:
  · SQL referencing a column a view does not have  -> the rule is logged as failed and skipped, forever
  · a message placeholder the SQL never returns    -> main.py falls back to printing the raw template with braces
  · a cell whose SQL has no `value` column         -> the cell is silently never emitted
  · a rule with a cooldown so long it can only fire once  -> looks like "nothing works" (this bit test-alert)

Needs sqlglot (dev only; CI installs it). Run: python3 tools/check_rules.py
"""
import glob
import re
import sys

import sqlglot
import yaml
from sqlglot import exp

SQL = open("init.sql").read()
errs, checked = [], 0


def schema() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for st in sqlglot.parse(SQL, read="postgres"):
        if not isinstance(st, exp.Create):
            continue
        name = getattr(getattr(st.this, "this", None), "name", None)
        if not name:
            continue
        if st.kind == "TABLE":
            out[name] = {c.name for c in st.find_all(exp.ColumnDef)}
        elif st.kind == "VIEW":
            out[name] = {e.alias_or_name for e in getattr(st.expression, "expressions", [])}
    for m in re.finditer(r"ALTER TABLE (\w+) ADD COLUMN IF NOT EXISTS (\w+)", SQL):
        out.setdefault(m.group(1), set()).add(m.group(2))
    return out


S = schema()
# columns Postgres provides that are not in any table
FREE = {"now", "current_setting", "value", "count", "avg", "sum", "min", "max", "round", "extract"}


def check_sql(where: str, query: str) -> set[str]:
    """Returns the query's output column names. Appends any unknown-column errors."""
    try:
        tree = sqlglot.parse_one(query, read="postgres")
    except Exception as e:  # noqa: BLE001
        errs.append(f"{where}: SQL does not parse ({e})")
        return set()

    # which real tables/views this query reads, and the aliases pointing at them
    alias_of: dict[str, str] = {}
    used: set[str] = set()
    for t in tree.find_all(exp.Table):
        if t.name in S:
            used.add(t.name)
            alias_of[t.alias or t.name] = t.name
        elif t.name not in {c.alias for c in tree.find_all(exp.CTE)}:
            errs.append(f"{where}: reads unknown table/view `{t.name}`")

    known = set().union(*(S[t] for t in used)) if used else set()
    # a CTE body can be a UNION, whose own .expressions is not the select list — walk to the first SELECT
    cte_cols = set()
    for c in tree.find_all(exp.CTE):
        sel = c.this if isinstance(c.this, exp.Select) else c.this.find(exp.Select)
        cte_cols |= {a.alias_or_name for a in getattr(sel, "expressions", [])}
    for col in tree.find_all(exp.Column):
        if col.table and col.table in alias_of:
            if col.name not in S[alias_of[col.table]]:
                errs.append(f"{where}: `{col.table}.{col.name}` is not a column of `{alias_of[col.table]}`")
        elif col.name not in known and col.name not in cte_cols and col.name not in FREE:
            errs.append(f"{where}: column `{col.name}` is in none of {sorted(used) or ['(no table)']}")

    top = tree.find(exp.Select)
    return {e.alias_or_name for e in top.expressions} if top else set()


for f in sorted(glob.glob("config/rules.yml") + glob.glob("packs/*/rules.yml")):
    for r in yaml.safe_load(open(f)) or []:
        checked += 1
        where = f"{f}:{r.get('id')}"
        outs = check_sql(where, r["sql"])
        cd = r.get("cooldown_minutes", 60)
        if cd > 20160:      # a fortnight
            errs.append(f"{where}: cooldown {cd} min is over a fortnight — it can fire about once. Deliberate?")
        msg = r.get("message")
        for lang, tmpl in (msg.items() if isinstance(msg, dict) else [("", msg)]):
            for ph in re.findall(r"\{(\w+)", str(tmpl)):
                if ph not in outs:
                    errs.append(f"{where} [{lang}]: message wants {{{ph}}} but the SQL returns {sorted(outs)}")

for f in sorted(glob.glob("packs/*/cells.yml")):
    for c in yaml.safe_load(open(f)) or []:
        checked += 1
        where = f"{f}:{c.get('cell')}"
        outs = check_sql(where, c["sql"])
        if "value" not in outs:
            errs.append(f"{where}: SQL must return a column named `value`, returns {sorted(outs)}")

print("\n".join(f"  x {e}" for e in errs) or f"  {checked} rules and cells check out against init.sql")
sys.exit(1 if errs else 0)
