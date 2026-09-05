# Coverage: the node against the Fab City Index

The Index is twenty cells: four pillars (Environmental, Economic, Social, Governance) by five scales (Community, City,
Region, Bioregion, Planet). A node fills cells at any scale; the kind of source changes, not the code.

## What a cell needs at each scale

| scale | describes | arrives as | cadence | `kind` |
|---|---|---|---|---|
| Community | this address, this lab | a device you own, or a nearby public sensor | minutes | `sensor` |
| City | a district, a municipality | an open-data portal, a municipal network | days | `portal` |
| Region | a province, a metro | statistical APIs, grid operators | months | `portal` |
| Bioregion | a watershed, a biome | hydrology, biodiversity, satellites | months to years | `portal`, `model` |
| Planet | boundary conditions | Earth models sampled at your coordinates | hours | `model` |

Two rules the code enforces. **Aggregation stops at Region**: Bioregion and Planet publish context downward and are never
rolled up. **`live` means measured here**; a model or a portal is `partial`, whatever its quality.

## Filled today, node #1

| cell | from | state |
|---|---|---|
| Environmental \| Community | your sensors, PM2.5 24h mean | live |
| Environmental \| City | nearest public sensors | partial |
| Environmental \| Bioregion | sea temperature; tree cover and land change (Earth Engine) | partial |
| Social \| Community | heat-exposure hours from indoor temp and humidity | live |
| Governance \| Community | ρ, alerts that led to action | partial → live at five actions |
| Governance \| City | the open-data portal's maintenance state | partial |

Six of twenty. `planetai cells` shows them; the dashboard draws them as a honeycomb.

## Empty, and what would fill each

| cell | a source that exists | who would write the pack |
|---|---|---|
| Economic \| Community | a fab lab's machine log (Fabman, a CSV) | a fab lab |
| Economic \| City | a business registry, KLEMS | a city partner |
| Social \| City | a survey via the node's own Telegram bot | Making Sense |
| Governance \| Region | Socrata / ArcGIS portals (Barcelona, Boston) | a civic-tech group |
| Environmental \| Region | a grid operator's hourly mix | a regional partner |
| Economic \| Region, Bioregion | procurement feeds (TED, ChileCompra, LKPP); material-flow accounts | an institution |

The Social column has the fewest sources of any in the registry. Heat-exposure hours is the first number in it.

## Reading the map

A green cell is a measurement at an address. A blue one is derived or modelled. An empty one has no source, not a
missing feature. The node does not fill what it cannot measure, and says which is which.
