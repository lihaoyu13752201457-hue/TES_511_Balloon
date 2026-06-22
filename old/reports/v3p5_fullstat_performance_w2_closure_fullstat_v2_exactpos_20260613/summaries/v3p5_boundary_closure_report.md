# v3p5 Boundary Closure Sidecars

Status: `PASS_V3P5_BOUNDARY_CLOSURE_SIDECARS`.
Statistics label: `fullstat_v2_exactpos`.
Base label: `fullstat_v2_exactpos`.
Authority role: `CURRENT_EXACT_POSITION_RATE_AUTHORITY`.

## 45 deg Atmosphere LOS Sidecar

This closes the scalar-inherited `T_atm` ambiguity as a sidecar by applying the Step06 Beer-Lambert depth model to a 45 deg slant column.

| case | T_ref slant | Z20d | T3 day | 20d 3sigma flux |
| --- | ---: | ---: | ---: | ---: |
| W2 hard window | 0.65203425 | 5.42468 | 5.93004 | 5.530275e-05 |
| spot_r90 | 0.65203425 | 7.20513 | 2.85677 | 4.163698e-05 |

## Spatial Annular Likelihood Sidecar

This closes the single-cut spatial-analysis boundary as a fixed-template multi-annulus Poisson likelihood sidecar.

- annuli: `6`
- full-aperture counting Z20d: `5.12688`
- annular likelihood Z20d: `8.45781`
- 20-day 3sigma flux: `3.547017e-05` ph cm^-2 s^-1
- gain vs spot_r90 time fold: `1.03451`

## Exact-Position Delayed Source

Status: `PASS_EXACT_RPIP_POINTSOURCE_PRODUCTION_TRANSPORT`.

Feasibility: `EXACT_RPIP_POINTSOURCE_SMOKE_VALIDATED_AND_PROMOTED_TO_V3P5_RUN`. The exact-RPIP `PointSource` path is smoke-validated and this `fullstat_v2_exactpos` report is built from the summarized exact-position delayed transport. Source mode: `sampled_equal_flux_pointsource_blocks`, PointSource blocks: `5000`. Convergence status: `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`.

## Outputs

- summary JSON: `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_boundary_closure_summary.json`
- 45 deg curve CSV: `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_45deg_los_time_curve.csv`
- annulus CSV: `outputs/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613/v3p5_spatial_annular_likelihood.csv`
