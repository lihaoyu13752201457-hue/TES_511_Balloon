# Local Inventory Map

INDEPENDENCE = SINGLE_SESSION_DEGRADED
ROLE = Orchestrator
SCOPE = file inventory only; no physics/gate verdict is made here.

## Current fix5/v3p5 Authority And Audit Inputs

| Purpose | Path | Evidence locator | Notes |
|---|---|---|---|
| Numeric/gate authority | `core_md/fix5_benchmarks.json` | lines `1-17`, JSON `/benchmarks`, `/required_artifacts`, `/audit_thresholds` | Single machine-readable authority for geometry, screen target, promotion bar, thresholds, and artifact contracts. |
| Current fix5 promotion decision | `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` | JSON `/decision`, `/B_cps`, `/prompt_cps`, `/delayed_cps`, `/comparison_vs_v3p5`, `/comparison_vs_old_new_geo_re` | Current full-stat promotion artifact; Local Data Auditor must not treat old new_geo_re gate as aligned when `/comparison_vs_old_new_geo_re/benchmark_alignment_decision` is `NOT_ALIGNED`. |
| Current Step05 summary | `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` | JSON `/normalization`, `/windows/broad_480_550`, `/windows/w2_510p58_511p42`, `/timeline` | Current prompt/delayed/science stream rates at broad 480--550 and W2 windows. |
| Current Step05 rate table | `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv` | rows: broad and W2 stream/stage rates | Compact CSV equivalent of Step05 window rates. |
| Prompt/source normalization audit | `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json` | JSON `/source_classes/0`, `/sanity_checks`, `/unit_checks` | Links prompt source surface, `1/sum(TT)` rule, fix5 geometry proof, and benchmark-alignment status. |
| Current simulation config authority | `core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json` | JSON `/components` | Reproducibility metadata: Cosima/MEGAlib/Geant4, seeds, geometry, transport event counts. |
| Paper evidence manifest | `core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json` | JSON `/entries/0-13`, `/gate_notes` | Maps manuscript-facing quantities to current source artifacts. |
| Current delayed convergence | `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` | JSON `/combined`, `/between_sampling_check`, `/verdict` | PI-02 convergence screen: multiple exact-position samplings for delayed selected rate. |
| Fix5 source manifest | `outputs/reports/fix5_fullstat_v2/fix5_source_manifest.json` | JSON `/geometry_setup`, `/source_cards`, `/far_field_or_surrounding_sphere`, `/normalization_constants` | Source-card provenance, far-field/source-surface metadata. |
| Fix5 benchmark alignment | `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` | JSON `/decision`, `/gate_consequence` | Old `new_geo_re` numbers are report-only unless decision is `ALIGNED`. |
| Fix5 verifier verdict | `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` | JSON `/overall_status`, `/rows` | Deterministic source/SIM geometry and delayed normalization checks. |
| Ground-state half-life audit | `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json` | JSON `/checks`, `/w_or_collimator_rows`, `/problems` | NUBASE and W/collimator-origin delayed source audit. |
| Exact-position delayed source summary | `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json` | JSON `/fixed_total_activity_Bq`, `/n_pointsource_blocks`, `/sampling_audit`, `/activity_slices`, `/delayed_transport` | Activity conservation, M-sampling, transport geometry/TE metadata. |
| W activation selected W2 audit | `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json` | JSON `/checks`, `/top_source_volumes`, `/event_table` | Maps W2 delayed selected events back to source volumes and W/collimator flag. |
| W activation selected event table | `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_events.csv` | rows 2--31 | Event-level W2 delayed selected origin table. |

## Old new_geo_re Authority And Historical Inputs

| Purpose | Path | Evidence locator | Notes |
|---|---|---|---|
| Old project memory | `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md` | lines `35-44`, `422-448`, `506-516`, `521-540`, `575-578`, `807-814` | Records W2 headline, broad 480--550 final decomposition, common time-axis and mission fold, and warnings about not mixing broad/W2/spot results. |
| Old review log | `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md` | lines `40-82`, `153-180`, `190-202` | Internal consistency review and caveats around delayed source, veto, prompt far-field normalization, and time variation. |
| Old execution report | `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md` | lines `79`, `120-138`, `172-188` | Validator and W2 uncertainty; CsI activation/I-128 anchor. |
| Old day15 summary | `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json` | JSON `/normalization`, `/expectation_rates_by_stream_cps`, `/delay_fix` | Broad 480--550 final expectation stream decomposition and old source-fix summary. |
| Old component rates | `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/image8_like_component_rates_with_science.csv` | CSV rows 2--10 | Component rates for 100--5000, 100--10000, and 480--550. |
| Old 480--550 spectrum | `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/timeline_spectrum_480_550_rates.csv` | CSV rows 2--141 | 0.5 keV bins with raw/BGO/final timeline and expectation rates. |
| Old 100--10000 spectrum | `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/timeline_spectrum_100_10000_rates.csv` | CSV rows 2--991 | 10 keV bins with raw/BGO timeline/expectation rates; no final Compton/FoV column. |
| Old activation inventory | `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/activation_inventory_day15_after_groundstate_fix.csv` | CSV rows; group by `nuclide` and `VN` | Day15 ground-state-fixed inventory; Local Data Auditor must cite group totals and row/field evidence. |
| Old Step09 W1/W2 table | `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv` | CSV rows 2--9 | Raw/scintillator/Compton-FoV/both rates for W1 and W2; row 9 is W2 both. |

## Derived Inventory Anchors For Auditors

These are pointers for Phase 1, not Orchestrator verdicts.

- Current fix5 W2 final rates are available in Step05 summary/rates: window `w2_510p58_511p42`, stage `side_compton_fov_pass`, streams prompt/delayed/science.
- Current fix5 broad 480--550 rates are available in Step05 summary/rates, same stream/stage definitions.
- Old `new_geo_re` broad 480--550 final expectation decomposition is in `complete_day15_summary.json` `/expectation_rates_by_stream_cps` and component-level CSV row `ActivationDelay(day15)`.
- Old `new_geo_re` W2 raw/scintillator/Compton-FoV/both decomposition is in `non_xray_background_w1_w2_veto_table.csv` rows 6--9.
- Old and current source-surface normalizations are not aligned by contract: current uses fix5 FarFieldAreaSource radius 60 cm; old review log records 35 cm far-field and area pi R^2 = 3848.45 cm2. Evidence for old: `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md:82`; evidence for current: `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json` `/source_classes/0/source_plane`.

## Frozen Output Boundary

- Current fix5/v3p5 artifacts listed above are read-only authority/comparison inputs for this harness.
- Old `/home/ubuntu/codex_tes_511_sim/new_geo_re` artifacts are read-only historical inputs.
- No geometry output, source card, run directory, Step05--Step09 authority output, or old project file should be overwritten by this audit.
