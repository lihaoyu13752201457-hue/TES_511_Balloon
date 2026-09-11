# TES_511_Balloon Migration Directory

Date: 2026-06-11

Source branch: `/home/ubuntu/codex_tes_511_sim/new_geo_re`

Target branch: `/home/ubuntu/TES_511_Balloon`

Scope: code/config/reference migration only. No simulation was run for this
migration step, and migrated source files were not internally rewritten for the
new DR/Cu64-fix geometry yet.

## Current Rule

This project is now staged for geometry iteration first. Keep the migrated code
as a working baseline until the geometry is finalized, then update geometry
paths, ADR/DR naming, validator assertions, and regenerated output contracts in
one controlled pass.

## Top-Level Directory Map

- `geo_refer/`
  - User-provided DEMO2 DR reference geometry package.
  - Treat as design/reference input, not generated authority.

- `code/geometry/`
  - Migrated legacy geometry generator: `GenerateGeo_ADR_v4c_mkflange.py`.
  - Current Cu64-fix step00 generator already exists as
    `build_demo2_dr_v2p2_geometry.py`.
  - Do not assume legacy ADR generator is correct for the final DR geometry
    until it is reconciled.

- `code/tools/`
  - Migrated full-chain helper scripts for geometry build, Step02 pipeline,
    delayed source fixing, Step05 reports, Step07/08 reports, validation, and
    audits.
  - `makedecaysourcewithplot_rpip.py` and `build_fixed_delay_source.py` were
    promoted here from Step02 source snapshots because `Project_List.md`
    requires them for delayed-source construction.

- `config/`
  - Migrated MEGAlib atmospheric source cards, science source cards, and
    science source metadata.
  - These cards still contain old geometry/path/name assumptions until the next
    geometry-path update pass.

- `inputs/nubase/`
  - Migrated NUBASE reference input used by delayed-source and half-life audits.

- `records/00_geometry/`
  - Migrated geometry schematic script and legacy schematic reference.
  - Reference only until the new DR geometry schematic is regenerated.

- `tests/`
  - Migrated lightweight tests and real-position delayed-source smoke test
    source files.
  - Old test `outputs/` and `__pycache__/` were intentionally not migrated.

- `stepwise_maintenance/step00_geometry/`
  - New Cu64-fix geometry step created in this target project before this
    migration.
  - Contains current generated geometry notes and 2D schematic for the modified
    sample-box concept.

- `stepwise_maintenance/step01_geo/`
  - Migrated Step01 geometry code, README, and source snapshots.
  - Old Step01 outputs were not migrated.

- `stepwise_maintenance/step02_raw_background_simulation/`
  - Migrated Step02 code, README, and source snapshots needed to rebuild prompt,
    buildup, delayed-source, and ground-state-fixed source inputs.
  - Old prompt/buildup run products were not migrated.

- `stepwise_maintenance/step03_delay_source/`
  - Migrated delayed-source audit/map code, README, and source snapshots.
  - Old Step03 outputs were not migrated.

- `stepwise_maintenance/step04_opticsim/`
  - Migrated optics code, Ge(111) config/XOP map, optics authority JSON, and
    design documentation.
  - Old Step04 generated outputs were not migrated.

- `stepwise_maintenance/step05_veto_time_axis/`
  - Migrated README describing the post-processing veto/time-axis layer.
  - Report outputs and event catalog cache were not migrated.

- `stepwise_maintenance/step06_mission_time_variation/`
  - Migrated Step06 code and README.
  - External EXPACS/PARMA backend still needs to be checked before future
    production reruns.

- `stepwise_maintenance/step07_source_cases/`
  - Migrated Step07 code and README.
  - Old generated source-case outputs were not migrated.

- `stepwise_maintenance/step08_significance/`
  - Migrated Step08 significance/sensitivity/statistical-uncertainty code and
    README.
  - Old significance outputs were not migrated.

- `stepwise_maintenance/step09_optics_bridge/`
  - Migrated EventList bridge and detector-coupled focus-response code plus
    README.
  - Old EventList, run configs, SIM products, and response outputs were not
    migrated.

- `stepwise_maintenance/figure_pack/`
  - Migrated final figure-pack build script only.

- `stepwise_maintenance/new_figure/`
  - Migrated new ABC figure build script only.

- Root `*.md`, `.gitignore`, and project memory/list files
  - Migrated as handoff/reference documentation.
  - `Project_List.md` remains the migration contract.
  - `Project_Memory.md`, `VALIDATION.md`, and
    `CODEX_A_SERIES_EXECUTION_REPORT_20260611.md` remain old-branch references
    until this new branch has fresh results.

## Intentionally Not Migrated

- `runs/`
- old `outputs/` production products
- old `stepwise_maintenance/*/outputs/` results
- old test `outputs/`
- `__pycache__/` and `*.pyc`
- large SIM/event-cache products such as `*.sim.gz` and `event_catalog.pkl`

## Next Pass After Geometry Is Stable

1. Update source-card geometry paths to the final `.geo.setup`.
2. Rename or document ADR/DR file names and symbols.
3. Update validator checks for the final DR/Cu64-fix component names.
4. Regenerate Step01 authority products.
5. Only after geometry is accepted, rerun Step02 onward in order.
