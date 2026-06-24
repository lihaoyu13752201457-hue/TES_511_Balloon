# WP00 Phase-1 Authority Lock

## Goal
Lock the read-only Phase-1 authority set for delayed-source v2 work.

## Allowed Inputs
- `AGENTS.md`
- `core_md/fix5_benchmarks.json`
- `core_md/METHOD_FIX5_SIM_CLOSURE.md`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/harness_20260624_2/HARNESS_ENGINEERING_TES511_DELAYED_SOURCE_AUTHORITY_V2_1_QUICK_CONTEXT.md`
- `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/*`
- `outputs/reports/user_redesign_multiholeW_fix5_20260621/*`
- `config/megalib_sources_fullsphere20_fix5_tilt45/*`
- `runs/step02_instant_fix5_fullstat_v2/*`
- `runs/step02_buildup_fix5_fullstat_v2/*`
- `runs/step02_decay_source_fix5_fullstat_v2/*`
- `runs/step02_delay_fix_fix5_fullstat_v2/*`
- `runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/*`
- `engineering/background_validation_20260624/00_manifest/*`
- `engineering/background_validation_20260624/01_prompt_source_audit/*`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/*`

## Forbidden Reads/Writes
- Do not modify `outputs/`, `runs/`, `stepwise_maintenance/`, `config/`, `old/`, or manuscript sources.
- Do not launch Cosima or any physics transport.

## Required Outputs
- `00_manifest/phase2_authority_manifest.json`
- `00_manifest/phase2_authority_manifest.md`
- `00_manifest/previous_phase_frozen_artifacts.json`
- `00_manifest/file_hashes.sha256`
- `00_manifest/execution_environment.json`
- `00_manifest/decision_log.md`
- `00_manifest/summary.json`
- `00_manifest/summary.md`

## Acceptance Criteria
- The fix5 geometry authority is unique and audited.
- Prompt source cards and Phase-1 prompt audit are located and PASS.
- Full-stat fix5 prompt/buildup raw products are present.
- Legacy delayed source artifacts are marked comparator-only.
- No baseline authority paths are overwritten or modified.

## Stop States
- `PASS`
- `BLOCKED_AMBIGUOUS_AUTHORITY`
- `BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING`
- `FAIL`

## Max Attempts
Two implementation attempts, one deterministic validation-fix retry.
