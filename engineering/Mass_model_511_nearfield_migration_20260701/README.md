# Mass_model_511 Nearfield Migration Engineering Package

This directory is a self-contained engineering handoff for replacing the older
NF2 detector-nearfield candidate geometry with the latest Mass_model_511 MEGAlib
detector geometry.

Read this directory directly in a new session when the active task is:

```text
continue / review / run the Mass_model_511 nearfield migration engineering package
```

## Read Order

1. `SESSION_BOOTSTRAP.md`
2. `HARNESS_MASS_MODEL_511_NEARFIELD_MIGRATION.md`
3. `00_manifest/FINAL_STATUS.md`
4. `00_manifest/authority_manifest.md`
5. `01_geometry/geometry_gate.md`
6. `04_bridge_resolution/bridge_resolution.md`
7. `02_run_plan/bridge_and_fullstat_release.csv`
8. `03_source_migration/source_dirs/Mass_model_511/source_migration_manifest.json`
9. `06_smoke_closure/CONCLUSION.md`
10. `11_manuscript_support/TODO_AND_RECENT_UPDATES_20260702.md`

## Current Status

- G0 authority: `AUTHORITY_PASS`
- G1 geometry: `GEOMETRY_PASS`
- G2 source migration: `SOURCE_COPY_PREPARED`
- G5 optics bridge: `OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`
- G3/G4 detector transport: `PASS_G3_G4_DETECTOR_TRANSPORT_SMOKE`
- G6 smoke-matrix detector response closure: `PASS_SMOKE_MATRIX_CLOSURE`
- Optics-model migration (parallel, `05_optics_migration/`): `OPTICS_GEOMETRY_MIGRATED_AND_MC_SMOKE_VERIFIED_IN_REPO`

## Optics Model Migration (`05_optics_migration/`)

The new f10m multiband **unified (一体)** optics geometry — six coplanar Ge(111)
rings (451–551 keV, 511 exact) as 1245 real Ge tiles + G10/Al support — has been
migrated **into this repo** and verified in-repo:

- core geometry file: `05_optics_migration/geometry/MultibandUnified_TilesAndSupport_f10m.geo`
- no overlaps: analytic ledger (`all_positive`) + Geant4 `CheckForOverlaps`
- runs Monte Carlo: in-repo cosima setup loads, is overlap-clean, and transports
- migration statement: `05_optics_migration/optics_migration.md` / `.json`

**Boundary:** this is an *available optics geometry model*, added as a parallel
record. It is NOT coupled into the detector background transport chain and does
NOT change the detector-only G5 above (`OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`
remains true for the detector branch). No background-rate or bridge claim.

## Important Boundary

This is a detector-only MEGAlib geometry migration with prompt/buildup and
delayed transport artifacts under `03_detector_transport/`, plus smoke-matrix
Step05 closure artifacts under `06_smoke_closure/`. It does not promote any old
OF1 optics-background result, and it does not make a full-stat background-rate,
no-effect, or manuscript-release claim. The previous OF1 `BLOCKED_OPTICS_BRIDGE`
remains true for the old independent OF1 optics-local campaign, but it is not a
blocker for this detector-only Mass_model_511 branch.

Do not overwrite the previous `engineering/nearfield_mass_impact_20260625`
outputs. New follow-up outputs should stay under this directory or a new dated
directory.

## Open Work And Recent Paper-Data Updates

See `11_manuscript_support/TODO_AND_RECENT_UPDATES_20260702.md` for the current
open engineering work list and the latest three fix5-derived paper-data updates
that must be carried into the next full-chain Mass_model_511 manuscript pass.
