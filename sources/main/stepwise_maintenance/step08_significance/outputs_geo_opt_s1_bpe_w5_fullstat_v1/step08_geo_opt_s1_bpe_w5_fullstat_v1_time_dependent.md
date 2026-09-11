# Step08 geo-opt S1/BPE/W5 Full-Stat Time-Dependent Significance

Status: `PASS_GEO_OPT_S1_BPE_W5_STEP08_TIME_DEPENDENT_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_PROMOTION`.

Claim level: GEO_OPT_S1_BPE_W5_L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_PROMOTION.

This folds geo-opt Step07 source cases through the geo-opt Step06 mission time axis and applies an analytic accidental live factor. Statistics label: `geo_opt_s1_bpe_w5_fullstat_v1`. The signal stream is the geo-opt focused replay; this is not a promotion or replacement decision.

Headline:
- A reference W2 `1e-4 ph cm^-2 s^-1`: `Z20d=8.16451`.
- T3/T5: `2.25326` / `7.08993` day.
- 20-day 3-sigma flux: `3.67444e-05 ph cm^-2 s^-1`.
- accidental loss range: `0.0103181` to `0.0112554`.
- W2 low-stat selected background events: `74`.

Outputs:
- cumulative significance: `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/cumulative_significance_by_case.csv`
- T3/T5 summary: `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/t3_t5_summary.csv`
- accidental live factors: `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/accidental_veto_by_time.csv`
- summary JSON: `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json`

Method caveats:
- Step08 inherits the Step05 bounded high-rate Poisson timeline approximation through Step06 event-rate folds; it applies only an analytic accidental live factor.
- The time-dependent significance is a counting projection from Step06/Step07 rates, not new per-bin Cosima transport or a spatial/profile-likelihood analysis.

Limitations:
- no promotion/replacement decision is made by this time-dependent fold
- compare against Mass_model_511/fix5 with identical selection and active-veto assumptions before making a geometry decision
- no spatial/profile likelihood gain is applied
