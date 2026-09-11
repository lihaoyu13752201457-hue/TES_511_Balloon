# EXEC / Integration Summary

Generated: 2026-07-07

2026-07-08 update: downstream atmospheric-511 interpretation now uses the
4pi EXPACS-like sidecar replay in
`engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/`.
The 2026-07-07 lower-hemisphere replay is retained as provenance only and is
not the current geometry-optimization conclusion.

Scope: XHGIH execution branch plus parent integration. No original `511_Mass`,
`Mass_model_511`, fix5 authority geometry, or paper-facing authority outputs
were modified.

## Current-Geometry Ingress And Veto Audit

Primary outputs:

- `ingress_summary.csv`
- `ingress_summary.json`
- `ingress_summary.md`
- `ingress_aggregate_summary.csv`
- `veto_efficiency_summary.csv`
- `veto_efficiency_summary.json`
- `veto_efficiency_summary.md`
- `veto_efficiency_by_source_window_stage.csv`
- `veto_efficiency_by_ingress_region.csv`
- `side_compton_class_counts.csv`

Scripts:

- `build_ingress_veto_audit.py`
- `build_ingress_veto_audit_fast.py`

The slow audit script was implemented by XHGIH-EXEC but timed out during its
bounded run. Parent integration added and ran `build_ingress_veto_audit_fast.py`.
The fast script uses the same denominator convention and avoids rescanning the
full atmospheric SIM except for the final atmospheric W2 event IDs.

W2 current geo-opt cutflow:

| family | raw | active pass | final pass | active rejection | Compton/FoV rejection vs active | final survival |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `eplus` | 62 | 40 | 35 | 0.354839 | 0.125000 | 0.564516 |
| `n` | 60 | 13 | 13 | 0.783333 | 0.000000 | 0.216667 |
| `atm511` | 114 | 114 | 107 | 0.000000 | 0.061404 | 0.938596 |

Definitions:

- active anticoincidence rejection = `1 - active_veto_pass / raw`
- Compton/FoV rejection = `1 - side_compton_fov_pass / active_veto_pass`
- total rejection = `1 - side_compton_fov_pass / raw`

Ingress caveat: prompt `eplus` and `n` use `IA INIT` ray/envelope-intersection
proxies, not a Geant4 boundary-crossing scorer. Atmospheric 511 raw/active/final
cutflow comes from the full 2026-07-08 4pi sidecar replay; atmospheric
ingress-region rows are only for the 107 final W2 candidates.

## Atmospheric 511 Replay

Current replay script:

- `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/build_geo_opt_atm511_sidecar_replay.py`

Current replay outputs:

- `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json`
- `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/atm511_sidecar_s1_nominal_bin_fluxes.csv`
- `engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/atm511_sidecar_systematic_scenarios.csv`

Status: `PASS_GEO_OPT_S1_BPE_W5_ATM511_4PI_SIDECAR_REPLAY`

Evidence:

- generated events: `3000000`
- observation time: `5146.38 s`
- geometry header: `engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- source model: EXPACS-like semi-empirical atmospheric 511-keV line sidecar,
  20 equal-mu bins over `theta=0..180 deg`
- nominal 4pi line flux: `0.0515558541132 ph cm^-2 s^-1`
- W2 raw/active/final: `114/114/107`
- broad 480-550 raw/active/final: `146/146/135`
- W2 final nominal rate: `0.0207913135058 cps`
- W2 final transfer: `0.403277452453 cps/(ph cm^-2 s^-1 4pi line flux)`
- sidecar-included W2 background: `0.0561719296626 cps`
- sidecar-included W2 `F3(20d)`: `4.62986036016e-05 ph cm^-2 s^-1`

This replay still shows no active anticoincidence rejection of atmospheric 511
W2 candidates; the W2 rejection is from side Compton/FoV only. The final
candidate entry proxy distribution is side-wall dominated: side_wall `74`,
top `24`, bottom `7`, side_window `2`.

## W-Barrel Hypothesis Geometry

Builder:

- `build_barrel_hypothesis_geometry.py`

Generated geometry package:

- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo.setup`
- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo`
- `geometry/Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.det`
- `geometry/Materials_Hyp_BarrelW_TES_CsI_ExternalSupport_20260707.geo`
- `barrel_hypothesis_geometry_manifest.json`

Figures:

- `figures/hyp_barrel_w_tes_csi_2d_detail.png`
- `figures/hyp_barrel_w_tes_csi_2d_detail.svg`
- `figures/hyp_barrel_w_tes_csi.wrl`

Geometry contents:

- Retained: TES/TES-pixel structure, CsI scintillator positions/shapes,
  `InstrumentFrame`/world container, and `NF2_OuterSupport_*` external supports.
- Removed: internal cryostat/passive shells, DR/cold structures, old window
  stack, and current GeoOpt plastic/BPE/W add-ons.
- Added: passive W barrel and thin Al side window.
- Active veto convention for this hypothesis: CsI only. Passive W/Al deposits
  are not active veto.

Barrel parameters:

- W inner radius: `30.0 cm`
- W outer radius: `33.0 cm`
- side z range: `-25.0 cm` to `10.0 cm`
- cap thickness: `3.0 cm`
- thin Al side window: `0.5 mm` total thickness
- W mass: about `797.26 kg`

This is an engineering stress-test geometry, not a deployable payload design.

## Positron-Only Barrel Runs

Run directory:

- `runs/geometry_optimization_20260704/barrel_eplus_hypothesis_20260707/`

Completed:

- 1-event load check: `Background_eplus_barrelW_loadcheck.source`
- 200k e+ smoke: `Background_eplus_barrelW_smoke.source`

Smoke analysis outputs:

- `barrel_eplus_smoke_summary.csv`
- `barrel_eplus_smoke_summary.json`
- `barrel_eplus_smoke_summary.md`
- `barrel_eplus_smoke_events.csv`

Smoke result:

- generated events: `200000`
- observation time: `85.1781 s`
- W2 raw/active/final: `0/0/0`
- broad 480-550 raw/active/final: `0/0/0`

Completed after integration:

- `Background_eplus_barrelW_2M.source`

The 2M run uses the same positron source family, the same barrel geometry, and
independent seed `260708`. It is still positron-only and still not an all-particle
or 20-day closure run.

2M analysis outputs:

- `barrel_eplus_2M_summary.csv`
- `barrel_eplus_2M_summary.json`
- `barrel_eplus_2M_summary.md`
- `barrel_eplus_2M_events.csv`

2M result:

- generated events: `2000000`
- observation time: `851.448 s`
- W2 raw/active/final: `0/0/0`
- broad 480-550 raw/active/final: `0/0/0`
- zero-count one-sided 95% upper rate: `0.00351839721692 cps`

Compared with current geo-opt e+ W2 final rate `0.0237663402077 cps`, the 2M
zero-count 95% upper limit is `14.8%` of the current final rate. This is a
positron-only hypothesis result, not an all-particle background closure.

## Review

Review artifacts:

- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review/REVIEW_PRECHECK.md`
- `engineering/geometry_optimization_20260704/08_ingress_veto_barrel_20260707_review/REVIEW_FINAL.md`

Final review status before the 2M extension: `PASS_WITH_LIMITATIONS`.

Known limitations:

- Atmospheric ingress-region rows are final-candidate-only and must not be read
  as per-region raw/active veto efficiencies.
- The barrel hypothesis removes many internal passive materials, so a reduction
  in e+ background can come from removing annihilation/scattering sites as well
  as from the external W barrel.
- Positron-only runs do not close all-particle background or 20-day sensitivity.
