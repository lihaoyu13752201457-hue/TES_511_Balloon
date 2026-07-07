# Post-Execution Review - Stage-1 Full-Stat Preflight - 2026-07-02

review_role: `review_subagent`
review_scope: `Stage-1 full-stat preflight artifacts`
status: `PARTIAL_PRE_MC_READY_STAGE1_NOT_RUN_TRANSPORT`

## Conclusion

The new Stage-1 artifacts are sufficient to move the prompt/buildup portion of
the Mass_model_511 full-stat detector background campaign from pure `NOT_RUN` to
`PRE_MC_READY / NOT_RUN_TRANSPORT`.

They are not sufficient to close TODO 1 as a full detector background campaign,
because TODO 1 also requires delayed full-stat source construction and delayed
transport. A precise reviewer status is:

- `full_stat_detector_background`: `PARTIAL_PRE_MC_READY_STAGE1`
- `prompt_instant_fullstat_transport`: `PRE_MC_READY / NOT_RUN_TRANSPORT`
- `prompt_buildup_fullstat_transport`: `PRE_MC_READY / NOT_RUN_TRANSPORT`
- `delayed_fullstat_transport`: `NOT_PREPARED_IN_STAGE1`
- `full_stat_physics_closure`: `NOT_CLAIMED`

No reviewed Stage-1 file incorrectly claims full-stat detector rates,
replacement/no-effect closure, Step05 closure, Step06--Step08 closure, P1/P2/P3
replay closure, or manuscript readiness.

## Reviewed Artifacts

- `engineering/Mass_model_511_nearfield_migration_20260701/build_fullchain_execution_manifest.py`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/FULLCHAIN_EXECUTION_STATUS.md`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/fullchain_execution_manifest.json`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/todo_status.csv`
- `engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/RUN_FULLSTAT_TRANSPORT_STAGE1.sh`
- `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1/{normalization.json,run_manifest.csv,job_sources/}`
- `runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1/{normalization.json,run_manifest.csv,job_sources/}`

## Checks

| Check | Result | Evidence / Notes |
| --- | --- | --- |
| Overall status boundary | `PASS` | `FULLCHAIN_EXECUTION_STATUS.md` and manifest say `PASS_STAGE1_PREFLIGHT_NOT_RUN`, Cosima full-stat transport was not started, and downstream delayed/Step05/Step06--Step08/P1-P3 remain blocked. |
| False full-stat physics closure | `PASS_NO_FALSE_CLOSURE_FOUND` | Manifest claim boundary says "Execution preflight only. No full-stat detector-rate, no replacement, no manuscript-readiness claim." TODO rows keep Step05, replacement, Step06--Step08, and P1/P2/P3 as blocked. |
| Source authority geometry | `PASS` | Manifest audits 8 source cards, each with exactly the Mass_model_511 geometry line and no forbidden fix5 geometry. |
| Job-source geometry | `PASS` | 136/136 job source cards contain `outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`. No reviewed job source matched the old fix5 baseline or NF2 geometry patterns. |
| Run manifests | `PASS` | Instant and buildup `run_manifest.csv` each have 69 lines = 68 jobs plus header. Each mode requests 25,210,216 events with gamma 10,000,000, gamma splits 12, non-gamma replicas 8. |
| Transport outputs absent | `PASS_EXPECTED_NOT_RUN` | No `.sim.gz` or `.dat` outputs were found in the two Stage-1 fullstat run dirs; manifest reports `existing_sim_outputs: 0`, `existing_dat_outputs: 0` for both modes. |
| Runner command boundary | `PASS_WITH_HEAVY_RUN_CAVEAT` | `RUN_FULLSTAT_TRANSPORT_STAGE1.sh` runs only instant and buildup full-stat transport with `--allow-heavy-run`, then rebuilds the execution manifest. It intentionally stops before delayed source construction and Step05. Running it is the heavy MC step and should require explicit operator ownership/approval. |
| Delayed full-stat readiness | `NOT_PREPARED_IN_STAGE1` | Stage-1 prepares prompt instant and buildup only. No full-stat delayed source, delayed transport runner, delayed normalization audit, or M-sampling inventory audit is released by these artifacts. |

## Status Decision

Recommended status update for the completion matrix:

| TODO / Subtask | Previous Review Status | Post-Execution Review Status | Why |
| --- | --- | --- | --- |
| TODO 1 full-stat detector background campaign | `OPEN` | `PARTIAL_PRE_MC_READY_STAGE1 / NOT_RUN_TRANSPORT` | Prompt instant and buildup run manifests/job sources are ready and geometry-clean, but no transport outputs exist and delayed full-stat chain is not prepared. |
| TODO 2 full-stat Step05 detector response | `OPEN` | `BLOCKED` | Requires completed prompt, buildup, delayed transport, then full-stat Step05 retarget. |
| TODO 3 no-material-effect / replacement release | `OPEN` | `BLOCKED` | Requires full-stat Step05 and Step08 comparison evidence. |
| TODO 4 Step06--Step08 mission-axis regeneration | `OPEN` | `BLOCKED` | Requires validated full-stat Step05. |
| TODO 5 optics integration decision | `OPEN_FOR_MANUSCRIPT_SCOPE_DECISION` | `UNCHANGED` | Stage-1 does not touch optics coupling. |
| TODO 6 P1/P2/P3 replay on Mass_model_511 | `OPEN_BLOCKED_BY_TODO_2_AND_TODO_4` | `UNCHANGED_BLOCKED` | Stage-1 has no Step05/Step08 Mass_model_511 products. |

## Review Notes

One naming/status precision issue: `todo_status.csv` keeps
`full_stat_detector_background` as `NOT_RUN` with `preflight_status=PASS`.
That is not false, but for downstream reviewers it would be clearer to expose a
distinct combined status such as `PARTIAL_PRE_MC_READY_STAGE1_NOT_RUN_TRANSPORT`
or split the row into prompt/buildup preflight and delayed transport readiness.

The `normalization.json` files contain a legacy-looking
`resource_estimate_from_smoke.source` value (`runs/smoke_instant_1k` /
`runs/smoke_buildup_100`) with zero estimates, while the execution manifest
uses Mass_model_511 smoke summaries for planning estimates. This does not block
preflight readiness because it is only a resource estimate, not physics
normalization, but later release notes should avoid citing the zero-estimate
normalization resource block as the resource authority.

## Follow-Up Gate For Next Review

After Stage-1 transport is actually run, the next review should require:

- 68/68 instant SIM and DAT outputs plus 68/68 buildup SIM and DAT outputs.
- log-error scan with no blocking errors.
- SIM headers sampled or fully audited to confirm Mass_model_511 geometry.
- run summary with generated event counts matching manifests.
- no Step05/full-stat rate claim until delayed full-stat source/transport and
  full-stat Step05 replay are also complete.
