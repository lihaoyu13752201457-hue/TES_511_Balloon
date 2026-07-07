# Final Completion Audit

Date: 2026-07-07

Status: `COMPLETE_FOR_REQUESTED_HYPOTHESIS_WITH_LIMITATIONS`

Scope: user-requested ingress/veto statistics, W-barrel hypothesis geometry, and
positron-only barrel transport. This is not a promotion to an all-particle
background model or 20-day sensitivity result.

## Requirement Checklist

| Requirement | Evidence | Result |
| --- | --- | --- |
| 1. Count where `e+`, `n`, and atmospheric 511 enter | `ingress_summary.json`, `ingress_summary.csv`, `ingress_aggregate_summary.csv`, `ingress_summary.md` | Done with IA-INIT ray/envelope entry proxies; not a Geant4 boundary scorer. |
| 2. Determine active-veto and Compton/FoV veto performance | `veto_efficiency_summary.json/csv/md`, atmospheric replay summary | Done with correct denominators. |
| 3. Create new hypothesis geometry retaining TES, CsI, and external supports; add W barrel and thin Al side window | `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.*`, `barrel_hypothesis_geometry_manifest.json`, WRL and 2D detail figure | Done. Original `511_Mass` / `Mass_model_511` geometries were not modified. |
| 4. Run positron-only test on the new geometry | `Background_eplus_barrelW_2M.*`, `barrel_eplus_2M_summary.*` | Done: 2M e+ only, zero TES-window candidates. |
| 5. Use two XHGIH subagents, parent plans | `PLANNING.md`, `EXEC_SUMMARY.md`, review directory | Done. XHGIH-EXEC implemented the package; XHGIH-REVIEW signed off with limitations. |

## Current-Geometry Veto Performance

W2 window: `510.58-511.42 keV`.

| family | raw | active pass | final pass | active rejection | Compton/FoV rejection vs active | final survival |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `eplus` | 62 | 40 | 35 | 35.48% | 12.50% | 56.45% |
| `n` | 60 | 13 | 13 | 78.33% | 0.00% | 21.67% |
| `atm511` | 108 | 108 | 95 | 0.00% | 12.04% | 87.96% |

Denominators:

- active rejection = `1 - active_veto_pass / raw`
- Compton/FoV rejection = `1 - final / active_veto_pass`
- total rejection = `1 - final / raw`

Atmospheric 511 replay:

- input: `3,000,000` lower-hemisphere mono-511 events
- observation time: `265.314 s`
- W2 final transfer: `0.358066291262 cps/(ph cm^-2 s^-1)`
- Harris Rc~11-13 added background: `0.00834351749248 cps`
- Harris-included W2 background: `0.0437241336493 cps`
- Harris-included `F3(20d)`: `4.08478147108e-05 ph cm^-2 s^-1`

## Where Final W2 Candidates Enter

These are final W2 `side_compton_fov_pass` candidate entry proxies from
`ingress_summary.json`.

| family | final events | entry-surface distribution | first-hit category highlights |
| --- | ---: | --- | --- |
| `eplus` | 35 | side 13, top 11, current-envelope miss 11 | GeoOpt plastic active 17, outer mechanics 11, TES 7 |
| `n` | 13 | top 6, current-envelope miss 3, side 2, bottom 2 | other 4, GeoOpt plastic active 2, G10 passive 2, CsI active 2 |
| `atm511` | 95 | side 73, top 14, bottom 8 | TES 95 |

Dominant atmospheric 511 final entry sectors:

- `side_phi00_000deg`: 16
- `side_phi07_315deg`: 16
- `side_phi01_045deg`: 16
- `side_phi02_090deg`: 12
- `side_phi06_270deg`: 10

Atmospheric ingress-region rows are final-candidate-only. They must not be read
as atmospheric raw/active per-region veto efficiencies.

## Barrel Hypothesis Geometry

Package:

- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`
- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo`
- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.det`
- `geometry/Materials_Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo`
- `figures/hyp_barrel_w_tes_csi.wrl`
- `figures/hyp_barrel_w_tes_csi_2d_detail.png`

Geometry status:

- retained TES/TES pixels, CsI positions/shapes, `InstrumentFrame`/world, and
  `NF2_OuterSupport_*` external supports
- removed internal cryostat/passive shell/DR/cold/window-stack/current GeoOpt
  plastic/BPE/W add-ons for this simplified hypothesis
- added passive W barrel and thin Al side window
- active veto for barrel analysis: CsI only at 50 keV; passive W/Al deposits are
  not veto

W barrel parameters:

- inner radius: `30.0 cm`
- outer radius: `33.0 cm`
- side z range: `-25.0..10.0 cm`
- cap thickness: `3.0 cm`
- thin Al side window total thickness: `0.5 mm`
- W mass: about `797.26 kg`

This is a stress-test geometry, not a deployable balloon mass design.

## Positron-Only Barrel Result

Run:

- source card: `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_2M.source`
- SIM: `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/Background_eplus_barrelW_2M.inc1.id1.sim.gz`
- log: `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/cosima_Background_eplus_barrelW_2M.log`
- generated particles: `2,000,000`
- observation time: `851.448 s`
- SIM header geometry: `Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`

Analysis:

- `barrel_eplus_2M_summary.json`
- `barrel_eplus_2M_summary.csv`
- `barrel_eplus_2M_summary.md`
- `barrel_eplus_2M_events.csv`

Result:

| window | raw | active pass | final pass | zero-count 95% upper rate |
| --- | ---: | ---: | ---: | ---: |
| `w2_510p58_511p42` | 0 | 0 | 0 | `0.00351839721692 cps` |
| `broad_480_550` | 0 | 0 | 0 | `0.00351839721692 cps` |

Compared with the current geo-opt W2 e+ final rate
`0.0237663402077 cps`, the 2M zero-count 95% upper rate is about `14.8%` of
the current e+ component.

## Review Status

Review artifacts:

- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review/REVIEW_PRECHECK.md`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review/REVIEW_FINAL.md`

Final review verdict: `PASS_WITH_LIMITATIONS`.

Important limitations:

- e+ barrel result is positron-only; it is not all-particle background closure.
- It is not a 20-day sensitivity result.
- The simplified barrel geometry removes many internal passive materials, so the
  e+ reduction is a combined effect of simplification plus external shielding,
  not a pure W-barrel-only attribution.
- Atmospheric 511 has no active-veto rejection in the replay; its W2 rejection
  is only side Compton/FoV.
