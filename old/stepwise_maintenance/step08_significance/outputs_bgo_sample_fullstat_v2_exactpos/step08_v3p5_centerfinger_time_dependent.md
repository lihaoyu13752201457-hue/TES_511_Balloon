# Step08 Bgo_sample Time-Dependent Significance

Status: `PASS_BGO_SAMPLE_STEP08_TIME_DEPENDENT_FULLSTAT_V2_EXACTPOS`.

Claim level: BGO_SAMPLE_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_FULLSTAT_V2_EXACTPOS.

This folds Bgo_sample Step07 source cases through the Bgo_sample Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `bgo_sample_fullstat_v2_exactpos`. It does not claim a profile-likelihood gain.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=6.43475`.
- T3/T5: `4.21622` / `11.7193` day.
- 20-day 3-sigma flux: `4.66219e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.00060587` to `0.00066221`.
- W2 low-stat selected background events: `248`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_bgo_sample_fullstat_v2_exactpos/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_bgo_sample_fullstat_v2_exactpos/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_bgo_sample_fullstat_v2_exactpos/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_bgo_sample_fullstat_v2_exactpos/step08_v3p5_centerfinger_time_dependent_summary.json`

Limitations:
- build a BGO-vs-CsI comparison package using the matched Step08 outputs
- no spatial/profile likelihood gain is applied to the BGO sample
