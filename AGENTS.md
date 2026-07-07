# AGENTS - repo entry pointer

## Instruction Priority

This file is a repo-level pointer. It does not override a user-named harness,
engineering brief, task file, or explicit mainline simulation request. If the
user names a specific file under `engineering/`, that file governs the session.

## Active Retained Packages

The current workspace is scoped to:

- `engineering/Mass_model_511_nearfield_migration_20260701/`
- `engineering/geometry_optimization_20260704/`

If the user says to continue the current Mass_model_511 work without naming a
different file, read:

1. `engineering/Mass_model_511_nearfield_migration_20260701/SESSION_BOOTSTRAP.md`
2. `engineering/Mass_model_511_nearfield_migration_20260701/README.md`

For the latest optimization review, start from:

1. `engineering/geometry_optimization_20260704/09_gpt_complement_ingress_veto_bpe_20260707/01_README_GPT_PARSE.md`
2. `engineering/geometry_optimization_20260704/10_gpt_geometry_optimization_direction_20260707/01_README_AND_PROMPT.md`
3. `engineering/geometry_optimization_20260704/11_expacs_atm511_line_gap_20260707/README.md`

## Current Status

- Mass_model_511 geometry migration exists and has current generated geometry
  under `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/`.
- The latest geo-opt branch adds the plastic scintillator/B-polyethylene/W-bottom
  optimization work under `engineering/geometry_optimization_20260704/`.
- The shared f10m A1 focused EventList bridge is retained at
  `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/`.

## Shared Safety Constraints

- Do not reintroduce deleted fix5 authority outputs unless the user explicitly
  asks to restore them.
- Do not overwrite retained Mass_model_511 or geometry-optimization products.
  New runs and reports go in new dated directories.
- Any run whose source card or SIM header points to the wrong geometry is
  invalid.
- Delayed or activation claims still require auditable normalization: NUBASE
  ground-state correction, per-family TT division guard, and source/inventory
  provenance. Do not treat a visually plausible delayed source as valid.
- Inspect the current worktree before making claims; do not rely on compressed
  chat history as authority.
