# METHOD — what the fix5 closure actually computes (read before the gates)

This file is the methodology layer the other fix5 documents assumed but never
stated. AGENTS / GUIDE / CONSTRAINTS / PRE_PROMPT reference `Step05`, `Step06`,
`Step08`, and "delayed normalization" as *labels*. If you only read those, you
can satisfy the letter of the contract (produce a file named `Step06`) while
getting the physics normalization wrong — which is the exact failure the
contract claims to prevent. Read this so the gates mean something.

Numbers live in `core_md/fix5_benchmarks.json` (single authority). This file
explains the method; that file holds the values. The older project-memory chain
was archived under `old/docs/core_md_legacy/`; use it only for provenance, not
as a current fix5 gate.

## 1. The physics hypothesis fix5 is testing

The current selected 511 keV background is **prompt-dominated**: ~93.8% prompt,
and of the total selected background **86.28% is prompt e+ annihilation 511**
(`fix5_benchmarks.json` -> v3p5_current_authority). The documented root cause of
the prompt-511 head is the **side-port thin-aluminium dewar wall** producing
511 along the side line-of-sight (Still/4K/60K Al shields + Al vacuum jacket in
the side-port through-cut).

fix5 = the user `multiholeW` redesign: it puts **multi-hole tungsten** around
the side port to attenuate that side-entry 511 / its parent positrons.

The hypothesis under test: *multi-hole W lowers the side-port prompt e+ 511
reaching the detector.* The **risk** — and the reason the gate is shaped
"prompt must not blow up" — is that tungsten can pay it back as **W
self-background**:

- prompt W fluorescence / secondaries;
- delayed **W activation** under the cosmic-ray/neutron flux (W/collimator is
  already ~4% of the v3p5 delayed activity).

So the loop is really asking: *does the W side redesign cut prompt e+ 511 without
adding offsetting W self-emission?* (memory: "pending MC confirmation of W
self-emission"). The 1/10 screen is the cheap first look at that trade.

## 2. The pipeline you are validating (and where the money is)

Eleven conceptual steps; the ones the gates touch:

- **Step02 (transport, EXPENSIVE).** Two native Cosima streams on the EXPACS/PARMA
  atmospheric source cards: `instant` (prompt) and `buildup` (isotope
  production for delayed activation). Plus the focused Laue signal stream
  (Step04/Step09) and the delayed-source transport (Step03).
- **Step05 (detector response + time axis, EXPENSIVE-ish).** Parses the prompt,
  delayed, and focused SIMs through the detector selection, then puts the three
  streams on **one common Poisson time axis**: each stream draws its number of
  **equivalent events from its rate x interval**, every instance gets a random
  time over the observation interval, instances are sorted and grouped within
  `COINCIDENCE_WINDOW_S = 1.0e-6 s`, and only then are the active-shield
  (CsI 50 keV / BGO 70 keV) and custom Compton/FoV vetoes applied. This is the
  "first hour of day 15" combined signal+background you described.
- **Step06 (mission-time fold, CHEAP).** Analytic trajectory correction over
  **81 bins, day 0 -> 20, 0.25-day spacing**, EXPACS/PARMA-anchored rate
  reweighting with **no new transport**. Folds altitude-dependent atmospheric
  511 transmission + prompt/delayed driver scaling + per-nuclide delayed-activity
  ODEs, closing to the Step05 day-15 point. This is what turns the day-15
  baseline into the 20-day mission-mean.
- **Step07/Step08 (significance, CHEAP).** Fold source/background over Step06,
  apply the accidental live-time factor, produce `Z20d` (20-day cumulative
  significance), `T3` (time to 3 sigma), `F3(20d)` (20-day 3-sigma flux). This
  is the detection-potential projection.

**Cost model — gate at the right boundary.** Step02 transport + Step05 response
are the expensive parts; Step06/07/08 are cheap rate-level folds that depend on
Step05. The 1/10 screen exists to avoid paying full-stat Step02+Step05 before
knowing the geometry is in the right ballpark. Never regenerate Step06/07/08
from a Step05 that has not passed provenance + normalization.

## 3. The two normalizations (this is where the chain has historically broken)

**Prompt: `1/sum(TT)`.** Each prompt particle-family rate is normalized by the
sum of its transport TimeTags. Self-consistency of this sum is a Verifier check.

**Delayed: a specific recipe, not "make it auditable".** The chain is:

1. `buildup` activation production -> true `CC IP RP <vol> x y z ZA exc t`
   production positions (RPIP).
2. **Ground-state half-life correction** against archived NUBASE2020
   (`inputs/nubase/nubase_2020.txt`); audited by
   `code/tools/audit_groundstate_half_life_units.py`.
3. **Per-family TT division guard.** In
   `runs/step02_delay_fix_<label>/normalization_audit_groundstate_fix.json`,
   each particle-family row must have `division == its buildup file/rep count`
   (gamma in `auto` mode) and `rp_scaled_total == rp_raw_total / division`.
   A missing/incorrect division is the historical **I-128 x8.0116
   over-normalization** bug (multi-rep buildup counted ~8x).
4. **Fixed activity (Bq)**, then **exact-position M-sampling**: M equal-flux
   `PointSource` blocks drawn from the weighted RPIP table (no
   `RadialProfileBeam` compression for the current authority).
5. **Cosima delayed transport** -> Step05 replay.

The M-sampling must preserve the inventory. The historical v3p5 audit
(`m_sampling_audit_summary.json`, built by the archived
`old/stepwise_maintenance/step03_delay_source/code/build_m_sampling_audit_20260616.py`)
must show, per case (thresholds in `fix5_benchmarks.json` -> audit_thresholds):

- `parsed_pointsource_blocks == M`;
- `manifest_flux_relative_delta == 0`, `source_text_flux_relative_delta < 1e-6`;
- `matched_back_to_exact_table_fraction == 1.0`;
- `ambiguous_coordinate_key_fraction == 0.0`;
- `missed_nuclides_total_activity_fraction <= 0.01` (the v3p5 M=50000 case
  reaches `6.7e-4`).

**fix5 specifically:** because fix5 adds tungsten, confirm the W/collimator-origin
delayed rows carry the correct division and ground-state correction; this is the
most likely place a fix5 delayed claim goes wrong.

## 4. What the benchmark numbers actually mean

Do not gate on a bare point value. From `fix5_benchmarks.json`:

- **new_geo_re prompt 0.0323 cps is a coarse 1/10 screen target, not the
  promotion bar**, and it carries a caveat: HANDOFF records that old new_geo_re
  had lower hard-window prompt *partly because its side region was blocked by a
  solid side-shield/material column and because the source-surface normalization
  differed*. So part of 0.0323 is a coverage + normalization artifact. Before
  using it as a gate, **verify the benchmark's selection definition (window /
  veto / Compton-FoV / source-surface normalization) matches the fix5
  computation** — `selection_definition` is currently `UNVERIFIED`.  The proof
  is not prose: emit `fix5_benchmarks.json` ->
  `required_artifacts.benchmark_alignment` with `decision == ALIGNED`; otherwise
  old new_geo_re is report-only.
- **new_geo_re delayed 0.1515 cps is ~40x above the current v3p5 line-window
  delayed (~0.0039).** "delayed < 0.1515" is therefore nearly vacuous; the
  meaningful delayed comparison is against the current v3p5 ~0.0039 and the W
  activation subcomponent.
- **The real promotion decision at full statistics is against
  v3p5_current_authority** (B=0.0630, Z20d=6.13, F3(20d)=4.89e-5), not against
  new_geo_re.  A replacement claim requires
  `required_artifacts.promotion_decision` and must satisfy
  `promotion_thresholds`: lower/equivalent total B, no unresolved delayed/W
  activation red flag, signal keep, and held/improved Z20d/F3.

## 5. Uncertainty and why the 1/10 screen is delicate

The current full-stat authority's selected background is only **~132 events
(~87 prompt-stream, ~45 delayed)** -> Poisson sigma ~9-11%. A 1/10 screen has
~13/~9 selected events -> sigma ~28-34%. Consequences, enforced by the gates:

- always report `N_eff` (selected event counts) and Poisson sigma alongside any
  1/10 rate;
- a bare 1.25x prompt tolerance is **inside** the 1/10 noise — treat
  `|fix5 - target|` within the *combined* sigma as "consistent";
- if the 1/10 selected-event count is so small that sigma is comparable to the
  gap to the target, the screen is **inconclusive** -> escalate statistics, do
  not pass/fail on noise.

The gate formulas are intentionally stored in `fix5_benchmarks.json` ->
`uncertainty_anchor`, not in agent memory.  In short: a hard fail needs enough
prompt events, acceptable relative sigma, benchmark alignment, and the
one-sigma-lower fix5 prompt rate still above `1.25 x` the old new_geo_re target.
Below that support, the correct result is "inconclusive, add statistics".

## 6. Required artifacts and why they exist

The loop is only closed when its structured artifacts exist:

- `fix5_source_manifest.json` prevents the common failure where a directory is
  named `fix5` but the source card still points at baseline geometry.
- `fix5_benchmark_alignment.json` prevents apples-to-oranges comparison against
  old new_geo_re.
- `fix5_verification_verdict.json` makes the Verifier's blocking checks
  deterministic rather than narrative.
- `fix5_promotion_decision.json` separates a coarse 1/10 screen from the final
  replacement claim against current v3p5.
- `fix5_merge_verdict.json` is required for any append/merge route; without it,
  run clean full-stat.

## 7. Code / authority map

- Current-authority anchors + rebuild commands: `core_md/workflow.md`.
- Legacy method memory and handoffs: `old/docs/core_md_legacy/`.
- All numbers + gate thresholds + scripts: `core_md/fix5_benchmarks.json`.
- Validators / audits: see `fix5_benchmarks.json` -> scripts.

## 8. Known historical failure modes (recognize them in a fix5 result)

- **x8.0116 I-128 over-normalization** — missing per-family TT division in the
  delayed source. Guard: the normalization audit.
- **Native `.det` Trigger/Veto filtered buildup SIM storage** — under-recorded
  RPIP production positions (neutron rep stored ~2k instead of full). Guard: the
  `.det` reference check; do not re-add native trigger blocks unless asked.
- **Route B FWHM/sigma confusion** — treating Siegert `60/10.5 deg` as FWHM.
- **Promoting a `spot_r90` ROI sidecar as the prompt-suppression strategy /
  headline** — explicitly disallowed; the prompt fix is geometry (side-port
  closure), and the headline is the hard-window selected rate.
- **A directory named `fix5` whose source card / SIM header points at baseline
  geometry** — invalid run; the single most important provenance guard.
