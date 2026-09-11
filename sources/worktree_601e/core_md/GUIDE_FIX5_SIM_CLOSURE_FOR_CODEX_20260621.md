# GUIDE — fix5 geometry simulation closure loop

Date: 2026-06-21.  This guide supersedes the prompt-511 geometry-refix loop for
the active task only.  The earlier Claude loop remains useful as a method, but
the objective has changed.

## One-Line Task

Use the already built fix5 geometry as the candidate mass model, run a
1/10-statistics test, decide whether it reaches the old `new_geo_re` prompt
scale after benchmark alignment, check that delayed does not introduce a new
v3p5/W-activation problem, then complete the remaining statistics and project
closure only if the staged gate passes or is explicitly escalated for more
statistics.

The numeric authority and required machine-readable artifacts are all in
`core_md/fix5_benchmarks.json`.  In particular, old `new_geo_re` is not a gate
until `required_artifacts.benchmark_alignment` reports `decision == ALIGNED`.

## Why This Is Not The Old Geometry-Refix Task

The old Claude loop searched for a minimally invasive passive high-Z shield on
top of the original baseline.  That strict route forbade changing baseline
structures such as `TES_*`, `Cu_ColdFinger_*`, and `Cryoperm_*`.

The present task is different:

- fix5 is already built as a user redesign mass model;
- the question is now performance validation, not geometry search;
- `check_prompt511_constraints.py` is expected to fail on fix5 because fix5 is
  not the baseline-only passive-shield refix candidate;
- the useful loop-engineering pattern is still retained: staged gates,
  Builder/Verifier separation, cheap-before-expensive, structured artifacts,
  and fail-closed decisions.

## Candidate Geometry Authority

Use this geometry for all fix5 source cards:

`outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

Read these fix5 artifacts first:

1. `outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md`
2. `outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json`
3. `outputs/reports/user_redesign_multiholeW_fix5_20260621/geometry_det_reference_check.json`
4. `outputs/reports/user_redesign_multiholeW_fix5_20260621/cosima_overlap_fix5_20260621.log`

Current fix5 geometry status:

- side-window through-cut audit: PASS;
- magnetic incident aperture audit: PASS;
- CsI bottom/side seam audit: PASS;
- `.det` reference check: PASS;
- `cosima CheckForOverlaps`: PASS;
- no prompt/delayed/signal MC closure yet.

## Comparison Benchmarks

Old `new_geo_re` comparison values:

- prompt total: `0.0323247092031 cps`;
- delayed total: `0.151456825339 cps`;
- prompt eplus: `0.0244744226824 cps`.

Current v3p5 references:

- current full-stat v2 prompt eplus: `0.0543377485018 cps`;
- current exact-position M=50000 Step05 selected background/signal:
  `0.06298036183985109 / 0.0011811656293957314 s^-1`.

Interpretation:

- For the 1/10 gate, "prompt close to `new_geo_re`" means prompt total is
  statistically consistent with `0.0323247092031 cps`, with a provisional
  tolerance up to `1.25x` only for go/no-go uncertainty, and only after
  benchmark alignment.
- "Delayed lower than `new_geo_re`" means delayed total is below
  `0.151456825339 cps`, with auditable delayed-source normalization; this is a
  loose historical screen, not the meaningful delayed bar.
- Full-stat closure must use the current v3p5 authority, not the 1/10 estimate
  or old `new_geo_re`, for any replacement claim.  The promotion decision must
  evaluate total B, delayed/W activation, signal keep, `Z20d`, and `F3(20d)`.

## Loop Roles

Use the same loop-engineering structure, with roles retargeted to validation.

### Orchestrator

Holds this guide, `CONSTRAINTS_FIX5_SIM_CLOSURE.md`, labels, gates, and stop
decisions.  It should not trust a run until the Verifier checks geometry
provenance and normalization.

### Builder

Creates fix5 source cards and runs the actual transport jobs in new output
directories.  It must return structured artifacts, not only prose:

- `fix5_source_manifest.json` as defined by
  `fix5_benchmarks.json` -> `required_artifacts.source_manifest`;
- `fix5_benchmark_alignment.json` before any old-new_geo_re pass/fail gate;
- run manifests;
- prompt/buildup/delayed transport summaries;
- Step05--Step08 summaries;
- logs and failed-job list;
- exact command lines and environment.

### Verifier

The Verifier's checks must be DETERMINISTIC (scripts + file assertions), not
agent prose, and must emit a structured verdict
`outputs/reports/fix5_*/fix5_verification_verdict.json` with one
`{check, status, evidence_path}` row per item below.  Reuse the existing
machinery (`fix5_benchmarks.json` -> scripts); do not re-implement it:

- source cards AND generated SIM headers contain the fix5 `.geo.setup` and never
  the baseline setup (grep assertion over every source/SIM);
- prompt normalization self-consistent (`1/sum(TT)`);
- delayed normalization closure passes (C1b): `normalization_audit_groundstate_fix.json`
  `status==PASS/problems==[]`, `audit_groundstate_half_life_units.py`, and the
  M-sampling thresholds;
- benchmark alignment before using old `new_geo_re` as a pass/fail gate:
  line-window, veto thresholds, Compton/FoV selection, source surface/far-field
  normalization, rate units, and `decision == ALIGNED`;
- 1/10 selected-event counts (`N_eff`) and Poisson sigma are reported, and
  exposure ratios stated honestly (the `1of10` label is not one tenth for every
  family);
- Step05--Step08 read fix5 outputs, not baseline — confirm via the
  exactpos-closure validator with a fix5 path prefix (see the validator note in
  `fix5_benchmarks.json`; its templates assume `v3p5_centerfinger_{label}`, so
  wire the path explicitly rather than letting it fall back to v3p5);
- comparison tables use the `fix5_benchmarks.json` keys for both `new_geo_re`
  (screen) and v3p5 (promotion bar), with the 0.0323 caveat attached.
- full-stat replacement claims include
  `fix5_benchmarks.json` -> `required_artifacts.promotion_decision`.

### Runner

Runs expensive MC only after Orchestrator marks the cheap gates green.  For this
task, Runner first executes 1/10.  It runs the remaining 9/10/full-stat closure
only if the 1/10 prompt and delayed gates pass.

Cost model (gate at the right boundary): Step02 transport + Step05 detector
response are the expensive parts; Step06/07/08 are cheap rate-level folds that
depend on Step05.  The 1/10 screen exists to avoid paying full-stat
Step02+Step05 before the geometry is shown to be in the right ballpark.  Never
regenerate Step06/07/08 from a Step05 that has not passed provenance (C1) and
normalization closure (C1b).

## Iteration Plan

### Phase 0 — Re-entry

Read:

1. `AGENTS.md`
2. `core_md/METHOD_FIX5_SIM_CLOSURE.md` (what the gates compute; read before the
   contract)
3. `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`
4. `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`
5. `core_md/fix5_benchmarks.json` (single numeric authority)
6. `core_md/Project_Memory.md` -> "The 11-Step Conceptual Chain", steps 9
   (common time axis), 10 (mission fold), 11 (significance)
7. `core_md/HANDOFF_20260617.md`
8. `core_md/workflow.md`
9. the four fix5 artifacts listed above

Then produce a checkpoint:

- active geometry path;
- benchmark prompt/delayed numbers;
- exact meaning of the 1/10 gate;
- which outputs must be regenerated and which old outputs are comparison only.

### Phase 1 — Fix5 Source Cards

Create a fix5-specific source-card directory by replacing only the geometry
setup line in the current v3p5 source-card templates.  Do not edit existing
baseline source-card directories in place.

Required audit:

- all source files contain fix5 `.geo.setup`;
- far-field radius and flux normalization are unchanged unless explicitly
  documented;
- source manifest records geometry path and normalization constants.

### Phase 2 — 1/10 Transport

Run low-stat prompt instant and activation buildup using the fix5 source cards.
The old `1of10` label in this repo is not exactly one tenth for every particle
family; the run report must state actual generated events and exposure ratios.

Build the fix5 delayed source and delayed transport for the same 1/10 label.
The delayed source must be derived from fix5 activation production, not copied
from baseline.

### Phase 3 — 1/10 Detector Response And Gate

Run Step05 detector response for the fix5 1/10 label.  Regenerate Step06,
Step07, and Step08 only after Step05 passes basic provenance and normalization
checks.

Gate:

- prompt total close to `0.0323247092031 cps` only if benchmark alignment is
  `ALIGNED`; otherwise report it as historical context and escalate/compare
  against v3p5;
- delayed total below `0.151456825339 cps` only as a loose aligned screen;
- delayed also compared to the current v3p5 delayed rate and W/collimator
  activation marked explicitly;
- source/SIM geometry provenance is fix5;
- no hidden reuse of baseline response outputs.

If the gate fails, stop and report the reason.  If the gate is statistically
inconclusive, escalate statistics rather than recording pass/fail.  Do not run
the remaining 9/10/full-stat production after a hard fail without user approval.

### Phase 4 — Complete Remaining Statistics

If Phase 3 passes, complete statistics by the safe default path:

1. clean full-stat fix5 production.

Append/merge is allowed only if `fix5_benchmarks.json` -> `merge_policy` is
fully satisfied and a `fix5_merge_verdict.json` reports PASS.  If in doubt, run
a clean full-stat fix5 label.

### Phase 5 — Full Project Closure

Regenerate:

- Step02 summaries;
- exact-position delayed-source summary if used;
- Step05 L1 response;
- Step06 mission-time variation;
- Step07 source cases;
- Step08 significance;
- Step09 focused signal replay through fix5 geometry;
- final fix5 closure report and comparison table.
- `fix5_promotion_decision.json` with total B, sigma, prompt, delayed, W
  activation, signal keep, `Z20d`, `F3(20d)`, and final decision.

The final report must compare:

- fix5 full-stat vs old `new_geo_re`;
- fix5 full-stat vs current v3p5 authority;
- 1/10 prediction vs full-stat result.

The final report may say "fix5 replaces current v3p5" only if
`fix5_benchmarks.json` -> `promotion_thresholds.automatic_pass_rule` is
satisfied, or if misses are explicitly marked `USER_REVIEW_REQUIRED` rather
than hidden as a pass.

## Required Output Layout

Use a new label rooted in `fix5`, for example:

- `runs/step02_instant_fix5_1of10/`
- `runs/step02_buildup_fix5_1of10/`
- `runs/step02_delay_fix_fix5_1of10/`
- `runs/step02_delayed_transport_fix5_1of10/`
- `stepwise_maintenance/step02_raw_background_simulation/outputs_fix5_1of10/`
- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_1of10_l1/`
- `outputs/reports/fix5_1of10_closure_20260621/`

For full-stat:

- use `fix5_fullstat` or `fix5_fullstat_exactpos_m50000_s260613`;
- do not write over current v3p5 or BGO outputs.

## Practical Cautions

- Existing scripts are heavily label/path based and may assume
  `v3p5_centerfinger_*`.  Treat path configuration as part of Builder's task.
- A run that says "fix5" in its directory name but uses baseline geometry in the
  source card is invalid.
- The native `.det` convention intentionally marks many passive volumes as
  sensitive for tracking; do not remove this unless the user asks.
- The old prompt-511 constraint checker is useful as historical context but not
  a pass/fail gate for fix5 replacement, because its objective is different.
