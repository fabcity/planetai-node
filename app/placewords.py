"""What a node that is not a house calls itself.

Every sentence the node writes was written for a house: "under this house's own heat line", "Somebody in the house has
answered". A community or district node (NODE_KIND) is not one, and its Wall and weekly report may face the public, so
its templates have the house words swapped, per language, before any sensor, station or place name is put in: names
are never touched. A home, a business or a node that never said reads every word as written. The words are Tomas's
(25 Nov 2026, planetai-design specs/2026-11-25-community-words-and-child-kits-design.md).

NODE_KIND and not NODE_SCALE: the scale is the Full Stack Metrics territory and defaults to `community` on every node,
houses included; the kind is what the node is for and defaults to `home`.
"""
from __future__ import annotations

import os
import re

HOUSE_KINDS = {"", "home", "business"}
PLACE_KINDS = {"community", "district"}
_OWN = {"community": "community", "district": "city"}     # the Wall's size for a kind; everything else is base

# Longest first: a row only ever sees text the rows above it left. Whole words, so "household", "Lighthouse",
# "casada" and "perumahan" stay as they are. A leading capital in the text is kept on the replacement.
SWAPS = {
    "en": [("this house's own heat line", "the heat line set here"),
           ("this house's heat line", "the heat line set here"),
           ("somebody in the house", "somebody here"),
           ("this house has", "this node has"),
           ("nothing in the house", "nothing here"),   # the node measures nothing of it, indoors or out
           ("in the house", "indoors"),
           ("this house's", "this place's"),
           ("the house's", "this place's"),
           ("this house", "this place"),
           ("the house", "this place")],
    "id": [("seseorang di rumah", "seseorang di sini"),
           ("di dalam rumah", "di dalam ruangan"),
           ("rumah ini", "tempat ini"),
           ("di rumah", "di sini"),                # "at home" in a sentence: here
           ("rumah", "tempat ini")],               # the noun alone; guarded against compounds (_GUARD)
    "es": [("alguien en la casa", "alguien aquí"),
           ("dentro de casa", "en el interior"),   # the indoor distance; not in the approved table, listed for Tomas
           ("en casa", "aquí"),                    # "En casa está…": a bare "lugar" would read "instead"
           ("esta casa", "este lugar"),
           ("la casa", "este lugar")],
}
# The distance labels (LABEL_WORDS) are one word each, so they take the bare word, and only they do: in a sentence a
# bare "casa" or "rumah" would turn "fuera de casa" into "fuera de lugar" and "rumah sakit" into "tempat ini sakit".
LABEL_SWAPS = {"en": [("house", "place")], "es": [("casa", "lugar")]}
# Indonesian "rumah" is a plain noun in every template ("Rumah menahan debu", "rumah juga"), so its bare row is a
# sentence row, kept off the compounds where it is not a house: rumah sakit, rumah tangga, rumah makan…
_GUARD = {("id", "rumah"): r"(?!\s+(?:sakit|tangga|makan|susun|adat|ibadah)\b)"}
def _compile(table):
    return {loc: [(re.compile(r"\b" + re.escape(old) + r"\b" + _GUARD.get((loc, old), ""), re.IGNORECASE), new)
                  for old, new in rows] for loc, rows in table.items()}


_RX, _RX_LABELS = _compile(SWAPS), _compile(LABEL_SWAPS)


def kind() -> str:
    """NODE_KIND as the node holds it: a settings row first, then the environment. Lowercase, stripped."""
    try:
        import settings
        k = settings.get("NODE_KIND", "")
    except Exception:  # noqa: BLE001 — a validator or a test without the app's settings
        k = os.getenv("NODE_KIND", "")
    return (k or "").strip().lower()


def is_house(k: str | None = None) -> bool:
    """True unless the node says it is a community or a district."""
    return (kind() if k is None else (k or "").strip().lower()) not in PLACE_KINDS


def own_scale(k: str | None = None) -> str:
    """The Wall's size this node is: community, city (a district), or base."""
    return _OWN.get(kind() if k is None else (k or "").strip().lower(), "base")


def swap(text: str, loc: str, labels: bool = False) -> str:
    """`text` with the house words of language `loc` replaced; unchanged for a language with no rows. `labels` adds the
    bare words, for the one-word distance labels only."""
    for rx, new in [*_RX.get(loc, ()), *(_RX_LABELS.get(loc, ()) if labels else ())]:
        text = rx.sub(lambda m, new=new: new[:1].upper() + new[1:] if m.group(0)[:1].isupper() else new, text)
    return text


def say(text: str, loc: str = "en") -> str:
    """One string the code writes itself (not a template table): as written on a house, swapped elsewhere."""
    return text if is_house() else swap(text, loc)


def swap_tree(obj, loc: str, labels: bool = False):
    """A new copy of `obj` with every string swapped; dicts and lists walked, anything else kept."""
    if isinstance(obj, str):
        return swap(obj, loc, labels)
    if isinstance(obj, dict):
        return {k: swap_tree(v, loc, labels) for k, v in obj.items()}
    if isinstance(obj, list):
        return [swap_tree(v, loc, labels) for v in obj]
    return obj


class Localized(dict):
    """A table keyed by language. `t[loc]` and `t.get(loc)` give the language's templates as written on a house, and
    swapped on a community or district node, worked out once per language and kind and kept on the table itself (a
    change of NODE_KIND takes effect on the next read, without a restart). Iterating the table gives what was written:
    read a language through `[loc]` or `.get(loc)`."""

    labels = False      # True on the distance labels' table (issues.LABEL_WORDS): the bare words apply there too

    def __getitem__(self, loc):
        value = dict.__getitem__(self, loc)
        k = kind()
        if is_house(k):
            return value
        memo = self.__dict__.setdefault("_swapped", {})
        if (loc, k) not in memo:
            memo[(loc, k)] = swap_tree(value, loc, self.labels)
        return memo[(loc, k)]

    def get(self, loc, default=None):
        return self[loc] if dict.__contains__(self, loc) else default
