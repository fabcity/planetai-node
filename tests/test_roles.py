"""The node's role is a bootstrap key: fixed at install, read at start, never a settings row.

    PYTHONPATH=app python3 tests/test_roles.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
os.environ.pop("NODE_KIND", None)

import placewords  # noqa: E402
import settings  # noqa: E402

# the four kinds fold to two roles
for k, want in [("home", "private"), ("business", "private"), ("", "private"),
                ("community", "community"), ("district", "community"), (" Community ", "community")]:
    assert placewords.role(k) == want, (k, placewords.role(k))
os.environ["NODE_KIND"] = "district"
assert placewords.role() == "community" and not placewords.is_house()
os.environ["NODE_KIND"] = "home"
assert placewords.role() == "private" and placewords.is_house()

# NODE_KIND is a bootstrap key, not a runtime one
assert "NODE_KIND" not in settings.RUNTIME
assert not settings.writable("NODE_KIND")
assert settings.BOOTSTRAP_GROUP["NODE_KIND"] == "basics"
os.environ["NODE_KIND"] = "community"
row = next(r for r in settings.describe(unlocked=False)["bootstrap"] if r["key"] == "NODE_KIND")
assert "planetai role private" in row["help"] and "Community node" in row["help"], row

# a stale settings row never wins over the environment
real = settings.get
settings.get = lambda k, d="": "home"
try:
    assert placewords.kind() == "community"
finally:
    settings.get = real

# update moves a stray row into .env and deletes it
src = (ROOT / "update.sh").read_text()
assert "NODE_KIND" in src and "DELETE FROM settings WHERE key = 'NODE_KIND'" in src
print("ok  roles")
