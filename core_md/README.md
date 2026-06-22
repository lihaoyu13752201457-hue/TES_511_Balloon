# Fix5 Current Authority Index

This directory now keeps the active fix5 simulation-closure contract only. Legacy
v3p5, BGO, prompt511, old `new_geo_re`, and historical review notes were moved
to `old/docs/core_md_legacy/`.

## Current Geometry

`outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

## Required Contract Files

- `fix5_benchmarks.json`: single numeric authority.
- `METHOD_FIX5_SIM_CLOSURE.md`: what Step02/05/06/07/08 and delayed normalization compute.
- `GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`: task guide and changed assumptions.
- `CONSTRAINTS_FIX5_SIM_CLOSURE.md`: enforced gates.
- `PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md`: startup checklist.
- `PROMPT_NEW_CHAT_FIX5_SIM_CLOSURE_20260622.md`: handoff prompt.

## Current Outputs

- `outputs/reports/user_redesign_multiholeW_fix5_20260621/`: geometry audit and visual material.
- `outputs/reports/fix5_1of10/`: 1/10 screen artifacts retained for provenance.
- `outputs/reports/fix5_fullstat_v2/`: full-stat source and transport release artifacts.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/`: final closure, W activation audit, and promotion decision.

## Current Stepwise Products

- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/`
- `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`
- `stepwise_maintenance/step07_source_cases/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`
- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`
- `stepwise_maintenance/step09_optics_bridge/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`

The focused-signal replay still consumes the retained optics EventList at
`stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/`; this is a
current fix5 input, not a v3p5 detector-background authority.

## Legacy Location

`old/README.md` lists the archived code, data, reports, old geometries, and
historical documents.
