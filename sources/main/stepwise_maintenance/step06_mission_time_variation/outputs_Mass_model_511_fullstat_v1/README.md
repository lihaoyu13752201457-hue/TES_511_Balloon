# Step06 Mass_model_511 Mission Time Variation

Status: `PASS_MASS_MODEL_511_STEP06_TIME_AXIS_MASS_MODEL_511_FULLSTAT_V1_NOT_REPLACEMENT`.

Claim level: MASS_MODEL_511_L1_MISSION_RATE_FOLD_MASS_MODEL_511_FULLSTAT_V1_NO_NEW_TRANSPORT_NOT_REPLACEMENT.

This is the Mass_model_511 `Mass_model_511_fullstat_v1` mission-axis fold. It does not run new Cosima transport; it reweights the current-geometry Step05 direct response rates over a synthetic 20-day trajectory.
The 511-keV atmosphere factor is a relative Beer-Lambert time fold anchored to the inherited Step05 scalar T_atm; it is not a new absolute 45 deg side-entry line-of-sight atmosphere calculation.

Key checks:
- T_atm day-15 closure: `0.739042388803` vs reference `0.739042388803`.
- W2 day-15 background/signal: `0.0480735` / `0.00118476` cps.
- W2 mission-mean background/signal: `0.0482222` / `0.00117637` cps.
- delayed activity scale range: `0.79732` to `1.04836`.

Outputs:
- summary JSON: `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/step06_Mass_model_511_fullstat_v1_summary.json`
- background time variation: `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/background_time_variation.csv`
- total activity by time: `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/total_activity_by_time.csv`
- figures: `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/figures`

Limitations:
- Run Step07/Step08 from this Step06 output before quoting a final 20-day threshold.
- No no-material-effect/replacement decision against fix5 is made by this rate-level fold.
- this is a rate-level fold, not per-bin detector transport.
