# Step08 v3p5 Center-Finger Time-Dependent Significance

Status: `PASS_V3P5_STEP08_TIME_DEPENDENT_FULLSTAT_V2_EXACTPOS`.

Claim level: V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FULLSTAT_V2_EXACTPOS.

This folds v3p5 Step07 source cases through the v3p5 Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `fullstat_v2_exactpos`. It does not claim a profile-likelihood gain.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=6.15522`.
- T3/T5: `4.73758` / `12.7718` day.
- 20-day 3-sigma flux: `4.87391e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.000789616` to `0.000865026`.
- W2 low-stat selected background events: `126`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos/step08_v3p5_centerfinger_time_dependent_summary.json`

Limitations:
- exact-position delayed source uses sampled PointSource support; support-size stability remains a robustness check
- no spatial/profile likelihood gain is applied
