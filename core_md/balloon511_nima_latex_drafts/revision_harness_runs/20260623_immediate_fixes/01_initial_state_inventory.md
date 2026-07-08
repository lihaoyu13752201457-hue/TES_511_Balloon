# Initial State Inventory

Role: Orchestrator.

## Git And Frozen Baseline

`00_git_baseline.txt` records the start-of-run dirty tree, frozen path hashes, and manuscript body hashes. The repository was already dirty at the start of this harness, including English/Chinese `.tex` and `.pdf`, paper resources, paper source figures, generated English `.md`, review files, and the `revision_harness_runs/` tree.

`00_resolved_frozen_paths.txt` lines 6-12 record exact frozen paths. Lines 14-46 record resolved semantic authority paths for old `new_geo_re`, current v3p5, BGO, and current fix5 authority outputs. Lines 48-49 record `UNRESOLVED_FROZEN_PATH_SPECS = NONE`.

One non-blocking missing candidate was recorded at `00_resolved_frozen_paths.txt:51-52`: `old/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_m50000_s260613_20260613/`. Other v3p5 exact-position authority paths were resolved.

## Current Manuscript-Facing Values

| Quantity | Current manuscript location |
|---|---|
| Day-15 selected background `3.92e-2 cps` and selected signal `1.19e-3 cps` | `balloon511_nima_draft_en.tex:550-553`; abstract also at line 40. |
| `Z20d = 7.80`, `T3 = 2.51 d`, `F3(20d)=3.85e-5 ph cm^-2 s^-1` | `balloon511_nima_draft_en.tex:560` and table lines 576-578. |
| Delayed selected rate `2.6(5)e-3 cps`, 30 selected delayed events | `balloon511_nima_draft_en.tex:575`; Phase 1 project evidence at `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md:143-152`. |
| Selected effective area `A_sel = 11.9 cm^2` at `F0=1e-4 ph cm^-2 s^-1` | `balloon511_nima_draft_en.tex:232`; evidence at `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md:122-128`. |
| Upstream active-Ge proxy `0.425674 Bq`, `20,000` decays, zero selected, `6.38e-5 cps` | `balloon511_nima_draft_en.tex:626-631`; evidence and stale-value note at `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md:77-111`. |

Chinese manuscript mirrors these values at `balloon511_nima_draft_zh.tex:497-525` and `554-558`.

## Existing Key Reports And Artifacts

Existing fix5 report artifacts include:

- `outputs/reports/fix5_1of10/fix5_source_manifest.json`
- `outputs/reports/fix5_1of10/fix5_benchmark_alignment.json`
- `outputs/reports/fix5_1of10/fix5_verification_verdict.json`
- `outputs/reports/fix5_1of10/fix5_delayed_source_exactpos_summary.json`
- `outputs/reports/fix5_fullstat_v2/fix5_source_manifest.json`
- `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json`
- `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json`

No existing file named `delayed_selected_rate_convergence.md`, `delayed_selected_rate_convergence.json`, or `delayed_selected_rate_convergence.csv` was found under `outputs/reports`, `stepwise_maintenance`, or `runs` during the Phase 0 path inventory.

## Existing Run Directories

Existing fix5 run directories include:

- `runs/step02_instant_fix5_1of10/`
- `runs/step02_buildup_fix5_1of10/`
- `runs/step02_decay_source_fix5_1of10/`
- `runs/step02_delay_fix_fix5_1of10/`
- `runs/step02_delayed_transport_fix5_1of10/`
- `runs/step02_instant_fix5_fullstat_v2/`
- `runs/step02_buildup_fix5_fullstat_v2/`
- `runs/step02_decay_source_fix5_fullstat_v2/`
- `runs/step02_delay_fix_fix5_fullstat_v2/`
- `runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/`
- `runs/step09_focus_fix5_fullstat_v2_exactpos_m50000_s260613/`

These are existing outputs and must not be overwritten by the immediate-fixes harness. Any PI-02 work must use a new run/report directory, for example `outputs/reports/fix5_immediate_fixes_20260623/`.

## Script And Pipeline Inventory

Potentially relevant existing scripts:

- Delayed/source normalization: `code/tools/build_fixed_delay_source.py`, `code/tools/audit_fix5_groundstate_half_life_units.py`, `code/tools/build_fix5_1of10_exactpos_delayed_source.py`, `code/tools/build_fix5_w_activation_selected_audit.py`.
- Fix5 release/closure: `code/tools/build_fix5_fullstat_release.py`, `code/tools/build_fix5_promotion_decision.py`, `code/tools/build_fix5_final_closure_report.py`, `code/tools/build_fix5_step09_focus.py`.
- Legacy v3p5 convergence/audits: `old/code/tools/build_v3p5_exactpos_convergence_report.py`, `old/code/tools/build_v3p5_exactpos_delayed_source.py`, `old/code/tools/validate_v3p5_exactpos_closure.py`.
- Figure pipeline: `core_md/balloon511_nima_latex_drafts/paper_source_figure_table/build_optics_figures.py`, `build_selection_time_axis_figure.py`, and `core_md/balloon511_nima_latex_drafts/paper_resource/build_expacs_flux_figure.py`.

## Known Stale Or Contamination Risks

- Phase 1 project audit records the old upstream Ge-proxy `zero_count_95_rate_s-1=0.00012534045848433615` as stale and explains that the manuscript-facing value should use `6.38e-5 cps` from generated decays divided by activity (`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md:102-111`).
- Phase 1 project audit also warns that `paper_resource/table_simulation_workflow_en.tex` still contains old/internal language including `seed 260613` and `1.25e-4 cps` and should not be used as manuscript-facing authority without cleanup (`core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md:233-237`).
- Review C6 states that source-card inventory checks are bookkeeping closure, not selected-rate convergence (`balloon511_nima_review_en_20260622.md:126-132`); PI-02 must therefore remain selected-rate based.
