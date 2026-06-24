# WP02 RPIP Identity And Coverage

## Goal
Align `CC IP RP` production-position records to the WP01 inventory using the full key `(production_tag, raw_logical_volume, ZA, excitation_state_id)`.

## Allowed Inputs
- `runs/step02_buildup_fix5_fullstat_v2/*.sim.gz`
- `runs/step02_buildup_fix5_fullstat_v2/run_manifest.csv`
- `engineering/delayed_source_authority_v2_20260624/01_raw_inventory/raw_inventory_all_states.csv`
- `engineering/delayed_source_authority_v2_20260624/01_raw_inventory/dat_exposure_by_tag.csv`

## Forbidden Reads/Writes
- Do not read or modify legacy delayed source files.
- Do not write outside `engineering/delayed_source_authority_v2_20260624/02_rpip_alignment/`.
- Do not use canonical volume for physics joins.

## Required Outputs
- `02_rpip_alignment/rpip_file_manifest.csv`
- `02_rpip_alignment/rpip_points_all.csv`
- `02_rpip_alignment/rpip_state_catalog.csv`
- `02_rpip_alignment/dat_rpip_key_join.csv`
- `02_rpip_alignment/dat_rpip_count_closure.csv`
- `02_rpip_alignment/volume_identity_audit.csv`
- `02_rpip_alignment/state_identity_audit.csv`
- `02_rpip_alignment/rpip_coverage_summary.json`
- `02_rpip_alignment/rpip_coverage_summary.md`
- `02_rpip_alignment/summary.json`
- `02_rpip_alignment/summary.md`

## Acceptance Criteria
- Join key is raw volume, not canonical volume.
- Every positive-activity key is represented or explicitly blocked.
- RPIP count closure is exact for represented raw inventory keys.
- Activity redistributed by canonicalization is reported, not used.
- No relevant excitation state is folded into ground state.

## Stop States
- `PASS`
- `BLOCKED_UNREPRESENTED_ACTIVITY`
- `FAIL_RPIP_ALIGNMENT`

## Max Attempts
Two implementation attempts, one deterministic validation-fix retry.
