# v3p5 Boundary Closure Sidecars

Status: `PASS_V3P5_BOUNDARY_CLOSURE_SIDECARS`.
Statistics label: `fullstat_v2`.
Base label: `fullstat_v2`.
Authority role: `CONSERVATIVE_RADIALPROFILE_BASELINE_CROSSCHECK`.

## 45 deg Atmosphere LOS Sidecar

This closes the scalar-inherited `T_atm` ambiguity as a sidecar by applying the Step06 Beer-Lambert depth model to a 45 deg slant column.

| case | T_ref slant | Z20d | T3 day | 20d 3sigma flux |
| --- | ---: | ---: | ---: | ---: |
| W2 hard window | 0.65203425 | 5.02544 | 6.66912 | 5.969625e-05 |
| spot_r90 | 0.65203425 | 7.20533 | 2.85657 | 4.163585e-05 |

## Spatial Annular Likelihood Sidecar

This closes the single-cut spatial-analysis boundary as a fixed-template multi-annulus Poisson likelihood sidecar.

- annuli: `6`
- full-aperture counting Z20d: `5.12702`
- annular likelihood Z20d: `8.45804`
- 20-day 3sigma flux: `3.546920e-05` ph cm^-2 s^-1
- gain vs spot_r90 time fold: `1.03454`

## Exact-Position Delayed Source

Status: `SOURCE_AUDITS_PASS_TRANSPORT_NOT_RERUN`.

Feasibility: `EXACT_RPIP_POINTSOURCE_SMOKE_VALIDATED_NOT_PRODUCTION_RERUN`. The exact-RPIP `PointSource` path is smoke-validated in `tests/realpos_delayed_smoke/` and `../codex_tes_511_sim/new_geo_re/tests/realpos_delayed_smoke/`, but this boundary is not paper-closed until the fixed-inventory v3p5 production delayed transport is rerun.

## Outputs

- summary JSON: `outputs/reports/v3p5_boundary_closure_20260613/v3p5_boundary_closure_summary.json`
- 45 deg curve CSV: `outputs/reports/v3p5_boundary_closure_20260613/v3p5_45deg_los_time_curve.csv`
- annulus CSV: `outputs/reports/v3p5_boundary_closure_20260613/v3p5_spatial_annular_likelihood.csv`
