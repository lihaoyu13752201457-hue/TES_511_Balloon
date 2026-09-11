# Final evidence gap closure summary

## Guardrail

Public wall-by-wall transmission was not tuned toward 0.80. The public-geometry smoke stayed at `transmissivity=0.3` for 1000 events, and the roughness sweep reported `0.3773 -> 0.16705` across `0..10 nm` roughness. These values are reported as reconstruction/systematic outputs, not calibration targets.

Large `runs/` outputs were reduced into this record directory and are treated as reproducible intermediates, not committed evidence files.

## 1. Laue vector diagnostics

Implemented recorded vector diagnostics in:

- `geant4_app/src/laue_multiring_darwin_guan_demo.cc`
- `geant4_app/src/laue_multiring_table_demo.cc`

The Guan-style process now records `plane_normal_*`, `scattering_q_vector_*`, `reciprocal_vector_*`, `lattice_G_nominal_*`, `lattice_G_perturbed_*`, `theta_B_rad`, `theta_local_rad`, `mosaic_perturbation_rad`, `q_minus_G_*`, `relative_bragg_residual_*`, and `angle_code_vs_recorded_reflect_rad` in `optics_history.csv`.

Production run:

- `runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k`
- `n_primaries=100000`
- `diffracted_events=24467`
- event invariant report: `laue/laue_vector_diagnostics_prod100k_event_invariants.md`
- per-ring/per-tile report: `laue/laue_vector_diagnostics_prod100k_group_residuals.md`

Result: `strict_vector_diffraction_status=PASS_RECORDED_PLANE_NORMAL`; max recorded-plane reflection-angle residual is `1.49e-08 rad`. Per-ring p99 `q-G` residuals are `0.0797..0.0878 invA`, and max relative Bragg residuals are `0.0591..0.0690` depending on ring.

Naming boundary: `scattering_q_vector_* = |k|*(k_out-k_in)` in inverse Angstrom. `reciprocal_vector_*` remains only as a backward-compatible alias for that scattering vector. `lattice_G_nominal_*` and `lattice_G_perturbed_*` are separate fixed-magnitude lattice vectors.

Interpretation: nonzero `q-G` and relative Bragg residuals are expected in the current virtual-crystallite model because it reflects elastically from the recorded perturbed plane while the Darwin-Hamilton branch probability is computed from scalar detuning. This is a model-systematics diagnostic, not a hidden tuning target.

## 2. Laue Fake-Table Regression

Added and ran `analysis/test_laue_fake_table_no_double_absorption.py`.

Result: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_fake_table_no_double_absorption_regression.md` reports PASS for all-forced `ABSORB`, `TRANSMIT`, and `DIFFRACT` fake tables. Each primary produced exactly one boundary decision.

## 3. Laue Detector Handoff Regression

Added and ran `analysis/test_laue_all_diffract_detector_handoff.py`.

Result: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_all_diffract_detector_handoff_regression.md` reports PASS. The all-diffract fake table produced 60 phase-space photons; `detector_only_demo` reported `n_input_photons=60`, `n_simulated=60`, `n_events_written=60`, and `event_summary.csv` contains 60 rows. This guards against dropping Laue diffracted photons through parent-ID assumptions or schema filters at the optics-detector boundary.

## 4. W/Si reflectivity provenance

Added and ran `analysis/run_wsi_reflectivity_provenance_sweep.py`.

Result: `records/2026-05-24_optics_evidence_gap_closure/reflectivity/wsi_reflectivity_provenance_roughness_sweep.md` reports PASS for the local backend cross-check: `xraydb.multilayer_reflectivity` vs the repository's manual s-polarization Parratt recursion, with roughness sweep `0..10 nm`.

This remains a local backend cross-check only. External IMD/DarpanX/CXRO/Henke provenance is still open.

## 5. Channel wall-by-wall roughness systematic

Added and ran `analysis/run_channel_wallbywall_roughness_sweep.py`.

Result: `records/2026-05-24_optics_evidence_gap_closure/channel/channel_wallbywall_roughness_sweep.md` reports public-geometry wall-by-wall runs at roughness `[0, 0.2, 0.5, 1, 2, 5, 10] nm`, each with 20000 primaries. The report includes:

- transmissivity and effective area;
- spot D90;
- event-weighted and bounce-weighted reflectivity;
- per-ring summaries;
- grazing-angle histograms.

The output schema is `public_geometry_wallbywall_reconstruction` and `is_first_principles_80pct_closure=false` for every roughness point.

## 6. Channel schema separation

Schema flags are implemented in:

- `geant4_app/src/channel_4ring_multibounce_demo.cc`
- `external_baseline/channel_raytrace_py/wallbywall_channel.py`
- `external_baseline/channel_raytrace_py/channel_raytrace.py`

Validated with `analysis/validate_channel_schema_separation.py`. The calibrated handoff smoke has `model_class=calibrated_detector_handoff`, while the public wall-by-wall smoke and every roughness sweep summary have `model_class=public_geometry_wallbywall_reconstruction`. Both schema families explicitly set `is_first_principles_80pct_closure=false`.

## Verification

```bash
analysis/run_with_geant4_114.sh cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_table_demo laue_multiring_darwin_guan_demo channel_4ring_multibounce_demo detector_only_demo -j2
python3 -m unittest tests.integration.test_geant4_laue_darwin_guan_demo tests.integration.test_geant4_laue_multiring_table_demo tests.integration.test_geant4_channel_4ring_multibounce_demo tests.integration.test_channel_wallbywall_rebuild tests.integration.test_geant4_detector_only_demo
python3 analysis/audit_laue_event_invariants.py --run-dir runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k --out records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_event_invariants.md
python3 analysis/audit_laue_vector_diagnostics_groups.py --run-dir runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k
python3 analysis/test_laue_fake_table_no_double_absorption.py
python3 analysis/test_laue_all_diffract_detector_handoff.py
python3 analysis/run_wsi_reflectivity_provenance_sweep.py
python3 analysis/run_channel_wallbywall_roughness_sweep.py
```

Result: build PASS; integration tests `Ran 6 tests ... OK (skipped=1)`; audit/regression scripts PASS.
