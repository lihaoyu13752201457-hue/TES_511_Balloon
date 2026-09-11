# Step06 geo-opt S1/BPE/W5 Mission Time Variation

Status: `PASS_GEO_OPT_S1_BPE_W5_STEP06_TIME_AXIS_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_NOT_PROMOTION`.

Claim level: GEO_OPT_S1_BPE_W5_L1_MISSION_RATE_FOLD_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_NO_NEW_TRANSPORT_NOT_PROMOTION.

This is the geo-opt `geo_opt_s1_bpe_w5_fullstat_v1` mission-axis fold. It does not run new Cosima transport; it reweights the geo-opt Step05 direct response rates over a synthetic 20-day trajectory.
The 511-keV atmosphere factor is a relative Beer-Lambert time fold anchored to the inherited Step05 scalar T_atm; it is not a new absolute 45 deg side-entry line-of-sight atmosphere calculation.

Key checks:
- T_atm day-15 closure: `0.739042388803` vs reference `0.739042388803`.
- W2 day-15 background/signal: `0.0353806` / `0.00118464` cps.
- W2 mission-mean background/signal: `0.0354833` / `0.00117625` cps.
- delayed activity scale range: `0.768066` to `1.04704`.

Outputs:
- summary JSON: `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step06_geo_opt_s1_bpe_w5_fullstat_v1_summary.json`
- background time variation: `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/background_time_variation.csv`
- total activity by time: `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/total_activity_by_time.csv`
- figures: `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/figures`

Method caveats:
- Step06 inherits the Step05 bounded high-rate Poisson timeline approximation; no new per-bin event transport or detector-response replay is performed.
- The delayed mission-time fold is anchored to the geo-opt ground-state-corrected day-15 activity ledger and reuses the exact-position delayed transport summary.

Limitations:
- Run Step07/Step08 from this Step06 output before quoting final mission detection potential.
- Compare against Mass_model_511/fix5 with the same selection and active-veto assumptions before making a geometry decision.
- this is a rate-level fold, not per-bin detector transport.
