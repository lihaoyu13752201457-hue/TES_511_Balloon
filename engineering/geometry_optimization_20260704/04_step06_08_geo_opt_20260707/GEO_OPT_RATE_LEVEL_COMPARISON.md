# Geo-opt S1/BPE/W5 rate-level comparison

Date: 2026-07-07

Label: `geo_opt_s1_bpe_w5_fullstat_v1`

Verdict: `RATE_LEVEL_NOT_PROMOTION`.

This comparison uses existing Step05 and Step08 summaries only. It is a
selection-consistent rate-level check against the available Mass_model_511 and
fix5 outputs, not a final geometry replacement decision.

## Inputs

- Geo-opt Step05:
  `stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json`
- Geo-opt Step08:
  `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json`
- Mass_model_511 Step05:
  `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.json`
- Mass_model_511 Step08:
  `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json`
- fix5 Step05:
  `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`
- fix5 Step08:
  `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613/step08_fix5_fullstat_v2_exactpos_m50000_s260613_time_dependent_summary.json`

## W2 Day-15 Step05

| branch | background cps | signal cps at 1e-4 | direct Z20d | direct F3 20d |
|---|---:|---:|---:|---:|
| geo-opt S1/BPE/W5 | 0.0353806162 | 0.00118463765 | 8.27893942 | 3.62365256e-05 |
| Mass_model_511 | 0.0480735488 | 0.00118475738 | 7.10310441 | 4.22350542e-05 |
| fix5 | 0.0392162265 | 0.00118587481 | 7.87186814 | 3.81103944e-05 |

Relative to Mass_model_511, geo-opt changes W2 background by `-26.40%`,
signal by `-0.010%`, direct Z20d by `+16.56%`, and direct F3 by `-14.20%`.
Relative to fix5, geo-opt changes W2 background by `-9.78%`, signal by
`-0.104%`, direct Z20d by `+5.17%`, and direct F3 by `-4.92%`.

## W2 Step08 Time-Dependent Fold

| branch | Z20d | F3 20d | T3 d | T5 d | background counts |
|---|---:|---:|---:|---:|---:|
| geo-opt S1/BPE/W5 | 8.16451400 | 3.67443794e-05 | 2.25325676 | 7.08993110 | 60655.9841 |
| Mass_model_511 | 7.03836754 | 4.26235201e-05 | 3.27269284 | 10.0817844 | 83242.1759 |
| fix5 | 7.79950031 | 3.84640026e-05 | 2.50572763 | 7.79019342 | 67953.7748 |

Relative to Mass_model_511, geo-opt changes time-dependent W2 Z20d by
`+16.00%`, F3 by `-13.79%`, T3 by `-31.15%`, T5 by `-29.68%`, and background
counts by `-27.13%`.

Relative to fix5, geo-opt changes time-dependent W2 Z20d by `+4.68%`, F3 by
`-4.47%`, T3 by `-10.08%`, T5 by `-8.99%`, and background counts by
`-10.74%`.

## Caveats

- The geo-opt Step05 summary uses
  `ADAPTIVE_BOUNDED_HIGH_RATE_POISSON_DRAW` because the full-interval active
  skin catalog would draw about `1.00081651e8` instances. The reported rates
  come from the same grouping/veto/Compton code on a bounded interval.
- Geo-opt Step08 applies an analytic accidental live factor to Step06/Step07
  rates; it is not new per-bin Cosima transport or a spatial/profile-likelihood
  analysis.
- The geo-opt active-skin accidental loss range is `1.0318%` to `1.1255%`,
  compared with `0.0984%` to `0.1078%` for Mass_model_511 and `0.0718%` to
  `0.0786%` for fix5. This is expected from the active plastic skin but must be
  reviewed before promotion.
- No `core_md` authority, fix5 authority output, Mass_model_511 geometry, or
  original `511_Mass` geometry is changed by this comparison.

## Decision

The geo-opt branch is favorable at the rate-level W2 comparison: it reduces
background while preserving signal and improves the Step08 counting projection
relative to the available Mass_model_511 and fix5 summaries. It remains
`NOT_PROMOTION` because the high active-skin timeline approximation and the
absence of new per-bin transport/profile-likelihood validation must be reviewed
before any geometry replacement claim.
