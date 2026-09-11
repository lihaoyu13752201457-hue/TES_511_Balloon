# Mass_model_511 Replacement Review

Status: `USER_REVIEW_REQUIRED_MASS_MODEL_511_NOT_AUTO_REPLACEMENT`

Current-geometry full chain is closed with fix5-matched M statistics, but automatic replacement is not supported because Mass_model_511 Z20d is lower than fix5; Mass_model_511 20-day 3-sigma flux is higher than fix5.

## Key Comparison

| metric | Mass_model_511 | fix5 | ratio Mass/fix5 | unit |
| --- | ---: | ---: | ---: | --- |
| W2 prompt final rate | 0.044088948 | 0.036641023 | 1.20327 | cps |
| W2 delayed final rate | 0.0039846007 | 0.0025752035 | 1.5473 | cps |
| W2 total background | 0.048073549 | 0.039216227 | 1.22586 | cps |
| W2 background sigma | 0.0055201627 | 0.0050083293 | 1.1022 | cps |
| W2 signal at 1e-4 | 0.0011847574 | 0.0011858748 | 0.999058 | cps |
| 20-day Z at 1e-4 | 7.0383675 | 7.7995003 | 0.902413 |  |
| 20-day 3-sigma flux | 4.262352e-05 | 3.8464003e-05 | 1.10814 | ph cm^-2 s^-1 |
| W/collimator selected delayed rate | 0 | 0 |  | cps |
| W/collimator fraction of delayed selected rate | 0 | 0 |  |  |

## Interpretation

- M/seed/transport statistics: `PASS`.
- Background is higher than fix5 by `0.00885732 cps`, which is `1.19` combined sigma.
- Signal response is essentially unchanged: Mass/fix5 ratio `0.999058`.
- Final 20-day sensitivity is worse than fix5: F3 ratio `1.10814`, Z ratio `0.902413`.
- W/collimator-origin selected delayed W2 rate is `0 cps` and is not dominant: `False`.

## Evidence

- mass_step05_summary: `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1/step05_Mass_model_511_fullstat_v1_l1_response_summary.json`
- mass_step06_summary: `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1/step06_Mass_model_511_fullstat_v1_summary.json`
- mass_step07_summary: `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1/source_case_summary.json`
- mass_step08_summary: `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/step08_Mass_model_511_fullstat_v1_time_dependent_summary.json`
- mass_delayed_source_summary: `engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed/candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json`
- mass_delayed_transport_manifest: `engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed_transport_campaign_manifest_candidate_Mass_model_511_fullstat_v1.json`
- mass_w_activation_selected_w2_audit: `engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/mass_model_511_w_activation_selected_w2_audit.json`
- mass_w_activation_selected_w2_events: `engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/mass_model_511_w_activation_selected_w2_events.csv`
- mass_model_511_p1_p2_p3_replay: `engineering/Mass_model_511_nearfield_migration_20260701/15_p1_p2_p3_replay_20260703/README.md`
- fix5_promotion_decision: `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`
- metrics_csv: `engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/mass_model_511_vs_fix5_metrics.csv`

## Pending

- Mass_model_511-specific P1/P2/P3 replay is completed separately but is not applied to the manuscript here.
- User decision is required before replacing the paper-facing fix5 authority with Mass_model_511 values.
