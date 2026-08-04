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

For the current S3c mainline and lightweight review, start from:

1. `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/README.md`
2. `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_mainline_analysis_summary.json`
3. `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/CLEANUP_MANIFEST.md`

For the earlier optimization-direction context, read:

1. `engineering/geometry_optimization_20260704/09_gpt_complement_ingress_veto_bpe_20260707/01_README_GPT_PARSE.md`
2. `engineering/geometry_optimization_20260704/10_gpt_geometry_optimization_direction_20260707/01_README_AND_PROMPT.md`
3. `engineering/geometry_optimization_20260704/11_expacs_atm511_line_gap_20260707/README.md`

For Compton/FoV Knob0 work, read:

1. `engineering/compton_veto_knob0_20260710/02_geometry_corrected_algorithm_test_20260711/FINDINGS_RECORD_20260711.md`
2. `engineering/compton_veto_knob0_20260710/02_geometry_corrected_algorithm_test_20260711/README.md`
3. `engineering/compton_veto_knob0_20260710/KNOB0_FLUORESCENCE_ARM_STRATIFICATION_BRIEF.md`
4. `engineering/compton_veto_knob0_20260710/01_s3c_atm511_knob0_replay_20260710/README.md`

## Current Status

- Mass_model_511 geometry migration exists and has current generated geometry
  under `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/`.
- The latest geo-opt branch adds the plastic scintillator/B-polyethylene/W-bottom
  optimization work under `engineering/geometry_optimization_20260704/`.
- S3c is the retained design-family mainline. `S3c-C0` is the measured heavy
  reference and `S3c-LW1` (BGO40 + Al8 + no outer W) is the first lightweight
  promotion candidate; the retained review package is
  `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/`.
- Legacy S3/S3a/S3b simulation and response products were removed on
  2026-07-10. Their original engineering packages retain only 27 Markdown
  conclusion documents; compact comparison snapshots live in the S3c review
  package.
- The geometry-corrected Knob0 replay found no algorithm benefit. The S3c
  atmospheric-511 baseline changes from 6 to 7 because of the pixel-position
  geometry repair, not the S0/S1 rule; every monotonic Knob0 candidate remains
  7 to 7. Mass_model_511 prompt/delayed survivors provide no long-arm
  background target, while tighter policies can reject focused signal. Do not
  promote Knob0, and do not treat the geometry repair as Step05 authority until
  detector-response closure is complete.
- The shared f10m A1 focused EventList bridge is retained at
  `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/`.

## Shared Safety Constraints

- Do not reintroduce deleted fix5 authority outputs unless the user explicitly
  asks to restore them.
- Do not recreate deleted S3/S3a/S3b simulation products unless the user
  explicitly asks for a restoration. New comparison runs belong under a new
  dated S3c mainline directory.
- Do not overwrite retained Mass_model_511 or geometry-optimization products.
  New runs and reports go in new dated directories.
- Any run whose source card or SIM header points to the wrong geometry is
  invalid.
- Delayed or activation claims still require auditable normalization: NUBASE
  ground-state correction, per-family TT division guard, and source/inventory
  provenance. Do not treat a visually plausible delayed source as valid.
- Inspect the current worktree before making claims; do not rely on compressed
  chat history as authority.
