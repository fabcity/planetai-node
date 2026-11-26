"""On Reticulum an act alert ends with the answers it takes (app/channels.py reticulum_answers), in the event buttons'
words, so someone in Sideband can answer it: done or not now for an alert, and doesn't fit too for an event, whose
number starts with e. Reticulum has no buttons, and real alerts have carried no number since v0.39. A community node's
alerts carry no line (Tomas, 26 Nov 2026: "No act, feeds only"). The bridge reads these words back
(fabcity/planetai-reticulum). channels.httpx.post is a fake. Run: PYTHONPATH=app python3 tests/test_reticulum_answers.py
"""
import logging
import os

import httpx

import channels

sent = []
channels.RETICULUM_URL = "http://reticulum:4243"
channels.RETICULUM_TO = lambda: ["aa11"]
channels.mesh_send = lambda text: None
channels.TG = lambda: ("tok", ["1"])


channels.log.setLevel(logging.WARNING)


def post(url, json, timeout):
    sent.append((url, dict(json)))
    return httpx.Response(200, request=httpx.Request("POST", url))


channels.httpx.post = post


def lxmf(level, text, answer, kind="", locale=""):
    """What notify() hands the bridge, and what it hands Telegram, for one alert on a node of `kind`."""
    os.environ["NODE_KIND"], os.environ["ALERT_LOCALE"] = kind, locale
    sent.clear()
    channels.notify(level, text, answer=answer)
    to_bridge = [j["text"] for u, j in sent if u.endswith("/send")]
    to_telegram = [j["text"] for u, j in sent if "telegram" in u]
    return to_bridge, to_telegram


r, tg = lxmf("act", "Hot in the Living Room.", "45")
assert r == ["Hot in the Living Room.\n\n↩ done 45 · not now 45"], r
assert tg and "↩" not in tg[0], "Telegram has its buttons; the line is Reticulum's only"
print("  an alert on Reticulum ends with done and not now, and its id")

r, _ = lxmf("act", "Hot in the Living Room.", "e7")
assert r == ["Hot in the Living Room.\n\n↩ done e7 · not now e7 · doesn't fit e7"], r
print("  an event's ends with the three answers, e and its id")

r, _ = lxmf("act", "Panas.", "e7", locale="id")
assert r == ["Panas.\n\n↩ selesai e7 · nanti dulu e7 · tidak cocok e7"], r
r, _ = lxmf("act", "Calor.", "45", kind="business", locale="es")
assert r == ["Calor.\n\n↩ hecho 45 · ahora no 45"], r
print("  in the node's language, on any private node")

for kind in ("community", "district", " Community "):
    r, _ = lxmf("act", "Smoke near Jimbaran.", "e7", kind=kind)
    assert r == ["Smoke near Jimbaran."], (kind, r)
print("  a community or district node's alerts carry no answers")

r, _ = lxmf("act", "Test.", "")
assert r == ["Test."], r
r, _ = lxmf("warn", "Windy.", "45")
assert r == [], "Reticulum gets act-level alerts only"
print("  no answer named, no line; below act, nothing goes to Reticulum")
