"""What this pack has on disk, what it computed, and what the Index cell says.  planetai run earth status"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

lat, lon, radius = A.aoi()
years = A.cached_years()
cs = A.changes()
size = sum(p.stat().st_size for p in A.cache().glob("*")) if A.cache().is_dir() else 0

print(f"earth · {A.node()} · {lat}, {lon} · UTM {A.utm_zone(lat, lon)} · {2 * radius / 1000:.1f} km square")
print(f"  cache: {A.cache()}  ({size / 1e6:.0f} MB)")
if years:
    print(f"  years cached: {', '.join(map(str, years))}  ({len(years)} of {len(A.YEARS)})")
    missing = [y for y in A.wanted_years() if y not in years]
    if missing:
        print(f"  not cached:   {', '.join(map(str, missing))}   planetai run earth fetch {' '.join(map(str, missing))}")
else:
    print("  years cached: none.  planetai run earth fetch")

if cs:
    print("  comparisons:")
    for c in cs:
        print(f"    {c['year_a']} → {c['year_b']}  mean {c['mean']:.4f}  "
              f"{c['share_over_threshold'] * 100:.2f}% over {c['threshold']}  "
              f"({c['hectares_over_threshold']:.0f} ha)  {c['png']}")
else:
    print("  comparisons: none.  planetai run earth change")

pair = A.latest_pair()
if pair:
    yoy = [c for c in cs if (c["year_a"], c["year_b"]) == pair]
    if yoy:
        print(f"\n  Environmental|City reports land_change_yoy = {yoy[0]['mean']:.4f} "
              f"({pair[0]} → {pair[1]}), state partial")
    else:
        print(f"\n  Environmental|City reports nothing yet: planetai run earth change {pair[0]} {pair[1]}")
else:
    print("\n  Environmental|City reports nothing: no two consecutive years are cached")

print(f"\n{A.ATTRIBUTION}")
