# Source Normalization Audit 20260623

Created UTC: 2026-06-23T08:38:09+00:00

This audit records the unit trail behind the manuscript-facing fix5 quantities. It is not a replacement for the fix5 closure authority files.

## Source Classes

### atmospheric_prompt_fix5

- Status: `current`
- Description: EXPACS/PARMA-derived full-sphere prompt cosmic source cards for fix5 geometry.
- Primary source: `outputs/reports/fix5_fullstat_v2/fix5_source_manifest.json` (json_pointer:/source_surface and /source_generation)
- Linked quantities: fix5_prompt_selected_rate_day15_w2, fix5_day15_selected_background_w2
- Equation `prompt_transport_normalization`: `selected_prompt_rate = selected_events / sum(TT_over_jobs)`; source `core_md/METHOD_FIX5_SIM_CLOSURE.md` (section 2).
- Equation `Step05_prompt_rule`: `prompt_rate_rule = 1/sum(TT)`; source `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` (json_pointer:/normalization/prompt_rate_rule).
- Unit check `prompt TT closure` = `1.0` dimensionless; source `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` (json_pointer:/normalization/prompt_normalization_audit/rate_times_tt_sum).
- Unit check `W2 prompt selected rate` = `0.036641023029691425` s^-1; source `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` (json_pointer:/prompt_cps).

### activation_delayed_fix5

- Status: `current_pi02_minimum_convergence_screen_done`
- Description: Day-15 activation delayed background with ground-state half-life correction and exact-position source sampling.
- Primary source: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` (json_pointer:/source_mode, /fixed_total_activity_Bq, /n_pointsource_blocks, /source_text_flux_relative_delta)
- Linked quantities: fix5_delayed_selected_rate_day15_w2, fix5_delayed_source_activity_day15
- Equation `ground_state_decay_constant`: `lambda = ln(2) / T_half_ground_state`; source `core_md/METHOD_FIX5_SIM_CLOSURE.md` (section 3.1).
- Equation `per_family_TT_division_guard`: `activation production is divided by source-family live time, not repeatedly by global TT`; source `core_md/METHOD_FIX5_SIM_CLOSURE.md` (section 3.2).
- Equation `delayed_rate_uncertainty`: `combined sigma = sqrt(sum selected_events) / sum(TE_s); relative = 1/sqrt(sum selected_events)`; source `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` (json_pointer:/combined and /runs).
- Unit check `old_total_activity_Bq` = `87.48329383240524` Bq; source `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json` (json_pointer:/old_total_activity_Bq).
- Unit check `new_total_activity_Bq` = `85.44920253876245` Bq; source `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json` (json_pointer:/new_total_activity_Bq).
- Unit check `normalization_status` = `PASS` status; source `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json` (json_pointer:/status).
- Unit check `selected_events` = `103` events; source `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` (json_pointer:/combined/selected_events).
- Unit check `relative_uncertainty` = `0.09853292781642932` dimensionless; source `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` (json_pointer:/combined/relative_uncertainty).
- Unit check `selected_rate_cps` = `0.0022127821289687215` s^-1; source `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` (json_pointer:/combined/selected_rate_cps).
- Convergence status: PI-02 DONE with four production-position samplings, 103 combined selected events, relative uncertainty 0.09853292781642932, and between-sampling check PASS.

### focused_signal_fix5

- Status: `current`
- Description: Focused 511 keV point-source replay through optics and detector response.
- Primary source: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` (json_pointer:/science_physical_normalization)
- Linked quantities: fix5_selected_signal_w2_F1e-4, fix5_selected_effective_area, fix5_Z20d_w2, fix5_F3_20d_w2
- Equation `selected_effective_area`: `A_sel = selected_signal_rate / F0`; source `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` (lines 122-128).
- Equation `significance`: `Z20d from Step08 using Step06 time-dependent background and science rates`; source `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json` (json_pointer:/results/A_point_w2_510p58_511p42_F0.0001).
- Unit check `A_sel = 0.00118587480749719 / 1e-4` = `11.8587480749719` cm^2; source `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/t3_t5_summary.csv` (row analysis_case_id=A_point_w2_510p58_511p42_F0.0001).
- Unit check `Z20d` = `7.79950030715189` sigma; source `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json` (json_pointer:/results/A_point_w2_510p58_511p42_F0.0001/Z20d).
- Unit check `F3_20d` = `3.8464002588077305e-05` ph cm^-2 s^-1; source `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json` (json_pointer:/results/A_point_w2_510p58_511p42_F0.0001/F3_20d_ph_cm2_s).

### upstream_ge_proxy_archived

- Status: `archived_with_corrected_upper_limit`
- Description: Archived upstream-optics Ge proxy activation upper-limit calculation.
- Primary source: `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json` (json_pointer:/total_activity_Bq, /generated_events_seen, /analysis_windows/W2/final_selected_events)
- Linked quantities: upstream_ge_proxy_upper_rate_corrected
- Equation `corrected_zero_count_upper_rate`: `-ln(0.05) / (generated_decays / total_activity_Bq)`; source `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` (lines 77-111).
- Unit check `corrected 95 pct upper rate` = `6.376e-05` cps; source `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` (lines 84-85).
- Unit check `deprecated TE based upper rate` = `0.00012534045848433615` s^-1; source `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json` (json_pointer:/zero_count_upper_limits/W2/final_rate_s-1).

## Sanity Checks

- `source_cards_fix5_geometry`: `PASS` from `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (json_pointer:/checks/source_cards_geometry).
- `job_sources_fix5_geometry`: `PASS` from `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (json_pointer:/checks/job_sources_geometry).
- `sim_headers_fix5_geometry`: `PASS` from `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (json_pointer:/checks/sim_header_geometry).
- `benchmark_alignment_old_new_geo_re`: `NOT_ALIGNED_REPORT_ONLY` from `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` (json_pointer:/decision).

## Machine-Readable Index Notes

- `parma_expacs_inputs.activation_delayed_fix5` is not an EXPACS/PARMA direct input. It points to `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` and the ground-state audit for the activation-derived delayed source normalization.
- `parma_expacs_inputs.upstream_ge_proxy_archived` is an archived upstream Ge proxy activation upper-limit input, not a current fix5 EXPACS/PARMA source. Its archived activity, generated decay count, and selected-event count are traced to `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json`.
- `megalib_cards.focused_signal_fix5` is traced through the focused 511 keV Step05/Step08 summaries rather than an atmospheric source-card family.
- The `benchmark_alignment_old_new_geo_re` status remains `NOT_ALIGNED_REPORT_ONLY` intentionally. It is a method caveat for the old prompt comparison, not a missing artifact to force-pass.
