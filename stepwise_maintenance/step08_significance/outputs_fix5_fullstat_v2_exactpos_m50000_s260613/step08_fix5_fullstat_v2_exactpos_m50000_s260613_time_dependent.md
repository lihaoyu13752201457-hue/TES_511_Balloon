# Step08 fix5 Full-Stat Time-Dependent Significance

Status: `PASS_FIX5_STEP08_TIME_DEPENDENT_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_SIGNAL_REPLAYED_NOT_PROMOTION`.

Claim level: FIX5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FIX5_FULLSTAT_V2_EXACTPOS_M50000_S260613_SIGNAL_REPLAYED_NOT_FINAL_PROMOTION.

This folds fix5 Step07 source cases through the fix5 Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `fix5_fullstat_v2_exactpos_m50000_s260613`. The signal stream is the fix5 focused replay; promotion still requires the final fix5 promotion decision artifact.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=7.7995`.
- T3/T5: `2.50573` / `7.79019` day.
- 20-day 3-sigma flux: `3.8464e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.000718415` to `0.000786398`.
- W2 low-stat selected background events: `84`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json`

Limitations:
- refresh the fix5 promotion decision artifact before any final replacement claim
- old new_geo_re benchmark alignment is NOT_ALIGNED; its prompt/delayed rates remain historical context only
- no spatial/profile likelihood gain is applied
