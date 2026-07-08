# Executor Log 20260623

Created UTC: 2026-06-23T08:38:09+00:00
Updated UTC: 2026-06-23T09:57:08+00:00 for pass 2 PI-02 convergence closure.

Independence: `SINGLE_SESSION_DEGRADED`. A fresh Executor subagent was spawned but did not return artifacts after interruption and was closed. This main session completed the Executor artifact pass without editing manuscript body files or protected authority outputs.

## Scope Executed

- PI-01 evidence manifest: `DONE`.
  - Created `core_md/balloon511_nima_latex_drafts/paper_evidence_manifest_20260623.json` and `.md`.
  - Explicitly marked old `1.2534e-4 s^-1` upstream-Ge proxy rate as stale with source `old/stepwise_maintenance/step11_upstream_optics_background/outputs_ge_proxy_delayed_response/step11_ge_proxy_delayed_detector_response_summary.json` (`/zero_count_upper_limits/W2/final_rate_s-1`).
- PI-02 delayed selected-rate convergence: `DONE`.
  - Updated `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json`, `.md`, and `.csv`.
  - Evidence: four independent production-position exact-position samplings, 103 combined selected events, combined selected rate `0.0022127821289687215 cps`, sigma `0.00021803190178715983 cps`, relative uncertainty `0.09853292781642932`, between-sampling check `PASS`.
  - New pass2 source labels: `fix5_pi02_exactpos_m50000_s260614`, `fix5_pi02_exactpos_m50000_s260615`, `fix5_pi02_exactpos_m50000_s260617`; existing authority sampling included as `fix5_fullstat_v2_exactpos_m50000_s260613`.
  - Geometry/source/SIM provenance is present for every run in `delayed_selected_rate_convergence.json` (`/runs/*/geometry_path`, `/source_card_path`, `/sim_header_geometry_path`, `/command`, `/output_path`, `/sampling_audit_status`, `/provenance_status`).
- PI-03 source normalization audit: `DONE_WITH_WARN`.
  - Created `source_normalization_audit_20260623.json` and `.md`.
  - WARN: detailed raw EXPACS/PARMA provenance and some render-level implementation details remain recoverable only through source manifest/log references in this pass.
- PI-04 simulation configuration authority: `DONE_WITH_WARN`.
  - Created `simulation_config_authority_20260623.json` and `simulation_config_table_20260623.md`.
  - WARN: ROOT config is absent in the current shell; production cuts, radioactive decay data version, and custom patch inventory are `TO_RECOVER`/`UNKNOWN`.
- PI-05 figures audit: `DONE_WITH_WARN`.
  - Created `figures_audit_20260623.json` and `.md`.
  - WARN: several exact figure generation commands remain `TO_RECOVER`; no figures were regenerated.

## Protected Outputs

No manuscript body files were edited. No frozen authority outputs were overwritten. New pass2 files were limited to the immediate-fixes harness/project audit artifacts, `code/tools/build_fix5_pi02_delayed_convergence.py`, the scoped source-builder extension in `code/tools/build_fix5_1of10_exactpos_delayed_source.py`, new PI-02 run directories under `runs/step02_delay_fix_fix5_pi02_exactpos_m50000_s26061[4,5,7]/` and `runs/step02_delayed_transport_fix5_pi02_exactpos_m50000_s26061[4,5,7]/`, and new report/cache files under `outputs/reports/fix5_immediate_fixes_20260623/` plus `outputs/reports/fix5_pi02_exactpos_m50000_s26061[4,5,7]/`.

## Evidence Anchors

- Current fix5 closure report: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_final_closure_report.json` (`/status = PASS_FIX5_FULLSTAT_CLOSURE`, `/decision = PASS_FIX5_REPLACES_V3P5`).
- Source/SIM geometry verification: `outputs/reports/fix5_fullstat_v2/fix5_verification_verdict.json` (`/checks/source_cards_geometry`, `/checks/job_sources_geometry`, `/checks/sim_header_geometry`).
- Delayed rate/event evidence: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` (`/delayed_cps`, `/delayed_selected_events`, `/delayed_sigma_method`).
- PI-02 convergence evidence: `outputs/reports/fix5_immediate_fixes_20260623/delayed_selected_rate_convergence.json` (`/verdict/pi_status = DONE`, `/combined/selected_events = 103`, `/combined/relative_uncertainty = 0.09853292781642932`, `/between_sampling_check/status = PASS`).
- Low-stat warning source addressed by pass2: `core_md/balloon511_nima_latex_drafts/balloon511_nima_review_en_20260622.md` lines 116-132.
- Corrected upstream-Ge upper rate: `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260622/phase1_project_audit.md` lines 77-111.

## Pass 2 Commands

- Build exact-position delayed source cards:
  - `python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py --label fix5_pi02_exactpos_m50000_s260614 build-source --n-decays 50000 --triggers 1000000 --seed 260614`
  - `python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py --label fix5_pi02_exactpos_m50000_s260615 build-source --n-decays 50000 --triggers 1000000 --seed 260615`
  - `python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py --label fix5_pi02_exactpos_m50000_s260617 build-source --n-decays 50000 --triggers 1000000 --seed 260617`
- Run Cosima delayed transports:
  - `source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh && cosima -s 260614 runs/step02_delay_fix_fix5_pi02_exactpos_m50000_s260614/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260614.source`
  - `source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh && cosima -s 260615 runs/step02_delay_fix_fix5_pi02_exactpos_m50000_s260615/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260615.source`
  - `source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh && cosima -s 260617 runs/step02_delay_fix_fix5_pi02_exactpos_m50000_s260617/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260617.source`
- Summarize new transports:
  - `python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py --label fix5_pi02_exactpos_m50000_s260614 summarize-transport`
  - `python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py --label fix5_pi02_exactpos_m50000_s260615 summarize-transport`
  - `python3 code/tools/build_fix5_1of10_exactpos_delayed_source.py --label fix5_pi02_exactpos_m50000_s260617 summarize-transport`
- Build combined convergence:
  - `python3 code/tools/build_fix5_pi02_delayed_convergence.py --labels fix5_fullstat_v2_exactpos_m50000_s260613 fix5_pi02_exactpos_m50000_s260614 fix5_pi02_exactpos_m50000_s260615 fix5_pi02_exactpos_m50000_s260617`

## Executor Gate Precheck

- G1 JSON parse: `PASS`; see `03_machine_gate_results.json` (`/gates/G1_json_parse/status`).
- G2 schema keys: `PASS`; see `03_machine_gate_results.json` (`/gates/G2_schema_keys/status`).
- G3 no protected overwrite: `PASS`; see `03_machine_gate_results.json` (`/gates/G3_no_overwrite_resolved_frozen_paths/status`, checked 296 frozen files).
- G4 evidence manifest source coverage: `PASS`; see `03_machine_gate_results.json` (`/gates/G4_provenance_rows/status`, checked 14 evidence entries and 12 unique source/support paths).
- G5 manuscript body hashes unchanged: `PASS`; see `03_machine_gate_results.json` (`/gates/G5_manuscript_frozen/status`).
