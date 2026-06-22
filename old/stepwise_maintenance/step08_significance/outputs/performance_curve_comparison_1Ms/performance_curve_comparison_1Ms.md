# 1 Ms 3sigma Performance Curve Comparison

Status: `PASS_PERFORMANCE_CURVE_COMPARISON_1MS`.

Claim level: L1_3SIGMA_FLUX_LIMIT_EXPOSURE_SCALING_COMPARISON.

`1 Ms` here means `1,000,000 s` exposure. Flux limits are Gaussian `S/sqrt(B)=3` limits.

## 1 Ms Result

| rank | case | 3sigma flux ph cm^-2 s^-1 | Z at 1e-4 | method |
| ---: | --- | ---: | ---: | --- |
| 1 | 511-CAM Fig.11 | 2.700000e-06 |  | digitized_from_511CAM_Fig11_right_panel_at_511keV |
| 2 | INTEGRAL/SPI | 5.000000e-05 |  | published_3sigma_1e6s_511keV_narrow_line |
| 3 | v3p5 W2 | 6.823007e-05 | 4.39689 | v3p5_time_dependent_cumulative_interpolation |
| 4 | DEMO2 legacy W2 spot_r90 | 8.748416e-05 | 3.42919 | legacy_pre_fix_documented_20d_Z_sqrt_exposure_scaling |
| 5 | v3p5 broad 480-550 | 9.165216e-05 | 3.27325 | v3p5_time_dependent_cumulative_interpolation |
| 6 | COSI scaled to 1 Ms | 9.533409e-05 |  | sqrt_time_scaled_from_published_2yr_3sigma_narrow_line_point_source_sensitivity |
| 7 | DEMO2 legacy W2 line | 1.441678e-04 | 2.08091 | legacy_pre_fix_documented_20d_Z_sqrt_exposure_scaling |
| 8 | DEMO2 legacy W1 mission-axis | 5.142158e-04 | 0.583413 | legacy_pre_fix_documented_20d_Z_sqrt_exposure_scaling |

Best 1 Ms case: `511-CAM Fig.11` with `F_3sigma=2.700000e-06 ph cm^-2 s^-1`.

## Outputs

- CSV: `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.csv`
- 511-CAM digitized CSV: `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/cam511_fig11_digitized_points.csv`
- figure: `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.png`
- summary JSON: `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms_summary.json`

## Limitations

- v3p5 curves use the `fullstat_v2` Step08 products available in this checkout.
- DEMO2 curves are legacy pre-fix documented 20-day headline values scaled as sqrt(exposure); they are retained only as historical markers after the x8.0116 delayed-source normalization review hold.
- COSI is converted to a 1 Ms point by sqrt(time) scaling from a published 2-year all-sky narrow-line sensitivity, so it is a comparison marker, not an observing-strategy equivalence.
- 511-CAM is digitized from the rendered Fig.11 right panel and should be treated as figure-derived.
- All values are Gaussian S/sqrt(B) 3-sigma flux limits, not a low-count exact Poisson construction.
