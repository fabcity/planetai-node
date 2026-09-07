# Handoff: the September 2026 surface audit

## What exists

| File | What it is |
|---|---|
| `docs/design/AUDIT_2026-09.md` | The report. Findings, evidence, severity, recommendations, in that order. |
| `docs/design/audit/tokens.csv` | 1,208 rows. Every hex, rgb/hsl/oklch, font-family, font shorthand, font-size, border-radius, box-shadow, letter-spacing and z-index in nine HTML and CSS files across both repos, with `repo, file, line, property, value, count`. |
| `docs/design/audit/shots/` | 162 PNGs. Six surfaces (landing, observatory, node0, dashboard on node #1, dashboard on pai-clean, FAB26 simulator) at 375×812, 768×1024 and 1440×900, light scheme, full page. Plus `shots/focus/<surface>/tab-{3,10,20}.png`. |
| `docs/design/audit/shots/_contact-sheet-*.png` | One grid per surface, five columns, tall pages cropped to the top 900 px of their scaled height and labelled "(top)". |
| `docs/design/audit/axe/` | One JSON per surface and view, plus `_summary.json` and `focus-order.json` (30 keyboard stops per surface with the computed outline and box-shadow at each). |
| `docs/design/audit/perf/` | `fast3g.json`, `observatory-coverage.json`, `reduced-motion.json`. |
| `docs/design/audit/api/` | The read-only capture from node #1 at 2026-09-06T14:08:06Z: `health`, `stats`, `rho`, `cells`, `alerts`, and `capture_time.txt`. Every live figure quoted in the report comes from these. |
| `docs/design/audit/observatory-*.json` | The ten-findings verification: `observatory-findings.json`, `observatory-findings-2.json` (mode toggle, scrubbers, persistence), `observatory-prov-by-view.json`, `observatory-load-state.json`. |
| `docs/design/audit/ia-clickpaths.json` | Visible-link counts per surface behind the click-path table. |
| `docs/design/audit/chart-accessible-names.json` | SVG and canvas accessible-name counts per surface. |
| `docs/design/audit/wall-type-sizes.json` | Computed font sizes in the wall view at 1440, 1920 and 2560 wide. |
| `docs/design/audit/scripts/` | Every script that produced the above. Kept so the set can be rebuilt, not because it is nice code. |

Nothing here is linked from a README, so `tools/check_docs.py` leaves it alone. That is deliberate.

The screenshot set is about 137 MB. It is committed on a local branch and has not been pushed, so `git branch -D` removes it completely if that is the wrong call.

## Where it came from

- **planetai** at `c222e06` on `main`, working tree dirty (`node0/get/*`).
- **planetai-node** at `fc437f9` on `main`; this work sits on `audit/design-2026-09-report`, branched from that commit. Three commits landed in the repo during the audit and `main` moved from `8f3aa4b` to `fc437f9`.
- **node #1**, `bayu-2`, `v0.32.1-1-g5003ef1`. Read over `ssh -L 8899:127.0.0.1:8081 fablabbali@bayu-2`. Read-only: five GET endpoints, `docker ps`, and one `grep` of `.env`. No write, no install, no `update`, no migration.
- **pai-clean**, the Lima VM, `v0.32.1`, `ingested: 0`, reachable from the host at `127.0.0.1:8080`. Not pristine: it carries two leftover test sensors, `evil-1` and `vm-test`.

## What is unverified

Listed in full at the end of the report. The five that matter most:

1. The April 2026 UX/UI review document was not found in either working directory. The ten findings were tested as the audit brief states them, corroborated by the `§P0-1`…`§P2-3` markers in the observatory source.
2. Nothing was captured from `planetai.fab.city`. Everything is the working tree served over `python3 -m http.server`. Four `index.fab.city` calls were blocked by same-origin policy and may succeed in production; Cloudflare compression would change every byte figure.
3. No Playwright Chromium was installed and none was downloaded. Every measurement is Google Chrome 152.0.7977.82, driven by `playwright-core` with `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`.
4. Node #1's wall screen was not photographed. The Telegram tool in this session cannot ask a device for a picture. The 3 m legibility figures are computed from measured type sizes and two stated panel assumptions.
5. The observatory grew by 2,528 bytes while the audit ran and is uncommitted. A rerun will not match byte for byte.

## Reproducing the screenshot set

Four things have to be up first.

```bash
# 1. the static site
cd "/Users/tomasdiez/Documents/Claude/Projects/FAB CITY/planetai" && python3 -m http.server 8790
```

```bash
# 2. node #1, read-only over the tailnet
ssh -f -N -L 8899:127.0.0.1:8081 fablabbali@bayu-2
```

```bash
# 3. the empty node — already forwarded to 127.0.0.1:8080 by Lima
limactl start pai-clean
```

```bash
# 4. playwright-core against the installed Chrome, no browser download
cd /tmp/planetai-audit && npm init -y && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i playwright-core axe-core
```

Then, from `docs/design/audit/scripts/`, with `OUT` inside each script pointed at `docs/design/audit`:

```bash
node shots.js landing && node shots.js node0 && node shots.js dashboard-node1 && node shots.js dashboard-clean && node shots.js observatory && node sim.js && python3 sheet.py
```

The whole set takes about 25 minutes, most of it the observatory's 54 views. `node shots.js <surface>` alone redoes one surface. The rest of the evidence:

```bash
node axe.js && node probe.js all && node obs-verify.js && node obs2.js && node obs3.js && node ia.js && node prov.js && node charts.js && node wall.js && python3 tokens.py
```

`tokens.py` and `sheet.py` write straight into `docs/design/audit/`; the rest write JSON there too. All paths inside the scripts are absolute and will need editing on another machine.

## The first four questions for the next phase

They are set out with their evidence at the end of the report. In short: which token canon wins, given that the Claude Design values appear in zero files; the provenance word list, given seven vocabularies in production; whether the observatory is frozen or rebuilt, given that the landing's only CTA points at it and it points at no node; and whether the dark register is allowed, given that the FCI ruling leaves it open by name and its own blue reaches 1.60:1 on its own dark ground.
