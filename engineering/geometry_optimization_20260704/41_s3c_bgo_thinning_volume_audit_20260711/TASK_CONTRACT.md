# TASK CONTRACT — 41_s3c_bgo_thinning_volume_audit_20260711

Author: Claude (planner). Executor: Codex. Scope is fixed; the executor must not
renegotiate it. If an instruction is impossible, record the gap in README
`## Gaps` and continue with the rest — do not substitute a different method.

## Questions to answer (from the user, verbatim intent)

1. **BGO 可以薄一点吗？** Quantify, by direct event counting on the retained
   atm511 SIM, how much additional atmospheric-511 leak-through each thinning
   option admits, and what that does to estimated total background B and 20-day
   F3 under the frozen component budget.
2. **哪些体积可以节约掉？** Rank every shield volume (BGO side / bottom cap /
   top annulus, W shell, Al shell) by background interceptions per kg, and
   produce a mass-vs-performance Pareto table for the option list below.

## Hard constraints (non-negotiable)

- **READ-ONLY** on all retained products. New files ONLY under
  `engineering/geometry_optimization_20260704/41_s3c_bgo_thinning_volume_audit_20260711/`.
- **NO new transport.** Cosima/Geant4 launches are forbidden. This is a replay
  + geometry-arithmetic audit only. If an input is missing, write
  `MISSING_INPUT` in README and continue; do not simulate around it.
- Do not modify the 40_ package, the Knob0 brief, or any retained run dir.
- Claim ceiling = **screening**. Forbidden in conclusions: "publication-matched",
  "validated F3", "promoted". Recommendations may only *propose* updates to the
  40_ run matrix.
- Every headline number in README carries its source path (quote rule).

## Pinned inputs (all paths relative to repo root)

- Geometry (do not edit): `engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- atm511 matched-4pi 3M SIM (~1.1 GB gz, has IA records):
  `runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709/Atm511SidecarS3cBgoW2mmAl3mmShell3M.inc1.id1.sim.gz`
- Prompt e+/n SIMs (SHOULD-level input, see T3):
  `runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709/`
- Component budget + masses + delayed activity (do not recompute, cite):
  `engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/*.csv`,
  `.../data/s3c_mainline_analysis_summary.json`,
  `engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/*.json`
- Frozen reference numbers (from 40_; use as-is):
  B_dominant=0.00388355 cps (e+ 0.00135997, n 0.00135670, atm511 0.00116688),
  residual=0.00116743 cps, B_total_C0=0.00505 cps, F3_C0=1.35976e-5;
  LW1 historical: F3 +11.75% vs C0, delayed 31.308 Bq vs C0 57.824 Bq.
- Volume boxes for coordinate classification (from 29_ README; verify against
  geometry file, G1): BGO side shell r 21.20–25.20 cm, z −19.40..40.90;
  BGO bottom cap r 0–25.20, z −23.40..−19.40; BGO top annulus r 20.90–25.20,
  z 40.90..44.90; W shell side r 25.5–25.7 approx + Al (read exact W/Al extents
  from the geometry file and record them). ρ_BGO=7.13, ρ_W=19.3, ρ_Al=2.70 g/cm3.
  Retained masses to reproduce: BGO side 250.689 kg, bottom 56.898 kg,
  top 17.761 kg (29_ README table).

## Method

**Thinning convention: remove material from the OUTER face; all inner faces
stay fixed** (preserves cavity clearance and signal-replay invisibility).

### T1 — coupled-counting thinning replay (atm511, MUST)

Single pass over the 3M SIM. For each generated photon: INIT position +
direction; first energy-depositing interaction (COMP/PHOT/PAIR; count
RAYL-first events separately as a data-quality metric and treat the first
non-RAYL IA as "the" interaction using the straight INIT ray).

For each photon whose INIT ray intersects the inner cavity (cylinder r<21.20,
z −19.40..40.90, i.e. it would reach the cavity if never stopped):

- Compute, along the straight ray, the material column (path length × density,
  g/cm2) through each shield volume, in order: C_orig = total column before
  cavity entry; X = column from ray start to the first interaction point;
  for each option, C_removed = column through the removed outer slabs, and
  C_new = C_orig − C_removed.
- Common-random-numbers coupling (memoryless exponential free path):
  the photon reaches the cavity un-interacted under an option iff X > C_new.
  Events with no interaction before cavity entry (X undefined) leak under all
  options. **New leak(option) = #{vetoed events with C_orig − X < C_removed}.**
- Conservation identity (machine gate G2, per option):
  leak(option) = passthrough(C0) + new_leak(option), and
  new_leak(option) + still_vetoed(option) = vetoed(C0). Exact integer identity.
- Transmission ratio T(option)/T(C0) = leak(option)/leak(C0).
  Predicted atm511 W2 rate(option) = 0.00116688 × that ratio. State the
  assumption: per-cavity-reaching-photon W2 conversion probability is
  option-independent.
- Also histogram X in linear depth along the chord within the BGO side shell
  and fit exp(−μ_eff·d); report μ_eff (gate G3).

Method-limit caveats to print verbatim in README: (a) coupling drops secondary
particles that interactions in the removed slab would have produced (biases
leak LOW); (b) some newly leaked photons would scatter in remaining material
and miss W2 anyway (biases leak HIGH); (c) e+/n/residual components are held
flat at the frozen budget — thinning effects on them are NOT modeled here and
require the 40_ run-matrix screening transport.

### T2 — option table (MUST)

For each option: recompute panel masses analytically (cylindrical shells,
pre-relief, no window-cut correction beyond what reproduces the 29_ masses —
if the 29_ masses imply a window-cut deduction, apply the same deduction
consistently and say so). Then apply T1 counting. Options:

| ID | change (BGO mm side/bottom/top; shell) |
|----|-----------------------------------------|
| O1 | remove W only (calibration row, cf. LW1) |
| O2 | side 40→30 |
| O3 | side 40→20 |
| O4 | bottom 40→30 |
| O5 | bottom 40→20 |
| O6 | top annulus 40→10 |
| O7 | top annulus removed |
| O8 | side40/bottom30/top10, no W (=LW4) |
| O9 | side30/bottom30/top30, no W (=LW5) |
| O10 | side30/bottom30/top10, no W |

Columns: option, mass_kg, dmass_kg, atm511_T_ratio (with binomial CI from the
counted events), predicted_atm511_w2_cps, predicted_B_total_cps (other
components frozen), F3_scale = sqrt(B_new/0.00505), predicted_F3_20d
(=1.35976e-5 × F3_scale), delayed_note, caveats.

Delayed column rules: O1 rows may cite the measured W removal effect
(57.824→31.308 Bq family evidence, from 40_/38_); BGO thinning rows get
"BGO activation is self-vetoing; mass reduction is monotonically favorable;
not quantified here". Do NOT extrapolate Bq numbers for BGO thinning.

**Method calibration (G4):** the O1 coupled-count prediction for the atm511
component must be compared against the LW1 historical screen. LW1's +11.75%
F3 is a total-background number that also includes Al 3→8; state that, then
report the comparison ratio. If the O1-implied F3 shift and the historical
LW1 F3 shift disagree by more than ×3, add `METHOD_LOW_CONFIDENCE` to the
README status block (WARN, not FAIL).

### T3 — panel importance map (SHOULD, budget-capped)

One streaming pass over the prompt e+/n SIMs (if projected scan time > 15 min,
subsample whole files uniformly and record the fraction): per shield volume,
count first-interactions (active-veto/attenuation role proxy) for primaries
and their secondaries reaching the shield. Combine with the atm511 pass to
produce `panel_importance.csv`: volume, mass_kg, atm511 interceptions,
eplus interceptions, n interceptions, interceptions per kg. If the prompt scan
is infeasible, deliver the atm511-only version and record the gap.

## Machine gates (validator = pure function, no judgment calls)

- G1 (FAIL): analytic masses reproduce 29_ README BGO masses within 1%
  (250.689 / 56.898 / 17.761 kg) AND W/Al extents read from the geometry file.
- G2 (FAIL): T1 conservation identities hold exactly per option.
- G3 (WARN): fitted μ_eff(BGO, 511 keV) ∈ [0.80, 1.10] cm⁻¹; outside → add an
  investigation note before shipping.
- G4 (WARN): calibration row rule above.
- G5 (FAIL): `git status --porcelain` shows changes only under the 41_ dir.
- G6 (FAIL): README quote rule — headline numbers carry source paths; status
  line is the first non-title line.

## Deliverables

```
41_s3c_bgo_thinning_volume_audit_20260711/
  TASK_CONTRACT.md            (this file, unmodified)
  README.md                   (status line first; answers Q1/Q2 in <=1 screen;
                               option table; method limits verbatim; ## Gaps;
                               ## Non-claims)
  code/                       (analysis + validator, rerunnable)
  data/depth_profile.csv
  data/thinning_leak_table.csv        (per option: counted integers + ratios)
  data/panel_importance.csv
  data/pareto_options.csv             (the T2 table)
  data/summary.json                   (machine-readable: inputs, gates, options)
```

One PNG (depth profile + leak-vs-thickness) is welcome but optional. No HTML
report required.

## Convergence protocol

Phase A: implement + run analysis. Phase B: run validator; fix and re-run at
most **2** times. If a FAIL gate still fails, set status
`FAIL_S3C_THINNING_AUDIT_<gate>` with an honest gap list and stop — do not
loop further. Success status: `PASS_S3C_THINNING_VOLUME_AUDIT`.

## Non-claims (copy into README)

- Screening arithmetic on frozen budgets; NOT a full S3c prompt-family or
  Step05–08 closure; NOT structural qualification; no promotion decision.
- atm511 absolute normalization inherits the unresolved Harris-vs-4π-sidecar
  calibration; ratios reported here are internal to the 4π sidecar and do not
  resolve it.
- The 6-event W2 atm511 anchor carries ±41% (1σ) counting error which
  dominates every predicted_atm511_w2_cps; print this next to the table.
