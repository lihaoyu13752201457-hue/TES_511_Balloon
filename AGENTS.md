# AGENTS — repo entry pointer (auto-loaded each session)

## Active task: fix5 simulation closure

The active task is no longer to search for a minimally invasive prompt-511
geometry refix.  The geometry candidate is fixed:

`outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

Before doing ANY fix5 prompt/delayed/signal simulation work, an agent MUST:

1. **Understand the method first (what the gates actually compute)**:
   `core_md/METHOD_FIX5_SIM_CLOSURE.md`.  The gates below are meaningless
   without this; a run can satisfy the contract's letter (produce a file named
   `Step06`) while getting the physics normalization wrong.
2. **Read once (task guide / "what changed")**:
   `core_md/GUIDE_FIX5_SIM_CLOSURE_FOR_CODEX_20260621.md`
3. **Obey every loop (enforced contract / gates)**:
   `core_md/CONSTRAINTS_FIX5_SIM_CLOSURE.md`
4. **Use the startup checklist for fresh conversations**:
   `core_md/PRE_PROMPT_FIX5_SIM_CLOSURE_20260621.md`
5. **If starting a brand-new chat / handoff**, use:
   `core_md/PROMPT_NEW_CHAT_FIX5_SIM_CLOSURE_20260622.md`

All numbers (geometry paths, benchmarks, gate thresholds, audit thresholds,
validator scripts) come from one machine-readable authority:
`core_md/fix5_benchmarks.json`.  The markdown contracts reference its keys; do
not trust a number restated in prose if it disagrees with that file.

## Active objective

Use the fix5 geometry to run a staged validation:

1. Build fix5-specific source cards and prove every source/SIM header uses the
   fix5 `.geo.setup`.
2. Run a 1/10-statistics test relative to the current project chain.
3. Gate:
   - prompt total close to old `new_geo_re` prompt total
     `0.0323247092031 cps`, only after benchmark alignment confirms the old
     selection/normalization is comparable;
   - delayed total lower than old `new_geo_re` delayed total
     `0.151456825339 cps` as a loose screen, while also checking delayed and
     W/collimator activation against the current v3p5 delayed authority.
4. If the 1/10 gate passes, complete a clean full-stat closure by default and
   regenerate Step02--Step08 plus the fix5 signal replay.  Append/merge requires
   a PASS merge verdict.

## Non-negotiable for this task

- Do not optimize or redesign geometry unless the user explicitly reopens
  geometry design.
- Do not overwrite current v3p5, BGO, or old `new_geo_re` authority outputs.
- Any run whose source card or SIM header points to the wrong geometry is
  invalid.
- 1/10 is a go/no-go screen, not a final publication-level rate claim.
- The 1/10 screen target is old `new_geo_re` (a coarse "did W blow up prompt"
  check that carries a side-coverage + source-surface normalization caveat); the
  real full-stat promotion bar is the current v3p5 exact-position authority.  Do
  not conflate the two.  See `fix5_benchmarks.json` -> decision_bar.
- Required artifacts are defined in `fix5_benchmarks.json` ->
  `required_artifacts`: source manifest, benchmark alignment, verification
  verdict, and final promotion decision.  Missing blocking artifacts mean no
  gate decision.
- Full-stat results override the 1/10 prediction.
- Delayed claims require auditable activation/source normalization: the NUBASE
  ground-state correction + per-family TT division guard + M-sampling inventory
  audit (see `METHOD_FIX5_SIM_CLOSURE.md` section 3), not just "looks reasonable".

## Historical documents

The previous Claude prompt-511 geometry-refix loop is retained for provenance:

- `core_md/GUIDE_PROMPT511_REFIX_FOR_CODEX_20260620.md`
- `core_md/CONSTRAINTS_PROMPT511.md`
- `core_md/PRE_PROMPT_CODEX_PROMPT511.md`

Those documents describe the baseline-only passive-shield optimization route.
They are not the active pass/fail contract for the fix5 replacement simulation
closure.
