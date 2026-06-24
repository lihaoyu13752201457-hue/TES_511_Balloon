# WP01 Raw State-Resolved Inventory Ledger

## Goal
Build the day-15 direct-production inventory ledger from raw fix5 full-stat activation `.dat` files.

## Allowed Inputs
- `runs/step02_buildup_fix5_fullstat_v2/*.dat`
- `runs/step02_buildup_fix5_fullstat_v2/run_manifest.csv`
- `runs/step02_buildup_fix5_fullstat_v2/normalization.json`
- `inputs/nubase/nubase_2020.txt`
- `engineering/delayed_source_authority_v2_20260624/00_manifest/phase2_authority_manifest.json`

## Forbidden Reads/Writes
- Do not read activity from legacy delayed source files.
- Do not write outside `engineering/delayed_source_authority_v2_20260624/01_raw_inventory/`.
- Do not modify baseline outputs, runs, source cards, Step05 outputs, or manuscript files.

## Required Outputs
- `01_raw_inventory/dat_file_manifest.csv`
- `01_raw_inventory/dat_exposure_by_tag.csv`
- `01_raw_inventory/raw_inventory_all_states.csv`
- `01_raw_inventory/raw_inventory_source_rows.csv`
- `01_raw_inventory/raw_inventory_summary.json`
- `01_raw_inventory/raw_inventory_summary.md`
- `01_raw_inventory/activity_omission_ledger.csv`
- `01_raw_inventory/duplicate_state_audit.csv`
- `01_raw_inventory/inventory_closure.json`
- `01_raw_inventory/summary.json`
- `01_raw_inventory/summary.md`

## Acceptance Criteria
- Every `.dat` file and TT record is counted.
- The physical key is `(production_tag, raw_logical_volume, ZA, excitation_state_id)`.
- Canonical volume appears only in report fields.
- Production rates use `sum(raw counts) / sum(TT by tag)`.
- Every raw RP row is classified exactly once.
- Duplicate state collisions and unclassified rows are zero.
- Direct activity total can be rebuilt from CSV with relative closure at or below `1e-10`.

## Stop States
- `PASS`
- `WARN`
- `BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING`
- `BLOCKED_AMBIGUOUS_EXCITATION_STATE`
- `FAIL_INVENTORY_CLOSURE`

## Max Attempts
Two implementation attempts, one deterministic validation-fix retry.
