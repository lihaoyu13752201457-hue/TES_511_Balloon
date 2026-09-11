# Stage-1 Transport Post-Run Review - 2026-07-02

review_role: `review_subagent`
review_scope: `Mass_model_511 Stage-1 full-stat prompt/buildup transport evidence`
checked_at_utc: `2026-07-02T15:13:59Z`
status: `PASS_STAGE1_PROMPT_BUILDUP_TRANSPORT`
stage1_prompt_buildup_transport_pass: `YES`
full_stat_detector_background_pass: `NO_DELAYED_NOT_PREPARED`
stage2_delayed_fullstat_entry: `YES_WITH_STAGE2_GATES`

## Conclusion

Stage-1 prompt/buildup transport can be marked `PASS` for output-presence,
runner, geometry-header, and no-false-closure gates.

This is not full detector-background campaign closure. Delayed full-stat source
construction/transport and full-stat Step05 detector response remain not ready,
so no detector-rate, replacement/no-effect, Step06--Step08, P1/P2/P3, or
manuscript-readiness claim is supported by this Stage-1 review.

## Evidence Reviewed

- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/fullchain_execution_manifest.json`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/FULLCHAIN_EXECUTION_STATUS.md`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/todo_status.csv`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/STAGE1_TRANSPORT_RECOVERY_NOTES.md`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/stage1_transport_20260702T135633Z_with_megalib_env.log`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/stage1_transport_20260702T143443Z_fixed_runner.log`
- `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1/{run_summary.md,run_summary.csv,logs/,*.sim.gz,*.dat}`
- `runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1/{run_summary.md,run_summary.csv,logs/,*.sim.gz,*.dat}`

## Gate Results

| Gate | Result | Evidence / Notes |
| --- | --- | --- |
| Manifest status | `PASS` | `overall_status=PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT_DELAYED_NOT_PREPARED`; instant and buildup mode records are both `PASS_STAGE1_TRANSPORT_OUTPUTS_PRESENT`. |
| Instant outputs | `PASS` | 68/68 `.sim.gz` and 68/68 `.dat` files exist in the instant full-stat run dir. |
| Buildup outputs | `PASS` | 68/68 `.sim.gz` and 68/68 `.dat` files exist in the buildup full-stat run dir. |
| Run summaries | `PASS_WITH_INSTANT_SKIP_CAVEAT` | Instant final `run_summary.md`: 68 jobs, `pass_or_skip=68`, `fail=0`, `events_generated=25210216`; final CSV has 68 `SKIP` rows after outputs already existed. Buildup final summary has 68 `PASS`, 0 fail, `events_generated=25210216`. |
| Instant SKIP support | `PASS` | Instant SKIP is supported by actual 68/68 SIM+DAT path existence, instant job logs with 68/68 `returncode=0`, and recovery transcript `stage1_transport_20260702T135633Z_with_megalib_env.log` showing instant `completed jobs=68 failures=0` before the later script-path failure. |
| Runner failure state | `PASS` | Current job logs: instant 68/68 final `returncode=0`; buildup 68/68 final `returncode=0`. `rg` for current job-log failure/library patterns returned no hits. |
| Recovery failures superseded | `PASS_WITH_HISTORY_RETAINED` | `STAGE1_TRANSPORT_RECOVERY_NOTES.md` records the first libSivan failure with no outputs. The `135633Z` recovery transcript records instant success, then exits 127 from a script path issue before buildup. The later `143443Z_fixed_runner.log` exits 0 and covers both modes; current manifest/output counts supersede the failed attempts. |
| SIM geometry headers | `PASS` | Full scan of 136 SIM headers found one unique `Geometry` line, all pointing to `/home/ubuntu/TES_511_Balloon/outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`. |
| Forbidden geometry | `PASS` | Header/job-source scans found 0 forbidden fix5 / old NF2 geometry references. Broad SIM text contains `NF2_OuterSupport_*` component names in event records; these are volume names, not geometry-header or source-card provenance failures. |
| False physics closure | `PASS_NO_FALSE_CLOSURE_FOUND` | Manifest claim boundary says Stage-1 output presence only. `todo_status.csv` keeps delayed, Step05, replacement/no-effect, Step06--Step08, and P1/P2/P3 blocked/not ready. |
| Disk condition | `WARN_NON_BLOCKING` | `df -h .` showed about 19G available on `/home/ubuntu/TES_511_Balloon`; acceptable for review, but Stage-2 should check space before starting delayed full-stat. |

## Status Decision

| Scope | Review status | Rationale |
| --- | --- | --- |
| Stage-1 prompt/buildup transport | `PASS` | Required 136 SIM and 136 DAT outputs exist, summaries/logs show no current failures, and all SIM headers use the Mass_model_511 geometry. |
| Instant final SKIP summary | `ACCEPTED` | The SKIP state is consistent with a rerun after successful instant outputs already existed; supported by file counts, per-job logs, and recovery transcript. Do not treat the instant CSV `sim_exists/dat_exists=False` fields as the output-presence authority. |
| Full-stat detector background campaign | `NOT_PASS_DELAYED_NOT_PREPARED` | Stage-1 excludes delayed full-stat source/transport and downstream Step05. |
| Delayed full-stat Stage-2 entry | `ALLOW_NEXT_STAGE` | Stage-1 no longer blocks Stage-2. Stage-2 still needs its own source/normalization audit, M-sampling inventory and TT division guard where applicable, run manifest, geometry header audit, and disk/runtime preflight. |

## Review Notes

The only material caveat is bookkeeping precision in the instant final
`run_summary.csv`: its rows are `SKIP`, and its `sim_exists/dat_exists` columns
remain `False` with zero sizes even though the referenced output paths now
exist. This does not block Stage-1 PASS because the final manifest, direct file
counts, run_summary.md, recovery transcript, and 68/68 instant job logs support
successful transport output presence. Future tooling should avoid using those
instant CSV boolean/size fields as the sole output-presence authority after a
skip/rerun.
