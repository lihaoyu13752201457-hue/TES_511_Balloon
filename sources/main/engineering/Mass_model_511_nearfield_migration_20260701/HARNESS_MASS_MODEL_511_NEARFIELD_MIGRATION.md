# Harness: Mass_model_511 Nearfield Migration

created_at_utc: `2026-07-07T15:02:28.172269+00:00`
status: `READY_FOR_DETECTOR_TRANSPORT_REVIEW`

## Objective

Replace the previous NF2 detector-nearfield support candidate used by the 20260625 engineering workflow with the latest Mass_model_511 detector MEGAlib geometry, while keeping the previous workflow's authority-lock/source-copy discipline.

## Active Geometry

- baseline detector: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- replaced nearfield candidate: `engineering/nearfield_mass_impact_20260625/01_geometry/fixed_candidates/detector_NF2_overlapfix_minimal/DEMO2_DR_fix5_NF2_closedcycle.geo.setup`
- active Mass_model_511 candidate: `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

## Gates

1. G0 authority: `00_manifest/authority_manifest.json`
2. G1 geometry: `01_geometry/geometry_gate.md`
3. G2 source migration: `03_source_migration/source_dirs/Mass_model_511/source_migration_manifest.json`
4. G5 bridge resolution: `04_bridge_resolution/bridge_resolution.md`
5. G3/G4 detector transport: not run by this artifact builder; use `02_run_plan/smoke_run_matrix.csv` after resource approval.

## Boundary

This harness is detector-only. The old OF1 optics bridge blocker is not carried into this branch because no independent optics-local mass model is being coupled to the detector. The old OF1 campaign remains blocked unless a separate bridge is built.
