# Optics Model Migration Statement — f10m multiband (unified / 一体)

generated_at_utc: `2026-07-07T14:58:08.744178+00:00`
status: `OPTICS_GEOMETRY_MIGRATED_AND_MC_SMOKE_VERIFIED_IN_REPO`

## What was migrated

- core geometry file (in-repo): `engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/geometry/MultibandUnified_TilesAndSupport_f10m.geo`
- model: six coplanar Ge(111) rings 451–551 keV (511 exact), **1245 real Ge tiles** on one
  shared template `MB_Tile`, plus G10 carrier + Al outer mount + 4 Al brackets.
- provenance (design/validation): `/home/ubuntu/opticsim/opticsim_full/designs/f10m_multiband_20260701`

## No-overlap evidence

- analytic ledger `engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/geometry/overlap_ledger.json`: all clearances positive = `True`
  (min tangential ≥ 65.66579709086105 µm, min radial 394.65499999999486 µm).
- Geant4 authoritative: cosima `CheckForOverlaps 500 0.0001` on all 1245 tiles + support → overlap-clean = `True`.

## In-repo Monte-Carlo verification

- setup `engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/geometry/multiband_unified_migrated.setup`, source `engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/geometry/multiband_unified_migrated.source` (all includes inside the repo).
- log `engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/verify/cosima_migrated_verify.log`: generated 9144 primaries, triggered **200** events, hits on **263** distinct tile positions.
- overlap-clean in this in-repo run: `True`.

## Boundary (read this)

This migrates an **optics mass/geometry model** into the repo and shows it loads, is
overlap-free, and transports under Monte Carlo from an in-repo setup. It is **not** coupled
into the detector background transport chain and does **not** change the main package's
detector-only `G5 = OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`. No background rate,
optics-to-detector bridge, or no-effect claim is made here.

## Reproduce

```bash
cd engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration
source megalib_env.sh
cosima geometry/multiband_unified_migrated.source   # overlap check + transport
python3 build_optics_migration.py                   # regenerate this statement
```
