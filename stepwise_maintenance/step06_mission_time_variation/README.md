# Step06 Mission Time Variation

Status: `L0_EXPACS_PROMPT_DRIVER_RATE_FOLD_COMPLETE`.

This step adds the first mission-time layer for `new_geo_re` without new Cosima transport.
The time-axis layer is unchanged by the B-FULL optics handoff: it still folds the existing Step05 response rates and does not add new Cosima transport or optics-mass activation.

## Trajectory Constraint

- Latitude center `34.0` deg with max offset `0.25` deg.
- Longitude center `100.0` deg with max offset `0.25` deg.
- Altitude reference `38.75` km with max offset `2.5` km.
- This is a synthetic/reference profile, not telemetry.

## Atmospheric Transmission

- Model: Beer-Lambert through residual atmospheric depth.
- The effective 511 keV mass attenuation coefficient is calibrated so the day-15/reference bin exactly reproduces the Step05 science ledger transmission.
- `T_ref = 0.739042388803`.
- `T_day15 = 0.739042388803`.
- absolute closure error `3.000e-13`.
- transmission range `0.646123` to `0.811095`.

This confirms the correction is internally consistent with the existing Step05 ledger.

## Prompt And Activation Driver

- Backend: `official_EXPACS_PARMA_CPP_driver`.
- 81-bin EXPACS/PARMA prompt driver status: `PASS`.
- The prompt detector-rate driver is a particle-weighted fold of the 81 trajectory-bin EXPACS/PARMA spectra using current 480-550 keV final-prompt particle weights.
- The delayed-production driver uses EXPACS/PARMA particle scales weighted by the buildup source particle rates, then the activity ODE carries the irradiation history.
- No time bin reruns Cosima detector transport; this is still a rate-level response fold.
- prompt scale at min altitude `1.16828`.
- prompt scale at max altitude `0.878797`.
- altitude vs prompt-scale correlation `-0.995335`.
- altitude vs 511 keV transmission correlation `0.997952`.

## Delayed Activity

- Each inventory nuclide/volume row is integrated with a half-life ODE.
- The ODE time series is anchored so every nuclide reproduces the fixed Step03 day-15 activity at the day-15 bin.
- max per-nuclide day-15 relative error `1.000e+00`.
- max total ODE/grid closure relative error `4.307e-14`.
- Rate folding currently uses a uniform per-Bq delayed response proxy because no per-nuclide detector-response matrix exists yet.

## Day-15 Closure

- prompt final cps day15 `0.0535666609652`.
- delayed final cps day15 `2.31224086684`.
- science final cps day15 `0.002399283866`.
- max relative day15 rate closure error `6.272e-14`.

## Outputs

- `outputs/trajectory_profile.csv`
- `outputs/time_dependent_driver_grid.csv`
- `outputs/atmosphere_transmission_511_by_time.csv`
- `outputs/particle_flux_by_time.csv`
- `outputs/expacs_particle_scale_by_time.csv`
- `outputs/expacs_prompt_driver_weights.csv`
- `outputs/expacs_prompt_driver_summary.json`
- `outputs/activity_by_time_nuclide_volume.csv`
- `outputs/total_activity_by_time.csv`
- `outputs/background_time_variation.csv`
- `outputs/step06_mission_time_variation_summary.json`
- `outputs/figures/`

## v3p5 Center-Finger 1/10 Output

Status: `PASS_V3P5_STEP06_TIME_AXIS_1OF10`.

Output:
`stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_1of10/README.md`.

This branch product keeps the same 20-day synthetic mission profile and
Beer-Lambert 511-keV atmospheric scaling, but folds the v3p5 Step05 direct
rates and v3p5 ground-state delayed-activity ledger. It is a rate-level
mission fold only; no time-bin Cosima transport is rerun.

Key v3p5 checks:

- T_atm day-15 closure: `0.739042388803`.
- W2 day-15 background/signal: `0.0157833 / 0.00118117 cps`.
- W2 mission-mean background/signal: `0.0155714 / 0.00117281 cps`.
- delayed activity scale range: `0.817308` to `1.05152`.

## Rebuild

```bash
python3 stepwise_maintenance/step06_mission_time_variation/code/build_step06_mission_time_variation.py
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py
```
