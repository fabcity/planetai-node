"""The hero's ground is this node's own cell, and it is drawn the way the design kit draws it.

Two things can go wrong here and neither raises. The drawing can drift from planetai-design, which
computes the same geometry in JavaScript with d3-geo — two languages, one picture, and no build step
between them. And the caption can outlive the geometry: it names a cell and says the node stands in
it, which was false on every node but #1 for the whole of v0.36.

The first is held by redrawing node #1's coordinates and comparing against app/static/node-ground.svg,
which is the design kit's own d3-geo output, vertex for vertex. If the projection, the fit or the
winding moves here, this fails.

What it does not hold: the sibling repo is not on a node and cannot be imported, so this pins the
drawing to the kit as it stood on 7 September 2026, not to the kit as it is now. A change to
planetai-geo's nodeGround() needs that file copied over again, and then this test says whether the
Python followed.
"""
import re
import sys

sys.path.insert(0, "app")
import math

try:
    import h3                                     # noqa: F401
except ImportError:
    print("  - ground check skipped (pip install -r app/requirements.txt)")
    sys.exit(0)
import ground

BALI = (-8.8271, 115.15709)          # node #1, Kuta Selatan
BARCELONA = (41.3874, 2.1686)
paths = lambda svg: re.findall(r' d="([^"]+)"', svg)

shipped = open("app/static/node-ground.svg").read()
drawn = ground.svg(*BALI)

# 1. the same picture the design kit computes, to the last vertex
assert paths(drawn) == paths(shipped), (
    "the ground has drifted from planetai-design's node-ground.svg. Compare against "
    "planetai-geo/index.mjs nodeGround() before changing anything here")
assert len(paths(drawn)) == 14, f"6 neighbours + 7 children + the cell, not {len(paths(drawn))}"
print("  node #1's ground redraws to the design kit's geometry, all 14 paths")

# 2. the caption is true, because it is this node's cell. It is page text rather than a stamp in the
#    drawing: the hero scales the ground with object-fit:cover, and a stamp at the foot of the frame
#    loses its cell id to the crop at 390 and the whole line at 1440.
here = ground.svg(*BARCELONA)
bali_id, bcn_id = h3.latlng_to_cell(*BALI, 8), h3.latlng_to_cell(*BARCELONA, 8)
assert bali_id != bcn_id
for svg, (lat, lon), cell in ((drawn, BALI, bali_id), (here, BARCELONA, bcn_id)):
    line = ground.facts(lat, lon)["caption"]
    assert line.startswith(f"{cell} · RES 8 · ") and line.endswith(" · THE CELL THIS NODE STANDS IN"), line
    assert line in svg[:svg.index("</title>")], "the file says what it is on its own, in <title>"
    assert "<text" not in svg, "the caption is the page's; a stamp in the frame gets cropped"
# The page is a renderer since v0.45: the two stamps are one `stamp` component, listed in the hero's
# anatomy and the wall's, and the caption reaches it through the band's data from /health. Asserting
# the anatomy is the guarantee the two ids used to give — an id can exist while nothing writes to it.
# (tests/test_shipped.py holds the same three facts; this suite skipped on every machine without h3,
# which is how the old literal survived here after it was gone from the page.)
import re as _re
def _haversine(a, b):
    p = math.pi / 180
    x = 0.5 - math.cos((b[0] - a[0]) * p) / 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * (1 - math.cos((b[1] - a[1]) * p)) / 2
    return 12742 * math.asin(math.sqrt(x))


# ---- presence: how much a coarse cell actually gives away -----------------------------------------
# The announced cell is the node's own res-8 cell rounded up to a parent, and the resolution IS the
# privacy control. These are the numbers that choice is made on, measured rather than asserted.
_here8 = h3.latlng_to_cell(*BALI, 8)
_blur = {}
for _r in (3, 4, 5, 6):
    _c = h3.cell_to_parent(_here8, _r)
    _lat, _lon = h3.cell_to_latlng(_c)
    _blur[_r] = ground.km(BALI[0], BALI[1], _lat, _lon) if hasattr(ground, "km") else _haversine(BALI, (_lat, _lon))
assert _blur[3] > 20, f"res 3 must not land near the house: it is {_blur[3]:.1f} km away"
assert _blur[3] > _blur[5], "a coarser cell has to blur further, or the setting means nothing"
assert h3.cell_to_parent(_here8, 3) != _here8, "the announced cell is never the node's own cell"
# and the distance between two nodes is two cell centres, so it is symmetric and carries no address
_men = h3.cell_to_parent(h3.latlng_to_cell(39.9496, 4.1100, 8), 3)
_a, _b = h3.cell_to_latlng(h3.cell_to_parent(_here8, 3)), h3.cell_to_latlng(_men)
_d = _haversine(_a, _b)
assert 11500 < _d < 13500, f"Bali to Menorca from two coarse cells is {_d:.0f} km, which is not the right planet"
print(f"  the announced cell blurs this node by {_blur[3]:.0f} km at res 3, and Menorca reads {_d:.0f} km away")

gui = open("app/static/dashboard.js").read()
assert 'data-component="stamp"' in gui, "the cell stamp is a component"
for _a in ("hero", "wall"):
    _anat = _re.search(rf"^\s*{_a}:\s*\[([^\]]*)\]", gui, _re.M)
    assert _anat and "'stamp'" in _anat.group(1), f"ANATOMY.{_a} must carry the cell stamp"
assert "d.cell ? d.cell.caption" in gui and "(snap.health || {}).cell" in gui, (
    "the hero and the wall print the caption from /health")
assert '"cell": _cell()' in open("app/main.py").read(), "/health carries the cell"
assert "THE CELL THIS NODE STANDS IN" not in shipped, (
    "app/static/node-ground.svg is the fallback for a node with no coordinates yet. It is node #1's "
    "cell and must claim nothing")
print(f"  the caption names the node's own cell: {bali_id} in Bali, {bcn_id} in Barcelona")

# 3. the edge is measured, not quoted. H3 publishes 531 m as the res-8 average; node #1's cell is
#    smaller than average and its six edges run 471-518 m. A table value printed beside a drawn cell
#    is the same small untruth as node #1's geometry on someone else's node.
b = h3.cell_to_boundary(bali_id)
edges = [round(h3.great_circle_distance(b[i], b[(i + 1) % 6], unit="m")) for i in range(6)]
assert len(set(edges)) > 1, "an H3 cell is never a regular hexagon; equal edges mean something drew one"
assert f" {round(sum(edges) / 6)} M EDGE " in ground.facts(*BALI)["caption"], f"the stamp should carry this cell's mean edge, {edges}"
print(f"  the stamp measures this cell: edges {min(edges)}-{max(edges)} m, mean {round(sum(edges) / 6)}")

# 4. the dark register. A paper or ink literal on an element does not flip, which is the bug
#    planetai-design's test/variant.test.js exists to stop; here every element must carry a class.
BINDS = {"ground", "land", "cell", "chain", "lit", "ring", "hair", "fig", "label"}
body = re.sub(r"<style>.*?</style>", "", here, flags=re.S)
for tag in re.findall(r"<(?:rect|path|line|circle|polygon|text|ellipse)\s[^>]*>", body):
    lit = re.search(r'(?:fill|stroke)="(#F9F5F2|#171717)"', tag, re.I)
    assert not lit, f"{lit.group(0)} on an element with no binding class: it will not flip"
    assert BINDS & set(re.search(r'class="([^"]*)"', tag).group(1).split()), tag
assert 'data-variant="dark"' in here and "#7FA5E8" in here and "#20388D" in here
print("  every element binds its colour to a variant token; the dark register's blue is #7FA5E8")

# 5. Barcelona is not Bali. Nothing about the drawing is a constant.
assert not set(paths(here)) & set(paths(drawn)), "no path survives a change of place"
assert ground.svg(*BARCELONA) is here, "one point is drawn once and kept"
print("  a different node draws a different ground")

# 6. the ground follows the page's register. It is an <img>, so it is a document of its own and no
#    CSS on the page reaches it: without this it drew #7FA5E8 on the paper hero at 2.29:1, which is
#    the one thing planetai-design's guards say may never happen. The page asks in the URL instead.
paper = ground.svg(*BALI, "paper")
assert 'data-variant="paper"' in paper, "?variant=paper must reach the root attribute"
assert 'data-variant="dark"' in drawn, "the default is still the dark register"
assert paths(paper) == paths(drawn), "the register changes the palette, never the geometry"

_main = open("app/main.py").read()
# The variant is interpolated into data-variant="..." inside the SVG, so the route may never pass a
# caller's string through. Two literals, chosen by comparison — that is what makes it uninjectable.
assert '_ground_svg("paper" if variant == "paper" else "dark")' in _main, (
    "the route must coerce ?variant= to one of two literals, not validate-and-forward it")
assert 'src="static/node-ground.svg?variant=${ctx.register}"' in open("app/static/dashboard.js").read(), (
    "the renderer must ask for the register it is in")

# The shipped fallback is drawn dark, so a node with no coordinates yet needs the attribute swapped
# or it puts the lifted blue on the paper hero — the same bug, one branch over.
assert 'data-variant="dark"' in shipped, "the shipped file is the dark register"
assert 'data-variant="paper"' in shipped.replace('data-variant="dark"', 'data-variant="paper"', 1)
assert "#20388D" in shipped and "#7FA5E8" in shipped, (
    "the fallback carries both registers in its own <style>, or swapping the attribute changes nothing")
print("  the ground follows the register: paper on the page, dark on the wall, geometry unchanged")
