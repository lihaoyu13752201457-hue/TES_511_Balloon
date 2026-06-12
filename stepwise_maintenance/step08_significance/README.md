# Step08 Time-Dependent Significance

Status: `PASS`.

Claim level: `L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL`.

This step folds Step07 source cases through the Step06 mission time axis and applies an analytic accidental live-time factor. It reports counting significance and a deliberately non-enhanced template proxy. It does not claim a full profile likelihood.

## Key Checks

- accidental loss range: `8.930756e-04` to `0.00120861`.
- day-15 scale loss sanity: `0.00103739`.
- A anchor final Z over 20 days: `0.613533`.
- A reference `1e-4` final Z over 20 days: `0.766916`.
- A reference `1e-4` does not reach 3 sigma inside the `20` day mission; constant-profile extrapolated 3-sigma time is `306.039` day.
- `template_proxy_Z` remains equal to counting `Z`; no profile-likelihood gain is claimed.

## Outputs

- `rate_independent_efficiencies`: `stepwise_maintenance/step08_significance/outputs/rate_independent_veto_efficiencies.csv`
- `accidental_veto_by_time`: `stepwise_maintenance/step08_significance/outputs/accidental_veto_by_time.csv`
- `accidental_representative_anchor`: `stepwise_maintenance/step08_significance/outputs/accidental_representative_anchor.csv`
- `cumulative_significance`: `stepwise_maintenance/step08_significance/outputs/cumulative_significance_by_case.csv`
- `t3_t5_summary`: `stepwise_maintenance/step08_significance/outputs/t3_t5_summary.csv`
- `headline_note`: `stepwise_maintenance/step08_significance/outputs/which_number_is_headline.md`
- `readme`: `stepwise_maintenance/step08_significance/README.md`
- `figures`: `stepwise_maintenance/step08_significance/outputs/figures`
- `line_window_sensitivity`: `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.md`
- `spatial_line_proxy`: `stepwise_maintenance/step08_significance/outputs/spatial_line_proxy.md`

## Sidecars

- Line-window sidecar uses the Step09 detector-coupled focused EventList response and reports W1/W2 sensitivity.
- Focused-spot spatial sidecar applies detector-coupled focused science centroids and current background TES centroids; the headline spatial cut is `spot_r90`.
- Current line sidecar: background `0.184347` cps, time-dependent `Z20d=2.73543`, `T3=24.056` day.
- Current spatial detector-coupled sidecar: EventList rows `12592`, headline `spot_r90=0.523692` cm, background `0.0551005` cps, time-dependent `Z20d=4.50779`, gain vs line `1.64793`. Best diagnostic cut is `spot_r68`.
- Performance-curve comparison sidecar reports `1 Ms = 1,000,000 s` Gaussian
  3-sigma flux limits across current DEMO2 headline curves and the v3p5
  low-stat checkpoint. Best current checkpoint is v3p5 W2 with
  `F_3sigma(1 Ms)=3.13482e-5 ph cm^-2 s^-1`; output is
  `stepwise_maintenance/step08_significance/outputs/performance_curve_comparison_1Ms/performance_curve_comparison_1Ms.md`.

## v3p5 Center-Finger 1/10 Output

Status: `PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10`.

Output:
`stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent.md`.

This branch product folds the v3p5 Step07 source cases through the v3p5 Step06
mission time axis and applies the analytic accidental live factor. It is still
a 1/10-statistics checkpoint and does not include a spatial/profile likelihood.

Key numbers at `1e-4 ph cm^-2 s^-1`, f10m A1 `A_eff(511)=20.08476 cm2`, and
`T_atm=0.739042`:

- broad `480-550 keV`: time-dependent `Z20d=5.76164`, `T3=5.245 day`.
- W2 `510.58-511.42 keV`: time-dependent `Z20d=12.3501`, `T3=0.9428 day`,
  20-day 3-sigma flux `2.42912e-5 ph cm^-2 s^-1`.
- Direct constant-rate sidecar remains available at
  `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_l1_significance.md`.

Low-stat warning: the W2 background is based on only `18` final selected
background events, so this is a closure checkpoint rather than a paper-facing
v3p5 sensitivity.

## Rebuild

```bash
python3 stepwise_maintenance/step08_significance/code/build_step08_significance.py
python3 stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py
python3 stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_l1_significance.py
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py
python3 stepwise_maintenance/step08_significance/code/build_performance_curve_comparison_1Ms.py
```
