# Evidence Drill-Down Prototype — F004 / #5

Self-contained static prototype: open `index.html` in any browser. No build step, no network.

Lead reviewed/repaired 27 September. Invented EUR figures; not a live actuarial calculation or complete numerical trace. The subtotal excludes the unavailable 2025 origin. Export buttons preview content; no files are downloaded. Bright analysis surface retained; final spatial graph design and workbench integration remain pending.

## Run instructions

```
open index.html
```

Or serve locally for best cursor behaviour:
```
cd prototype/evidence-drilldown
python3 -m http.server 8080 --bind 127.0.0.1
# open http://localhost:8080
```

## Click-through walkthrough

### L0 — Workspace Summary (default)
1. **Review subtotal** card: teal accent, explicitly incomplete and synthetic. Click to inspect fixture provenance.
2. **Model narrative** node: violet badge, labelled "model narrative — never a calculation input". Cannot feed into any calculation.
3. **Origin rows**: click to expand — assumptions → factors → source cells in drill order (headline → origins → assumptions → factors → cells).
4. **Observed zero**: separate zero observation under Origin 2023 shows €0 with observed/outside-window badges; not a missing value or a member of the displayed pair.
5. **Exclusion with rationale**: Scenario A (amber "excluded" badge + rationale) vs Scenario B (green "included") — same observation, no source mutation.
6. **Unavailable-blocked**: Origin 2025 paid development evidence — no invented factor or reserve value.

### L1 — Node Payloads + Paginated Adjacency
7. Click Connected evidence. Use Prev/Next to page through the three origins with a stable fixture cursor. Click an origin to return to its expanded overview. This is an in-memory UI simulation, not the production graph cursor contract.

### L2 — On-Demand Blobs
8. Click Source details and select a card to inspect actual synthetic fixture JSON. No claim records or complete actuarial trace are claimed.

### Export Policy
9. Click Local review preview to inspect a sample policy and reference shape.
10. Click Public synthetic preview to inspect the public fixture shape. These are previews only.

## Evidence states to verify

| State | Where to look |
|---|---|
| Observed zero | Origin 2023 Q1 cell |
| Excluded / included same source | Scenario compare section |
| Unavailable-blocked | Origin 2025 factor + cell |
| Future availability | Not in this fixture (reserved for extension) |
| Validation outcomes | valid / warning / invalid badges |
| Fitting membership | included / excluded / outside-window badges |
| Lazy levels | L0/L1/L2 nav buttons |
| Provenance | Click any card |
| Export policy | Sidebar preview buttons; no downloads |

## Browser regression check

`browser-smoke.cjs` requires Node >=20, Playwright resolvable by Node, and Chrome. With the local server running:

```sh
node browser-smoke.cjs http://127.0.0.1:8080
```

If Playwright is installed elsewhere, set NODE_PATH to its node_modules directory. The authoring environment supplies it through `artifacts/workbook-authoring/node_modules`; that dependency is not bundled for public clones.

Verified: pagination forward/back, three-level expansion, observed zero, blocked origin, missing provenance, keyboard card activation, source details, export preview and 390px horizontal overflow. No page errors. Desktop/mobile screenshots inspected. Original empty adjacency and narrative-provenance crash reproduced before repair. JS syntax alone had missed both. This is interaction verification, not numerical/model/security certification or final visual acceptance.

## JS syntax check

```
node --check app.js
```
