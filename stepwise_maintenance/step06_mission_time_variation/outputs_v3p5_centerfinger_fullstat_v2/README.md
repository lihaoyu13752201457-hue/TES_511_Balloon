# Step06 v3p5 Center-Finger Mission Time Variation

Status: `PASS_V3P5_STEP06_TIME_AXIS_FULLSTAT_V2`.

Claim level: V3P5_L1_MISSION_RATE_FOLD_FULLSTAT_V2_NO_NEW_TRANSPORT.

This is the v3p5 `fullstat_v2` mission-axis fold. It does not run new Cosima transport; it reweights the v3p5 Step05 direct response rates over a synthetic 20-day trajectory.
The 511-keV atmosphere factor is a relative Beer-Lambert time fold anchored to the inherited Step05 scalar T_atm; it is not a new absolute 45 deg side-entry line-of-sight atmosphere calculation.

Key checks:
- T_atm day-15 closure: `0.739042388803` vs reference `0.739042388803`.
- W2 day-15 background/signal: `0.0729576` / `0.00118117` cps.
- W2 mission-mean background/signal: `0.0730428` / `0.00117281` cps.
- delayed activity scale range: `0.816642` to `1.05137`.

Outputs:
- summary JSON: `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2/step06_v3p5_centerfinger_fullstat_v2_summary.json`
- background time variation: `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2/background_time_variation.csv`
- total activity by time: `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2/total_activity_by_time.csv`
- figures: `stepwise_maintenance/step06_mission_time_variation/outputs_v3p5_centerfinger_fullstat_v2/figures`

Limitations:
- low-stat v3p5 prompt final rates can be zero in W2;
- delayed source still uses the axisymmetric RadialProfileBeam compression;
- this is a rate-level fold, not per-bin detector transport.
