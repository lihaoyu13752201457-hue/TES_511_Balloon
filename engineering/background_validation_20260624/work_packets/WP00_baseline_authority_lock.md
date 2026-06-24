# WP00 Baseline Authority Lock

## Goal
Lock current fix5/CsI baseline geometry, source, run, delayed, Step05, and manuscript authority without modifying authority outputs.

## Allowed inputs
- outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/
- config/megalib_sources_fullsphere20_fix5_tilt45/
- runs/step02_instant_fix5_fullstat_v2/
- runs/step02_buildup_fix5_fullstat_v2/
- runs/step02_decay_source_fix5_fullstat_v2/
- runs/step02_delay_fix_fix5_fullstat_v2/
- stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/
- outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/
- core_md/balloon511_nima_latex_drafts/balloon511_nima_draft_en.tex

## Forbidden reads/writes
- Do not write outside engineering/background_validation_20260624/.
- Do not modify outputs/, runs/, stepwise_maintenance/, config/, old/, or manuscript source.

## Required outputs
- 00_manifest/baseline_authority_manifest.json
- 00_manifest/baseline_authority_manifest.md
- 00_manifest/file_hashes.sha256
- 00_manifest/execution_environment.json
- 00_manifest/decision_log.md

## Acceptance criteria
- Current authority paths are unique and all required hashes are present.

## Stop states
- PASS
- BLOCKED_AMBIGUOUS_AUTHORITY

## Max attempts
2 implementation attempts, 1 deterministic validation-fix retry.
