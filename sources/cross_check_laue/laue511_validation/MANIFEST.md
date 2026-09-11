# Workspace Manifest

This directory is a compact cross-check workspace for the current
`/home/ubuntu/opticsim` Ge(111) Laue optics output.

## Top Level

- `README.md`: quick start and current boundary.
- `MANIFEST.md`: directory map and artifact policy.
- `pyproject.toml`: minimal project metadata.
- `laue511/`: Python reference kernel, bridge helpers, and report summarizers.
- `data/laue/`: copied ring configuration used by the current opticsim Laue run.
- `tools/`: command-line tools for checks, imports, audits, and summary rebuilds.
- `tests/`: lightweight `unittest` suite.
- `reports/`: stable generated evidence only.
- `benchmarks/`: imported or generated benchmark evidence.

## Stable Reports

- `reports/laue511_crosscheck_summary.md`: human-readable top-level status.
- `reports/validation_manifest.json`: machine-readable top-level status.
- `reports/geant4_current_crosscheck/`: 100k historical Geant4/Python kernel comparison.
- `reports/geant4_rebuilt_5k_crosscheck/`: retained summary from current-source Geant4 smoke.
- `reports/focal_convention_audit/`: ring-radius and focal-plane convention audit.
- `reports/external_lens_handoff/`: external-observables import-path handoff audit.
- `reports/heart_adapter_feasibility/`: HEART source/interface feasibility audit
  for the current per-tile Laue lens handoff.
- `reports/bfull_offaxis_scan/`: B-FULL stage-2 off-axis scan evidence for
  the new non-forced finite-MFP Geant4 path.
- `reports/bfull_single_tile_xop_scan/`: B-FULL single-tile scan using the
  imported XOP/CRYSTAL 511 keV rocking curve as the finite-MFP backend.
- `reports/bfull_rocking_curve_map_status/`: B-FULL per-ring external
  rocking-curve map coverage and the currently available complete map CSV.
- `reports/bfull_full_lens_xop_map_scan/`: B-FULL full-lens scan using the
  complete XOP/CRYSTAL per-ring map as the finite-MFP backend, with retained
  runs reporting a custom Geant4 `G4VEmProcess` in the EM category and checked
  transmitted focal-crossing phase-space rows.
- `reports/full_lens_observables/`: full-lens focal-plane geometry and effective-area audit.
- `reports/python_full_lens_reference/`: Python-only full-lens effective-area reference.
- `reports/cosima_bridge_current_audit/`: DIFFRACT bridge provenance audit.
- `reports/cosima_bridge_transmitted_current_audit/`: TRANSMIT bridge provenance audit.

## Benchmarks

- `benchmarks/xrt_pytte/`: imported PyTTE perfect-crystal check.
- `benchmarks/crystalpy/`: generated CrystalPy perfect-crystal rocking curve.
- `benchmarks/kohnle1998/`: imported Kohnle 1998 Ge(111) endpoint benchmark.
- `benchmarks/opticsim_table_lens/`: imported five-ring table-driven vs online-process closure.
- `benchmarks/xop_crystal/`: imported CRYSTAL `diff_pat` Ge(111) 511 keV mosaic Laue curve
  plus generated per-ring CRYSTAL curves under `benchmarks/xop_crystal/multiring/`.
- `benchmarks/reference_outputs/`: LLL/HEART status notes, external full-lens
  import/hit schemas, oracle request pack, per-tile oracle handoff table, HEART
  adapter request, HEART independent-plane-normal handoff patch, retained
  patched HEART full-lens HDF5 outputs, and imported external-lens
  observables.

## Artifact Policy

Do not keep raw smoke-test outputs here unless they are promoted to one of the
stable report or benchmark directories above. Temporary EventList/sidecar files,
Geant4 build directories, and exploratory outputs should stay under `/tmp` and
be deleted after use.

Run this before handoff:

```bash
python3 tools/run_lightweight_crosscheck.py
```
