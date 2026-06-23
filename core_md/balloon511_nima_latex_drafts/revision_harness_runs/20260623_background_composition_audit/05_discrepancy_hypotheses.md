# 05 Discrepancy Hypotheses

INDEPENDENCE = SUBAGENT

Role: Local Data Auditor. Scope: classify local old/current discrepancy causes using current fix5/v3p5 outputs and old `new_geo_re` outputs only.

## Summary Verdict

NO_BUG: I found no local evidence for a current fix5 delayed normalization bug. Evidence: `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` `/rows/9/status=PASS`, `/rows/10/status=PASS`, `/rows/11/status=PASS`, `/rows/18/status=PASS`, `/rows/21/status=PASS`; `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` `/verdict/decision=DONE`.

WARN: old `new_geo_re` and current fix5 are not aligned enough for gate-style pass/fail comparisons. Evidence: `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` `/decision=NOT_ALIGNED`, `/selection_equivalence_status=UNVERIFIED`, `/normalization_equivalence_status=UNVERIFIED`; `core_md/fix5_benchmarks.json` `/benchmarks/new_geo_re/selection_definition=UNVERIFIED...`.

## DEFINITION_ONLY

PASS: part of the discrepancy is definition-only: old broad `480--550 keV` day15 rates are not W2 line-window or spot-cut rates. Evidence: `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md:807` says not to use broad `480-550 keV` day-15 final rates as W2 or spot-cut results; old broad delayed final is `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json` `/expectation_rates_by_stream_cps/delayed/final=2.31224086683797`, while old W2 delayed is `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv` row 9 `delayed_cps=0.15211317269106375`.

PASS: source-surface/normalization definitions differ. Evidence: `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` `/source_surface_or_far_field_normalization = NOT_ALIGNED_FOR_OLD_NEW_GEO_RE; fix5 uses FarFieldAreaSource radius_cm=60.`; old review evidence `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md:82` records old prompt normalization with `35 cm far-field`.

## PHYSICAL_MODEL_DIFFERENCE

PASS: the old delayed source inventory is much larger and CsI/I-128 dominated. Evidence: old `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json` `/delay_fix/new_total_activity_Bq=624.2710918319826`; old `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md:188` reports `Chain I-128 activity | 533.2757337939476 Bq`.

PASS: current fix5 has a much smaller fixed delayed source and audited zero selected W/collimator W2 contribution. Evidence: current `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` `/fixed_total_activity_Bq=85.44920253876245`, `/activity_slices/w_or_collimator_volume_activity_Bq=0.9860798278743999`; current `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json` `/checks/w_or_collimator_selected_events=0`, `/checks/w_or_collimator_fraction_of_delayed_selected_rate=0.0`.

PASS: current selected W2 composition is prompt-dominated, unlike old W2. Evidence: old W2 `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv` row 9 `prompt_cps=0.03223400479533992`, `delayed_cps=0.15211317269106375`; current `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` `/prompt_cps=0.036641023029691425`, `/delayed_cps=0.0025752034889400762`.

## STATISTICAL_LIMITATION

WARN: the single-seed current W2 delayed row has only 30 selected delayed events, although the four-sampling convergence artifact improves this to 103 selected events. Evidence: current `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` `/delayed_selected_events=30`, `/delayed_sigma_cps=0.0004701656803528284`; convergence `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` `/combined/selected_events=103`, `/combined/relative_uncertainty=0.09853292781642932`.

PASS: the old W2 final row has higher effective support than the current current single-seed delayed row, so some old/current rate-ratio precision differences are expected. Evidence: old `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv` row 9 `effective_catalog_events=366.68501714731394`; current `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` `/prompt_selected_events=54`, `/delayed_selected_events=30`.

## STALE_OR_PROVENANCE_RISK

WARN: old `new_geo_re` is explicitly historical for fix5 gates and under unverified selection/normalization alignment. Evidence: `core_md/fix5_benchmarks.json` `/benchmarks/new_geo_re/provenance = Old new_geo_re from the prompt-511 refix handoff. Legacy provenance under the 2026-06-12 review hold.`; `core_md/fix5_benchmarks.json` `/benchmarks/new_geo_re/selection_definition = UNVERIFIED...`; `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` `/decision=NOT_ALIGNED`.

WARN: current Step05 summary itself still labels Step06--Step08 regeneration as pending, while the later verifier/promotion artifacts report those steps consumed. Treat the promotion decision and verifier as the later authority for final fix5, not the stale pending text inside Step05. Evidence: current Step05 `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` `/pending/0 = Regenerate Step06--Step08...`; verifier `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` `/rows/16/status=PASS_NON_PROMOTION`, `/rows/18/status=PASS`; promotion decision `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` `/decision=PASS_FIX5_REPLACES_V3P5`.

## PROBABLE_BUG

NO_BUG: wrong current fix5 geometry in current source/SIM headers is not supported. Evidence: `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` `/rows/0/details/contains_forbidden_baseline_geometry=0`, `/rows/8/details/sim_headers_with_forbidden_baseline_geometry=0`, `/rows/11/details/geometry_ok=true`, `/rows/20/details/geometry_ok=true`.

NO_BUG: current delayed activity/source mismatch is not supported by the audited fixed-source and M-sampling records. Evidence: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` `/sum_flux_check_Bq=85.44920253876245`, `/fixed_total_activity_Bq=85.44920253876245`, `/sampling_audit/manifest_flux_relative_delta=0.0`, `/sampling_audit/source_text_flux_relative_delta=4.53631512934923e-10`.

NO_BUG: current per-family delayed over-normalization is not supported. Evidence: `runs/step02_delay_fix_fix5_fullstat_v2/normalization_audit_groundstate_fix.json` `/status=PASS`, `/problems=[]`, `/rows/6/division=8.0`, `/rows/6/rp_raw_total=251062.0`, `/rows/6/rp_scaled_total=31382.75`.

NO_BUG: current delayed cps dimension error is not supported. Evidence: `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` `/runs/0/selected_events=30`, `/runs/0/TE_s=11649.564832`, `/runs/0/selected_rate_cps=0.0025752034889400762`; same file `/combined/selected_events=103`, `/combined/total_TE_s=46547.736739`, `/combined/selected_rate_cps=0.0022127821289687215`.

## Ranked Local Explanation

1. PHYSICAL_MODEL_DIFFERENCE: old `new_geo_re` delayed activity is about `624.27 Bq`, dominated by `533.28 Bq` I-128 in CsI active shield; current fix5 fixed activity is `85.45 Bq` and the audited selected W2 delayed W/collimator contribution is zero.
2. DEFINITION_ONLY: old broad `480--550 keV` delayed (`2.31224 cps`) is not old W2 delayed (`0.152113 cps`), and current `100--10000 keV` apples-to-apples values are NOT_AVAILABLE.
3. STALE_OR_PROVENANCE_RISK: old `new_geo_re` has `UNVERIFIED` selection definition and fix5 benchmark alignment is `NOT_ALIGNED`, so old values are report-only.
4. STATISTICAL_LIMITATION: current selected delayed is low-count per seed, but the four-sampling convergence screen reaches 103 selected events and relative uncertainty `0.0985`.
5. PROBABLE_BUG: not supported by the local authority artifacts reviewed here.
