# Laue 511 keV Validation

Independent cross-check workspace for the current `/home/ubuntu/opticsim` Ge(111)
Laue optics model.

The scope here is deliberately small:

- `laue511/`: Python reference kernel and schema helpers.
- `data/laue/`: copied ring configuration used by the current opticsim Laue run.
- `tools/`: runnable checks and bridge utilities.
- `tests/`: lightweight `unittest` coverage.
- `reports/`: stable cross-check outputs only.

Recommended commands:

```bash
cd /home/ubuntu/cross_check_laue/laue511_validation
python3 tools/run_lightweight_crosscheck.py
```

Useful single-step commands:

```bash
python3 tools/laue_sanity.py
python3 tools/audit_focal_convention.py
python3 tools/audit_cosima_bridge.py \
  --input /home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process/phase_space.csv \
  --history /home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process/optics_history.csv
python3 tools/compare_geant4_vs_reference.py \
  --geant4-run /home/ubuntu/opticsim/runs/geant4_laue_darwin_guan_process \
  --out reports/geant4_current_crosscheck
python3 tools/audit_full_lens_observables.py
python3 tools/build_python_full_lens_reference.py
python3 tools/export_external_lens_request.py
python3 tools/build_heart_adapter_feasibility.py --heart-src path/to/HEART
python3 tools/audit_external_lens_handoff.py
python3 tools/import_opticsim_baselines.py
python3 tools/generate_crystalpy_curve.py
# Optional, with xoppylib/dabax available:
# python3 tools/generate_xop_crystal_multiring_curves.py
python3 tools/build_bfull_rocking_curve_map_status.py
# Optional, after building /tmp/opticsim-bfull-build/laue_multiring_bfull_demo:
# python3 tools/run_bfull_offaxis_scan.py --n 2000 --seed 20260529
# python3 tools/run_bfull_single_tile_xop_scan.py --n 3000 --seed 20260529
# python3 tools/run_bfull_full_lens_xop_map_scan.py --seed 20260529
# Optional, if re-importing CRYSTAL diff_pat output:
# python3 tools/import_xop_crystal_diffpat.py --diffpat-dat path/to/diff_pat.dat --diffpat-par path/to/diff_pat.par
# Optional, once an external full-lens oracle export is available:
# python3 tools/import_external_lens_observables.py --input path/to/external_lens_observables.csv
# or, for detector-plane hit tables:
# python3 tools/import_external_lens_hits.py --input path/to/external_lens_hits.csv --incident-weight <total incident ray weight>
# or, for HEART HDF5 detector-image output:
# python3 tools/import_heart_detector_image.py --input path/to/heart_output.h5
# or, to rebuild the retained HEART tile-summary detector image with the
# current Guan-style direction perturbation convention:
# python3 tools/rebuild_heart_detector_from_tile_summary.py --out path/to/heart_output.h5 --summary path/to/run_summary.json
python3 tools/build_validation_summary.py
python3 -m unittest discover -s tests
```

Current boundary:

We implement a custom Laue optics kernel and couple it to Geant4/MEGAlib
through a phase-space bridge. The kernel is benchmarked against independent
Laue-lens and single-crystal diffraction tools.

Do not state that Geant4/MEGAlib natively supports 511 keV Laue diffraction.

Current observed issue:

- the ring CSV is internally consistent with a focal length of about
  `8301.4997 mm`;
- the current historical Geant4 run summary reports `8300 mm` as the focal
  plane distance.

This has been quantified in `reports/focal_convention_audit/`. The focal-plane
offset contributes a maximum isolated `p_diff` shift of about `4.1e-05`, so the
current reports keep `8300 mm` as the operational Geant4 convention and record
the CSV as a center-plane Bragg-radius table.

Stable outputs from the current pass:

- `reports/laue511_crosscheck_summary.md`: top-level human-readable status.
- `reports/validation_manifest.json`: machine-readable status manifest.
- `reports/geant4_current_crosscheck/`: historical 100k-event opticsim run.
- `reports/geant4_rebuilt_5k_crosscheck/`: current-source rebuild smoke,
  raw Geant4 outputs generated under `/tmp` and not retained.
- `reports/focal_convention_audit/`: ring-radius and focal-plane convention
  audit.
- `reports/external_lens_handoff/`: import-path handoff audit using the
  current-reference external-observables example and temporary output cleanup.
- `reports/heart_adapter_feasibility/`: source-level HEART adapter feasibility
  audit showing why a direct HEART flat-crystal run is not yet a comparable
  current-lens oracle unless the Ge(111) diffracting-plane normal is controlled
  independently of the mechanical slab normal.
- `reports/bfull_offaxis_scan/`: B-FULL non-forced finite-MFP Geant4 off-axis
  scan evidence. It compares observed interaction falloff with the local
  diffraction-only predictor and ring-2 XOP/CRYSTAL 511 keV rocking curve
  interpolation.
- `reports/bfull_single_tile_xop_scan/`: B-FULL ring-2/tile-0 scan using the
  XOP/CRYSTAL 511 keV rocking curve CSV as the Geant4 finite-MFP backend. It
  checks recorded `p_reflect` against the interpolated XOP reflectivity.
- `reports/bfull_rocking_curve_map_status/`: B-FULL per-ring external
  rocking-curve map coverage.
- `reports/bfull_full_lens_xop_map_scan/`: B-FULL full-lens scan using the
  complete per-ring XOP/CRYSTAL map with `--require-rocking-curve-map`; the
  retained runs report a custom `G4VEmProcess` in the Geant4 EM category, and
  recorded `p_reflect` values are checked against the ring-specific external
  curves. The retained B-FULL runs also check that `transmitted_space.csv`
  contains the actual primary focal-plane crossings reported in each summary.
- `reports/full_lens_observables/`: full-lens focal-plane geometry and
  effective-area closure audit.
- `reports/python_full_lens_reference/`: Python-only full-lens reference from
  ring config and Darwin-Hamilton probabilities.
- `reports/cosima_bridge_current_audit/`: DIFFRACT phase-space bridge audit
  with history-derived ring/tile provenance.
- `reports/cosima_bridge_transmitted_current_audit/`: TRANSMIT phase-space
  bridge audit with history-derived ring/tile provenance.
- `benchmarks/xrt_pytte/`: imported PyTTE perfect-crystal check.
- `benchmarks/kohnle1998/`: imported Kohnle 1998 Ge(111) endpoint benchmark.
- `benchmarks/opticsim_table_lens/`: imported five-ring opticsim table-driven
  vs online-process closure.
- `benchmarks/crystalpy/`: generated CrystalPy perfect-crystal rocking curve.
- `benchmarks/xop_crystal/`: imported CRYSTAL `diff_pat` mosaic Laue rocking
  curve for Ge(111) at 511 keV plus generated per-ring CRYSTAL curves under
  `benchmarks/xop_crystal/multiring/`.
- `benchmarks/reference_outputs/EXTERNAL_LENS_OBSERVABLES_SCHEMA.md`: import
  schema for future LLL/HEART full-lens observables.
- `benchmarks/reference_outputs/EXTERNAL_LENS_HITS_SCHEMA.md`: detector-plane
  hit-table schema for external tools that export photon hits instead of
  reduced observables.
- `benchmarks/reference_outputs/external_lens_oracle_request.json`: input
  request pack for future LLL/HEART full-lens runs.
- `benchmarks/reference_outputs/external_lens_oracle_tiles.csv`: per-tile
  handoff table with tile centers, expected diffracted directions, and ideal
  Ge(111) diffracting-plane normals for an external full-lens oracle.
- `benchmarks/reference_outputs/heart_lens_adapter_request.json`: HEART-specific
  handoff notes for mapping that tile table into HEART and exporting
  detector-plane hits into the local importer.
- `benchmarks/reference_outputs/heart_independent_plane_normal.patch`: minimal
  HEART handoff patch adding an optional `diff_plane_N` flat-crystal argument so
  mechanical slab normal and Ge(111) diffracting-plane normal can be separated.
- `benchmarks/reference_outputs/heart_patched_full_lens.h5`: patched HEART
  full-lens detector-image output using HEART-native detector hits.
- `benchmarks/reference_outputs/heart_patched_full_lens_guan_direction.h5`:
  HEART full-lens detector weights rebinned with the current Guan-style
  direction perturbation detector convention.
- `benchmarks/reference_outputs/external_lens_observables/`: imported
  full-lens HEART-derived observables, currently `ok=true`.
