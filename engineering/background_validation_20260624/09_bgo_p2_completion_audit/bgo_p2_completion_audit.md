# BGO P2 Completion Audit

Status: `PASS_BGO_P2_COMPLETION_AUDIT`

Generated UTC: `2026-06-24T07:22:42Z`

## Checks

| Check | Status | Blocking | Evidence |
|---|---|---:|---|
| `harness_preconditions_g0_to_g4` | `PASS` | `true` | `engineering/background_validation_20260624` |
| `resource_guard_user_approval` | `PASS` | `true` | `engineering/background_validation_20260624/05_matched_runs_resource_guard/USER_APPROVAL_20260624.md` |
| `bgo_same_envelope_geometry` | `PASS` | `true` | `engineering/background_validation_20260624/04_bgo_variant/summary.json` |
| `bgo_source_manifest_flux_geometry_parity` | `PASS` | `true` | `engineering/background_validation_20260624/05_matched_runs_resource_guard/bgo_source_card_manifest.csv` |
| `all_bgo_source_cards_use_bgo_geometry` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs` |
| `all_p2_sim_headers_use_bgo_geometry` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2` |
| `p0_p1_p2_transport_stages_complete` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs` |
| `p2_run_matrix_matches_fix5_authority` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2` |
| `delayed_groundstate_and_division_audit` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delay_fix/normalization_audit_groundstate_fix.json` |
| `delayed_exactpos_m_sampling_inventory` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delay_fix/bgo_p2_exactpos_m50000_s260613_delayed_source_manifest.json` |
| `delayed_transport_header_and_counts` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delayed_transport_exactpos/DelayedDecayBgoP2ExactposM50000S260613.inc1.id1.sim.gz` |
| `focused_signal_replay_bgo_geometry` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/step09_focus/step09_focus_summary.json` |
| `step05_identical_selection_ingest` | `PASS` | `true` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/step05_ingest_exactpos_with_focus/bgo_engineering_step05_ingest_summary.json` |
| `w2_bgo_vs_fix5_comparison_with_uncertainty` | `PASS` | `false` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/step05_ingest_exactpos_with_focus/bgo_engineering_step05_ingest_summary.json` |
| `selected_w_origin_decomposition` | `WARN_NOT_AVAILABLE` | `false` | `engineering/background_validation_20260624/06_bgo_matched_runs/p2/delay_fix/bgo_p2_exactpos_m50000_s260613_delayed_source_manifest.json` |
| `no_tracked_authority_outputs_modified` | `PASS` | `true` | `git status --porcelain=v1` |

## W2 Result

- BGO background: `0.0374918947291 cps` from `158` final prompt+delayed events.
- fix5 background: `0.0392162265186 cps` from `84` final prompt+delayed events.
- BGO - fix5: `-0.00172433178956 cps`, simple-Poisson z `-0.2392`.
- BGO signal at reference flux: `0.00118056700506 cps`; signal keep vs fix5 `0.995524`.

Interpretation: the BGO engineering run is not off-provenance, but the BGO/fix5 W2 total-background difference is not statistically resolved by the simple independent-sample Poisson check. Do not claim a material preference from this result.

## Nonblocking Warnings

- `selected_w_origin_decomposition`: `WARN_NOT_AVAILABLE`.
