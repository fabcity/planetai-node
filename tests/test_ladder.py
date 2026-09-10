"""The order of the model ladder, which decides whether household data leaves the network.

`strongest` sends every question to the online API when one is configured. `fallback` keeps it as the net under
this machine and the tailnet, used only when neither answers — what you want from a backup model. `private` drops
it entirely. A typo in AGENT_PREFER must not quietly behave like `strongest`, which is why settings.CHOICES pins
the three values; this test covers the ordering itself.
"""
import sys
import types

# agent_loop imports httpx and mcp for the parts this test does not touch. Stub them; the Makefile already does the
# same for httpx in the other suites.
for name, attrs in (("httpx", {"AsyncClient": object, "HTTPError": type("HTTPError", (Exception,), {})}),
                    ("mcp", {"ClientSession": object}),
                    ("mcp.client", {}),
                    ("mcp.client.streamable_http", {"streamable_http_client": lambda *a, **k: None})):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)

sys.path.insert(0, "app")
import agent_loop as A  # noqa: E402

BOTH = {"AGENT_ONLINE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
        "AGENT_ONLINE_KEY": "k", "AGENT_REMOTE_URL": "http://100.64.0.1:8082/v1"}


def names(**over):
    return [r.name for r in A.ladder({**BOTH, **over})]


assert names(AGENT_PREFER="strongest") == ["online", "remote", "local"], names(AGENT_PREFER="strongest")
# online ABOVE local: a rung is skipped only when it fails, and the 4B local model never fails, it answers
# badly — so online last meant a configured paid model was never reached while the tailnet box slept.
assert names(AGENT_PREFER="fallback") == ["remote", "online", "local"], names(AGENT_PREFER="fallback")
assert names(AGENT_PREFER="private") == ["remote", "local"], names(AGENT_PREFER="private")

# fallback with nothing online configured is just the local ladder, not an empty one
assert names(AGENT_PREFER="fallback", AGENT_ONLINE_KEY="") == ["remote", "local"]
# local is always last-resort present, even with nothing else set at all
assert [r.name for r in A.ladder({"AGENT_PREFER": "fallback"})] == ["local"]

# a URL that is not a URL is not a rung — node #1 held the text of .env.example's own comment here
assert "online" not in names(AGENT_PREFER="fallback", AGENT_ONLINE_URL="# https://api.anthropic.com/v1 or ..."), \
    "a non-URL must not become a rung that can only fail"
assert "remote" not in names(AGENT_PREFER="fallback", AGENT_REMOTE_URL="100.64.0.1:8082"), \
    "a host with no scheme is not a URL"

# the one setting where a typo must be refused rather than tolerated: not-"private" sends data off the network
sys.path.insert(0, "app")
import settings as S  # noqa: E402
assert S.CHOICES["AGENT_PREFER"] == ("strongest", "fallback", "private"), S.CHOICES.get("AGENT_PREFER")

print("the ladder: strongest online-first, fallback remote-online-local, private online-never, and a non-URL is not a rung")

# A key that ships blank must not carry a trailing comment. Compose's env_file strips an inline comment only when the
# key has a value: `KEY=    # note` hands the container "# note". Node #1 ran for weeks with the text of
# .env.example's own comment in AGENT_ONLINE_URL, and AGENT_REMOTE_URL shipped the same trap — a blank remote URL
# became a rung pointing at "# a bigger local model on your tailnet".
import re as _re
_env = open(".env.example").read()
_bad = _re.findall(r"^([A-Z_][A-Z0-9_]*)=[ \t]+#.*$", _env, _re.M)
assert not _bad, f"put the comment on its own line above these keys, not after them: {_bad}"

print(".env.example: no blank key carries a trailing comment compose would read as its value")
