# CONSTRAINTS — fix5 simulation closure (short enforced contract)

This contract replaces the old prompt-511 geometry-refix objective for the
active task.  The geometry is fixed: use fix5, do not optimize geometry unless
the user explicitly reopens geometry design.

Read `core_md/METHOD_FIX5_SIM_CLOSURE.md` first: the gates below are checks on a
specific method (Poisson common-time-axis merge, analytic 81-bin mission fold,
NUBASE+division delayed normalization).  Without it these gates are only
file-name checks.  All numbers come from `core_md/fix5_benchmarks.json`; the
values restated below are convenience copies of its keys.

## Objective

Run the current project pipeline on the fix5 geometry and decide whether it can
replace the current v3p5 geometry for the selected 511 keV rate result.

Primary staged goal:

1. Run a 1/10-statistics fix5 test relative to the current full project chain.
2. Check:
   - `PROMPT_total` is at the old `new_geo_re` scale, but only after benchmark
     alignment.
   - `DELAYED_total` is checked against old `new_geo_re` only as a loose aligned
     screen, and does not introduce a clear v3p5-delayed/W-activation problem.
3. If both pass, run a clean full-stat fix5 closure by default and close the
   Step02--Step08/Step09 project chain.  Append/merge is allowed only with the
   explicit merge verdict in `fix5_benchmarks.json` -> `merge_policy`.

## Fixed Inputs

- Candidate geometry:
  `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/`
- Main setup:
  `outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Fix5 handoff:
  `outputs/reports/user_redesign_multiholeW_fix5_20260621/USER_CYLMAG_REDESIGN_MULTIHOLEW_FIX5_SUMMARY.md`
- Fix5 geometry audit:
  `outputs/reports/user_redesign_multiholeW_fix5_20260621/side_window_material_path_audit_fix5.json`
- Fix5 overlap log:
  `outputs/reports/user_redesign_multiholeW_fix5_20260621/cosima_overlap_fix5_20260621.log`

Do not use `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/`
for fix5 production source cards except as a comparison baseline.

## Benchmark Numbers

Old `new_geo_re` comparison values from the prompt-511 handoff:

- `PROMPT_old_total_cps = 0.0323247092031`
- `DELAYED_old_total_cps = 0.151456825339`
- `PROMPT_old_eplus_cps = 0.0244744226824`

Current v3p5 full-stat reference values:

- `PROMPT_current_eplus_cps = 0.0543377485018`
- current exact-position M=50000 Step05 background/signal:
  `0.06298036183985109 / 0.0011811656293957314 s^-1`
- current exact-position W2 delayed: `~0.0039 cps`; Step08 `Z20d = 6.13039`.

Reading these correctly (do not gate on a bare point value):

- **Decision bar.** `new_geo_re` is the coarse 1/10 *screen* target only; the
  real full-stat *promotion* bar is the v3p5 exact-position authority.  fix5
  succeeds by lowering the v3p5 total selected background (mainly side-port
  prompt e+ 511) without adding W self-background, holding/improving `Z20d`.
- **`PROMPT_old_total_cps = 0.0323` carries a caveat.** Old `new_geo_re` had
  lower hard-window prompt partly because its side region was blocked by a solid
  side-shield/material column and because source-surface normalization differed
  (HANDOFF).  Verify the benchmark selection definition (window / veto /
  Compton-FoV / source-surface normalization) matches the fix5 computation
  before comparing; it is currently `UNVERIFIED`.
- **`DELAYED_old_total_cps = 0.1515` is ~40x above the current v3p5 delayed
  (~0.0039).** "delayed < 0.1515" is nearly vacuous; the meaningful comparison
  is against ~0.0039 and the W-activation subcomponent.
- **Uncertainty.** The v3p5 full-stat selected background is only ~132 events
  (~87 prompt-stream) -> sigma ~9-11%; a 1/10 screen has ~13/~9 events ->
  sigma ~28-34%.  Always report `N_eff` and Poisson sigma; a bare 1.25x prompt
  tolerance is inside the 1/10 noise.
- **Alignment requirement.** Old `new_geo_re` numbers can be used as gates only
  after producing `fix5_benchmarks.json` -> `required_artifacts.benchmark_alignment`
  with `decision == ALIGNED`.  If not aligned, report them as historical context
  and gate against the current v3p5 authority instead.

## Gates

C0. Geometry fixed and audited.

- `side_window_material_path_audit_fix5.json` must have `overall_pass=true`.
- `cosima_overlap_fix5_20260621.log` must reach `Summary for run Minimum` and
  contain no `GeomVol`, `Overlap`, `Fatal`, or `Exception`.

C1. Source-card provenance.

- Every fix5 prompt, buildup, delayed, and signal source card must use the fix5
  `.geo.setup`.
- The generated SIM files must confirm the same `Geometry` path in their header.
- Surrounding sphere / far-field normalization must be explicitly reported.
- Before any Cosima transport, emit `fix5_benchmarks.json` ->
  `required_artifacts.source_manifest` and prove it contains the fix5 setup, all
  source cards, source surface/far-field normalization, exposure/event ratios,
  seeds, and expected SIM outputs.
- Before any gate decision, emit `fix5_benchmarks.json` ->
  `required_artifacts.verification_verdict`; no blocking check may be non-PASS.
- Before any pass/fail comparison to old `new_geo_re`, emit
  `required_artifacts.benchmark_alignment` with `decision == ALIGNED`.

C1b. Delayed normalization closure (the historically buggy step).

- `runs/step02_delay_fix_<label>/normalization_audit_groundstate_fix.json`:
  `status == PASS`, `problems == []`, each family `rp_scaled_total ==
  rp_raw_total / division` (the missing division is the x8.0116 I-128 bug).
- Ground-state correction audited via `audit_groundstate_half_life_units.py`.
- M-sampling audit (`fix5_benchmarks.json` -> audit_thresholds):
  `parsed_pointsource_blocks == M`, `matched_back_to_exact_table_fraction == 1.0`,
  `manifest_flux_relative_delta == 0`, `missed_nuclides_total_activity_fraction
  <= 0.01`.
- fix5 adds tungsten: confirm W/collimator-origin delayed rows carry correct
  division and ground-state correction.

C2. 1/10 prompt gate.

- Report first: selected prompt event count (`N_eff`) and Poisson sigma.  The
  "uncertainty interval" is `PROMPT_total_1of10 +/- its Poisson sigma`.
- Provisional pass: use `fix5_benchmarks.json` ->
  `uncertainty_anchor.provisional_pass_formula`.  This requires benchmark
  alignment; otherwise the old `new_geo_re` number is report-only.
- Strong pass: `PROMPT_total_1of10 <= PROMPT_old_total_cps`.
- Inconclusive: use `uncertainty_anchor.inconclusive_if`; do not pass OR fail on
  noise -> escalate statistics.
- Hard fail: use `uncertainty_anchor.hard_fail_formula`; if it triggers, stop
  and report; do not spend 9/10.
- A 1/10 prompt rate with fewer than
  `uncertainty_anchor.min_prompt_selected_events_for_rate_claim` selected prompt
  events is a screen result only, not a publishable rate claim.

C3. 1/10 delayed gate.

- Loose (nearly vacuous): `DELAYED_total_1of10 < DELAYED_old_total_cps` (0.1515)
  only after benchmark alignment.  Without alignment it is report-only.
- Meaningful: compare against the current v3p5 W2 delayed (~0.0039 cps) and
  report the W/collimator activation subcomponent explicitly, since fix5 adds W.
- If 1/10 delayed exceeds current v3p5 delayed by more than its own 1 sigma,
  mark the screen YELLOW even if it passes the loose old-new_geo_re threshold.
- Also report delayed selected event count, sigma, normalization, activity
  inventory, dominant nuclides, W/collimator-origin activity/rate, and whether
  the delayed sample reaches
  `uncertainty_anchor.min_delayed_selected_events_for_meaningful_1of10_claim`.

C4. Full-stat promotion gate.

Only after C2 and C3 pass:

- Complete a clean full-stat fix5 production run by default.
- Append/merge is forbidden unless `fix5_benchmarks.json` -> `merge_policy` is
  fully satisfied and `fix5_merge_verdict.json` reports PASS.
- Do not merge incompatible source-card geometries, seeds, normalization rules,
  or delayed source inventories.

C5. Full closure gate.

Final success requires:

- prompt, delayed, and total W2 selected rates with uncertainties;
- prompt eplus decomposition;
- delayed isotope/material/source-position audit;
- signal replay through fix5 geometry and signal keep/rate;
- Step05, Step06, Step07, Step08 outputs regenerated for the fix5 label;
- comparison table against old `new_geo_re` and current v3p5;
- `fix5_benchmarks.json` -> `required_artifacts.promotion_decision` with the
  full-stat B, sigma, prompt, delayed, W activation, signal keep, `Z20d`, and
  `F3(20d)`;
- pass/fail interpretation using `fix5_benchmarks.json` ->
  `promotion_thresholds`: lower/equivalent total B vs v3p5, signal keep >= 0.95,
  `Z20d` held/improved, `F3(20d)` held/improved, and no unresolved delayed red
  flag;
- disclosure that fix5 is a user redesign mass model, not the minimal
  baseline-only prompt511 refix candidate.

## Stop Rules

- If any run uses the wrong geometry setup, invalidate that run and rerun.
- If `source_manifest` or `verification_verdict` is missing, do not start or
  gate the run.
- If the `new_geo_re` benchmark alignment is missing or not `ALIGNED`, do not
  use old `new_geo_re` for prompt/delayed pass/fail.
- If 1/10 prompt fails, do not run the remaining 9/10 without user approval.
- If the 1/10 screen is statistically inconclusive (C2), escalate statistics;
  do not record a pass or a fail.
- If delayed normalization is not auditable, do not claim delayed is lower.
- If append/merge lacks a PASS merge verdict, run clean full-stat instead.
- If full-stat results contradict the 1/10 decision, the full-stat result wins.
