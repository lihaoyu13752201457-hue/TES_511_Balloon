# SF3 Plan-1 final chain audit

Status: `PASS__SF3_PLAN1_CHAIN_COMPLETE__CENTRAL_FULLSTAT_GATE_RECORDED`

This closes the fresh SF3 approximately one-third screen against the frozen 47/SE3 small-table denominator. No SE3/S3d transport was rerun, and this finalizer did not open, stat, discover or hash a SIM payload.

## Chain closure

| Stage | Status | Summary |
|---|---|---|
| stage00 | PASS | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/00_input_audit/input_audit.json` |
| stage01 | PASS__SF3_PLAN1_PROMPT_COMPLETE | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/01_prompt/summary.json` |
| stage02 | PASS__SF3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/02_activation/day15_summary.json` |
| stage03 | PASS__SF3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/03_delayed/summary.json` |
| stage04 | PASS__SF3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/04_common_response/summary.json` |
| stage05 | PASS__SF3_VS_FROZEN_SE3_DAY15_AND_FULL_ENVELOPE_COMPARISON | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/05_se3_vs_sf3_matched_comparison/summary.json` |
| stage06 | PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_AND_GATE | `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/06_mission/summary.json` |

## Central 20-day result and sole full-stat gate

| Quantity | SF3 | Frozen SE3 |
|---|---:|---:|
| Full-envelope selected rays | 21785 / 37194 | 21657 / 37194 |
| Full-envelope Aeff (cm²) | 11.7639 | 11.69478 |
| S20 (counts) | 1286.832682 | 1279.288658 |
| B20 (counts) | 361685.5527 | 98257.66905 |
| F3 central (ph cm⁻² s⁻¹) | 0.000140205404 | 7.350822463e-05 |
| F3 componentwise proxy | 0.0004725340581 | 0.000448131034 |

Central F3 ratio SF3/SE3: **1.907343085**; threshold: **<= 0.75**; decision: `STOP__NO_FULLSTAT_TOPUP`. The componentwise proxy is reported only and never controls this gate.

Conditional disposition: `STOP__NO_FULLSTAT_TOPUP`. The finalizer launched neither transport nor top-up.

## Transport closure

- 21 background jobs: 1,280,693 instant and 1,015,492 buildup histories.
- Eight delayed cells registered: 7 RUN_83334 and 1 auditable SKIP_ZERO_A15.
- One fresh SF3 full-envelope signal: 37,194 rays.
- Effective canonical receipts: 29.
- The three SF3 W volumes remain passive diagnostics, disjoint from the three-BGO plus three-plastic active veto.

## Resource contract

- Configured ceiling: 6 CPU cores with an adaptive 4–6 worker design; this is a budget, not the observed execution setting.
- Actual controller after systemd-oomd recovery: 4 workers. The completed manual pressure episode used the observed quota sequence 4→3→4; all logged guard sessions stayed within [3, 4] cores and any throttle had to close restored at four cores.
- Guard-session coverage: 7 closed sessions spanning ['background', 'delayed', 'signal']. A safe all-four-core session passes and no artificial throttle is required.
- Peak cgroup memory-pressure some avg10: 43.42% against the recorded 50% kill gate; approximately 20 s later: 3.67%; later recovery: 0%.
- MemAvailable floor: 1,610,612,736 bytes; SwapFree floor: 8,589,934,592 bytes.
- Dynamic disk reserve: 8,589,934,592 bytes; final check free: 47,734,743,040 bytes.
- The pressure guard changed only aggregate CPUQuota, retained the four admitted workers, and did not signal or terminate a job.
- GUI-disconnected partial attempts are retained in the recovery audit, excluded from statistics, and whole-job retries start from event zero with the registered seed.

Machine-readable audit: `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/07_final_audit/final_audit.json`
Canonical receipt table: `/home/ubuntu/.codex/worktrees/ddb4/TES_511_Balloon/engineering/geometry_optimization_20260815/49_sf3_plan1_transport_20260816/outputs/07_final_audit/job_receipts.csv`
