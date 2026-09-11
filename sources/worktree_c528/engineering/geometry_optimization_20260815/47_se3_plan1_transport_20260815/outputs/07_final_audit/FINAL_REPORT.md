# SE3 Plan-1 final chain audit

Status: `PASS__SE3_PLAN1_EFFECTIVE_SE3_ONLY_CHAIN_COMPLETE`

This is the effective SE3-only approximately one-third atmospheric cosmic-ray screen. No fresh S3d transport receipt or SIM is used. S3d enters only through frozen corrected-M05 small-table background anchors.

## Chain closure

| Stage | Status | Summary |
|---|---|---|
| stage00 | PASS | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/00_input_audit/input_audit.json` |
| stage01 | PASS__SE3_PLAN1_PROMPT_COMPLETE | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/01_prompt/summary.json` |
| stage02 | PASS__SE3_CANDIDATE_OWN_ACTIVATION_AND_DELAYED_SOURCES_READY | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/02_activation/day15_summary.json` |
| stage03 | PASS__SE3_PLAN1_DELAYED_RAW_CATALOG_8_REGISTERED_SOURCE_CELLS_COMPLETE | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/03_delayed/summary.json` |
| stage04 | PASS__SE3_PLAN1_COMMON_RESPONSE_AND_FULL_ENVELOPE_SIGNAL_COMPLETE | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/04_common_response/summary.json` |
| stage05 | PASS__SE3_PLAN1_DAY15_BACKGROUND_COMPARISON_AND_SE3_ONLY_FULL_ENVELOPE_SIGNAL | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/05_matched_comparison/summary.json` |
| stage06 | PASS__SE3_FULL_ENVELOPE_81NODE_ABSOLUTE_F3__S3D_RATIO_UNAVAILABLE_BY_USER_SCOPE | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/06_mission/summary.json` |

## Central results

| Quantity | Value |
|---|---:|
| SE3 day-15 prompt W2 rate (cps) | 0 |
| SE3 day-15 delayed W2 rate (cps) | 0.06011336206 |
| SE3 day-15 total W2 background (cps) | 0.06011336206 |
| SE3 full-envelope selected rays | 21657 / 37194 |
| SE3 full-envelope W2 Aeff (cm²) | 11.69478 |
| SE3 S20 (counts/20 d at reference flux) | 1279.288658 |
| SE3 B20 (counts/20 d) | 98257.66905 |
| SE3 F3 central (ph cm⁻² s⁻¹) | 7.350822463e-05 |
| SE3 F3 componentwise proxy (ph cm⁻² s⁻¹) | 0.000448131034 |
| SE3/S3d frozen-background B20 ratio | 0.6813803823 |
| Fair SE3/S3d full-envelope F3 ratio | UNAVAILABLE_BY_USER_SCOPE |
| Fair SE3/S3d full-envelope F3 proxy ratio | UNAVAILABLE_BY_USER_SCOPE |

The historical S3d post-Be 37,194→27,855 result is retained separately for continuity only. It is excluded from every full-envelope signal, S20, Z20, and F3 geometry ratio.

## Effective transport receipts

| Job | Stage/mode/family | Events | Seed | Attempt | SIM bytes (receipt) | Receipt |
|---|---|---:|---:|---:|---:|---|
| se3_instant_p_shard0001 | background/instant/p | 8483 | 257745019 | 1 | 1568347710 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_p_shard0001.json` |
| se3_instant_n_shard0001 | background/instant/n | 77664 | 350333121 | 1 | 1725554182 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_n_shard0001.json` |
| se3_instant_alpha_shard0001 | background/instant/alpha | 1986 | 698219815 | 1 | 1140978610 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_alpha_shard0001.json` |
| se3_instant_gamma_shard0001 | background/instant/gamma | 267312 | 17335553 | 1 | 825997475 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_gamma_shard0001.json` |
| se3_instant_gamma_shard0002 | background/instant/gamma | 267312 | 1444771823 | 2 | 664687976 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_gamma_shard0002.json` |
| se3_instant_gamma_shard0003 | background/instant/gamma | 267311 | 510145530 | 2 | 696295592 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_gamma_shard0003.json` |
| se3_instant_gamma_shard0004 | background/instant/gamma | 267311 | 75116849 | 2 | 744023681 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_gamma_shard0004.json` |
| se3_instant_eminus_shard0001 | background/instant/eminus | 98447 | 24441020 | 1 | 999557843 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_eminus_shard0001.json` |
| se3_instant_eplus_shard0001 | background/instant/eplus | 20062 | 11951432 | 1 | 1064758936 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_eplus_shard0001.json` |
| se3_instant_muminus_shard0001 | background/instant/muminus | 3481 | 2095522014 | 1 | 45034036 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_muminus_shard0001.json` |
| se3_instant_muplus_shard0001 | background/instant/muplus | 1324 | 959043160 | 1 | 15040689 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_instant_muplus_shard0001.json` |
| se3_buildup_p_shard0001 | background/buildup/p | 8483 | 564553771 | 1 | 1596187496 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_p_shard0001.json` |
| se3_buildup_n_shard0001 | background/buildup/n | 77664 | 1251619310 | 1 | 1608962098 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_n_shard0001.json` |
| se3_buildup_alpha_shard0001 | background/buildup/alpha | 1448 | 642058344 | 1 | 869442134 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_alpha_shard0001.json` |
| se3_buildup_gamma_shard0001 | background/buildup/gamma | 261834 | 759462178 | 2 | 806937816 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_gamma_shard0001.json` |
| se3_buildup_gamma_shard0002 | background/buildup/gamma | 261833 | 1834413879 | 1 | 734443191 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_gamma_shard0002.json` |
| se3_buildup_gamma_shard0003 | background/buildup/gamma | 261833 | 1199774548 | 1 | 742484816 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_gamma_shard0003.json` |
| se3_buildup_eminus_shard0001 | background/buildup/eminus | 98447 | 1474371813 | 1 | 986965650 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_eminus_shard0001.json` |
| se3_buildup_eplus_shard0001 | background/buildup/eplus | 20062 | 327081436 | 1 | 1266988827 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_eplus_shard0001.json` |
| se3_buildup_muminus_shard0001 | background/buildup/muminus | 22564 | 1992673634 | 1 | 284891815 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_muminus_shard0001.json` |
| se3_buildup_muplus_shard0001 | background/buildup/muplus | 1324 | 929993937 | 1 | 16379245 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_buildup_muplus_shard0001.json` |
| se3_delayed_p | delayed/delayed/p | 83334 | 411155092 | 1 | 120898829 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_p.json` |
| se3_delayed_n | delayed/delayed/n | 83334 | 1790685736 | 1 | 120376293 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_n.json` |
| se3_delayed_alpha | delayed/delayed/alpha | 83334 | 1553238536 | 1 | 121023673 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_alpha.json` |
| se3_delayed_gamma | delayed/delayed/gamma | 83334 | 394632688 | 1 | 99252020 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_gamma.json` |
| se3_delayed_eminus | delayed/delayed/eminus | 83334 | 773195088 | 1 | 97396242 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_eminus.json` |
| se3_delayed_eplus | delayed/delayed/eplus | 83334 | 1836486006 | 1 | 121433487 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_eplus.json` |
| se3_delayed_muminus | delayed/delayed/muminus | 83334 | 482454111 | 1 | 106494046 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/se3_delayed_muminus.json` |
| signal_full_envelope_se3 | signal/signal/focused_gamma | 37194 | 93405522 | 1 | 25960816 | `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/runs/geometry_optimization_20260815/se3_plan1_one_third_transport_v1/receipts/signal_full_envelope_se3.json` |

## Resource receipt totals

- Effective jobs: 29 (21 background + 7 delayed RUN + 1 SE3 signal).
- Dynamic zero-A15 skips: 1.
- SIM bytes from receipt metadata: 19,216,795,224; artifact bytes: 19,688,561,799.
- Maximum audited process-group RSS: 6,976,733,184 bytes.
- Disk free before stage07 publication: 76,047,114,240 bytes; 8 GiB reserve pass: True.

Machine-readable audit: `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/07_final_audit/final_audit.json`
Receipt table: `/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/47_se3_plan1_transport_20260815/outputs/07_final_audit/job_receipts.csv`

No SIM payload was opened, statted, or hashed by this finalizer.
