# 04 Delay Normalization Audit

INDEPENDENCE = SUBAGENT

Role: Local Data Auditor. Scope: read-only audit of current fix5 delayed/prompt normalization and old `new_geo_re` delayed inventory evidence.

## Verdicts

- PASS: current fix5 geometry provenance is clean for source cards, job sources, prompt/buildup SIM headers, delayed SIM header, and signal SIM header. Evidence: `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` `/rows/0/details/contains_fix5_geometry=8`, `/rows/8/details/sim_headers_with_fix5_geometry=136`, `/rows/11/details/geometry_ok=true`, `/rows/20/details/geometry_ok=true`.
- PASS: current prompt normalization follows `1/sum(TT)`. Evidence: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` `/normalization/prompt_rate_rule = per-tag event rate = 1 / sum(TT_s for prompt dat files with that tag)`, `/normalization/prompt_normalization_audit/status = PASS`, `/normalization/prompt_normalization_audit/rows/2/rate_times_tt_sum = 1.0`.
- PASS: current delayed ground-state and per-family division guard pass. Evidence: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json` `/status = PASS_FIX5_GROUNDSTATE_HALF_LIFE_AUDIT`, `/checks/normalization_status = PASS`, `/checks/normalization_problems = []`; `runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json` `/status = PASS`, `/problems = []`, `/rows/6 = tag=n, files=8, division=8.0, rp_raw_total=251062.0, rp_scaled_total=31382.75`.
- PASS: current exact-position M-sampling inventory passes. Evidence: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` `/sampling_audit/status=PASS`, `/sampling_audit/parsed_pointsource_blocks=50000`, `/sampling_audit/manifest_flux_relative_delta=0.0`, `/sampling_audit/source_text_flux_relative_delta=4.53631512934923e-10`, `/sampling_audit/matched_back_to_exact_table_fraction=1.0`, `/sampling_audit/ambiguous_coordinate_key_fraction=0.0`, `/sampling_audit/missed_nuclides_total_activity_fraction=0.0001463401094264377`.
- PASS: current W/collimator activation is audited and not a selected W2 component. Evidence: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json` `/checks/w_or_collimator_new_activity_Bq=0.9860798287567217`; `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json` `/checks/w_or_collimator_selected_events=0`, `/checks/w_or_collimator_selected_rate_hz=0`, `/checks/w_or_collimator_fraction_of_delayed_selected_rate=0.0`.
- PASS: current delayed selected-rate convergence meets the PI-02 local screen. Evidence: `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` `/combined/independent_production_position_samplings=4`, `/combined/selected_events=103`, `/combined/selected_rate_cps=0.0022127821289687215`, `/combined/relative_uncertainty=0.09853292781642932`, `/combined/between_sampling_check=PASS`, `/verdict/decision=DONE`.
- NO_BUG: no local evidence was found for the current delayed cps using `1e6` decays as seconds, using `TE_s` as activity, or double-counting activity. Evidence: `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` `/runs/0/selected_events=30`, `/runs/0/TE_s=11649.564832`, `/runs/0/selected_rate_cps=0.0025752034889400762`; same file `/combined/selected_events=103`, `/combined/total_TE_s=46547.736739`, `/combined/selected_rate_cps=0.0022127821289687215`.
- WARN: old `new_geo_re` is not current fix5 authority. Evidence: `core_md/fix5_benchmarks.json` `/benchmarks/new_geo_re/selection_definition = UNVERIFIED...`; `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` `/selection_equivalence_status=UNVERIFIED`, `/normalization_equivalence_status=UNVERIFIED`, `/decision=NOT_ALIGNED`.

## Old new_geo_re Delayed Chain

Old day15 ground-state-fixed delayed activity is `624.2710918319826 Bq` with `5968` source blocks after fix. Evidence: `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json` `/delay_fix/new_total_activity_Bq=624.2710918319826`, `/delay_fix/source_blocks_after_fix=5968`, `/delay_fix/fixed_source_contains_W183=false`, `/delay_fix/fixed_source_contains_W180=false`.

Old activation is dominated by CsI/I-128. Evidence: `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md:188` reports `Chain I-128 activity | 533.2757337939476 Bq`; `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/activation_inventory_day15_after_groundstate_fix.csv` row 2 has `CsI_Active_Shield_Bottom03,I-128,Activity_Bq_after_fix=49.832546179576646`.

Old prompt source normalization differs from current fix5. Evidence: `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json` `/normalization/prompt_time_s=541.3815137522625`; `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md:82` records `35 cm far-field, area πR²=3848.45 cm², gamma time ... 541.38 s`.

## Current fix5 Delayed Chain

Current fixed delayed source activity is `85.44920253876245 Bq`, exact-position M-sampling uses `50000` equal-flux `PointSource` blocks, and W/collimator activity is `0.9860798278743999 Bq` (`~1.154%` of fixed activity). Evidence: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` `/fixed_total_activity_Bq=85.44920253876245`, `/n_pointsource_blocks=50000`, `/flux_per_pointsource_Bq=0.001708984050775249`, `/activity_slices/w_or_collimator_volume_activity_Bq=0.9860798278743999`.

Current top delayed source activity is still CsI/I-128, but at a much smaller total scale than old `new_geo_re`. Evidence: `runs/step02_delay_fix_fix5_fullstat_v2/groundstate_activity_corrections.csv` row 2 has `CsI_Bottom_Quadrant_03,I-128,new_groundstate_activity_Bq=7.822245023524668`; row 23 has `Passive_W_Bottom_Plate_detector_bay,W-187,new_groundstate_activity_Bq=0.9319387837983522`.

Current prompt source surface is a fix5 full-sphere far-field source with radius `60 cm`. Evidence: `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json` `/source_plane/atmospheric_prompt_fix5/radius_cm=60.0`, `/source_plane/atmospheric_prompt_fix5/area_cm2=11309.733552923255`; current Step05 summary `/normalization/prompt_time_s=184.2200984295893`.

## Local Conclusion

The current fix5 delayed normalization chain has no reproducible local normalization bug from the audited artifacts. The old/current delayed composition split is mainly explained by different source inventory scale, source geometry/material/selection response, exact-position handling, and unaligned source-surface/selection definitions. The old chain is useful historical context, but the local files do not support using old delayed rates as a current fix5 authority.
