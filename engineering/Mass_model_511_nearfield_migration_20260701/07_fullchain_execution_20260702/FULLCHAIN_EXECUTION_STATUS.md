# Mass_model_511 Full-Chain Execution Status

generated_at_utc: `2026-07-02T15:08:44Z`
overall_status: `PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT_DELAYED_NOT_PREPARED`

## What Was Prepared And Run

- Full-stat candidate prompt and buildup run manifests/job source cards were prepared with existing `code/tools/run_equiv2602_pipeline_NEW_GEO.py`.
- Stage-1 prompt and buildup full-stat Cosima transport outputs are present.
- Source authority cards and paper files were not edited.

## Mode Preflight

| mode | status | jobs | events | existing SIM | existing DAT | estimate CPU-days | estimate GB |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `instant` | `PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT` | 68 | 25210216 | 68/68 | 68/68 | 0.140 | 6.472 |
| `buildup` | `PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT` | 68 | 25210216 | 68/68 | 68/68 | 0.142 | 6.510 |

## TODO Status

| target | status | evidence | notes |
| --- | --- | --- | --- |
| `full_stat_detector_background` | `STAGE1_TRANSPORT_OUTPUTS_PRESENT_DELAYED_NOT_PREPARED` | `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1/run_manifest.csv; runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1/run_manifest.csv` | Prompt/buildup Stage-1 full-stat Cosima transport outputs are present. Delayed full-stat is not prepared. |
| `full_stat_step05_detector_response` | `BLOCKED` | `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/mass_model_511_smoke_closure.json` | Requires completed full-stat prompt, buildup, delayed source/transport, then a full-stat retarget of the Step05 smoke parser. |
| `no_material_effect_or_replacement_release` | `BLOCKED` | `core_md/README.md; historical fix5 gate bundle removed from cleaned checkout` | Requires full-stat Step05 candidate rates and comparison against historical fix5 paper authority. |
| `step06_step08_mission_axis_regeneration` | `BLOCKED` | `stepwise_maintenance/step06_mission_time_variation; stepwise_maintenance/step07_source_cases; stepwise_maintenance/step08_significance` | Existing Step06-Step08 scripts are fix5-label authority outputs; Mass_model_511 retarget waits for full-stat Step05 rates. |
| `p1_p2_p3_replay_on_mass_model_511` | `BLOCKED` | `engineering/paper_review_p1_p2_p3_data_check_20260702/outputs` | Requires Mass_model_511 full-stat Step05/Step08 products before line-width, atmospheric 511, and geometry-framing replay. |
| `transport_outputs_present` | `PASS` | `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1; runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1` | This row is PASS only after all 136 SIM and 136 DAT outputs exist. |

## Runnable Entry

- Stage-1 transport runner: `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/RUN_FULLSTAT_TRANSPORT_STAGE1.sh`
- Full manifest: `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/fullchain_execution_manifest.json`
- TODO CSV: `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/todo_status.csv`

Downstream delayed/Step05/Step06-Step08/P1-P3 remain blocked until delayed full-stat and full-stat detector-response products exist.
