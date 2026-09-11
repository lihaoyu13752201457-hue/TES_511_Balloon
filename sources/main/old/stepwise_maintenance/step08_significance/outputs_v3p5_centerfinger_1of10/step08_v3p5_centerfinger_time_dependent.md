# Step08 v3p5 Center-Finger Time-Dependent Significance

Status: `PASS_V3P5_STEP08_TIME_DEPENDENT_1OF10`.

Claim level: V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_1OF10.

This folds v3p5 Step07 source cases through the v3p5 Step06 mission time axis and applies an analytic accidental live factor. It remains a 1/10-statistics checkpoint and does not claim a profile-likelihood gain.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=12.3501`.
- T3/T5: `0.942791` / `2.67299` day.
- 20-day 3-sigma flux: `2.42912e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.000726453` to `0.000793153`.
- W2 low-stat selected background events: `18`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_1of10/step08_v3p5_centerfinger_time_dependent_summary.json`

Limitations:
- W2 prompt final rate is zero in this 1/10 prompt sample;
- W2 background has only 18 final selected background events;
- delayed source is still RadialProfileBeam-compressed;
- no spatial/profile likelihood gain is applied.
