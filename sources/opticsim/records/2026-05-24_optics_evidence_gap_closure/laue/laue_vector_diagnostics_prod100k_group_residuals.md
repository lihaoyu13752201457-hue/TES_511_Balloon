# Laue vector diagnostics production residuals

- run_dir: `runs/geant4_laue_darwin_guan_vector_diagnostics_prod100k`
- n_primaries: 100000
- diffracted_events: 24467
- model: `guan_reiazi_style_online_darwin_hamilton_virtual_crystallite_v2`
- event_csv: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_events.csv`
- per_ring_csv: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_per_ring.csv`
- per_tile_csv: `records/2026-05-24_optics_evidence_gap_closure/laue/laue_vector_diagnostics_prod100k_per_tile.csv`

## Naming

- `scattering_q_vector_* = |k| * (k_out - k_in)` in inverse Angstrom.
- `reciprocal_vector_*` is retained as a backward-compatible alias for the same scattering vector.
- `lattice_G_nominal_*` uses the unperturbed design-focus plane normal and fixed `|G|=2*pi/d_hkl`.
- `lattice_G_perturbed_*` uses the recorded virtual-crystallite plane normal and the same fixed lattice magnitude.

## Per-Ring Residuals

| ring | n | max reflect angle rad | max q err invA | p99 q-G pert invA | max rel Bragg pert | p99 mosaic rad |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 5110 | 1.49012e-08 | 8.35266e-10 | 0.0796873 | 0.0621224 | 0.000188951 |
| 1 | 4947 | 1.49012e-08 | 8.63562e-10 | 0.0807417 | 0.0590961 | 0.000186752 |
| 2 | 4970 | 1.49012e-08 | 8.82131e-10 | 0.0840899 | 0.0595934 | 0.000187182 |
| 3 | 4776 | 1.49012e-08 | 8.73106e-10 | 0.0871078 | 0.0642408 | 0.000190373 |
| 4 | 4664 | 1.49012e-08 | 8.04376e-10 | 0.0878077 | 0.0689822 | 0.000193271 |

## Worst Tiles By Relative Bragg Residual

| ring:tile | n | max rel Bragg pert | p99 q-G pert invA | max reflect angle rad |
|---|---:|---:|---:|---:|
| 4:54 | 62 | 0.0689822 | 0.132685 | 1.49012e-08 |
| 4:38 | 75 | 0.0656348 | 0.126246 | 0 |
| 3:28 | 69 | 0.0642408 | 0.123565 | 1.49012e-08 |
| 4:29 | 71 | 0.0635629 | 0.122261 | 0 |
| 3:43 | 73 | 0.0624308 | 0.120084 | 0 |
| 0:59 | 71 | 0.0621224 | 0.11949 | 0 |
| 4:35 | 69 | 0.061495 | 0.118284 | 1.49012e-08 |
| 4:67 | 71 | 0.0607772 | 0.116903 | 0 |
| 3:33 | 83 | 0.0601733 | 0.115742 | 0 |
| 2:8 | 76 | 0.0595934 | 0.114626 | 0 |
| 1:47 | 69 | 0.0590961 | 0.11367 | 1.49012e-08 |
| 4:33 | 88 | 0.0589465 | 0.113382 | 0 |
| 0:51 | 62 | 0.0586661 | 0.112842 | 0 |
| 3:65 | 74 | 0.0578232 | 0.111221 | 1.49012e-08 |
| 1:65 | 72 | 0.0577832 | 0.111144 | 0 |
| 2:32 | 59 | 0.0576452 | 0.110879 | 1.49012e-08 |
| 0:17 | 82 | 0.0576241 | 0.110838 | 0 |
| 1:64 | 71 | 0.0574566 | 0.110516 | 0 |
| 0:21 | 69 | 0.0571227 | 0.109874 | 0 |
| 1:20 | 74 | 0.0568682 | 0.109384 | 0 |

## Interpretation

- The recorded-plane reflection invariant is the direct vector-implementation check; it should be near zero.
- `q-G` is intentionally reported separately. The current Guan-style virtual-crystallite model perturbs the plane normal and reflects elastically, while the Darwin-Hamilton branch probability is computed from scalar detuning around the nominal Bragg condition.
- Therefore a nonzero `q-G` or `|q|-|G|` residual is expected for off-Bragg/mosaic-perturbed events. It is a model-systematics diagnostic, not a hidden retuning target.
- Publication-grade closure would require a model that samples crystallite orientation and enforces the Ewald/Laue condition consistently, or explicitly justifies the present off-Bragg residual as an accepted approximation.
