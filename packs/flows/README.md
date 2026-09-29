# flows — what a place makes, uses, fixes, takes in and sends out

**What it adds** — the first production numbers in the Index, typed by the people who made the things.
A lab or a household logs one line; the node keeps it as a reading, sums it into `Economic|Community`,
`Social|Community` and `Environmental|Community` cells, and shows the place its own numbers in the weekly
report before the Index sees them. Nothing here runs yet: the vocabulary is decided
(`docs/decisions/2026-09-28-flows.md`), the code ships in v0.76.

**The grammar** — one line, three parts, one number:

```
<action>.<class>.<ring>    value in the class's unit
produce.filter.cell        3
consume.filament.beyond    1.2
modify.appliance.cell      1
cite.design.beyond         1
```

*action* is a ValueFlows verb, unchanged: `produce` `consume` `use` `work` `modify` `transfer` `cite`.
A repair is `modify`; a design taken in is `cite`, because it is neither used up nor worn. *class* is one of
the 26 in `packs/flows/resources.yml`, and the class carries everything that does not vary per line: the
unit, the nature of the thing (physical, digital, information, service), the Index pillar, the
planetary-boundary ceiling, the doughnut foundation, and the EW-MFA bin. *ring* is where it came from or went
to, in the Index's scales: `cell` `city` `region` `beyond`. Unit, nature and every tag come from the class, so
the metric carries only what varies.

**Why these numbers** — the Index formula is FCI = DIDO · (1 − PITO) · ρ and until now no node has logged a
single thing a place made. The ring says where; the class's nature says what kind of thing. Physical from
`beyond` is a product in: PITO. Digital from anywhere, and physical made in the cell, is DIDO. The ring
alone cannot tell a design file from a finished chair, both arriving from Hamburg; the nature can.

**The profile** — this pack's vocabulary is the Fab City profile of ValueFlows, `fabcity-flows` 1.0, published
at https://planetai.fab.city/vocab/flows/1.0/ with one URI per class. ValueFlows is CC BY-SA 4.0 and its
definitions are paraphrased and linked, never copied; the profile itself is CC BY 4.0 like every pack's
data. A class, once used, is never renamed or given a new unit. Adding a class is a minor version; changing a
verb, a ring or a unit is a major version and a decision entry. It is a profile and not a fork on purpose:
every tool that reads ValueFlows reads these rows, and a fork would lose them all.

**Alignment: EPCIS 2.0 / CBV** — so a Digital Product Passport or UNTP tool can read an export the day one
exists. Recorded here, used by nothing on the node.

| verb | EPCIS event | CBV bizStep | note |
|---|---|---|---|
| `produce` | TransformationEvent, `outputQuantityList` | `assembling` or `creating_class_instance` | quantity with `uom` |
| `consume` | TransformationEvent, `inputQuantityList` | same event as the produce it fed | |
| `modify` | ObjectEvent, action OBSERVE | `repairing` | EPCIS has the step; VF pairs it with `accept` |
| `transfer` in | ObjectEvent, action OBSERVE | `receiving` | `sourceList` type `location` carries the ring |
| `transfer` out | ObjectEvent, action OBSERVE | `shipping` | `destinationList` type `location` carries the ring |
| end of life | ObjectEvent | `collecting` / `destroying`, disposition `disposed` | `transfer.waste_residual.beyond` |
| `use` | none | none | no EPCIS notion of using a tool without consuming it |
| `work` | none | none | no EPCIS notion of labour |
| `cite` | none | none | no EPCIS notion of a design as an unconsumed input |

The three gaps are the argument for logging in ValueFlows and aligning to EPCIS, not the other way round.

**Alignment: W3C PROV-O** — five lines, for anyone who reads provenance graphs.

| verb | PROV-O |
|---|---|
| `produce` | `prov:wasGeneratedBy` (the thing, by the activity) |
| `consume` | `prov:used` and `prov:wasInvalidatedBy` |
| `modify` | `prov:wasDerivedFrom` (the fixed thing, from the broken one) |
| `use`, `cite` | `prov:used` |
| `work` | `prov:wasAssociatedWith` (the activity, with the agent) |

**What it assumes** — a person converts to the class's unit once, before typing; a line in grams is refused,
not converted. A ring left out is `cell`. Two identical lines a second apart are two rows, because the server
stamps microseconds. Self-reported is a survey, so every cell this pack computes is `partial`; `live` is for
a measured flow, which a machine on MQTT can give the same table later.

**What it does not know** — what went into what: there is no process link between `consume.filament.beyond`
and `produce.filter.cell`, so the pack can total and cannot trace. Which machine: `machine_hours` is one
class until a resources table names them. Who: the logger is `flow:<NODE>`, never a name, and there is no
note column, on purpose. Whether a row is true: it is what the place said, and the cell says so.

**What leaves the node** — cells, through the cells endpoint, as for every pack. Rows do not: the child push
and the daily export both exclude `source = 'flows'`. When a parent node or a named reader wants monthly
totals, that is a wire document in ValueFlows names, written then and not before.

**Where the ideas came from** — the verbs and classification rule are ValueFlows 1.0.0 (24 Feb 2026). The
`nature` field is Nondominium's Layer 0 (Sensorica). The signing lesson for the wire, when it comes, is
Interfacer's own September 2026 security review. The EW-MFA bins are Eurostat's. The alignments are GS1's
and W3C's. None of their software runs here.
