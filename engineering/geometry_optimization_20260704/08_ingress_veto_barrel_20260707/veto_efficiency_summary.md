# Ingress And Veto Audit

Generated: `2026-07-07T16:53:30Z`

Scope: current `geo_opt_s1_bpe_w5_fullstat_v1` W2 candidates only.

Ingress definition: `IA INIT` is read from each SIM event.  The entry surface is a proxy from the INIT ray intersecting the current geo-opt outer envelope in instrument-local coordinates: radius 27.9 cm, z -23.6..7.7 cm, inverse 45 deg Y rotation.  This is not a Geant4 boundary-crossing scorer.

Veto definition: active anticoincidence is `active_veto_keV < 50 keV`, with CsI/BGO/legacy active names and `GeoOpt_S1_PlasticFullWrap*` counted as active.  Compton/FoV veto reuses `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py` with `reject_policy=keep`.

## Veto Cutflow

| family | raw | active pass | final pass | active rejection | Compton/FoV rejection vs active | final survival |
|---|---:|---:|---:|---:|---:|---:|
| eplus | 62 | 40 | 35 | 0.355 | 0.125 | 0.565 |
| n | 60 | 13 | 13 | 0.783 | 0.000 | 0.217 |
| atm511 | 114 | 114 | 107 | 0.000 | 0.061 | 0.939 |

## Dominant Final Entry Proxies

| family | entry proxy | events | fraction |
|---|---|---:|---:|
| atm511 | side_phi07_315deg | 17 | 0.159 |
| atm511 | side_phi00_000deg | 16 | 0.150 |
| atm511 | side_phi01_045deg | 13 | 0.121 |
| atm511 | side_phi06_270deg | 11 | 0.103 |
| atm511 | side_phi02_090deg | 10 | 0.093 |
| atm511 | top_phi00_000deg | 8 | 0.075 |
| atm511 | top_phi01_045deg | 6 | 0.056 |
| atm511 | top_phi07_315deg | 5 | 0.047 |
| atm511 | side_phi05_225deg | 4 | 0.037 |
| atm511 | side_phi04_180deg | 2 | 0.019 |
| atm511 | bottom_phi04_180deg | 2 | 0.019 |
| atm511 | top_phi05_225deg | 2 | 0.019 |
| atm511 | top_phi02_090deg | 2 | 0.019 |
| atm511 | side_neg_x_window_axis_pm15deg | 2 | 0.019 |
| atm511 | bottom_phi07_315deg | 2 | 0.019 |
| atm511 | bottom_phi02_090deg | 1 | 0.009 |
| atm511 | side_phi03_135deg | 1 | 0.009 |
| atm511 | bottom_phi01_045deg | 1 | 0.009 |
| atm511 | top_phi04_180deg | 1 | 0.009 |
| atm511 | bottom_phi05_225deg | 1 | 0.009 |
| eplus | phi04_180deg | 4 | 0.114 |
| eplus | top_phi00_000deg | 3 | 0.086 |
| eplus | top_phi02_090deg | 3 | 0.086 |
| eplus | side_phi00_000deg | 3 | 0.086 |
| eplus | side_phi06_270deg | 3 | 0.086 |
| eplus | top_phi05_225deg | 2 | 0.057 |
| eplus | top_phi01_045deg | 2 | 0.057 |
| eplus | phi00_000deg | 2 | 0.057 |
| eplus | side_phi05_225deg | 2 | 0.057 |
| eplus | side_phi03_135deg | 2 | 0.057 |
| eplus | phi06_270deg | 1 | 0.029 |
| eplus | phi03_135deg | 1 | 0.029 |
| eplus | phi05_225deg | 1 | 0.029 |
| eplus | phi01_045deg | 1 | 0.029 |
| eplus | phi02_090deg | 1 | 0.029 |
| eplus | side_phi02_090deg | 1 | 0.029 |
| eplus | side_phi07_315deg | 1 | 0.029 |
| eplus | side_neg_x_window_axis_pm15deg | 1 | 0.029 |
| eplus | top_phi06_270deg | 1 | 0.029 |
| n | top_phi06_270deg | 2 | 0.154 |
| n | side_phi01_045deg | 1 | 0.077 |
| n | top_phi01_045deg | 1 | 0.077 |
| n | phi05_225deg | 1 | 0.077 |
| n | side_phi00_000deg | 1 | 0.077 |
| n | top_phi07_315deg | 1 | 0.077 |
| n | bottom_phi06_270deg | 1 | 0.077 |
| n | phi07_315deg | 1 | 0.077 |
| n | top_phi03_135deg | 1 | 0.077 |
| n | bottom_phi07_315deg | 1 | 0.077 |
| n | phi03_135deg | 1 | 0.077 |
| n | top_phi02_090deg | 1 | 0.077 |

## Files

- `ingress_summary.csv/json/md` from `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707`
- `veto_efficiency_summary.csv/json/md` from `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707`
- `veto_efficiency_by_source_window_stage.csv`, `veto_efficiency_by_ingress_region.csv`, `side_compton_class_counts.csv`
- Event records are embedded in `ingress_summary.json`; raw W2 event rows: `229`.

## Fast Audit Caveat

Atmospheric 511 veto efficiency is sourced from the full P2 replay summary. Atmospheric ingress-region breakdown is final-candidate only.
