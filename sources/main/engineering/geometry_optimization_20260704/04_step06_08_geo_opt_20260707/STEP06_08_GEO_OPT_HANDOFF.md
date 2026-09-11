# Geo-opt S1/BPE/W5 Step06-Step08 handoff

Date: 2026-07-07

Label: `geo_opt_s1_bpe_w5_fullstat_v1`

Scope: rate-level Step06/Step07/Step08 landing for the geo-opt geometry branch.
No `core_md` authority files, original `511_Mass` geometry, `Mass_model_511`
geometry, fix5 authority outputs, or BGO authority outputs were edited.

## Inputs

- Step05 response:
  `stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json`
- Step02 delayed summary:
  `engineering/geometry_optimization_20260704/02_fullstat_prompt_delay_20260706/delayed_source/delayed_source_exactpos_summary.json`
- Ground-state activity ledger:
  `runs/geometry_optimization_20260704/step02_delay_fix_geo_opt_s1_bpe_w5_fullstat_v1/groundstate_activity_corrections.csv`
- Focused signal manifest:
  `engineering/geometry_optimization_20260704/03_step05_detector_response_20260706/signal_transport_manifest.json`

## Commands Run

```bash
python3 -m py_compile stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py
python3 -m py_compile stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py
python3 -m py_compile stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py
python3 stepwise_maintenance/step06_mission_time_variation/code/build_v3p5_centerfinger_step06_time_axis.py --label geo_opt_s1_bpe_w5_fullstat_v1
python3 stepwise_maintenance/step07_source_cases/code/build_v3p5_centerfinger_step07_source_cases.py --label geo_opt_s1_bpe_w5_fullstat_v1
python3 stepwise_maintenance/step08_significance/code/build_v3p5_centerfinger_step08_time_dependent.py --label geo_opt_s1_bpe_w5_fullstat_v1
```

## Status

- Step06:
  `PASS_GEO_OPT_S1_BPE_W5_STEP06_TIME_AXIS_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_NOT_PROMOTION`
- Step07:
  `PASS_GEO_OPT_S1_BPE_W5_STEP07_SOURCE_CASES_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_PROMOTION`
- Step08:
  `PASS_GEO_OPT_S1_BPE_W5_STEP08_TIME_DEPENDENT_GEO_OPT_S1_BPE_W5_FULLSTAT_V1_SIGNAL_REPLAYED_NOT_PROMOTION`

## Key Outputs

- Step06 directory:
  `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- Step06 summary:
  `stepwise_maintenance/step06_mission_time_variation/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step06_geo_opt_s1_bpe_w5_fullstat_v1_summary.json`
- Step07 directory:
  `stepwise_maintenance/step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- Step07 summary:
  `stepwise_maintenance/step07_source_cases/outputs_geo_opt_s1_bpe_w5_fullstat_v1/source_case_summary.json`
- Step08 directory:
  `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/`
- Step08 summary:
  `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json`
- Step08 report:
  `stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent.md`
- Rate-level comparison:
  `engineering/geometry_optimization_20260704/04_step06_08_geo_opt_20260707/GEO_OPT_RATE_LEVEL_COMPARISON.md`

## Headline Checks

- Step06 W2 day-15 background: `0.03538061615676972 cps`
- Step06 W2 mission-mean background: `0.03548328406725096 cps`
- Step06 W2 mission-mean signal at `1e-4 ph cm^-2 s^-1`:
  `0.0011762547243436407 cps`
- Step07 W2 response: `11.84637650538332 cps/(ph cm^-2 s^-1)`
- Step08 W2 `Z20d`: `8.164513995796844`
- Step08 W2 `F3(20d)`: `3.674437941492199e-05 ph cm^-2 s^-1`
- Step08 W2 `T3`: `2.253256761157534 d`
- Step08 W2 `T5`: `7.089931096536265 d`

## Rate-Level Comparison Verdict

Comparison verdict: `RATE_LEVEL_NOT_PROMOTION`.

- Relative to Mass_model_511, geo-opt changes Step08 W2 Z20d by `+16.00%`,
  F3 by `-13.79%`, and background counts by `-27.13%`.
- Relative to fix5, geo-opt changes Step08 W2 Z20d by `+4.68%`, F3 by
  `-4.47%`, and background counts by `-10.74%`.
- This is favorable at the rate-level, but still not a geometry promotion
  because the high active-skin timeline approximation and lack of new per-bin
  transport/profile-likelihood validation remain open.

## Validation Notes

- Summary/status files exist for Step06, Step07, and Step08.
- Summary-declared input and output paths exist.
- Step06 key CSVs and four PNG figures exist.
- Step07 response authority and source-case CSVs exist.
- Step08 accidental, cumulative significance, T3/T5 CSVs, MD report, and PNG
  figure exist.
- A scan of the new output directories found no Mass_model_511/fix5 signal or
  output path being used as a geo-opt result. Mentions of `Mass_model_511` and
  `fix5` are limited to comparison caveats and the explicit statement that the
  geo-opt signal provenance is the geo-opt `signal_transport_manifest.json`.

## Caveats

- Step06 and Step08 preserve the Step05 bounded high-rate Poisson timeline
  caveat. Step06 is a rate-level mission fold; Step08 applies an analytic
  accidental live factor on Step06/Step07 rates.
- No new per-bin Cosima transport, no detector-response replay, and no
  spatial/profile-likelihood gain are claimed in Step06-Step08.
- These products are not a promotion/replacement decision. A geometry decision
  still needs selection-consistent comparison against Mass_model_511/fix5 and
  review of the Step05 caveat in that comparison context.
