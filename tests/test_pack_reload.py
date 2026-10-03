"""Adapters keep pacing state in module globals, so one module must serve every poll. It used to be executed afresh
each time, which made the NEA pack ask for its first four feeds on every poll and never reach wind or rain."""
import pathlib, sys, tempfile
sys.path.insert(0, "app")
import packs as P

P._loaded.clear()
with tempfile.TemporaryDirectory() as t:
    d = pathlib.Path(t) / "x"; d.mkdir()
    f = d / "adapter.py"
    f.write_text("calls = []\ndef fetch(hc):\n    calls.append(1)\n    return [], []\n")
    P._enabled = lambda: [d]; P._allow_code = lambda: True
    for _ in range(2):
        for _, fn in P.adapters(None):
            fn()
    assert len(P._loaded["x"][1].calls) == 2, "adapter state was reset between polls"
    # an edited adapter is picked up
    import os, time
    f.write_text("calls = []\ndef fetch(hc):\n    return [], []\n")
    os.utime(f, (time.time() + 5, time.time() + 5))
    list(P.adapters(None))
    assert P._loaded["x"][1].calls == []
print("pack reload: ok")
