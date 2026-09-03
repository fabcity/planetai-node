"""Offline sanity checks on init.sql and the Dockerfile. Not a Postgres parser — it catches the specific mistakes that have
actually bitten us: unbalanced parens (a comment inside an expression), and non-idempotent statements
(which break updating a running node, because init.sql is applied to live databases)."""
import re
import sys

sql = open("init.sql").read()
errs = []

for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
    code = re.sub(r"--.*$", "", stmt, flags=re.M)
    if code.count("(") != code.count(")"):
        errs.append(f"unbalanced parens (a comment inside an expression?): {stmt.splitlines()[0][:80]}")
    head = " ".join(code.split()[:3]).upper()
    up = code.upper()
    if head.startswith("CREATE TABLE") and "IF NOT EXISTS" not in up:
        errs.append(f"not idempotent: {head}")
    if head.startswith(("ALTER TABLE", "CREATE INDEX")) and "IF NOT EXISTS" not in up:
        errs.append(f"not idempotent: {head}")
    if head.startswith("CREATE VIEW"):
        name = code.split()[2]
        if f"DROP VIEW IF EXISTS {name}" not in sql:
            errs.append(f"view {name} has no preceding DROP VIEW IF EXISTS (CREATE OR REPLACE cannot reorder columns)")

for line in sql.splitlines():
    if "--" in line and re.search(r"\([^)]*--", line):
        errs.append(f"comment inside parentheses: {line.strip()[:80]}")

# the Dockerfile must not enumerate modules: a list goes stale the moment a module is added
dockerfile = open("app/Dockerfile").read()
for line in dockerfile.splitlines():
    if line.startswith("COPY") and line.endswith(("./", "/app/")) and ".py" in line and "*.py" not in line:
        errs.append(f"app/Dockerfile enumerates modules — use COPY *.py ./ : {line.strip()}")

print("\n".join(f"  x {e}" for e in errs) or "  init.sql + Dockerfile ok")
sys.exit(1 if errs else 0)
