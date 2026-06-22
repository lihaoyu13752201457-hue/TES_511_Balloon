# Step08 v3p5 Center-Finger Time-Dependent Significance

Status: `PASS_V3P5_STEP08_TIME_DEPENDENT_FULLSTAT_V2_EXACTPOS_M20000_S260613`.

Claim level: V3P5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FULLSTAT_V2_EXACTPOS_M20000_S260613.

This folds v3p5 Step07 source cases through the v3p5 Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `fullstat_v2_exactpos_m20000_s260613`. It does not claim a profile-likelihood gain.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=6.14261`.
- T3/T5: `4.7579` / `12.8295` day.
- 20-day 3-sigma flux: `4.88392e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.00078985` to `0.000865295`.
- W2 low-stat selected background events: `129`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/step08_v3p5_centerfinger_time_dependent_summary.json`

Limitations:
- exact-position delayed source uses sampled PointSource support; support-size stability remains a robustness check
- no spatial/profile likelihood gain is applied
