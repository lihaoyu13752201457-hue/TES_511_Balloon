# Stale Artifact Manifest

Status: `NO_RATE_AUTHORITY`.

No existing artifact was overwritten or replaced. The following artifacts remain usable only as legacy-reference artifacts for the pre-v2 delayed source method:

- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`: RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_promotion_decision.json`: RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_final_closure_report.json`: RETAINED_AS_LEGACY_REFERENCE_NOT_V2_PROMOTED

If v2 is later promoted with full-stat selected-rate evidence, these delayed-dependent products must be regenerated:
- Step05 delayed stream and combined background
- Step06 delayed mission-time fold
- Step07 source-case ledger
- Step08 significance/sensitivity tables
- BGO delayed inventory/rate dependency if the same legacy builder is used
- manuscript delayed-background numbers and derived sensitivity rows
