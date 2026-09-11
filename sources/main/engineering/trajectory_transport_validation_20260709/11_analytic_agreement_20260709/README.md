# Analytic Agreement Audit - Trajectory Validation

Status: `PASS_ANALYTIC_AGREEMENT_AUDIT_BUILT`

## Question

Do the existing targeted prompt transport points agree with the Step06 analytic prompt scaling points?

This audit uses only the existing targeted extraction table:
`engineering/trajectory_transport_validation_20260709/05_targeted_stats/targeted_prompt_results.csv`.
No Cosima transport was rerun.

## Primary Result

For the high-statistics prompt 480--550 keV band, the MC points are not statistically consistent
with the old Step06 single prompt scalar. That scalar is not Claude/Fable5's corrected analytic
formula; it is the historical depth/cutoff proxy that the corrected model replaced. The same MC
points are consistent with a live-PARMA species-weighted expectation, which is the particle-family
resolution implementation of Claude's corrected prompt source-response formula:
`R_prompt_j(t) = sum_b Phi_b(t) * K_prompt[j,b]`.

The Fable5-style curve figure now draws that same live-PARMA source-response
expectation as a continuous green curve over all 81 frozen trajectory bins. The
red MC validation points should be compared to this green curve; the yellow and
orange curves are the old Step06 scalar proxies kept as a visual contrast.

### Combined e+ + n + gamma 480--550 keV band

| point | model | MC/REF | expected | Q | sigma_Q | z |
|---|---|---:|---:|---:|---:|---:|
| L1 | `step06_prompt_scalar` | 1.12522 | 1.05299 | 1.0686 | 0.0180483 | 3.8 |
| L1 | `live_parma_species_weighted` | 1.12522 | 1.13484 | 0.991526 | 0.0167466 | -0.506 |
| H1 | `step06_prompt_scalar` | 0.894649 | 0.964753 | 0.927334 | 0.0152827 | -4.75 |
| H1 | `live_parma_species_weighted` | 0.894649 | 0.89105 | 1.00404 | 0.0165468 | 0.244 |
| L2 | `step06_prompt_scalar` | 1.11773 | 1.05245 | 1.06203 | 0.0182897 | 3.39 |
| L2 | `live_parma_species_weighted` | 1.11773 | 1.12439 | 0.994077 | 0.0171195 | -0.346 |

### e+ only 480--550 keV band

| point | model | MC/REF | expected | Q | sigma_Q | z |
|---|---|---:|---:|---:|---:|---:|
| L1 | `step06_prompt_scalar` | 1.12542 | 1.05299 | 1.06878 | 0.00655227 | 10.5 |
| L1 | `live_parma_particle_flux` | 1.12542 | 1.12546 | 0.999962 | 0.00613035 | -0.00621 |
| H1 | `step06_prompt_scalar` | 0.899767 | 0.964753 | 0.93264 | 0.00568256 | -11.9 |
| H1 | `live_parma_particle_flux` | 0.899767 | 0.897144 | 1.00292 | 0.0061108 | 0.479 |
| L2 | `step06_prompt_scalar` | 1.10822 | 1.05245 | 1.05299 | 0.00646323 | 8.2 |
| L2 | `live_parma_particle_flux` | 1.10822 | 1.11499 | 0.993922 | 0.00610068 | -0.996 |

## Verdict Table

| scope | metric | model | primary subset | max |z| | verdict |
|---|---|---|---|---:|---|
| `combined_species` | `band480_550` | `live_parma_species_weighted` | all combined points | 0.506 | `CONSISTENT_WITHIN_2SIGMA` |
| `combined_species` | `band480_550` | `step06_prompt_scalar` | all combined points | 4.75 | `REJECTED_GT_3SIGMA` |
| `combined_species` | `tes_any` | `live_parma_species_weighted` | all combined points | 8.79 | `REJECTED_GT_3SIGMA` |
| `combined_species` | `tes_any` | `step06_prompt_scalar` | all combined points | 26.4 | `REJECTED_GT_3SIGMA` |
| `per_particle` | `band480_550` | `live_parma_particle_flux` | eplus only | 0.996 | `CONSISTENT_WITHIN_2SIGMA` |
| `per_particle` | `band480_550` | `step06_prompt_scalar` | eplus only | 11.9 | `REJECTED_GT_3SIGMA` |
| `per_particle` | `tes_any` | `live_parma_particle_flux` | eplus only | 4.64 | `REJECTED_GT_3SIGMA` |
| `per_particle` | `tes_any` | `step06_prompt_scalar` | eplus only | 32 | `REJECTED_GT_3SIGMA` |

## Boundary

- This is a prompt targeted-statistics audit only.
- It does not validate Step05 W2 selection, activation production, delayed inventory, or delayed selected rates.
- It supports the narrower statement that the old Step06 prompt scalar is too coarse at these points,
  while a live-PARMA species-weighted prompt expectation is statistically compatible with the current targeted MC band rates.

## Outputs

- `analytic_agreement_rows.csv`: per-point Q, uncertainty, and z values.
- `analytic_agreement_summary.json`: compact machine-readable verdicts.
- `claude_source_response_curve_by_time.csv`: continuous 81-bin Claude/PARMA source-response curve used by the Fable5-style plot.
- `CLAUDE_FORMULA_REVIEW.md`: recovered corrected formula and mapping to this audit.
- `figures/analytic_curves_with_claude_source_response.png`: Fable5-style curve plot with Claude/PARMA prediction and targeted MC overlap.
- `figures/tes_w2_cumulative_significance_claude_source_response.png`: Fable5-style cumulative significance plot with validation-point Q labels.
- `../scripts/plot_claude_formula_fable5_style.py`: figure regeneration script.
- `README.md`: this report.
