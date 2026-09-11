# Step08 Mass_model_511 Full-Stat Time-Dependent Significance

Status: `PASS_MASS_MODEL_511_STEP08_TIME_DEPENDENT_MASS_MODEL_511_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_REPLACEMENT`.

Claim level: MASS_MODEL_511_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_MASS_MODEL_511_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_REPLACEMENT.

This folds Mass_model_511 Step07 source cases through the Mass_model_511 Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `Mass_model_511_fullstat_v1`. The signal stream is the current-geometry focused replay; this is not a no-effect/replacement decision.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=7.03837`.
- T3/T5: `3.27269` / `10.0818` day.
- 20-day 3-sigma flux: `4.26235e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.000984187` to `0.00107781`.
- W2 low-stat selected background events: `93`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json`

Limitations:
- no no-material-effect/replacement decision against fix5 is made by this time-dependent fold
- Mass_model_511-specific P1/P2/P3 replay remains open if this branch becomes paper authority
- no spatial/profile likelihood gain is applied
