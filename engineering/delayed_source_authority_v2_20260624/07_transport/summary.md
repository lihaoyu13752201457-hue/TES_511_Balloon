# WP07 Pilot Transport

status: `PARTIAL_PILOT_TRANSPORT_SOURCE_V2_NATIVE_SELECTION_DIAGNOSTIC_LEGACY_TIMEOUT_NOT_PROMOTION`

Claim boundary: 1000-trigger pilot transport and selected-rate diagnostic only; no full-stat promotion.

| pilot | run | generated IDs | kept events | W2 final events | W2 final cps |
|---|---:|---:|---:|---:|---:|
| v2_weighted_eventlist | `PASS` | 1000 | 840 | 0 | 0 |
| native_volume_activation | `PASS` | 1000 | 832 | 1 | 0.0869998 |
| legacy_l0 | `TIMEOUT_PREVIOUS` |  |  |  | 0 |

Outputs:
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_transport_run_summary.json`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_transport_run_summary.md`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_selected_rate_diagnostics.csv`
- `engineering/delayed_source_authority_v2_20260624/07_transport/summary.md`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_runs/v2_eventlist_pilot1000.inc1.id1.sim.gz`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_runs/v2_eventlist_pilot1000.log`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_runs/native_activation_pilot1000.inc1.id1.sim.gz`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_runs/native_activation_pilot1000.log`
- `engineering/delayed_source_authority_v2_20260624/07_transport/pilot_runs/legacy_l0_pilot1000.log`

Findings:
- Ran only the prepared 1000-trigger WP07 pilot matrix; no full-stat transport or promotion was launched.
- v2_weighted_eventlist: W2 side-Compton/FoV pass 0 events, 0 cps (pilot_event_weight_Bq from weighted PPS ledger)
- native_volume_activation: W2 side-Compton/FoV pass 1 events, 0.0869998 cps (sum(RP activity in native ActivationSources store)/Triggers)
- legacy_l0: transport status TIMEOUT_PREVIOUS
