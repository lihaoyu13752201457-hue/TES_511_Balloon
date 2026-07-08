# Phase 1 project audit

Role: independent Project Auditor for the Balloon511 NIM A revision harness.

Scope: audit the current Phase 1 English manuscript against local project
evidence and file hygiene. I wrote only this artifact.

## Files read first

- `core_md/balloon511_nima_latex_drafts/balloon511_nima_revision_harness_20260622.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_delta.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/pass_1.diff`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex`
- `core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md`

## Project evidence checked

- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/t3_t5_summary.csv`
- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json`
- `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step06_fix5_fullstat_v2_exactpos_m50000_s260613_summary.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_final_closure_report.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_groundstate_half_life_audit_summary.json`
- `core_md/fix5_benchmarks.json`
- `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json`
- `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_rates.csv`
- `old/stepwise_maintenance/step11_upstream_optics_background/status.json`

Note: the exact path requested as
`stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/summary.json`
does not exist. The final closure report points to the concrete Step06 file
listed above, and that file was used for Step06 checks.

## N1 counts, rates, Z, and F3

Verdict: PASS.

Current manuscript lines 533-560 report about `6.8e4` background counts,
`2.0e3` signal counts, day-15 rates `3.92e-2` and `1.19e-3 cps`,
`Z20d=7.80`, `T3=2.51 d`, and `F3(20d)=3.85e-5 ph cm^-2 s^-1`.

Project evidence:

- `t3_t5_summary.csv`, row `A_point_w2_510p58_511p42_F0.0001`, gives
  `final_rate_day15_cps=0.00118587480749719`,
  `background_final_cps_day15=0.0392162265186315`,
  `response_cps_per_ph_cm2_s=11.8587480749719`,
  `total_source_counts=2033.1694381571392`,
  `total_background_counts=67953.7748377242`,
  `final_counting_Z=7.79950030715189`,
  `T3_day_counting=2.5057276321553323`, and
  `T5_day_counting=7.7901934220953635`.
- Step06 summary `checks` gives day-15 rates
  `w2_day15_background_final_cps=0.0392162265186315` and
  `w2_day15_science_final_cps_at_ref_flux=0.00118587480749719`, plus
  mission-weighted rates `0.03935462874339332` and
  `0.001177483126730607`.
- Step08 summary `checks` gives
  `A_reference_w2_Z20d_time_dependent=7.79950030715189`,
  `A_reference_w2_T3_day=2.5057276321553323`,
  `A_reference_w2_flux_3sigma_20d_ph_cm2_s=3.8464002588077305e-05`,
  `A_reference_w2_source_counts=2033.1694381571392`, and
  `A_reference_w2_background_counts=67953.7748377242`.
- Final closure report comparison table gives
  `W2 total selected background cps = 0.0392162265186315`,
  `Reference-flux signal cps = 0.00118587480749719`,
  `Z20d = 7.79950030715189`, and
  `F3(20d) = 3.8464002588077305e-05`.

The manuscript rounding is internally consistent with the project evidence.

## N2 zero-event upper rate and fraction

Verdict: PASS, with a stale-archived-UL note.

Current manuscript lines 625-631 report a `0.425674 Bq` upstream active-Ge
proxy delayed source, `20,000` delayed decays, zero selected W511 events, a
95% upper rate of `6.38e-5 cps`, and a fraction of about `0.16%` of the
selected W511 background.

Arithmetic check:

- `-ln(0.05) / (20000 / 0.4256743799573773) = 6.376e-5 s^-1`, so
  `6.38e-5 cps` is the correct rounded 95% zero-count upper rate.
- `6.38e-5 / 0.0392162265186315 = 0.00163`, so the manuscript's `0.16%`
  fraction is correct against the project W2 day-15 selected background.

Traceability evidence:

- Archived Step11 status records target inventory nuclides Ga-70 and Ga-73,
  each with `activity_Bq=0.21283718997868864`, total
  `0.4256743799573773 Bq`.
- Archived Step11 status delayed transport records `triggers_requested=20000`,
  `SE=20000`, and `ID=20000`.
- Archived Step11 detector-response summary records
  `total_activity_Bq=0.4256743799573773`, `generated_events_seen=20000`,
  `events_kept=0`, `pixel_hits_kept=0`, and `tes_events=0`.
- Archived Step11 rates CSV records every W2 selected stage with `events=0`
  and `rate_s-1=0`.

Stale archived value note:

- The archived Step11 summary/status also record
  `zero_count_95_rate_s-1=0.00012534045848433615`, derived from Cosima
  `TE_s=23900.760455`. The Phase 1 harness/review identifies this as the old
  value to correct. For the manuscript N2 rate, the relevant physical exposure
  is generated decays divided by total activity, not Cosima elapsed `TE_s`.
  Therefore the manuscript's `6.38e-5 cps` and `0.16%` fraction are now
  traceable and should replace the archived derived upper limit in
  manuscript-facing text.

## N3 selected effective area

Verdict: PASS.

Current manuscript line 232 states
`A_sel = S_W511 / F0 = 11.9 cm^2`.

Project evidence:

- `t3_t5_summary.csv`, row `A_point_w2_510p58_511p42_F0.0001`, gives
  `response_cps_per_ph_cm2_s=11.8587480749719`.
- The same row gives `final_rate_day15_cps=0.00118587480749719` at
  `flux_ph_cm2_s=0.0001`, which also yields
  `0.00118587480749719 / 0.0001 = 11.8587480749719 cm^2`.

The manuscript's `11.9 cm^2` is the correct rounded selected effective area.

## N6 delayed selected rate, event count, and uncertainty wording

Verdict: PASS.

Current manuscript lines 574-589 report the delayed component as
`2.6(5)e-3 cps`, 6.6% of selected background, with the uncertainty described
as a Monte Carlo statistical scale inferred from the selected delayed event
count and excluding source-sampling/model systematics. Lines 603-606 and
646 explicitly state that the delayed precision is limited by 30 selected
events and that higher-statistics convergence remains required.

Project evidence:

- `fix5_w_activation_selected_w2_audit.json` gives `selected_events=30`,
  `selected_rate_hz=0.0025752034889400762`,
  `w_or_collimator_selected_events=0`, and
  `w_or_collimator_selected_rate_hz=0`.
- Final closure report comparison table gives
  `W2 delayed selected cps = 0.0025752034889400762` and
  `fix5_sigma = 0.0004701656803528284`.
- `fix5_promotion_decision.json` records the delayed sigma method as
  `delayed_cps/sqrt(delayed_selected_events)`, with
  `delayed_selected_events=30`.
- Delayed source audit gives `eligible_rpip_rows=251681`,
  `fixed_total_activity_Bq=85.44920253876245`, and
  `source_text_flux_relative_delta=4.53631512934923e-10`.
- Ground-state half-life audit gives old/new total activities
  `87.48329383240524 Bq` and `85.44920253876245 Bq`.

The manuscript's rounded `2.6(5)e-3 cps` is traceable to the selected delayed
count and does not import the review's back-calculated count as an unsupported
paper claim. The uncertainty wording is appropriately limited.

## File hygiene

Verdict: PASS for project-data hygiene; non-blocking dirty manuscript-support
notes remain.

`pass_1.diff` contents:

- The pass diff touches only
  `balloon511_nima_draft_en.tex` and two manuscript figure PNG deletions:
  `fig_delayed_exactpos_rpip_distribution.png` and
  `fig_exactpos_sampling_necessity.png`.
- It does not show modifications to simulation authority outputs, Step06,
  Step08, fix5 reports, `runs/`, or `core_md/fix5_benchmarks.json`.

Current project-evidence status:

- `git status --short -- outputs stepwise_maintenance runs core_md/fix5_benchmarks.json`
  returned no dirty paths.
- The checked evidence files are not dirty.

Current dirty manuscript/harness tree:

- Phase 1/harness-related dirty or untracked paths include the English `.tex`,
  English `.pdf`, regenerated English `.md`, review/harness markdown, the
  `revision_harness_runs/` directory, the exporter under
  `core_md/balloon511_nima_latex_drafts/tools/`, and neutral-renamed figure
  PNGs.
- Other dirty paths exist under `core_md/balloon511_nima_latex_drafts/`,
  including the Chinese draft files, `paper_resource/`, and
  `paper_source_figure_table/` support files. These are outside the requested
  Project Auditor write scope and are not simulation authority files. Because
  they are not represented in `pass_1.diff`, I treat them as pre-existing or
  externally authored dirty files for this audit.

No simulation/project data hygiene blocker was found. The warning is for the
non-clean manuscript support tree and the need to keep those unrelated dirty
files separated from Phase 1 gate decisions.

## Internal/debug token grep

Verdict: PASS for the current English `.tex` and `.md`.

Checked case-insensitive tokens:

`fix5`, `v3p5`, `exact-position`, `exactpos`, `seed 260613`, `seed-260613`,
`smoke test`, `full-statistics`, `manuscript-facing`,
`source text flux closure`, `current sampled-position`,
`headline hard-window`, `hard-window`, `Compton/FoV`, `FoV-pass`,
`detection time`, and `mission sensitivity`.

Checked case-sensitive token:

`PASS`

The grep over
`core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex` and
`core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.md` returned
no matches for the requested token list.

## Unsupported or potentially blocking manuscript numbers

No blocking unsupported manuscript number was identified in the checked Phase 1
scope. The prior N2 traceability warning is resolved by the archived Step11
upstream Ge-proxy files listed above.

Non-blocking notes:

- The Step06 path named in the user request as `summary.json` is absent, but
  the concrete Step06 summary path recorded in the final closure report exists
  and supports the manuscript's Step06-dependent rates.
- `paper_resource/table_simulation_workflow_en.tex` still contains older
  internal/stale language (`seed 260613` and `1.25e-4 cps`), but that file is
  not the current English manuscript or generated `.md` reviewed by the Phase 1
  loop. It should not be used as the manuscript-facing authority without a
  separate cleanup pass.

PROJECT_AUDIT_VERDICT = PASS
