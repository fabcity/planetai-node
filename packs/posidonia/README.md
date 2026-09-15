# posidonia

One number about the sea that a coastal Mediterranean node already has, read against the plant that
the coast is made of.

**Written for Menorca, Illes Balears** — a node on an island whose beaches, water clarity and fishing
all sit on top of *Posidonia oceanica* meadows. Every threshold here is western Mediterranean.

## What it adds

- `thermal_stress` — the sea has averaged 28.4 °C or more for three days. `info`.
- `warm_watch` — the sea has held 27 °C or more for a week, below the stress line. `info`, weekly at most.
- `Environmental|Bioregion` — days in the last 90 with a mean sea temperature at or above 28.4 °C.

No adapter, no key, no dependency, no new metric. It reads `sea_surface_temp` from the `marine-point`
sensor that `packs/coast` already writes, so a node with `coast` enabled gets this for free.

## Where the numbers come from

28.4 °C is Marbà & Duarte (2010), *Mediterranean warming triggers seagrass (Posidonia oceanica) shoot
mortality*, Global Change Biology 16:2366–2375: six years of seawater temperature and annual shoot
demography at **Cabrera Archipelago National Park**, about 90 km from Menorca. Shoot mortality tracks
warming, and above roughly 28.4 °C the meadow loses more shoots than it recruits. The two heat waves
in that record reached 28.83 °C (2003) and 28.54 °C (2006).

27 °C sustained is the softer band the same literature associates with reduced photosynthesis. It is
here as a watch level, not a decision.

Unusually for a threshold in this repository, these were measured **in the same water as the node that
reads them**. That is the whole argument for the pack: it is a local line, not a global one borrowed.

## What this pack does not know

- **Where the meadow actually is.** It does not fetch the Decret 25/2018 protected-zone geometry the
  Govern de les Illes Balears publishes (*Zones Alt Valor*, *Zones a Regular*, GeoJSON and CSV on
  `intranet.caib.es/opendatacataleg`). It asks whether the water is hot, not whether there is seagrass
  under it. A node in a sandy bay with no Posidonia will get the same alert as one over a meadow.
- **The sea temperature is modelled, not measured.** It is a point sample from Open-Meteo Marine at
  the nearest ocean grid cell, which for an inland node can be kilometres away and is a different body
  of water from the bay anyone actually swims in. The cell is `partial` for that reason and must stay so.
- **Depth.** Posidonia grows from the surface down to about 40 m, and a surface temperature is not the
  temperature at the rhizome. Deep meadows are buffered; shallow ones are not.
- **Everything else that kills seagrass.** Anchoring, turbidity, nutrients and coastal works do more
  damage in a season than a warm summer does, and none of them are visible from here.
- **Catalan.** Menorca's own language. `ALERT_LOCALE` offers `en`, `id` and `es`; the Spanish strings
  here are assistant-written and have not been read by a native speaker, the same caveat
  `app/issues/coast.yml` carries for its own.

## Tuning it for your place

If your node is not in the western Mediterranean, do not keep these numbers — the species may not even
be there. *Posidonia oceanica* is endemic to the Mediterranean. A node in the Baltic or the Caribbean
wanting the same shape of pack should fork it, name its own seagrass and find a threshold measured in
its own water. That is the point of the `thresholds:` field in `pack.yaml`.
