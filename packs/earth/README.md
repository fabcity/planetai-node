# earth — the node's own square of AlphaEarth

Google's AlphaEarth Foundations model turns a year of satellite observation into a 64-number vector for every
10 m pixel of the planet. Two vectors for the same pixel in two different years point in almost the same
direction if nothing happened there, and apart if something did. That is the whole of this pack: download the
node's square, take the angle between years, report it.

The layers are published as Cloud-Optimized GeoTIFFs in a public bucket, `gs://alphaearth_foundations`, under
CC BY 4.0. The node reads the window it needs over HTTPS with no key and no account.

## What it is not

- **Not air, water or emissions.** The embeddings describe land surface and coastal water as seen from orbit.
  Nothing in them is a measurement of what you breathe. That is what the sensors on the wall are for.
- **Not monitoring.** One layer per year, published after the year ends. It is a retrospective record of
  structure, not a signal you can act on this week.
- **Not an explanation.** The number says this square looks different from last year. It cannot say a road
  was cut, a warung was built, a hillside was cleared or a field flooded. Someone who walks there can.
- **Not ours to reproduce.** It is a Google artifact. We can mirror it and do arithmetic on it because the
  licence allows that. We could not make it again, and we cannot check it against anything.

## The arithmetic

Each channel is a signed byte. The bucket's README gives the mapping to the analysis value:

    v = (raw / 127.5) ** 2 * sign(raw)

and the 64-vector has Euclidean length 1 **after** that mapping. This matters more than it looks: on the raw
integers the vectors have length about 321, so a dot product taken before de-quantising is wrong and still
looks like a number between plausible bounds. Measured on 20,000 pixels of the Bali tile, de-quantised norms
came out at 1.000093, spread 0.002, every one within 0.01 of unit length. `planetai run earth verify` re-runs
that check on whatever is cached here.

Because the vectors are already unit length, the cosine is just the dot product, and

    distance = 1 - dot(A, B)

per pixel, clipped to [0, 2]. `-128` in any channel means no data; the bucket's README says it is then in
every channel, and those pixels are excluded from every statistic. The comparison runs in bands of 100 rows,
because one de-quantised year is 256 MB of float and a node may have 2 GB of memory.

### Where "changed" starts

`CHANGED = 0.15`, one constant at the top of `packs/earth/change.py`. It is the only number in this pack that
was chosen rather than measured, and it was calibrated on one 10 km square of Kuta Selatan, Bali. There, it
sits at about the 99th percentile of a consecutive-year comparison: 0.96 % of the square for 2023→2024,
1.19 % for 2024→2025, and 4.9 % over the two-year gap 2023→2025. So a quiet year stays quiet and a real change
stands out. Somewhere with monsoon flooding, snow, or a working agricultural calendar will have a different
baseline; look at the distribution in the JSON before trusting the hectares. A lower threshold is not more
sensitive, it is noisier: at 0.05 a third of this square is "changed" every year.

## The cache

Files under `out/earth/<node>/`, which is the one writable path the app container has:

| file | what |
|---|---|
| `<year>.npy` | the raw signed bytes for the square, north up, 64 x H x W |
| `meta.json` | the point, the radius, the tile the index chose per year, the window bounds |
| `change_<A>_<B>.png` | the map: grey ramp, north up, the node ringed, 1 km scale bar |
| `change_<A>_<B>.json` | mean, median, p95, the share and hectares over the threshold, bounds, source objects |

Measured on node #1 (Bali, `EARTH_RADIUS_M=5000`, a 10 km square, 1000 x 1000 px):

- **64 MB on disk per year**, 576 MB for all nine.
- **about 103 MB pulled per year**, 925 MB for all nine. More than the file it keeps, because the source is
  tiled internally in 1024 px blocks and a square centred on the node straddles four of them. Aligning the
  window to those blocks would cost 14.5 MB, and would put the node 2 km from one edge of its own square.
- **about 150 seconds per year**, so all nine is roughly 22 minutes. Run it from a shell rather than over
  MCP, where a script is cut off at 15 minutes.
- one extra download the first time only: the dataset's tile index. It is 798 MB and has no GeoJSON form, so
  the pack binary-searches it by byte offset for the node's UTM zone and reads only that zone's block. For
  Bali that was 26 range reads, 189 kB, then one block of 8.8 MB. The result is kept in `meta.json`.

Nothing is downloaded on a poll. The pack fetches on command; the adapter only reads what is already here.

## The commands

```bash
planetai run earth fetch            # every year the dataset has (or EARTH_YEARS); --force re-reads a cached one
planetai run earth fetch 2024 2025  # just these
planetai run earth change           # the two latest consecutive cached years
planetai run earth change 2023 2025 # any two
planetai run earth status           # years, bytes, comparisons, what the cell reports
planetai run earth verify           # the dataset's claims against the files, and whether the reading landed
```

The pack is code, so it needs `PACKS_ALLOW_CODE=1` in `.env` and `planetai packs install` for `rasterio` and
`numpy`. Read `packs/earth/adapter.py` before you enable it.

## The cell

One: `Environmental|City`, `partial`, the mean per-pixel distance for the latest consecutive pair. It stays
`partial` however good it is. The node did the arithmetic, but the input is a model's description of a place,
not a measurement anyone here could repeat, and `live` in this project means measured here.

## Two numbers for one thing

The `earth-engine` pack already reports `land_change_score` on `ee-point`: 1 − cosine similarity of the *mean*
embedding vector over 1 km, computed inside Earth Engine, behind a service-account key. This pack reports the
mean of the *per-pixel* distances over 10 km, computed here, from a public bucket, with no key. They are
different quantities and they will not agree — averaging vectors first cancels the noise that averaging
distances keeps. On node #1, Earth Engine's 1 km score for 2025 is 0.037; this pack's 10 km 2024→2025 mean is
0.041. Two numbers for the same idea, with different provenance, is a thing to resolve rather than ship
forever. Flagged in `docs/HANDOFF_earth_pack.md`; the decision is not the pack's to make.

## Attribution

The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind. CC BY 4.0.

This is the wording the dataset's licence asks for, and it travels with every derivative: the pack manifest,
the `/earth` endpoint, the dashboard card, the PNG's own metadata, and the daily export.

This pack is alpha, like the rest of the node. If the numbers look wrong for your place, that is worth an
email: info@fab.city.
