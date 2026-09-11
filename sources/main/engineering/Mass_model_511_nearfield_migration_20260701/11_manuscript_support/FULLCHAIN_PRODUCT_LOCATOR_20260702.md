# Full-Chain Product Locator - 2026-07-02

Status: `MASS_MODEL_511_FULLCHAIN_PARTIAL_ONLY_FIX5_FULLCHAIN_COMPLETE`

The complete publication full-chain located in the workspace is fix5_fullstat_v2_exactpos_m50000_s260613. For Mass_model_511, full-stat prompt and buildup transports are present and certified; full-stat delayed transport and downstream Step05-Step08/P1-P3 replay are not located.

No simulation was launched by this locator audit.

## Mass_model_511 Products

| Product | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| Smoke Step05 matrix | `PASS_SMOKE_MATRIX_CLOSURE` | `engineering/Mass_model_511_nearfield_migration_20260701/06_smoke_closure/mass_model_511_smoke_closure.json` | smoke only |
| Full-stat prompt/instant transport | `PASS_LOCATED_AND_CERTIFIED` | `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1`; `engineering/Mass_model_511_nearfield_migration_20260701/12_review_20260702/stage1_transport_postrun_review_20260702.json` | transport output presence only |
| Full-stat buildup transport | `PASS_LOCATED_AND_CERTIFIED` | `runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1`; `engineering/Mass_model_511_nearfield_migration_20260701/12_review_20260702/stage1_transport_postrun_review_20260702.json` | transport output presence only |
| Stage-1 review | `PASS_STAGE1_PROMPT_BUILDUP_TRANSPORT` | `engineering/Mass_model_511_nearfield_migration_20260701/12_review_20260702/stage1_transport_postrun_review_20260702.json` | says full detector background is not PASS |

### Mass_model_511 Products Not Located In Standard Paths

| Expected product | Located? | Path checked |
| --- | --- | --- |
| dir | `False` | `runs/Mass_model_511_nearfield_migration_20260701/step02_decay_source_candidate_Mass_model_511_fullstat_v1` |
| dir | `False` | `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_fix_candidate_Mass_model_511_fullstat_v1` |
| dir | `False` | `runs/Mass_model_511_nearfield_migration_20260701/step02_delay_exactpos_candidate_Mass_model_511_fullstat_v1` |
| dir | `False` | `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_fullstat_v1` |
| dir | `False` | `stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1` |
| dir | `False` | `stepwise_maintenance/step06_mission_time_variation/outputs_Mass_model_511_fullstat_v1` |
| dir | `False` | `stepwise_maintenance/step07_source_cases/outputs_Mass_model_511_fullstat_v1` |
| dir | `False` | `stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1` |

## Located Complete Paper Authority

- label: `fix5_fullstat_v2_exactpos_m50000_s260613`
- status: `PASS_FIX5_FULLSTAT_CLOSURE`
- decision: `PASS_FIX5_REPLACES_V3P5`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

This is the complete publication chain already present in the workspace. It supports current paper numbers, but it is not a Mass_model_511 replacement chain. Key evidence:
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_final_closure_report.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`
- `runs/step02_instant_fix5_fullstat_v2`
- `runs/step02_buildup_fix5_fullstat_v2`
- `runs/step02_decay_source_fix5_fullstat_v2`
- `runs/step02_delay_fix_fix5_fullstat_v2`
- `runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613`
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1`
- `stepwise_maintenance/step06_mission_time_variation/outputs_fix5_fullstat_v2_exactpos_m50000_s260613`
- `stepwise_maintenance/step07_source_cases/outputs_fix5_fullstat_v2_exactpos_m50000_s260613`
- `stepwise_maintenance/step08_significance/outputs_fix5_fullstat_v2_exactpos_m50000_s260613`
- `stepwise_maintenance/step09_optics_bridge/outputs_fix5_fullstat_v2_exactpos_m50000_s260613`

## P1/P2/P3 Update Products

Status: `FOUND_FIX5_DERIVED_NOT_MASS_MODEL_511_REPLAY`

These update the fix5 paper authority; they are carry-forward inputs, not Mass_model_511 full-chain replay products.
- `engineering/paper_review_p1_p2_p3_data_check_20260702/outputs/p1_linewidth_sensitivity_summary.json`
- `engineering/paper_review_p1_p2_p3_data_check_20260702/outputs/p2_atm511_transfer_summary.json`
- `engineering/paper_review_p1_p2_p3_data_check_20260702/outputs/paper_data_sufficiency_summary_20260702.md`

## Excluded Products Found

- `FOUND_BUT_EXCLUDED_OLD_NF2_BRANCH`: `engineering/nearfield_mass_impact_20260625/05_detector_fullstat` - AGENTS and package bootstrap say not to overwrite or reinterpret this branch as Mass_model_511.
- `FOUND_BUT_EXCLUDED_BGO_BRANCH`: `engineering/background_validation_20260624/06_bgo_matched_runs/p2` - Different BGO validation branch, not Mass_model_511 candidate geometry.

## Operational Conclusion

Do not rerun Mass_model_511 prompt/buildup full-stat transport; those are already present and certified. If the manuscript continues to use the existing paper authority, use the fix5 full-chain products above. If a Mass_model_511 replacement/no-effect claim is still required, the remaining gaps are only:
- Mass_model_511 full-stat delayed source and delayed transport
- Mass_model_511 full-stat Step05 detector-response release
- Mass_model_511 no-material-effect/replacement comparison against fix5 authority
- Mass_model_511 Step06-Step08 mission/source/significance regeneration
- Mass_model_511-specific P1/P2/P3 replay
