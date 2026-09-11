# Startup Reading Log

INDEPENDENCE = SINGLE_SESSION_DEGRADED
ROLE = Orchestrator
SCOPE = Phase 0 startup and freeze only; no physics/gate verdict is made here.

## Harness Contract Readback

- Harness objective: explain the large old `new_geo_re` vs current fix5/v3p5 background-composition discrepancy, especially delayed/activation, with public-literature sanity check; default is audit-only and no modification unless a reproducible delayed-chain bug is found. Evidence: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_background_composition_audit/PROMPT_NEW_SESSION_BACKGROUND_COMPOSITION_AUDIT_HARNESS_ZH.md:3` and `:11-16`.
- Required output directory and artifact list are fixed by the harness. Evidence: same prompt `:127-151`.
- Role independence and quote rule are explicit: verdicts must carry `INDEPENDENCE` and PASS/WARN/FAIL/BUG/NO_BUG requires source path + line or JSON/CSV locator. Evidence: same prompt `:160-177`.
- Phase 0 is documentation-only: freeze state, read required files, write inventory and comparison plan; no code edits or new MC. Evidence: same prompt `:181-196`.

## Fix5 Method And Gate Files Read

- `AGENTS.md`: active geometry fixed; read METHOD/GUIDE/CONSTRAINTS/PRE_PROMPT before fix5 simulation work; do not overwrite current v3p5/BGO/old new_geo_re authority outputs. Evidence: `AGENTS.md:8-28`, `AGENTS.md:48-67`.
- `core_md/METHOD_FIX5_SIM_CLOSURE.md`: Step05 places prompt/delayed/focused streams on one Poisson time axis with 1 us grouping before active-shield and Compton/FoV veto; Step06 is an 81-bin analytic mission fold, not new transport. Evidence: `core_md/METHOD_FIX5_SIM_CLOSURE.md:48-65`.
- `core_md/METHOD_FIX5_SIM_CLOSURE.md`: prompt normalization is `1/sum(TT)`; delayed normalization requires RPIP production positions, NUBASE ground-state correction, per-family TT division guard, fixed activity, exact-position M-sampling, delayed transport, then Step05 replay. Evidence: `core_md/METHOD_FIX5_SIM_CLOSURE.md:73-110`.
- `core_md/METHOD_FIX5_SIM_CLOSURE.md`: old `new_geo_re` prompt target is a coarse screen with side-coverage/source-surface caveat; old delayed 0.1515 cps is nearly vacuous relative to current v3p5 delayed; real promotion is against v3p5 current authority. Evidence: `core_md/METHOD_FIX5_SIM_CLOSURE.md:112-136`.
- `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`, `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`, `core_md/PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md`: read for workflow, gates, and startup checklist. Key constraints are mirrored in `core_md/fix5_benchmarks.json` and must defer to JSON on numeric conflicts.
- `core_md/fix5_benchmarks.json`: machine-readable authority; fix5 geometry is `/geometry/fix5_geo_setup`, benchmark alignment is required before old new_geo_re gate comparison, and promotion decision fields are fixed. Evidence: `core_md/fix5_benchmarks.json:1-17`, `:20-81`, `:84-113`.

## Current Project Evidence Chain Read

- `core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json`: 14 entries were enumerated; entries include current fix5 W2 total background, prompt, delayed, signal, Z20d/F3, and delayed convergence support. Evidence: JSON pointers `/entries/0`, `/entries/5`, `/entries/7`, `/entries/8`, `/gate_notes`.
- `core_md/balloon511_nima_latex_drafts/source_normalization_audit_20260623.json`: source classes and unit checks were inspected; current prompt source uses fix5 geometry and FarFieldAreaSource radius 60 cm, delayed uses exact-position M=50000 source plus PI-02 convergence. Evidence: JSON pointers `/source_classes/0/source_plane`, `/source_classes/1/source_plane`, `/source_classes/1/unit_checks`.
- `core_md/balloon511_nima_latex_drafts/simulation_config_authority_20260623.json`: reproducibility metadata inspected for Cosima/MEGAlib/Geant4, fix5 geometry, seed policy, delayed exact-position seed, and Step05 RNG seed. Evidence: JSON pointers `/components` entries `fix5_geometry_setup`, `delayed_exactpos_seed`, `step05_rng_seed`.
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`: inspected current promotion decision and evidence pointers. Evidence: JSON pointers `/decision`, `/B_cps`, `/prompt_cps`, `/delayed_cps`, `/comparison_vs_v3p5`, `/comparison_vs_old_new_geo_re`, `/evidence`.
- `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json`: inspected PI-02 delayed convergence screen. Evidence: JSON pointers `/combined`, `/between_sampling_check`, `/verdict`.
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`: inspected Step05 normalization, broad 480--550 and W2 windows, stream event counts/rates, and timeline draw summary. Evidence: JSON pointers `/normalization`, `/windows/broad_480_550`, `/windows/w2_510p58_511p42`, `/timeline_draw_summary`.
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv`: inspected CSV rows for current broad and W2 stream/stage rates; row evidence will be restated in artifact 03.

## Old new_geo_re Evidence Chain Read

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md`: inspected current old-project memory for W2 headline, Step05 broad 480--550 decomposition, Step05/Step06 semantics, and warnings not to use broad 480--550 as W2/spot. Evidence: lines found at `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md:35-44`, `:422-448`, `:506-516`, `:521-540`, `:575-578`, `:807-814`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md`: inspected consistency review, delayed-source/path/veto normalization notes, and limitations. Evidence: `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md:40-82`, `:153-180`, `:190-202`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md`: inspected validator/pass report, day15 delayed final, W2 time-dependent stats, and CsI/I-128 anchor. Evidence: `/home/ubuntu/codex_tes_511_sim/new_geo_re/CODEX_A_SERIES_EXECUTION_REPORT_20260611.md:79`, `:120-138`, `:172-188`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json`: inspected old day15 Step05 summary and broad 480--550 decompositions. Evidence: JSON pointers `/expectation_rates_by_stream_cps`, `/delay_fix`, `/normalization`.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/image8_like_component_rates_with_science.csv`: inspected component-level broad-band and 480--550 rates; row evidence will be restated in artifact 03.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/timeline_spectrum_480_550_rates.csv` and `timeline_spectrum_100_10000_rates.csv`: inspected spectrum bin CSV headers and sample rows; row sums will be handled by Local Data Auditor.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/activation_inventory_day15_after_groundstate_fix.csv`: inspected old activation inventory; row/group evidence will be restated in artifact 04.
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv`: inspected old W1/W2 raw/scintillator/Compton-FoV/both table; row evidence will be restated in artifact 03.

## Optional/Context Files

- Current draft TeX files were not opened in Phase 0 because the harness says they are needed only if checking whether manuscript claims are affected. Evidence: prompt `:85-88`. They remain available for later gatekeeper/report steps if artifacts 03--06 indicate manuscript-impact risk.
- `core_md/Project_Memory.md` and `core_md/HANDOFF_20260617.md` referenced by `PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md` were not present in the current repository root during `rg`; this is a non-blocking context gap for this harness because the harness-specific §2 required list points to `fix5_benchmarks.json` and the old external `new_geo_re` files instead.

## Actions Already Taken

- Created/froze `00_git_baseline.txt` with `git status --porcelain`, key input hashes, and key output directory summaries. Evidence: `00_git_baseline.txt` in this harness directory.
- Spawned two real subagents for independent Local Data Auditor and Literature Auditor roles as requested by the harness role model. Evidence: prompt `:160-177` defines role independence; subagent outputs are expected in artifacts 03--06.

## Boundary

No code, geometry, old `new_geo_re` authority outputs, or current fix5/v3p5 authority outputs were modified in Phase 0. Only harness artifacts in this directory are being written.
