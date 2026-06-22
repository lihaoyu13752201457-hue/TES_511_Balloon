# TES_511_Balloon

Detector-coupled simulation workspace for a balloon-borne focused 511 keV TES Laue-lens telescope.

Current paper-facing branch: fix5 multi-hole-W geometry.

Current geometry:

- `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

Current fix5 entry points:

- `AGENTS.md`: active task contract pointer.
- `core_md/README.md`: compact fix5 authority index.
- `core_md/fix5_benchmarks.json`: single machine-readable numeric authority.
- `core_md/METHOD_FIX5_SIM_CLOSURE.md`: method and normalization contract.
- `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`: gate contract.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/`: final fix5 closure and promotion artifacts.
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/`: detector-response/time-axis output.
- `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`: mission-time fold.
- `stepwise_maintenance/step07_source_cases/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`: source-case ledger.
- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`: significance outputs.
- `stepwise_maintenance/step09_optics_bridge/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/`: fix5 focused-signal replay.
- `core_md/balloon511_nima_latex_drafts/`: manuscript drafts.

Legacy v3p5, BGO, prompt511, new_geo_re, smoke, and old review assets live under `old/`.

Large local transport products under `runs/` remain ignored unless explicitly promoted to a tracked summary.
