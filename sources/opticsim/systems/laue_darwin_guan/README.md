# Laue Darwin/Guan-style Same-Geometry Package

This directory is a same-geometry comparison package for the Ge(111) Laue line.
It is intentionally separate from the existing Barhoum-style Geant4 executable.

## Purpose

The existing mainline Geant4 app follows the Barhoum advanced-example pattern:
a custom `G4VDiscreteProcess` is forced at the lens boundary, and
`PostStepDoIt` directly decides `ABSORB / TRANSMIT / DIFFRACT`.

This package records the same five-ring geometry and restructures the logic in
the Guan/Reiazi direction:

- `GuanDarwinDynamicalModel` in the compiled C++ executable owns the online
  Darwin-Hamilton mosaic crystal physics.
- `GuanStyleCrystalBraggModel` computes Bragg mismatch, crystal-plane normal,
  and ideal diffracted direction.
- `GuanStyleLaueBraggProcess` is only the Geant4-style step adapter that applies
  the three branch decision.

This is not a claim that Guan/Reiazi source code was copied or that a new
Geant4 EM category process has been registered. It is a local closure package
that tests whether the higher-confidence model/process split produces the same
geometry and probability behavior as the current Barhoum-style run without
reusing the 01 probability table during compiled Geant4 tracking.

## Files

- `geometry/ge111_480_550keV_multiring_darwin_config.csv`: same Ge(111)
  five-ring geometry snapshot used by the current Laue mainline.
- `darwin_guan_compare.py`: legacy standalone table-backed comparison runner.
- `geant4_app/src/laue_multiring_darwin_guan_demo.cc`: compiled Geant4 C++
  executable using the model/process split with online Darwin-Hamilton mosaic
  probabilities.
- `analysis/compare_geant4_darwin_guan_vs_barhoum.py`: compares the compiled
  Guan-style Geant4 run against the Barhoum-style run.
- `results/same_geometry_comparison/summary.json`: generated summary.
- `results/same_geometry_comparison/per_ring_summary.csv`: generated
  Guan-style expected/sample branch summary.
- `results/same_geometry_comparison/barhoum_comparison.csv`: generated
  per-ring comparison against `runs/geant4_laue_multiring_darwin`.
- `results/same_geometry_comparison/GEANT4_DARWIN_GUAN_VS_BARHOUM_REPORT.md`:
  generated explanation and comparison report.

## Reproduce

```bash
python3 systems/laue_darwin_guan/darwin_guan_compare.py
```

The standalone Python runner is kept only as a same-geometry regression
snapshot. Use the compiled command below for the current 02 physics backend.

The compiled Geant4 implementation is built through CMake:

```bash
cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_darwin_guan_demo
/tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo --n 100000 --seed 20260522 --mosaic-fwhm-arcsec 30 --crystallite-um 5 --out runs/geant4_laue_darwin_guan_process
python3 analysis/compare_geant4_darwin_guan_vs_barhoum.py
```

The legacy runner deliberately stores hashes of the geometry and probability
table so the comparison can detect accidental drift. The compiled runner still
accepts `--efficiency-table` for backward-compatible command lines, but its
summary records `uses_external_efficiency_table_for_physics=false`.
