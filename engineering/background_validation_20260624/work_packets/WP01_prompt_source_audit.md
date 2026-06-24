# WP01 Prompt Source Normalization Audit

## Goal
Audit current fix5 prompt source units, angular bins, far-field radius, area, splits, replicas, seeds, and selected-rate closure.

## Allowed inputs
- config/megalib_sources_fullsphere20_fix5_tilt45/
- runs/step02_instant_fix5_fullstat_v2/
- stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/
- old/code/tools/build_v3p5_centerfinger_step05_l1_response.py
- /home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSource.cc

## Forbidden reads/writes
- Do not write outside engineering/background_validation_20260624/01_prompt_source_audit/.
- Do not modify source cards, Step05 outputs, manuscript source, or authority reports.

## Required outputs
- summary.json
- summary.md
- source_card_inventory.csv
- source_flux_bin_audit.csv
- prompt_normalization_audit.json
- prompt_normalization_audit.md
- prompt_weight_closure.csv
- farfield_geometry_audit.json
- farfield_geometry_audit.md

## Acceptance criteria
- Radius authority unique.
- Source flux bin sum relative closure <= 1e-8.
- Generated counts, replicas, and seeds complete.
- Independent selected-rate reconstruction relative difference <= 1e-6.
- Area/projected-area handling has local code evidence.
- All rates carry sum_w2.

## Stop states
- PASS
- WARN
- BLOCKED_SOURCE_SEMANTICS
- BLOCKED_RADIUS_MISMATCH
- FAIL_NORMALIZATION

## Max attempts
2 implementation attempts, 1 deterministic validation-fix retry.
