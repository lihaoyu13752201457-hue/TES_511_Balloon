# Step06 fix5 Mission Time Variation

Status: `PASS_FIX5_STEP06_TIME_AXIS_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_NOT_PROMOTION`.

Claim level: FIX5_L1_MISSION_RATE_FOLD_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_NO_NEW_TRANSPORT_NOT_FINAL_PROMOTION.

This is the fix5 `fix5_fullstat_v2_exactpos_m50000_s260613` mission-axis fold. It does not run new Cosima transport; it reweights the fix5 Step05 direct response rates over a synthetic 20-day trajectory.
The 511-keV atmosphere factor is a relative Beer-Lambert time fold anchored to the inherited Step05 scalar T_atm; it is not a new absolute 45 deg side-entry line-of-sight atmosphere calculation.

Key checks:
- T_atm day-15 closure: `0.739042388803` vs reference `0.739042388803`.
- W2 day-15 background/signal: `0.0392162` / `0.00118587` cps.
- W2 mission-mean background/signal: `0.0393546` / `0.00117748` cps.
- delayed activity scale range: `0.843764` to `1.05219`.

Outputs:
- summary JSON: `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step06_fix5_fullstat_v2_exactpos_m50000_s260613_summary.json`
- background time variation: `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/background_time_variation.csv`
- total activity by time: `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/total_activity_by_time.csv`
- figures: `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/figures`

Limitations:
- Run Step07/Step08 from this Step06 output and refresh the promotion decision artifact before any final replacement claim.
- Old new_geo_re prompt/delayed numbers remain blocked as pass/fail gates while benchmark alignment is NOT_ALIGNED.
- this is a rate-level fold, not per-bin detector transport.
