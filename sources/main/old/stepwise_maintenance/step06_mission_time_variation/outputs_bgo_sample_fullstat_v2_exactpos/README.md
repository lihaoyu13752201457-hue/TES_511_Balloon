# Step06 Bgo_sample Mission Time Variation

Status: `PASS_BGO_SAMPLE_STEP06_TIME_AXIS_FULLSTAT_V2_EXACTPOS`.

Claim level: BGO_SAMPLE_L1_MISSION_RATE_FOLD_FULLSTAT_V2_EXACTPOS_NO_NEW_TRANSPORT.

This is the Bgo_sample `bgo_sample_fullstat_v2_exactpos` mission-axis fold. It does not run new Cosima transport; it reweights the BGO Step05 direct response rates over a synthetic 20-day trajectory.
The 511-keV atmosphere factor is a relative Beer-Lambert time fold anchored to the inherited Step05 scalar T_atm; it is not a new absolute 45 deg side-entry line-of-sight atmosphere calculation.

Key checks:
- T_atm day-15 closure: `0.739042388803` vs reference `0.739042388803`.
- W2 day-15 background/signal: `0.0578455` / `0.00118595` cps.
- W2 mission-mean background/signal: `0.057833` / `0.00117756` cps.
- delayed activity scale range: `0.438786` to `1.03529`.

Outputs:
- summary JSON: `stepwise_maintenance/step06_mission_time_variation/outputs_bgo_sample_fullstat_v2_exactpos/step06_bgo_sample_fullstat_v2_exactpos_summary.json`
- background time variation: `stepwise_maintenance/step06_mission_time_variation/outputs_bgo_sample_fullstat_v2_exactpos/background_time_variation.csv`
- total activity by time: `stepwise_maintenance/step06_mission_time_variation/outputs_bgo_sample_fullstat_v2_exactpos/total_activity_by_time.csv`
- figures: `stepwise_maintenance/step06_mission_time_variation/outputs_bgo_sample_fullstat_v2_exactpos/figures`

Limitations:
- Downstream Step07, Step08, and the BGO-vs-CsI hard-window comparison are closed for this label.
- Optional: run BGO spatial/profile-likelihood sidecars before claiming spatial-analysis gains.
- Optional: add BGO material-uncertainty or detector-threshold sensitivity scans before claiming robustness against those choices.
- this is a rate-level fold, not per-bin detector transport.
