"""run_rules in ALERT_ENGINE=rules and shadow, without importing app main (importing it starts a second MQTT client).
Parses app/main.py, takes run_rules' source, execs it against fakes. 'events' and a typo must behave as rules.
Run: python3 tests/test_run_rules_modes.py
"""
import ast
import contextlib
import pathlib

src = pathlib.Path(__file__).resolve().parent.parent / "app" / "main.py"
tree = ast.parse(src.read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_rules")
code = compile(ast.Module(body=[fn], type_ignores=[]), "run_rules", "exec")

OLD = {"id": "old", "sql": "OLD_SQL", "message": "old {x}", "level": "act"}
KINDED = {"id": "kinded", "sql": "KINDED_SQL", "message": "k", "level": "act", "kind": "sustained"}


def run(mode):
    sqls, notified, ran = [], [], []

    class Cur:
        def execute(self, sql, *a):
            sqls.append(sql)

        def fetchone(self):
            return {"id": 1} if sqls[-1].startswith("INSERT") else None

    class Con:
        def cursor(self):
            return contextlib.nullcontext(Cur())

    @contextlib.contextmanager
    def db():
        yield Con()

    class NS:
        pass

    packs, index, events_pg, settings, log = NS(), NS(), NS(), NS(), NS()
    packs.load_rules = lambda: [OLD, KINDED]
    index.run_ro = lambda cur, sql: (sqls.append(sql), [{"sensor_id": "s", "x": 1}])[1]
    events_pg.candidates = lambda rule, rows: ["cand"]
    events_pg.run = lambda cur, cands, m, now: ran.append((cands, m))
    settings.get = lambda k, d=None: mode if k == "ALERT_ENGINE" else d
    log.warning = log.info = lambda *a: None
    g = dict(packs=packs, index=index, events_pg=events_pg, settings=settings, log=log, db=db,
             notify=lambda lvl, text: notified.append(text), ha_alert=lambda *a: None,
             run_report=lambda cur: None, _quiet=lambda lvl: False, LOCALE=lambda: "en", _local_now=lambda: "now")
    exec(code, g)
    g["run_rules"]()
    return sqls, notified, ran


for mode in ("rules", "events", "typo", "", None):
    sqls, notified, ran = run(mode)
    assert "KINDED_SQL" not in sqls, (mode, "a kinded rule's SQL ran")
    assert not ran, (mode, "event engine ran")
    assert notified == ["old 1"], (mode, notified)
print("  rules (and 'events', a typo, empty): kinded rules never run their SQL, no event engine, old rule sent once")

sqls, notified, ran = run("shadow")
assert "KINDED_SQL" in sqls and "OLD_SQL" in sqls
assert notified == ["old 1"], notified
assert sum(s.startswith("INSERT") for s in sqls) == 1, "only the old rule writes an alerts row"
assert ran == [(["cand"], "shadow")], ran
print("  shadow: kinded rule runs, writes no alerts row, sends nothing; engine called once in shadow; old rule still sent")
