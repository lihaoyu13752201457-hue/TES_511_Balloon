# Legacy vs v2 Comparison

Status: `NO_RATE_AUTHORITY`.

| metric | legacy | v2 / diagnostic | verdict |
|---|---:|---:|---|
| day15_total_activity_Bq | 85.44920253876245 | 86.99984206699579647254965784789326599505157688568 | SOURCE_LEVEL_V2_DIFFERS_NOT_RATE_PROMOTED |
| legacy_w2_510p58_511p42_delayed_side_compton_fov_cps | 0.00257520348894 |  | NO_V2_FULLSTAT_SELECTED_RATE |
| legacy_broad_480_550_delayed_side_compton_fov_cps | 0.00317608430303 |  | NO_V2_FULLSTAT_SELECTED_RATE |
| v2_pilot_w2_delayed_side_compton_fov_cps |  | 0 | PILOT_DIAGNOSTIC_ONLY |
| native_pilot_w2_delayed_side_compton_fov_cps |  | 0.086999842067 | VOLUME_NATIVE_PILOT_DIAGNOSTIC_ONLY |
| tag_aware_native_total_activity_Bq |  | 88.05469096172384620331311970190066 | EXPLAINED_MODEL_DIFFERENCE |

The v2 source-level authority is closed, but the harness G8 selected-rate requirements are not closed:
- no v2 full-stat selected-rate extraction;
- no pooled final W2 selected-event count >= 300;
- no v2 source/transport seed variance or `sum_w2` selected-rate ledger;
- legacy L0 comparator pilot timed out before producing SIM output.
