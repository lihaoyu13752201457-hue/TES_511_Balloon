# 03 Current vs new_geo_re Rate Matrix

INDEPENDENCE = SUBAGENT

Role: Local Data Auditor. Scope: read-only reconstruction from current fix5/v3p5 outputs and old `/home/ubuntu/codex_tes_511_sim/new_geo_re` authority outputs. No simulation or code was run.

## Verdicts

- WARN: old `new_geo_re` is report-only for fix5 gates. Evidence: `outputs/reports/fix5_fullstat_v2/fix5_benchmark_alignment.json` `/decision = NOT_ALIGNED`; same file `/gate_consequence = Old new_geo_re prompt_total_cps and delayed_total_cps may be reported as historical context only, not used as pass/fail gates.`
- PASS: W2 line-window values exist on both sides. Evidence: old `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv` row 9 has `W2_511_pm_420eV,both,rate_cps=0.18434717748640367,prompt_cps=0.03223400479533992,delayed_cps=0.15211317269106375`; current `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` `/B_cps=0.0392162265186315`, `/prompt_cps=0.036641023029691425`, `/delayed_cps=0.0025752034889400762`.
- WARN: current apples-to-apples `100--10000 keV` value is NOT_AVAILABLE. Evidence: current `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` `/windows` contains `broad_480_550` and `w2_510p58_511p42`; old `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/image8_like_component_rates_with_science.csv` row 10 has `rate_100_10000_keV_cps=61.6606315105`.

## Matrix

| Comparison | Old new_geo_re | Current fix5 | Ratio / status |
| --- | ---: | ---: | --- |
| W2 `510.58--511.42 keV`, final/both total background | `0.18434717748640367 cps` | `0.0392162265186315 cps` | current/old `0.2127302791`; available but NOT_ALIGNED for gate |
| W2 prompt | `0.03223400479533992 cps` | `0.036641023029691425 cps` | current/old `1.1367195377` |
| W2 delayed | `0.15211317269106375 cps` | `0.0025752034889400762 cps` | old/current `59.0684089022`; delayed fraction old `82.5%`, current `6.57%` |
| Broad `480--550 keV` final background | `2.365807527803181 cps` | `0.06628201291851338 cps` | current/old `0.02801665484`; definition-similar but NOT_ALIGNED |
| Broad `480--550 keV` prompt | `0.05356666096521081 cps` | `0.06310592861548728 cps` | current/old `1.1780821780` |
| Broad `480--550 keV` delayed | `2.31224086683797 cps` | `0.003176084303026095 cps` | old/current `728.0162131197`; old broad delayed fraction `97.7%` |
| Old image8-like `100--10000 keV` total | `61.6606315105 cps` | `NOT_AVAILABLE` | no forced comparison |
| Old image8-like `100--10000 keV` activation | `58.8567533967 cps` | `NOT_AVAILABLE` | no forced comparison |

## Evidence Notes

- Old W2 row: `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step09_optics_bridge/outputs/non_xray_background_w1_w2_veto_table.csv` row 9.
- Current W2 row: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv` rows 13 and 16; same values are promoted in `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json` `/prompt_cps`, `/delayed_cps`, and `/B_cps`.
- Old broad day15 final: `/home/ubuntu/codex_tes_511_sim/new_geo_re/outputs/reports/day15_complete_report/complete_day15_summary.json` `/expectation_rates_by_stream_cps/prompt/final=0.05356666096521081`, `/expectation_rates_by_stream_cps/delayed/final=2.31224086683797`, `/science_sensitivity/background_final_cps_prompt_plus_delayed=2.365807527803181`.
- Current broad final: `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json` `/windows/broad_480_550/physical_reference_flux/background_cps=0.06628201291851338`.

## Local Interpretation

The huge delayed discrepancy is real in the local files, but it is not a single apples-to-apples gate result. W2 old delayed is about `59x` current fix5 delayed; broad `480--550` old delayed is about `728x` current fix5 delayed. The broad-window old value must not be used as the W2 line-window value; old project memory explicitly warns this at `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md:807`.
