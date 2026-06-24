# WP08 Promotion Decision

Task: decide whether source-v2 evidence can promote a delayed selected-rate authority and identify downstream impacts.

Input allowlist:
- `engineering/delayed_source_authority_v2_20260624/04_custom_source_v2/source_v2_manifest.json`
- `engineering/delayed_source_authority_v2_20260624/05_native_activation/tag_aware_native_vs_direct_comparison.json`
- `engineering/delayed_source_authority_v2_20260624/06_time_constant/timing_authority.json`
- `engineering/delayed_source_authority_v2_20260624/07_transport/summary.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json`
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json`

Forbidden actions:
- no Cosima transport
- no Step05-Step08 rebuild
- no manuscript overwrite
- no geometry/prompt/selection edits

Acceptance gate: emit V2_PROMOTED, LEGACY_RETAINED, or NO_RATE_AUTHORITY with evidence, affected artifacts, and manuscript-number manifest.

Termination status: NO_RATE_AUTHORITY if full-stat v2 selected-rate evidence is absent.
