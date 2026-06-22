# PRE-PROMPT — fix5 simulation closure

You are continuing the TES_511_Balloon fix5 simulation closure task.

Repository root:

`/home/ubuntu/TES_511_Balloon`

## Do First

Read these files, in order:

1. `AGENTS.md`
2. `core_md/METHOD_FIX5_SIM_CLOSURE.md` (what the gates compute)
3. `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`
4. `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`
5. `core_md/fix5_benchmarks.json` (single numeric authority)
6. `core_md/Project_Memory.md` -> "The 11-Step Conceptual Chain", steps 9/10/11
7. `core_md/HANDOFF_20260617.md`
8. `core_md/workflow.md`
9. `outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md`
10. `outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json`

Do not start MC before confirming the checkpoint below.

## Checkpoint To State Before Running

Reply with:

1. fix5 `.geo.setup` path;
2. in your own words: how Step05 puts prompt/delayed/focused streams on one
   Poisson time axis, and how Step06 folds the day-15 point to a 20-day mission
   (proves you read the method, not just the labels);
3. the delayed-normalization recipe and the audit artifacts/thresholds that make
   it auditable (NUBASE ground-state correction, per-family TT division guard,
   M-sampling inventory audit);
4. old `new_geo_re` prompt/delayed numbers AND the v3p5 promotion-bar numbers,
   stating which is the 1/10 screen target and which is the full-stat promotion
   bar, plus the 0.0323 selection/normalization caveat;
5. the required machine-readable artifacts from `fix5_benchmarks.json`:
   `fix5_source_manifest.json`, `fix5_benchmark_alignment.json`,
   `fix5_verification_verdict.json`, and final `fix5_promotion_decision.json`;
6. what "1/10 pass" means, including benchmark alignment, the
   `N_eff`/Poisson-sigma reporting rule, hard-fail formula, and inconclusive
   case;
7. which existing outputs are comparison-only and must not be overwritten;
8. the first concrete Builder/Verifier/Runner split.

## Active Objective

The geometry is fixed.  Do not optimize geometry.

Use fix5 geometry:

`outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

Run a 1/10-statistics test first:

- prompt total should be close to old `new_geo_re` prompt total
  `0.0323247092031 cps`, but only after benchmark alignment proves the old
  selection/normalization is comparable;
- delayed total should be below old `new_geo_re` delayed total
  `0.151456825339 cps` only as a loose aligned screen, while also comparing delayed and
  W/collimator activation against the current v3p5 delayed authority.

If the 1/10 gate passes, complete the remaining statistics/full-stat closure
with a clean full-stat run by default, then regenerate the project chain through
Step08 plus the fix5 signal replay.  Append/merge is allowed only with a PASS
`fix5_merge_verdict.json`.

## Loop Model

- Orchestrator: holds guide, constraints, gates, and stop decisions.
- Builder: creates fix5 source cards and runs transport jobs in new directories.
- Verifier: independently checks geometry provenance, normalization, delayed
  source inventory, benchmark alignment, comparison numbers, and promotion
  decision artifacts.
- Runner: runs MC only after the current gate is green.

Fail closed:

- wrong geometry in source/SIM header -> invalidate and rerun;
- missing source manifest / benchmark alignment / verification verdict -> do not
  gate the run;
- old `new_geo_re` not aligned -> report it only as historical context;
- 1/10 prompt clearly fails by the JSON hard-fail formula -> stop and report;
- 1/10 statistically inconclusive -> escalate statistics, do not pass/fail;
- delayed normalization not auditable -> no delayed claim;
- append/merge without PASS merge verdict -> run clean full-stat instead;
- full-stat result overrides 1/10.
