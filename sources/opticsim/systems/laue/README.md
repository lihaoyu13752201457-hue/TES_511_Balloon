# Laue Optics System

This directory is the manifest for the Ge(111) Laue-lens line. Source, data,
and run products remain in the normal repo locations so tests and build scripts
do not need path changes.

## Current Mainline

- Geant4 app: `geant4_app/src/laue_multiring_table_demo.cc`
- Guan-style compiled Geant4 app: `geant4_app/src/laue_multiring_darwin_guan_demo.cc`
- Ring configuration: `data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- Darwin mosaic table: `data/laue/Ge111_480_550keV_darwin_mosaic_table.csv`
- Main run: `runs/geant4_laue_multiring_darwin`
- IO validation: `runs/io_contract_validation_geant4_laue_multiring_darwin`
- Group report: `records/2026-05-20_laue_group_meeting_presentation.html`
- Guan/Darwin-style same-geometry comparison: `systems/laue_darwin_guan`
- Guan-style compiled Geant4 run: `runs/geant4_laue_darwin_guan_process`

## Interpretation

The current Laue model is table-driven and benchmarked against the local
Darwin/Zachariasen checks already recorded in `docs/validation_matrix.md`.
No Geant4 source code modification is required for the current application-level
process.

`systems/laue_darwin_guan` is a separate comparison package. It keeps the same
five-ring geometry and records the Guan/Reiazi-style model/process split. Its
standalone Python runner is a legacy table-backed closure check; the compiled
Geant4 02 executable is the current online-physics implementation.

`geant4_app/src/laue_multiring_darwin_guan_demo.cc` is the compiled Geant4
version of that split: `GuanDarwinDynamicalModel` owns the crystal physics and
`GuanStyleLaueBraggProcess` is registered on gamma as an application-level
discrete process. Unlike the 01 baseline, it computes the branch probabilities
online with a Darwin-Hamilton mosaic backend and does not read the 01
`pAbs/pDiff/pTrans` table during tracking. It is not a Geant4 toolkit
EM-category patch and does not copy Guan/Reiazi source code.
