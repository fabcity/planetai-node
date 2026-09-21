"""Issues — what a place can be better or worse at, that a household recognises by name.

The core measures nothing in particular (docs/DOMAINS.md, first line). The dashboard was the one
component that did: it knew the word `pm25`, it knew WHO 15, and it worked out for itself which
sensor was "the room". This package is where that knowledge moves, so the page can go back to
drawing.

One `.yml` per issue, in this directory. Each declares its name in three languages, whether it is
sensed or context, its metric and unit, its line, which packs feed it, how each of the four
distances is computed, its sentence templates, and what to say with no source. **Adding a fifth
issue is a fifth `.yml` plus a pack that declares its domain, and nothing else changes** —
`tests/test_issues.py` asserts exactly that by loading a synthetic `water.yml`.

Loading is as dumb as `app/packs.py`: read the directory, parse the YAML, validate, log and skip
anything broken. A malformed file must not take the node down; `make lint` is where a broken file in
this repo gets caught.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

log = logging.getLogger("planetai.issues")
HERE = Path(__file__).resolve().parent

LOCALES = ("en", "id", "es")
KINDS = ("sensed", "context")

# The four distances, in order. From schema.py so there is one list, not two.
from .schema import DISTANCES  # noqa: E402  (kept here so `issues.DISTANCES` reads naturally)

# The attribution classifier's classes. A sensed issue needs a sentence for every one of them,
# because the classifier will hand it any of them and a missing template is a `{brace}` on a wall.
CLASSES = ("clear", "inside", "everywhere", "outside_worse", "mixed", "unknown")

# The five states. `act` · `notable` · `quiet` are said with the attribution sentence; `context` and
# `none` have nothing to attribute, so they are said with their own.
STATE_SENTENCES = ("context", "none")

# Everything a template may ask for, and nothing else. The engine fills all five; a template using
# a name that is not here would render a literal brace to somebody's kitchen wall.
# `span` and `since` are the land record's own history: "between 2024 and 2025", "8.5 % since 2017".
# They fill from the earth cell's `extra` and are empty for every other issue, so a template that
# names them on an issue that cannot fill them renders a clean sentence rather than a brace.
PLACEHOLDERS = ("verb", "n", "unit", "where", "cmp", "span", "since")

WHERE_FROM = ("stats", "observations", "earth")
AGGREGATES = ("mean", "median", "fenced_median")
FUNCTIONS = ("apparent",)
COMPARE_MODES = ("ratio", "difference")
TRENDS = ("rising", "steady", "falling")

# The words shared by every issue, so four files do not carry four copies of "the street". An issue
# overrides one of these with its own `where:` block — land and coast both rename `region`, because
# "over this square of the map" is not where a wave is.
WHERE_WORDS = {
    "en": {"room": "in the room", "yard": "on the wall outside", "ring": "on the street",
           "region": "over this square of the map"},
    "id": {"room": "di dalam ruangan", "yard": "di dinding luar", "ring": "di jalan",
           "region": "di atas kotak peta ini"},
    "es": {"room": "en la habitación", "yard": "en la pared de fuera", "ring": "en la calle",
           "region": "sobre este cuadrado del mapa"},
}
# The same four places as things a number can be compared WITH, which is a different phrase in every
# language and in English too: "over on the street" is not a sentence.
NOUN_WORDS = {
    "en": {"room": "the room", "yard": "the wall outside", "ring": "the street", "region": "the model"},
    "id": {"room": "ruangan", "yard": "dinding luar", "ring": "jalan", "region": "model"},
    # Spanish contracts de + el into del, so "por encima de el modelo" is wrong and every other
    # phrasing that fixes it breaks one of the three templates. "lo que dice el modelo" works in all
    # three and reads better than any of them.
    "es": {"room": "la habitación", "yard": "la pared de fuera", "ring": "la calle",
           "region": "lo que dice el modelo"},
}
# The four distances as column headings: short, and the same four words wherever they appear.
#
# CHANGED 21 September 2026, and it reverses half of Decision 6. That decision gave English the
# system's own words — room, yard, ring, region — and the other two languages the household's, and
# the result was a page that labelled a column `YARD` above a sentence reading "on the wall
# outside". Two vocabularies for one place, on one screen, in the one language that had them.
# These are now the sentence's nouns in all three, so a heading and the line under it name the same
# thing. `yard` was the worst of them: nothing at node #1 is a yard, it is a wall.
#
# The API KEYS do not change. `room/yard/ring/region` are what `/issues.distances` publishes, what
# every issue's `stack` is keyed on and what a pack's `where:` block overrides; renaming those would
# be a wire break for a wording problem. Only the words a person reads change.
LABEL_WORDS = {
    "en": {"room": "room", "yard": "wall outside", "ring": "street", "region": "model"},
    "id": {"room": "ruangan", "yard": "dinding luar", "ring": "jalan", "region": "model"},
    # NOUN_WORDS' Spanish for `region` is a clause — "lo que dice el modelo" — because the sentence
    # templates need one. A column heading is not a sentence, so it takes the noun out of it.
    "es": {"room": "habitación", "yard": "pared de fuera", "ring": "calle", "region": "modelo"},
}
# {cmp} is assembled from these. Never a bare number: a comparison a household can read.
# "a, b and c". The list separator the sentences use when one comparison covers several distances.
JOIN_WORDS = {"en": "and", "id": "dan", "es": "y"}
CMP_WORDS = {
    "en": {"over": "over {noun}", "under": "under {noun}", "level": "level with {noun}"},
    "id": {"over": "di atas {noun}", "under": "di bawah {noun}", "level": "setara dengan {noun}"},
    "es": {"over": "por encima de {noun}", "under": "por debajo de {noun}", "level": "igual que {noun}"},
}
# Why an issue is in the state it is in. The engine returns the code and the rendered line, so the
# page draws a kicker without owning any of these words. Eight codes, three locales, one table.
# How the land record says when. `between` takes the two years of the latest comparison; `since`
# takes the longest span the pack computed and its figure, and carries its own full stop because the
# template puts it between two sentences and it is often absent.
SPAN_WORDS = {
    "en": {"between": "between {a} and {b}", "since": "{pct} % since {year}."},
    "id": {"between": "antara {a} dan {b}", "since": "{pct} % sejak {year}."},
    "es": {"between": "entre {a} y {b}", "since": "{pct} % desde {year}."},
}
# Simple mode's whole answer: one sentence per stage, written HERE and never in the browser. A
# sentence about what was observed is a claim about the data, and the page draws what the node
# computes. Four sentences, three languages, and every figure in them is already in the bundle.
#
# `measure` deliberately does not report rho. rho is specified in docs/SPEC_rho.md over its own
# window and computed by app/index.py from a query this engine cannot make — `Replay` answers five
# table reads and no more, so a fixture could not render it. A second rho computed from a different
# window would be a second rho, and two of them disagreeing on one page is worse than one of them
# being absent. This sentence reports the ledger the Act stage draws, and says that is what it is.
DIGEST_WORDS = {
    "en": {
        "observe": "{issues} issues watched here, read from {stations} stations. "
                   "{headline} has the most to say: it is {phrase}.",
        "observe_none": "{issues} issues watched here, and no station is reading any of them.",
        "decide": "At resolution {res} one cell is {area} m\u00b2, and this node's {stations} stations "
                  "fall in {occupied} of them \u2014 {mine} in its own cell. The node says where it is "
                  "to about {metres} m, and {leave}.",
        "act": "{open} asks are open, {top} of them about {issue}. "
               "Somebody in the house has answered {answered}.",
        "act_none": "Nothing is open. Somebody in the house has answered {answered}.",
        "measure": "Of the {acts} alerts here that asked for something, {answered} have been "
                   "answered, and the usual wait was {median} minutes.",
        "measure_none": "Of the {acts} alerts here that asked for something, none have been "
                        "answered yet.",
        "measure_empty": "Nothing here has asked anybody to do anything.",
        "stays": "nothing at this grain leaves the machine",
        "leaves": "this grain may leave the machine",
        "state": {"act": "over the line and asking for something", "notable": "worth a look",
                  "quiet": "quiet", "context": "context, and it never asks",
                  "none": "reading nothing"},
    },
    "id": {
        "observe": "{issues} isu dipantau di sini, dibaca dari {stations} stasiun. "
                   "{headline} paling banyak bicara: {phrase}.",
        "observe_none": "{issues} isu dipantau di sini, dan tidak ada stasiun yang membacanya.",
        "decide": "Pada resolusi {res} satu sel seluas {area} m\u00b2, dan {stations} stasiun node ini "
                  "jatuh di {occupied} di antaranya \u2014 {mine} di selnya sendiri. Node menyebut "
                  "posisinya sampai sekitar {metres} m, dan {leave}.",
        "act": "{open} permintaan terbuka, {top} di antaranya tentang {issue}. "
               "Seseorang di rumah telah menjawab {answered}.",
        "act_none": "Tidak ada yang terbuka. Seseorang di rumah telah menjawab {answered}.",
        "measure": "Dari {acts} peringatan di sini yang meminta sesuatu, {answered} telah dijawab, "
                   "dan waktu tunggu biasanya {median} menit.",
        "measure_none": "Dari {acts} peringatan di sini yang meminta sesuatu, belum ada yang "
                        "dijawab.",
        "measure_empty": "Tidak ada di sini yang meminta siapa pun melakukan sesuatu.",
        "stays": "tidak ada pada perincian ini yang keluar dari mesin",
        "leaves": "perincian ini boleh keluar dari mesin",
        "state": {"act": "di atas garis dan meminta sesuatu", "notable": "layak dilihat",
                  "quiet": "tenang", "context": "konteks, dan tidak pernah meminta",
                  "none": "tidak membaca apa pun"},
    },
    "es": {
        "observe": "{issues} asuntos vigilados aqu\u00ed, le\u00eddos desde {stations} estaciones. "
                   "{headline} es el que m\u00e1s dice: {phrase}.",
        "observe_none": "{issues} asuntos vigilados aqu\u00ed, y ninguna estaci\u00f3n lee ninguno.",
        "decide": "En la resoluci\u00f3n {res} una celda son {area} m\u00b2, y las {stations} estaciones "
                  "de este nodo caen en {occupied} de ellas \u2014 {mine} en la suya propia. El nodo "
                  "dice d\u00f3nde est\u00e1 con unos {metres} m, y {leave}.",
        "act": "{open} peticiones abiertas, {top} de ellas sobre {issue}. "
               "Alguien en la casa ha respondido {answered}.",
        "act_none": "No hay nada abierto. Alguien en la casa ha respondido {answered}.",
        "measure": "De las {acts} alertas de aqu\u00ed que ped\u00edan algo, {answered} han sido "
                   "respondidas, y la espera habitual fue de {median} minutos.",
        "measure_none": "De las {acts} alertas de aqu\u00ed que ped\u00edan algo, ninguna ha sido "
                        "respondida todav\u00eda.",
        "measure_empty": "Nada de aqu\u00ed ha pedido a nadie que haga nada.",
        "stays": "nada de este grano sale de la m\u00e1quina",
        "leaves": "este grano puede salir de la m\u00e1quina",
        "state": {"act": "por encima de la l\u00ednea y pide algo", "notable": "merece una mirada",
                  "quiet": "tranquilo", "context": "contexto, y nunca pide nada",
                  "none": "no lee nada"},
    },
}
# Why THIS issue is at the top, in the household's language. The node ranks them, so the node says
# how — a page that keeps its own copy of the rule goes stale the moment the ranking changes, which
# is not hypothetical: v0.59 changed it on 18 September and the sentence describing it lived in
# dashboard.js, where nothing connected the two. A ranking a reader cannot check is the one thing
# this page does not do, so the explanation travels with the ranking.
HEADLINE_RULE = {
    "en": "The issue with most to say leads \u2014 and where two have as much to say, the one that has "
          "moved most in the last three hours. An even tie goes to the order this place chose, under "
          "Set up \u2192 Issues.",
    "id": "Isu yang paling banyak bicara memimpin \u2014 dan bila dua sama banyaknya, yang paling berubah "
          "dalam tiga jam terakhir. Bila tetap seri, urutannya mengikuti pilihan tempat ini, di "
          "Set up \u2192 Issues.",
    "es": "Lidera el asunto que m\u00e1s tiene que decir \u2014 y si dos dicen otro tanto, el que m\u00e1s se ha "
          "movido en las \u00faltimas tres horas. Si hay empate exacto, manda el orden que eligi\u00f3 este "
          "lugar, en Set up \u2192 Issues.",
}
REASON_WORDS = {
    "en": {
        "open_ask_current": "asked at {when}, and still true",
        "open_ask_stale":   "asked at {when}; the reading came back on its own, the ask is still open",
        "alert_today":      "a {level} at {when}, over now",
        "over_line":        "over the line, and nobody has been asked to do anything",
        "over_line_peak":   "over the line since the day's high of {peak} at {peak_at}, and nobody has been asked to do anything",
        "no_alert":         "quiet",
        "no_alert_peak":    "quiet; the day's high was {peak} at {peak_at}",
        "context_only":     "it informs, it never asks",
        "ask_how":          "Reply /act {id} on Telegram and say what you did.",
        "not_watched":      "not watched here",
        "no_source":        "no source",
    },
    "id": {
        "open_ask_current": "diminta pada {when}, dan masih berlaku",
        "open_ask_stale":   "diminta pada {when}; bacaannya sudah kembali sendiri, permintaannya masih terbuka",
        "alert_today":      "{level} pada {when}, sudah lewat",
        "over_line":        "di atas batas, dan belum ada yang diminta melakukan apa pun",
        "over_line_peak":   "di atas batas sejak puncak hari ini {peak} pada {peak_at}, dan belum ada yang diminta melakukan apa pun",
        "no_alert":         "tenang",
        "no_alert_peak":    "tenang; puncak hari ini {peak} pada {peak_at}",
        "context_only":     "memberi tahu, tidak pernah meminta",
        "ask_how":          "Balas /act {id} di Telegram dan sebutkan apa yang Anda lakukan.",
        "not_watched":      "tidak dipantau di sini",
        "no_source":        "tidak ada sumber",
    },
    "es": {
        "open_ask_current": "pedido a las {when}, y sigue vigente",
        "open_ask_stale":   "pedido a las {when}; la lectura volvió sola, la petición sigue abierta",
        "alert_today":      "un {level} a las {when}, ya pasado",
        "over_line":        "por encima del límite, y no se ha pedido nada a nadie",
        "over_line_peak":   "por encima del límite desde el máximo del día, {peak} a las {peak_at}, y no se ha pedido nada a nadie",
        "no_alert":         "tranquilo",
        "no_alert_peak":    "tranquilo; el máximo del día fue {peak} a las {peak_at}",
        "context_only":     "informa, nunca pide",
        "ask_how":          "Responde /act {id} en Telegram y di qué hiciste.",
        "not_watched":      "no se vigila aquí",
        "no_source":        "sin fuente",
    },
}


def _problems(key: str, d: dict) -> list[str]:
    """Everything wrong with one issue declaration, in the words its author needs to fix it."""
    p: list[str] = []
    if not isinstance(d, dict):
        return [f"{key}: the file is not a mapping"]

    for loc in LOCALES:
        if not (d.get("name") or {}).get(loc):
            p.append(f"{key}: name.{loc} is missing")
        if not (d.get("empty") or {}).get(loc):
            p.append(f"{key}: empty.{loc} is missing — say what there is to say with no source")

    kind = d.get("kind")
    if kind not in KINDS:
        p.append(f"{key}: kind is {kind!r}; it must be one of {KINDS}")
    for f in ("metric", "unit"):
        if not d.get(f):
            p.append(f"{key}: {f} is missing")
    if not isinstance(d.get("dp"), int):
        p.append(f"{key}: dp must be an integer number of decimal places")

    line = d.get("line")
    if line is not None:
        if not isinstance(line, dict):
            p.append(f"{key}: line must be a mapping or empty (~)")
        else:
            for f in ("value", "source"):
                if line.get(f) is None:
                    p.append(f"{key}: line.{f} is missing — a line with no named source is a number "
                             f"somebody will have to go and look up")

    cmp_ = d.get("compare") or {}
    if kind == "sensed":
        if cmp_.get("mode") not in COMPARE_MODES:
            p.append(f"{key}: compare.mode is {cmp_.get('mode')!r}; it must be one of {COMPARE_MODES}. "
                     f"A concentration compares by ratio, a temperature by difference, and the engine "
                     f"must not guess from the unit.")
        if not isinstance(cmp_.get("margin"), (int, float)) or cmp_.get("margin") is True:
            p.append(f"{key}: compare.margin must be a number")

    packs = d.get("packs") or {}
    if not isinstance(packs.get("domains"), list) or not packs["domains"]:
        p.append(f"{key}: packs.domains must list at least one pack domain")
    if not isinstance(packs.get("rules", []), list):
        p.append(f"{key}: packs.rules must be a list of <pack>/<rule> ids")
    for rid in packs.get("rules") or []:
        if "/" not in str(rid):
            p.append(f"{key}: packs.rules has {rid!r}; rule ids are namespaced <pack>/<id>")

    dist = d.get("distances")
    if not isinstance(dist, dict) or set(dist) != set(DISTANCES):
        p.append(f"{key}: distances must have exactly these keys: {', '.join(DISTANCES)} "
                 f"(an absent distance is ~, so the page can say why)")
    else:
        if not any(dist.values()):
            p.append(f"{key}: every distance is empty, so this issue can never have a value")
        for name, spec in dist.items():
            p += _distance_problems(f"{key}.distances.{name}", spec)

    for r in d.get("readouts") or []:
        if not isinstance(r, dict) or not r.get("metric") or not r.get("sensor_id"):
            p.append(f"{key}: a readout needs at least a metric and a sensor_id")
        elif not all((r.get("label") or {}).get(loc) for loc in LOCALES):
            p.append(f"{key}: the {r['metric']} readout needs a label in every locale")

    want = set(STATE_SENTENCES) if kind == "context" else {"none"}
    for loc in LOCALES:
        s = (d.get("sentences") or {}).get(loc)
        if not isinstance(s, dict):
            p.append(f"{key}: sentences.{loc} is missing — all three locales carry the same placeholders")
            continue
        attribution = s.get("attribution") or {}
        if kind == "sensed":
            for c in CLASSES:
                if not attribution.get(c):
                    p.append(f"{key}: sentences.{loc}.attribution.{c} is missing")
        state = s.get("state") or {}
        for st in want:
            if not state.get(st):
                p.append(f"{key}: sentences.{loc}.state.{st} is missing")
        uses_verb = False
        for where, tpl in list(attribution.items()) + list(state.items()):
            found = re.findall(r"\{(\w+)\}", str(tpl))
            uses_verb = uses_verb or "verb" in found
            for ph in found:
                if ph not in PLACEHOLDERS:
                    p.append(f"{key}: sentences.{loc}.{where} asks for {{{ph}}}, which the engine "
                             f"does not fill. It fills {', '.join(PLACEHOLDERS)}.")
        # {verb} is the only placeholder whose words are the issue's own, because "Climbing to" is
        # right for a concentration and wrong for a sea temperature. An issue that asks for it says
        # its three words; an issue that does not need not.
        if uses_verb:
            for t in TRENDS:
                if not (s.get("verbs") or {}).get(t):
                    p.append(f"{key}: sentences.{loc} uses {{verb}}, so sentences.{loc}.verbs.{t} "
                             f"is needed")
        for w in (d.get("where") or {}).get(loc, {}):
            if w not in DISTANCES:
                p.append(f"{key}: where.{loc}.{w} is not one of {', '.join(DISTANCES)}")
    return p


def _distance_problems(where: str, spec) -> list[str]:
    if spec is None:
        return []
    if not isinstance(spec, dict):
        return [f"{where} must be a mapping or ~"]
    p = []
    src = spec.get("from")
    if src not in WHERE_FROM:
        p.append(f"{where}.from is {src!r}; it must be one of {WHERE_FROM}")
    if src == "stats":
        if spec.get("place") not in DISTANCES:
            p.append(f"{where}.place is {spec.get('place')!r}; it must be one of {DISTANCES}")
        if not spec.get("field"):
            p.append(f"{where}.field is missing — which of the rolling means to read")
        if spec.get("aggregate") not in AGGREGATES:
            p.append(f"{where}.aggregate is {spec.get('aggregate')!r}; it must be one of {AGGREGATES}")
    if src == "observations" and not spec.get("sensor_id"):
        p.append(f"{where}.sensor_id is missing — which model or portal row to read")
    if src in ("stats", "observations"):
        metrics = spec.get("metrics")
        if not isinstance(metrics, list) or not 1 <= len(metrics) <= 2:
            p.append(f"{where}.metrics must be one metric, or two for a function that takes two")
    fn = spec.get("function")
    if fn is not None and fn not in FUNCTIONS:
        p.append(f"{where}.function is {fn!r}; the engine knows {FUNCTIONS}")
    if fn == "apparent" and len(spec.get("metrics") or []) != 2:
        p.append(f"{where} applies apparent(), which needs exactly two metrics: temperature then humidity")
    # There is no `fallback:`. It existed for one afternoon, pointing at a metric retired in v0.33.1,
    # and the reason it was retired is the reason not to have the mechanism: a second number for one
    # idea, with different provenance, is worse than one number. An issue with no source says so.
    if "fallback" in spec:
        p.append(f"{where} has a fallback. Issues do not fall back to a different measure of the "
                 f"same idea — see the region column in app/issues/land.yml for why. A distance "
                 f"with no source is empty and the page says why.")
    return p


def load(path: Path | str | None = None) -> dict[str, dict]:
    """Every issue declared in `path` (this directory by default), keyed by file stem.

    A file that does not parse or does not validate is logged and dropped: one bad issue must not
    cost the household the other three.
    """
    out: dict[str, dict] = {}
    for f in sorted(Path(path or HERE).glob("*.yml")):
        try:
            d = yaml.safe_load(f.read_text()) or {}
        except Exception as e:  # noqa: BLE001
            log.warning("issue %s: does not parse (%s)", f.name, e)
            continue
        bad = _problems(f.stem, d)
        if bad:
            for b in bad:
                log.warning("issue %s: %s", f.name, b)
            continue
        d["key"] = f.stem
        out[f.stem] = d
    return out


def order(declared: str, available: dict[str, dict]) -> tuple[list[str], list[str]]:
    """NODE_ISSUES, parsed. Returns (the order to draw, the names that were dropped).

    An unknown name is dropped and logged, never fatal: a keeper who types `air,heat,watar` gets a
    page with air and heat on it and a line in the log, not a node that will not answer. An empty
    setting falls back to the order the files are in, which is the packs' own alphabetical order.
    """
    names = [n for n in (declared or "").replace(" ", "").split(",") if n]
    keep = [n for n in names if n in available]
    dropped = [n for n in names if n not in available]
    for n in dropped:
        log.warning("NODE_ISSUES names %r, which no app/issues/*.yml declares — dropping it", n)
    seen, uniq = set(), []
    for n in keep:
        if n not in seen:
            seen.add(n); uniq.append(n)
    return (uniq or sorted(available)), dropped


def issues(cur, settings) -> dict:
    """The whole issues object: order, per-issue state, stack, line, attribution, sentence, asks.

    The engine is imported here rather than at module scope so that `engine` can import this module
    for its declarations without the two chasing each other round an import cycle.
    """
    from . import engine
    return engine.compute(cur, settings, load())
