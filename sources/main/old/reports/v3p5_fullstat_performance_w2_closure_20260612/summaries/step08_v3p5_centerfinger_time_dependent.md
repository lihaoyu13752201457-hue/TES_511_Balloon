# Step08 v3p5 Center-Finger Time-Dependent Significance

Status: `PASS_V3P5_STEP08_TIME_DEPENDENT_FULLSTAT_V2`.

Claim level: V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FULLSTAT_V2.

This folds v3p5 Step07 source cases through the v3p5 Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `fullstat_v2`. It does not claim a profile-likelihood gain.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=5.70221`.
- T3/T5: `5.46687` / `15.338` day.
- 20-day 3-sigma flux: `5.26111e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.000739145` to `0.000806914`.
- W2 low-stat selected background events: `247`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2/step08_v3p5_centerfinger_time_dependent_summary.json`

Limitations:
- delayed source is still RadialProfileBeam-compressed;
- no spatial/profile likelihood gain is applied.
