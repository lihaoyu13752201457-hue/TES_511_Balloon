# Laue event-level direction invariant audit

- run_dir: `runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k`
- history: `runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k/optics_history.csv`
- phase_space: `runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k/phase_space.csv`
- output_csv: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_event_invariants.csv`
- diffracted_events_checked: 24467
- missing_phase_rows: 0
- direction_model: `guan_virtual_crystallite_plane_normal; emitted DIFFRACT direction is reflected across the recorded plane normal`
- strict_vector_diffraction_status: `PASS_RECORDED_PLANE_NORMAL`
- recorded_plane_normal_rows: 24467

## Result

When `plane_normal_*` and `reciprocal_vector_*` columns are present, this audit checks the emitted `k_out` against reflection across the recorded plane normal and checks the recorded reciprocal vector against `|k|*(k_out-k_in)`. Older runs without those columns remain limited to focus and scalar-Bragg checks.

| metric | value |
|---|---:|
| k_out norm error | max=2.22045e-16, p50=0, p90=1.11022e-16, p99=2.22045e-16 |
| angle k_out vs actual phase-space focus | max=1.49012e-08, p50=0, p90=0, p99=0 |
| angle k_out vs nominal optical-axis focus | max=0.000498742, p50=8.41476e-05, p90=0.000204318, p99=0.000322963 |
| angle k_out vs implied reflection plane | max=1.49012e-08, p50=0, p90=0, p99=0 |
| angle k_out vs recorded plane-normal reflection | max=1.49012e-08, p50=0, p90=0, p99=0 |
| recorded plane-normal norm error | max=7.0205e-11, p50=2.30029e-11, p90=4.62946e-11, p99=5.97565e-11 |
| recorded reciprocal-vector error | max=8.82131e-10, p50=3.02275e-10, p90=5.29024e-10, p99=6.75124e-10 |
| recorded reciprocal-vector parallel angle | max=2.58096e-08, p50=0, p90=1.49012e-08, p99=1.49012e-08 |
| abs(recorded q magnitude - ideal Bragg q magnitude) | max=0.132685, p50=0.021915, p90=0.0535721, p99=0.0835731 |
| q minus nominal lattice G magnitude | max=0.132686, p50=0.0219154, p90=0.0535726, p99=0.0835736 |
| q minus perturbed lattice G magnitude | max=0.132685, p50=0.021915, p90=0.0535721, p99=0.0835731 |
| relative Bragg residual vs nominal G | max=0.0689826, p50=0.0113937, p90=0.0278521, p99=0.0434494 |
| relative Bragg residual vs perturbed G | max=0.0689822, p50=0.0113935, p90=0.0278518, p99=0.0434491 |
| recorded mosaic perturbation | max=0.000302929, p50=7.28936e-05, p90=0.00013185, p99=0.00018908 |
| abs(history delta_theta - recomputed delta_theta) | max=4.28683e-13, p50=1.38947e-13, p90=2.77656e-13, p99=3.57967e-13 |

Focus-direction invariant: **PASS** at tolerance `1e-07 rad`
Recorded plane-normal vector invariant: **PASS_RECORDED_PLANE_NORMAL** at tolerance `1e-07 rad`

## Worst event

| field | value |
|---|---:|
| event_id | 1122 |
| ring_id | 0 |
| tile_id | 42 |
| energy_keV | 480.0 |
| norm_error | 0.0 |
| angle_code_vs_actual_focus_rad | 1.4901161193847656e-08 |
| angle_code_vs_nominal_focus_rad | 7.467399924678082e-06 |
| angle_code_vs_implied_reflect_rad | 0.0 |
| theta_B_rad | 0.003953680740257215 |
| theta_local_rad | 0.003956265292140615 |
| delta_theta_history_rad | 2.584552103e-06 |
| delta_theta_recomputed_rad | 2.5845518834000103e-06 |
| delta_theta_abs_diff_rad | 2.1959998991222425e-13 |
| implied_plane_normal_x | -0.8656741178681446 |
| implied_plane_normal_y | -0.5005922893371006 |
| implied_plane_normal_z | 0.003959988566921702 |
| recorded_vector_diagnostic_model | guan_virtual_crystallite_plane_normal |
| recorded_plane_normal_norm_error | 5.90636428654534e-11 |
| angle_code_vs_recorded_reflect_rad | 0.0 |
| recorded_q_vector_error_invA | 1.4228758473139903e-10 |
| recorded_q_parallel_angle_rad | 0.0 |
| recorded_q_mag_minus_expected_abs_invA | 0.003073783000000052 |
| q_minus_G_nominal_mag_invA | 0.003073813127 |
| q_minus_G_perturbed_mag_invA | 0.003073782454 |
| relative_bragg_residual_nominal | 0.001598056878 |
| relative_bragg_residual_perturbed | 0.001598040931 |
| recorded_mosaic_perturbation_rad | 7.133439711e-06 |

## Claim boundary

- `PASS_RECORDED_PLANE_NORMAL` means the checked run emits a plane-normal diagnostic and `k_out` is consistent with reflection across that recorded normal.
- A table-driven run may still be a focus-preserving scaffold if its recorded diagnostic model is a design-focus normal with separate focal-plane mosaic jitter.
- A Guan-style run with `guan_virtual_crystallite_plane_normal` can support a strict recorded-vector claim for the checked event stream; publication-grade validation still depends on material/systematics evidence.
- Nonzero `q-G` and relative Bragg residuals expose off-Bragg/mosaic detuning in the current virtual-crystallite model; they are not hidden by the reflection-angle invariant.
